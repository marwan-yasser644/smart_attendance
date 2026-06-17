import os
import sqlite3

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

from .config import Config


db = SQLAlchemy()
csrf = CSRFProtect()


def migrate_sqlite_schema(app: Flask) -> None:
    """Keep a local SQLite database compatible with the current models.

    Two concerns are handled here:
      1. The newer production models (Course/Lecture/Section/Student and the
         extra columns on attendance_sessions) — if missing, the dev SQLite file
         is rebuilt from scratch (dev-only convenience, never runs on Postgres).
      2. The RBAC columns on `lecturers` (username, is_active,
         must_change_password) — these are added in place with ALTER TABLE so no
         user data is lost, and any legacy role strings are normalised.
    """
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

        # If missing new columns or tables, rebuild the database
        if 'course_id' not in columns or not has_courses:
            conn.close()
            os.remove(db_path)
            print(f'ℹ️ Rebuilt SQLite schema at {db_path} to add new production models (Course, Lecture, Section, Student).')
            return

        # ── Add RBAC columns to lecturers in place (preserve existing rows) ──
        cur.execute('PRAGMA table_info(lecturers)')
        lect_cols = {row[1] for row in cur.fetchall()}
        if 'username' not in lect_cols:
            cur.execute('ALTER TABLE lecturers ADD COLUMN username VARCHAR(80)')
        if 'is_active' not in lect_cols:
            cur.execute("ALTER TABLE lecturers ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1")
        if 'must_change_password' not in lect_cols:
            cur.execute("ALTER TABLE lecturers ADD COLUMN must_change_password BOOLEAN NOT NULL DEFAULT 0")
        # Normalise any legacy role values to the canonical two-role set.
        cur.execute("UPDATE lecturers SET role='DEAN' WHERE lower(role) IN ('admin','dean')")
        cur.execute("UPDATE lecturers SET role='TA' WHERE role IS NULL OR role NOT IN ('DEAN','TA')")
        conn.commit()
        conn.close()
    except sqlite3.Error:
        return


def seed_demo_lecturer(app: Flask) -> None:
    """Seed a first DEAN account on an empty database (dev convenience).

    In production the first DEAN is created manually in Neon (see
    docs/RBAC_SETUP.md); this seed only fires when the table is empty."""
    with app.app_context():
        from .models import ROLE_DEAN, Lecturer

        if not Lecturer.query.first():
            demo = Lecturer(
                name='Dr. Ahmed Hassan',
                email='admin@kfu.edu.eg',
                username='dean',
                role=ROLE_DEAN,
                is_active=True,
                must_change_password=False,
            )
            demo.set_password('admin123')
            db.session.add(demo)
            db.session.commit()
            print('✅ Demo DEAN created: admin@kfu.edu.eg / admin123')


def register_error_handlers(app: Flask) -> None:
    from flask import render_template

    @app.errorhandler(403)
    def forbidden(_e):
        return render_template('errors/403.html'), 403


def create_app(config_object: type[Config] | None = None) -> Flask:
    base_dir = os.path.dirname(os.path.dirname(__file__))
    app = Flask(
        __name__,
        template_folder=os.path.join(base_dir, 'templates'),
        static_folder=os.path.join(base_dir, 'static'),
    )
    app.config.from_object(config_object or Config)

    db.init_app(app)
    csrf.init_app(app)

    from .routes.main import main_bp

    app.register_blueprint(main_bp)

    register_error_handlers(app)

    with app.app_context():
        try:
            migrate_sqlite_schema(app)
            db.create_all()
            seed_demo_lecturer(app)
        except Exception as e:
            # Log but don't crash in production - database may be unavailable initially
            if app.config.get('FLASK_ENV') != 'production':
                raise
            app.logger.error(f"Database initialization warning: {e}")

    return app


app = create_app()


def init_db() -> None:
    with app.app_context():
        migrate_sqlite_schema(app)
        db.create_all()
        seed_demo_lecturer(app)
