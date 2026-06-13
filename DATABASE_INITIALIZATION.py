"""
DATABASE INITIALIZATION GUIDE
Complete setup for Smart Attendance Web Application
"""

# =============================================================================
# PART 1: AUTOMATIC INITIALIZATION (Current Implementation)
# =============================================================================

"""
Your app/__init__.py already handles automatic initialization:

    def create_app(config_object: type[Config] | None = None) -> Flask:
        app = Flask(...)
        app.config.from_object(config_object or Config)
        
        # Initialize SQLAlchemy ORM
        db.init_app(app)
        
        # Register blueprints
        app.register_blueprint(main_bp)
        
        with app.app_context():
            # Auto-create tables from models
            db.create_all()
            
            # Migrate SQLite schema if needed
            migrate_sqlite_schema(app)
            
            # Seed demo data
            seed_demo_lecturer(app)
        
        return app

FLOW:
    run.py (or app start)
        ↓
    init_db() called
        ↓
    create_app() executes
        ↓
    db.init_app(app)
        ↓
    db.create_all() [creates all tables]
        ↓
    migrate_sqlite_schema() [updates schema if needed]
        ↓
    seed_demo_lecturer() [creates admin account]
        ↓
    ✅ Database ready!
"""


# =============================================================================
# PART 2: MANUAL INITIALIZATION (For Flask CLI / Management)
# =============================================================================

"""
Add these to a new file: app/cli_commands.py
"""

from flask import Flask
from app import db
from app.models import Student, Course, Lecture, Section, Lecturer

def register_db_commands(app: Flask):
    """Register database management CLI commands."""
    
    @app.cli.command()
    def init_db():
        """Initialize the database - create all tables."""
        db.create_all()
        print('✅ Database initialized - all tables created')
    
    @app.cli.command()
    def drop_db():
        """Drop all database tables - WARNING: destroys all data!"""
        if input('⚠️ Delete ALL data? Type "yes" to confirm: ') == 'yes':
            db.drop_all()
            print('✅ Database dropped')
        else:
            print('❌ Cancelled')
    
    @app.cli.command()
    def reset_db():
        """Reset database - drop all and reinitialize."""
        if input('⚠️ Reset database? Type "yes" to confirm: ') == 'yes':
            db.drop_all()
            db.create_all()
            print('✅ Database reset')
        else:
            print('❌ Cancelled')
    
    @app.cli.command()
    def seed_demo_data():
        """Seed demo data for testing."""
        with app.app_context():
            # Create demo lecturer
            lecturer = Lecturer(
                name='Dr. Test Lecturer',
                email='lecturer@college.edu',
                role='lecturer'
            )
            lecturer.set_password('password123')
            
            # Create demo course
            course = Course(
                code='CS101',
                title='Introduction to Computer Science',
                lecturer_id=1
            )
            
            # Create demo lecture
            lecture = Lecture(
                title='Lecture 1: Basics',
                course_id=1,
                lecturer_id=1
            )
            
            # Create demo section
            section = Section(
                name='Section A',
                lecture_id=1,
                capacity=30
            )
            
            # Create demo students
            students = [
                Student(
                    student_id='DEMO001',
                    full_name='Demo Student 1',
                    email='student1@college.edu',
                    section_id=1
                ),
                Student(
                    student_id='DEMO002',
                    full_name='Demo Student 2',
                    email='student2@college.edu',
                    section_id=1
                ),
                Student(
                    student_id='DEMO003',
                    full_name='Demo Student 3',
                    email='student3@college.edu',
                    section_id=1
                ),
            ]
            
            db.session.add_all([lecturer, course, lecture, section] + students)
            db.session.commit()
            print('✅ Demo data seeded')
    
    @app.cli.command()
    def db_stats():
        """Show database statistics."""
        with app.app_context():
            print('\n📊 Database Statistics:')
            print(f'  Lecturers: {Lecturer.query.count()}')
            print(f'  Courses: {Course.query.count()}')
            print(f'  Lectures: {Lecture.query.count()}')
            print(f'  Sections: {Section.query.count()}')
            print(f'  Students: {Student.query.count()}')
            from app.models import AttendanceSession, AttendanceRecord
            print(f'  Attendance Sessions: {AttendanceSession.query.count()}')
            print(f'  Attendance Records: {AttendanceRecord.query.count()}\n')


# =============================================================================
# PART 3: ENVIRONMENT-SPECIFIC CONFIGURATION
# =============================================================================

"""
Update your config.py for different environments:
"""

import os
from datetime import timedelta

class Config:
    """Base configuration."""
    BASE_DIR = os.path.dirname(os.path.dirname(__file__))
    INSTANCE_DIR = os.path.join(BASE_DIR, 'instance')
    os.makedirs(INSTANCE_DIR, exist_ok=True)

    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f'sqlite:///{os.path.join(INSTANCE_DIR, "attendance.db")}'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Production URL for QR code generation
    BASE_URL = os.environ.get('BASE_URL', '').strip()
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = True  # HTTPS only
    SESSION_COOKIE_HTTPONLY = True  # No JavaScript access
    SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False
    SQLALCHEMY_ECHO = False  # Set to True to see SQL queries
    SESSION_COOKIE_SECURE = False  # Allow HTTP in dev


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False
    SQLALCHEMY_ECHO = False
    SESSION_COOKIE_SECURE = True
    # Require proper DATABASE_URL in production


class TestingConfig(Config):
    """Testing configuration."""
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'  # In-memory database
    WTF_CSRF_ENABLED = False


# =============================================================================
# PART 4: INITIALIZATION WITH ERROR HANDLING
# =============================================================================

"""
Production-ready initialization function:
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import logging

logger = logging.getLogger(__name__)

def init_database(app: Flask, db: SQLAlchemy) -> bool:
    """
    Initialize database with error handling.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        with app.app_context():
            # Check database connection
            db.engine.execute('SELECT 1')
            logger.info('✅ Database connection verified')
            
            # Create all tables
            db.create_all()
            logger.info('✅ Database tables created/verified')
            
            # Check if migration is needed (SQLite only)
            if app.config['SQLALCHEMY_DATABASE_URI'].startswith('sqlite'):
                from app import migrate_sqlite_schema
                migrate_sqlite_schema(app)
                logger.info('✅ SQLite schema migrated')
            
            return True
            
    except Exception as e:
        logger.error(f'❌ Database initialization failed: {str(e)}')
        return False


# =============================================================================
# PART 5: USAGE IN run.py / WSGI SERVER
# =============================================================================

"""
Updated run.py with better error handling:
"""

#!/usr/bin/env python3
"""
Smart Attendance System - Development Server
"""

import sys
import os
from app import app, init_db

def main():
    print("=" * 55)
    print("  Smart Attendance System")
    print("  Faculty of Artificial Intelligence")
    print("  Kafrelsheikh University")
    print("=" * 55)
    
    try:
        # Initialize database
        print("\n🔧 Initializing database...")
        init_db()
        print("✅ Database ready!\n")
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Start server
    print("  Server starting at → http://localhost:5000")
    print("  Demo login: admin@kfu.edu.eg / admin123")
    print("  Press CTRL+C to stop\n")
    
    try:
        app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n👋 Server stopped")


if __name__ == '__main__':
    main()


# =============================================================================
# PART 6: WSGI APPLICATION (for production deployment)
# =============================================================================

"""
Create file: wsgi.py (for Gunicorn/uWSGI)
"""

import os
from app import app, init_db

# Set environment
os.environ.setdefault('FLASK_ENV', 'production')

# Initialize database on app startup
with app.app_context():
    init_db()

if __name__ == '__main__':
    app.run()


# =============================================================================
# PART 7: DOCKER DEPLOYMENT
# =============================================================================

"""
Create file: docker-entrypoint.sh (for Docker)
"""

#!/bin/bash
set -e

echo "🐳 Smart Attendance Container Starting..."

# Wait for database to be ready (if using external DB)
if [ ! -z "$DATABASE_URL" ]; then
    echo "⏳ Waiting for database..."
    while ! python -c "import psycopg2; psycopg2.connect('$DATABASE_URL')" 2>/dev/null; do
        sleep 1
    done
    echo "✅ Database is ready"
fi

# Initialize/migrate database
echo "🔧 Initializing database..."
python -c "from app import app, init_db; init_db()"
echo "✅ Database ready"

# Start application
echo "🚀 Starting Gunicorn..."
exec gunicorn --bind 0.0.0.0:5000 \
              --workers 4 \
              --timeout 60 \
              --access-logfile - \
              --error-logfile - \
              wsgi:app


# =============================================================================
# PART 8: INITIALIZATION CHECKLIST
# =============================================================================

"""
✅ Complete Database Initialization Checklist:

DEVELOPMENT:
  [ ] 1. pip install -r requirements.txt
  [ ] 2. export FLASK_APP=run.py
  [ ] 3. python run.py
  [ ] 4. Database auto-initializes
  [ ] 5. Demo account created: admin@kfu.edu.eg / admin123
  [ ] 6. Access http://localhost:5000

PRODUCTION - PostgreSQL:
  [ ] 1. Create database: createdb attendance_db
  [ ] 2. Create user: createuser app_user -P
  [ ] 3. Grant privileges: GRANT ALL ON DATABASE attendance_db TO app_user;
  [ ] 4. Set DATABASE_URL=postgresql://app_user:pass@localhost/attendance_db
  [ ] 5. Set SECRET_KEY=<strong-random-key>
  [ ] 6. python -c "from app import init_db; init_db()"
  [ ] 7. Start application
  
PRODUCTION - Docker:
  [ ] 1. docker build -t attendance:latest .
  [ ] 2. docker run -e DATABASE_URL=postgresql://... attendance:latest
  [ ] 3. Database initializes automatically on startup

VERIFICATION:
  [ ] 1. Check tables exist: sqlite> .tables
  [ ] 2. Check indexes: sqlite> PRAGMA index_list(attendance_records);
  [ ] 3. Test connection: python -c "from app import db; db.engine.execute('SELECT 1')"
  [ ] 4. Verify demo data: curl http://localhost:5000/login

BACKUP:
  [ ] 1. Weekly backups: pg_dump attendance_db > backup_$(date +%Y%m%d).sql
  [ ] 2. Store in: /backups/ or cloud storage
  [ ] 3. Test restore: psql attendance_db < backup.sql

MONITORING:
  [ ] 1. Log slow queries: SQLALCHEMY_ECHO = True (dev only)
  [ ] 2. Monitor disk space: SELECT pg_database_size('attendance_db');
  [ ] 3. Monitor connections: SELECT count(*) FROM pg_stat_activity;
  [ ] 4. Set up alerts for: > 100 connections, > 80% disk usage
"""


# =============================================================================
# PART 9: TROUBLESHOOTING
# =============================================================================

"""
PROBLEM: "database.db is locked"
SOLUTION: SQLite has write lock issues with concurrent access
FIX: 1. Use PostgreSQL for production
    2. Enable WAL mode: PRAGMA journal_mode=WAL;
    3. Set timeout: SQLALCHEMY_ENGINE_OPTIONS = {'connect_args': {'timeout': 30}}

PROBLEM: "no such table: students"
SOLUTION: Database not initialized
FIX: 1. Ensure db.create_all() is called
    2. Check if database file exists
    3. Verify SQLALCHEMY_DATABASE_URI is correct

PROBLEM: "duplicate key value violates unique constraint"
SOLUTION: Attempting to insert duplicate student_id
FIX: 1. Check Student.create_student() returns None for duplicates
    2. Use unique constraint in data validation
    3. Handle IndexError exception

PROBLEM: Queries are slow (> 100ms)
SOLUTION: Missing indexes or N+1 queries
FIX: 1. Verify indexes exist on searched columns
    2. Use lazy='joined' for relationships to avoid N+1
    3. Enable SQLALCHEMY_ECHO to see generated SQL
    4. Use query.explain() to see execution plan
"""
