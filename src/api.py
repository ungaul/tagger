import os
import io
import base64
import time
from datetime import datetime
from PIL import Image

from dateutil import parser
from mutagen import File
from mutagen.mp3 import MP3
from mutagen.flac import FLAC, Picture
from mutagen.mp4 import MP4, MP4Cover
from mutagen.id3 import (ID3, APIC, error as ID3Error, TPE1, TPE2, TIT2, TALB, TDRC, TCON, TKEY, TRCK, TXXX, ID3NoHeaderError)
from sqlalchemy import or_

from data import METADATA_KEYS, ALLOWED_EXTENSIONS, MUSIC_FOLDER, PAGE_SIZE
from models import db, MusicFile

_last_scan_time = 0
SCAN_INTERVAL_SECONDS = 60

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

    cover_base_64 = data.pop('cover_base_64', None)
    if cover_base_64:
        try:
            image_bytes = base64.b64decode(cover_base_64)
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
            meta = {**{k: str(v) for k,v in audio.tags.items()}, 'cover_base_64': meta_cover}
            return meta
        except Exception as e:
            print(f"Error encoding cover: {e}")
            meta = {k: str(v) for k,v in audio.tags.items()}
            meta['cover_base_64'] = None
            return meta
    else:
        print("No cover found")
        meta = {k: str(v) for k,v in audio.tags.items()}
        meta['cover_base_64'] = None
        return meta

def filter_and_sort_music_files(query, sort_by, sort_order, offset):
    q = MusicFile.query

    if query:
        query_like = f"%{query}%"
        filters = []
        for keys in METADATA_KEYS.values():
            for key in keys:
                if hasattr(MusicFile, key):
                    filters.append(getattr(MusicFile, key).ilike(query_like))
        if filters:
            q = q.filter(or_(*filters))

    if sort_by and hasattr(MusicFile, sort_by):
        col = getattr(MusicFile, sort_by)
        col = col.desc() if sort_order == 'desc' else col.asc()
        q = q.order_by(col)
    else:
        q = q.order_by(MusicFile.filename.asc())

    total = q.count()
    items = q.offset(offset).limit(PAGE_SIZE).all()

    musics = []
    for mf in items:
        meta = {c.name: getattr(mf, c.name) for c in MusicFile.__table__.columns}
        musics.append({'filename': mf.filename, 'metadata': meta})

    more = (offset + PAGE_SIZE) < total
    return {'musics': musics, 'more': more}

def get_music_metadata(filename):
    mf = MusicFile.query.filter_by(filename=filename).first()
    if not mf:
        return None, {"error": "File not found"}, 404
    meta = {c.name: getattr(mf, c.name) for c in MusicFile.__table__.columns}
    return {"filename": filename, "metadata": meta}, None, 200

def update_music_metadata(filename, data):
    mf = MusicFile.query.filter_by(filename=filename).first()
    if not mf:
        return {"error": "File not found"}, 404

    filepath = os.path.join(MUSIC_FOLDER, filename)
    success = set_metadata(filepath, data)
    if not success:
        return {"error": "Failed to save metadata"}, 500

    modified_date = data.get("modified_date")
    if modified_date:
        try:
            if isinstance(modified_date, str):
                dt = parser.parse(modified_date)
            elif isinstance(modified_date, datetime):
                dt = modified_date
            else:
                dt = None
            if dt:
                ts = dt.timestamp()
                os.utime(filepath, (ts, ts))
        except Exception as e:
            print(f"Failed to set mtime during update for {filename}: {e}")

    for key, val in data.items():
        if hasattr(mf, key):
            setattr(mf, key, val)

    new_name = data.get('new_filename')
    if new_name:
        new_path = os.path.join(MUSIC_FOLDER, new_name)
        if os.path.exists(new_path):
            return {"error": "New filename already exists"}, 400
        try:
            os.rename(filepath, new_path)
            mf.filename = new_name
        except Exception as e:
            return {"error": f"Failed to rename file: {str(e)}"}, 500

    db.session.commit()
    return {"success": True, "filename": mf.filename}, 200

def delete_music_file(filename):
    if not filename:
        return {"error": "Missing filename"}, 400
    if not allowed_file(filename):
        return {"error": "File type not supported"}, 400

    filepath = os.path.join(MUSIC_FOLDER, filename)
    mf = MusicFile.query.filter_by(filename=filename).first()
    if not mf or not os.path.isfile(filepath):
        return {"error": "File not found"}, 404

    try:
        os.remove(filepath)
        db.session.delete(mf)
        db.session.commit()
        return {"success": True, "filename": filename}, 200
    except Exception as e:
        return {"error": str(e)}, 500
    
def extract_value(meta, keys):
    for key in keys:
        val = meta.get(key)
        if val:
            if isinstance(val, list):
                if len(val) > 0 and val[0].strip() != "":
                    return val[0]
            elif isinstance(val, str):
                if val.strip() != "":
                    return val
            else:
                return val
    return None

import base64

def get_cover_bytes(filepath):
    ext = filepath.lower().rsplit('.', 1)[-1]
    try:
        if ext == 'mp3':
            try:
                id3 = ID3(filepath)
            except ID3NoHeaderError:
                return None
            for tag in id3.values():
                if isinstance(tag, APIC):
                    return tag.data
        elif ext == 'flac':
            audio_flac = FLAC(filepath)
            if audio_flac.pictures:
                return audio_flac.pictures[0].data
        elif ext in ('m4a', 'mp4'):
            audio_mp4 = MP4(filepath)
            covers = audio_mp4.tags.get('covr')
            if covers:
                return covers[0]
    except Exception as e:
        print(f"Error reading cover from {filepath}: {e}")
    return None

def extract_value(meta, keys):
    for key in keys:
        val = meta.get(key)
        if val:
            if isinstance(val, list):
                if len(val) > 0 and str(val[0]).strip() != "":
                    return val[0]
            elif isinstance(val, str):
                if val.strip() != "":
                    return val
            else:
                return val
    return None

def scan_and_sync(app):
    with app.app_context():
        disk_files = [f for f in os.listdir(MUSIC_FOLDER) if allowed_file(f)]
        db_files = {mf.filename: mf for mf in MusicFile.query.all()}
        for filename in list(db_files.keys()):
            if filename not in disk_files:
                db.session.delete(db_files[filename])
        db.session.commit()

        db.session.expire_all()
        db_files = {mf.filename: mf for mf in MusicFile.query.all()}

        for filename in disk_files:
            filepath = os.path.join(MUSIC_FOLDER, filename)
            stat = os.stat(filepath)
            mtime = datetime.fromtimestamp(stat.st_mtime)

            mf = db_files.get(filename)
            if mf:
                db_mod_date = mf.modified_date if hasattr(mf, 'modified_date') else None
                if db_mod_date and isinstance(db_mod_date, datetime):
                    if db_mod_date >= mtime:
                        continue
                elif mf.updated_at and mf.updated_at >= mtime:
                    continue

            meta = get_all_metadata(filepath)

            data = {}
            for field, keys in METADATA_KEYS.items():
                if field == "filename":
                    data[field] = filename
                elif field == "cover_base_64":
                    cover_bytes = get_cover_bytes(filepath)
                    if cover_bytes:
                        data[field] = base64.b64encode(cover_bytes).decode("utf-8")
                    else:
                        data[field] = None
                else:
                    data[field] = extract_value(meta, keys)

            data["modified_date"] = mtime

            if mf is None:
                mf = MusicFile(filename=filename)
                db.session.add(mf)

            for k, v in data.items():
                setattr(mf, k, v)

            mf.updated_at = datetime.utcnow()

        db.session.commit()
def conditional_scan(app):
    global _last_scan_time
    now = time.time()
    if now - _last_scan_time > SCAN_INTERVAL_SECONDS:
        scan_and_sync(app)
        _last_scan_time = now