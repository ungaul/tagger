import os
from flask_migrate import Migrate
from flask import Flask, jsonify, request, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

from models import db, User
from api import filter_and_sort_music_files, get_music_metadata, update_music_metadata, delete_music_file, scan_and_sync, conditional_scan
from data import METADATA_KEYS

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////app/data/data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key')

db.init_app(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

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

@app.route('/api/tags')
@login_required
def get_metadata_keys():
    return jsonify(METADATA_KEYS)

@app.route('/api/music')
@login_required
def api_list_music():
    try:
        offset = int(request.args.get('offset', '0'))
    except ValueError:
        offset = 0

    query = request.args.get('q', '')
    sort_by = request.args.get('sort_by', 'title').lower().strip()
    sort_order = request.args.get('sort_order', 'asc').lower().strip()

    conditional_scan(app)
    result = filter_and_sort_music_files(query, sort_by, sort_order, offset)
    return jsonify(result)

@app.route('/api/music/<path:filename>', methods=['GET', 'POST'])
@login_required
def api_song(filename):
    if request.method == 'GET':
        data, error, status = get_music_metadata(filename)
        if error:
            return jsonify(error), status
        return jsonify(data)

    data_req = request.json or {}
    data, status = update_music_metadata(filename, data_req)
    if status != 200:
        return jsonify(data), status
    return jsonify(data)

@app.route('/api/music/delete', methods=['POST'])
@login_required
def api_delete_music():
    data = request.json or {}
    filename = data.get('filename')
    response, status = delete_music_file(filename)
    return jsonify(response), status

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return jsonify({"success": True})

def create_admin():
    username = os.getenv("DB_USERNAME", "admin")
    password = os.getenv("DB_PASSWORD", "changeme")

    with app.app_context():
        admin = User.query.filter_by(username=username).first()
        if not admin:
            admin = User(username=username)
            admin.set_password(password)
            db.session.add(admin)
            try:
                db.session.commit()
                print(f"Admin user '{username}' created")
            except Exception as e:
                db.session.rollback()
                print(f"Error creating admin user: {e}")
        else:
            print(f"Admin user '{username}' already exists")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5013, debug=True)