import os
from main import app
from models import db, User

def create_admin():
    username = os.getenv("DB_USERNAME", "admin")
    password = os.getenv("DB_PASSWORD", "changeme")

    with app.app_context():
        if User.query.filter_by(username=username).first() is None:
            admin = User(username=username)
            admin.set_password(password)
            db.session.add(admin)
            db.session.commit()
            print(f"Admin user '{username}' created")
        else:
            print(f"Admin user '{username}' already exists")

if __name__ == "__main__":
    create_admin()