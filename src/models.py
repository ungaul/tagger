from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()
    
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
class MusicFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(512), unique=True, nullable=False)

    title = db.Column(db.String(256))
    artist = db.Column(db.String(256))
    album = db.Column(db.String(256))
    tsrc = db.Column(db.String(64))
    publisher = db.Column(db.String(256))
    producers = db.Column(db.String(256))
    year = db.Column(db.String(32))
    genre = db.Column(db.String(128))
    track = db.Column(db.String(32))
    bpm = db.Column(db.String(16))
    key = db.Column(db.String(16))
    length = db.Column(db.String(32))
    label = db.Column(db.String(256))

    musicbrainz_artist_id = db.Column(db.String(64))
    musicbrainz_album_id = db.Column(db.String(64))
    spotify_url = db.Column(db.String(512))
    barcode = db.Column(db.String(64))
    catalog_number = db.Column(db.String(64))
    asin = db.Column(db.String(64))
    media_type = db.Column(db.String(64))
    musicbrainz_album_release_country = db.Column(db.String(8))
    musicbrainz_album_status = db.Column(db.String(32))
    musicbrainz_album_type = db.Column(db.String(32))
    musicbrainz_album_artist_id = db.Column(db.String(64))
    musicbrainz_release_group_id = db.Column(db.String(64))
    musicbrainz_release_track_id = db.Column(db.String(64))

    script = db.Column(db.String(16))
    ufid = db.Column(db.String(128))

    comment = db.Column(db.Text)
    description = db.Column(db.Text)
    likes = db.Column(db.Integer)
    dislikes = db.Column(db.Integer)
    software = db.Column(db.String(128))
    views = db.Column(db.Integer)
    rating = db.Column(db.String(16))
    download_date = db.Column(db.String(64))
    uploader = db.Column(db.String(128))
    purl = db.Column(db.String(512))
    synopsis = db.Column(db.Text)
    modified_date = db.Column(db.Text)
    acoustid_id = db.Column(db.String(64))
    copyright = db.Column(db.String(256))
    involved_people = db.Column(db.Text)
    lyrics = db.Column(db.Text)
    cover_base_64 = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<MusicFile {self.filename}>"