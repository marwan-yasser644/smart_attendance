import os
import sqlite3

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from .config import Config


db = SQLAlchemy()


def migrate_sqlite_schema(app: Flask) -> None:
    """Rebuild SQLite if the schema is outdated (missing new columns from model updates)."""
    uri = app.config['SQLALCHEMY_DATABASE_URI']
    if not uri.startswith('sqlite:///'):
        return

    db_path = uri.replace('sqlite:///', '', 1)
    if not os.path.exists(db_path):
        return

    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Check if the new columns exist on attendance_sessions
        cur.execute('PRAGMA table_info(attendance_sessions)')
        columns = {row[1] for row in cur.fetchall()}
        
        # Check if the new Course, Lecture, Section, Student tables exist
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='courses'")
        has_courses = cur.fetchone() is not None
        
        conn.close()
        
        # If missing new columns or tables, rebuild the database
        if 'course_id' not in columns or not has_courses:
            os.remove(db_path)
            print(f'ℹ️ Rebuilt SQLite schema at {db_path} to add new production models (Course, Lecture, Section, Student).')
    except sqlite3.Error:
        return


def seed_demo_lecturer(app: Flask) -> None:
    with app.app_context():
        from .models import Lecturer

        if not Lecturer.query.first():
            demo = Lecturer(name='Dr. Ahmed Hassan', email='admin@kfu.edu.eg', role='admin')
            demo.set_password('admin123')
            db.session.add(demo)
            db.session.commit()
            print('✅ Demo lecturer created: admin@kfu.edu.eg / admin123')


def create_app(config_object: type[Config] | None = None) -> Flask:
    base_dir = os.path.dirname(os.path.dirname(__file__))
    app = Flask(
        __name__,
        template_folder=os.path.join(base_dir, 'templates'),
        static_folder=os.path.join(base_dir, 'static'),
    )
    app.config.from_object(config_object or Config)

    db.init_app(app)

    from .routes.main import main_bp

    app.register_blueprint(main_bp)

    with app.app_context():
        migrate_sqlite_schema(app)
        db.create_all()
        seed_demo_lecturer(app)

    return app


app = create_app()


def init_db() -> None:
    with app.app_context():
        migrate_sqlite_schema(app)
        db.create_all()
        seed_demo_lecturer(app)
