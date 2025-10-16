import os
import io
import base64

from flask import Flask, jsonify, request
from PIL import Image

from mutagen import File
from mutagen.mp3 import MP3
from mutagen.flac import FLAC, Picture
from mutagen.mp4 import MP4, MP4Cover
from mutagen.id3 import (
    ID3, APIC, error as ID3Error, TPE1, TPE2, TIT2, TALB, TDRC, TCON, TKEY, TRCK, TXXX, ID3NoHeaderError
)

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from models import db, User
from flask_login import LoginManager
from flask import render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////app/data/data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key')

db.init_app(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

from models import User

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

MUSIC_FOLDER = '/app/musics'
PAGE_SIZE = 25
ALLOWED_EXTENSIONS = ('.mp3', '.flac', '.m4a', '.mp4', '.ogg', '.wav')

def allowed_file(filename):
    return filename.lower().endswith(ALLOWED_EXTENSIONS)

def embed_cover_mp3(id3, image_data):
    id3.delall('APIC')
    id3.add(
        APIC(
            encoding=3,
            mime='image/jpeg',
            type=3,
            desc='Cover',
            data=image_data
        )
    )

def embed_cover_flac(audio, image_data):
    audio.clear_pictures()
    pic = Picture()
    pic.data = image_data
    pic.type = 3
    pic.mime = 'image/jpeg'
    audio.add_picture(pic)

def embed_cover_mp4(audio, image_data):
    audio.tags['covr'] = [MP4Cover(image_data, imageformat=MP4Cover.FORMAT_JPEG)]

def set_metadata(filepath, data):
    if not os.access(filepath, os.W_OK):
        print(f"Permission denied: cannot write to file {filepath}")
        return False
    audio = File(filepath, easy=False)
    if not audio:
        return False

    cover_b64 = data.pop('cover_base64', None)
    if cover_b64:
        try:
            image_bytes = base64.b64decode(cover_b64)
            img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG')
            image_bytes = img_byte_arr.getvalue()
        except Exception:
            return False

        ext = filepath.lower().rsplit('.', 1)[-1]
        try:
            if isinstance(audio, MP3) or ext == 'mp3':
                id3 = ID3(filepath)
                embed_cover_mp3(id3, image_bytes)
                id3.save(filepath)
            elif isinstance(audio, FLAC) or ext == 'flac':
                embed_cover_flac(audio, image_bytes)
                audio.save()
            elif isinstance(audio, MP4) or ext in ('m4a', 'mp4'):
                embed_cover_mp4(audio, image_bytes)
                audio.save()
        except Exception:
            return False

    if isinstance(audio, MP3):
        try:
            id3 = ID3(filepath)
        except ID3Error:
            id3 = ID3()

        key_map = {
            "artist": TPE1,
            "album_artist": TPE2,
            "title": TIT2,
            "album": TALB,
            "year": TDRC,
            "genre": TCON,
            "key": TKEY,
            "track": TRCK,
        }

        for frame in list(id3.keys()):
            if frame in [frame_.__name__ for frame_ in key_map.values()] or frame == 'TXXX':
                id3.delall(frame)

        handled = set(key_map.keys())

        for key, frame_class in key_map.items():
            if key in data and data[key]:
                id3.add(frame_class(encoding=3, text=str(data[key])))

        for k, v in data.items():
            if k in handled or not v:
                continue
            id3.add(TXXX(encoding=3, desc=k, text=str(v)))

        id3.save(filepath)
        return True

    elif isinstance(audio, FLAC):
        for k, v in data.items():
            if v in (None, ''):
                if k in audio.tags:
                    del audio.tags[k]
            else:
                audio.tags[k] = str(v)
        audio.save()
        return True

    elif isinstance(audio, MP4):
        tag_map = {
            'title': '\xa9nam',
            'artist': '\xa9ART',
            'album': '\xa9alb',
            'year': '\xa9day',
            'genre': '\xa9gen',
            'comment': '\xa9cmt',
        }
        for k, v in data.items():
            tk = tag_map.get(k.lower())
            if not tk:
                continue
            if v in (None, ''):
                if tk in audio.tags:
                    del audio.tags[tk]
            else:
                audio.tags[tk] = [str(v)]
        audio.save()
        return True

    else:
        audio = File(filepath, easy=True)
        if not audio:
            return False
        for k, v in data.items():
            if v in (None, ''):
                if k in audio:
                    del audio[k]
            else:
                audio[k] = str(v)
        audio.save()
        return True

def get_all_metadata(filepath):
    audio = File(filepath, easy=False)
    if not audio or not audio.tags:
        print("No audio or tags found")
        return {}

    cover_data = None
    try:
        ext = filepath.lower().rsplit('.', 1)[-1]
        if ext == 'mp3':
            try:
                id3 = ID3(filepath)
            except ID3NoHeaderError:
                print("ID3 header error")
                id3 = None
            if id3:
                for tag in id3.values():
                    if isinstance(tag, APIC) and tag.type in (0, 3):
                        cover_data = tag.data
                        break

        elif ext == 'flac':
            audio_flac = FLAC(filepath)
            if audio_flac.pictures:
                cover_data = audio_flac.pictures[0].data

        elif ext in ('m4a', 'mp4'):
            audio_mp4 = MP4(filepath)
            covers = audio_mp4.tags.get('covr')
            if covers:
                cover_data = covers[0]

    except Exception as e:
        print(f"Error reading cover: {e}")
        cover_data = None

    if cover_data:
        try:
            meta_cover = base64.b64encode(cover_data).decode('utf-8')
            meta = {**{k: str(v) for k,v in audio.tags.items()}, 'cover_base64': meta_cover}
            return meta
        except Exception as e:
            print(f"Error encoding cover: {e}")
            meta = {k: str(v) for k,v in audio.tags.items()}
            meta['cover_base64'] = None
            return meta
    else:
        print("No cover found")
        meta = {k: str(v) for k,v in audio.tags.items()}
        meta['cover_base64'] = None
        return meta

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        user = User.query.filter_by(username=username).first()
        if user is None or not user.check_password(password):
            return jsonify({"error": "Invalid username or password"}), 401
        login_user(user)
        return jsonify({"success": True})
    else:
        return jsonify({"error": "POST required"}), 405

@app.route('/api/music')
@login_required
def api_list_music():
    try:
        offset = int(request.args.get('offset', '0'))
    except ValueError:
        offset = 0

    query = request.args.get('q', '').lower().strip()
    sort_by = request.args.get('sort_by', 'title').lower().strip()
    sort_order = request.args.get('sort_order', 'asc').lower().strip()
    all_files = sorted(f for f in os.listdir(MUSIC_FOLDER) if allowed_file(f))
    if query:
        filtered = []
        for f in all_files:
            path = os.path.join(MUSIC_FOLDER, f)
            meta = get_all_metadata(path)

            search_keys = {
                'title': ['TIT2', 'title', 'TXXX:title', 'TXXX:©nam'],
                'artist': ['TPE1', 'TPE2', 'artist', 'TXXX:artist', 'TXXX:ARTISTS', 'TSO2', 'TSOP'],
                'album': ['TALB', 'album', 'TXXX:album', 'TXXX:©alb'],
                'genre': ['TCON', 'genre', 'TXXX:genre', 'TXXX:©gen'],
            }

            texts = []
            for keys in search_keys.values():
                for key in keys:
                    val = meta.get(key)
                    if val:
                        if isinstance(val, list):
                            texts.extend([str(v).lower() for v in val])
                        else:
                            texts.append(str(val).lower())

            if any(query in t for t in texts):
                filtered.append(f)

        all_files = filtered

    def extract_sort_key(filename):
        path = os.path.join(MUSIC_FOLDER, filename)
        meta = get_all_metadata(path)

        key_map = {
            'title': ['TIT2', 'title', 'TXXX:title', 'TXXX:©nam'],
            'artist': ['TPE1', 'artist', 'TXXX:artist', 'TXXX:ARTISTS'],
            'album': ['TALB', 'album', 'TXXX:album', 'TXXX:©alb'],
            'year': ['TDRC', 'year', 'TXXX:originalyear'],
        }

        keys = key_map.get(sort_by, [])
        for k in keys:
            v = meta.get(k)
            if v:
                if isinstance(v, list):
                    return str(v[0]).lower()
                else:
                    return str(v).lower()
        return ""

    reverse = (sort_order == 'desc')
    all_files.sort(key=extract_sort_key, reverse=reverse)

    chunk = all_files[offset:offset + PAGE_SIZE]
    items = []
    for filename in chunk:
        path = os.path.join(MUSIC_FOLDER, filename)
        meta = get_all_metadata(path)
        items.append({'filename': filename, 'metadata': meta})

    more = len(all_files) > offset + PAGE_SIZE
    return jsonify({'musics': items, 'more': more})

@app.route('/api/music/<path:filename>', methods=['GET', 'POST'])
@login_required
def api_song(filename):
    filepath = os.path.join(MUSIC_FOLDER, filename)
    if not os.path.isfile(filepath) or not allowed_file(filename):
        return jsonify({"error": "File not found"}), 404

    if request.method == 'GET':
        meta = get_all_metadata(filepath)
        return jsonify({"filename": filename, "metadata": meta})

    data = request.json or {}
    success = set_metadata(filepath, data)
    if not success:
        return jsonify({"error": "Failed to save metadata"}), 500

    new_name = data.get('new_filename')
    if new_name:
        new_path = os.path.join(MUSIC_FOLDER, new_name)
        if os.path.exists(new_path):
            return jsonify({"error": "New filename already exists"}), 400
        try:
            os.rename(filepath, new_path)
            filename = new_name
        except Exception as e:
            return jsonify({"error": f"Failed to rename file: {str(e)}"}), 500

    return jsonify({"success": True, "filename": filename})

@app.route('/api/music/delete', methods=['POST'])
@login_required
def api_delete_music():
    data = request.json or {}
    filename = data.get('filename')
    if not filename:
        return jsonify({"error": "Missing filename"}), 400

    if not allowed_file(filename):
        return jsonify({"error": "File type not supported"}), 400

    filepath = os.path.join(MUSIC_FOLDER, filename)
    if not os.path.isfile(filepath):
        return jsonify({"error": "File not found"}), 404

    try:
        os.remove(filepath)
        return jsonify({"success": True, "filename": filename})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5013, debug=True)