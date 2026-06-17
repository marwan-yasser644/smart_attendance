"""
SMART ATTENDANCE DATABASE - USAGE GUIDE
========================================

This file demonstrates practical examples of using the database models
and operations for the Smart Attendance system.
"""

# =============================================================================
# EXAMPLE 1: Initialize Database (in app/__init__.py or run.py)
# =============================================================================

from app import db, create_app

# The database is automatically initialized in the app factory:
# - create_app() calls db.init_app(app)
# - db.create_all() creates all tables
# - seed_demo_lecturer(app) creates a demo account

app = create_app()

with app.app_context():
    # All tables are created automatically
    # You can now use the ORM models


# =============================================================================
# EXAMPLE 2: Create a Student
# =============================================================================

from app.models import Student

with app.app_context():
    # Single student creation
    student = Student.create_student(
        student_id='CS001',
        full_name='Ahmed Mohamed',
        email='ahmed@college.edu',
        section_id=1  # Optional
    )
    
    if student:
        print(f"✅ Student created: {student.full_name}")
    else:
        print("❌ Student already exists")


# =============================================================================
# EXAMPLE 3: Bulk Import Students
# =============================================================================

from app.models.db_operations import StudentOperations

with app.app_context():
    students_data = [
        {'student_id': 'CS001', 'full_name': 'Ahmed Mohamed', 'email': 'ahmed@college.edu'},
        {'student_id': 'CS002', 'full_name': 'Fatima Ali', 'email': 'fatima@college.edu'},
        {'student_id': 'CS003', 'full_name': 'Omar Hassan', 'email': 'omar@college.edu'},
        {'student_id': 'CS004', 'full_name': 'Layla Ibrahim', 'email': 'layla@college.edu'},
    ]
    
    result = StudentOperations.bulk_import_students(
        section_id=1,
        students_data=students_data
    )
    
    print(f"✅ Created: {result['created']} students")
    if result['failed']:
        print(f"❌ Failed: {result['failed']} students")
        for failure in result['failed_records']:
            print(f"   - {failure}")


# =============================================================================
# EXAMPLE 4: Record Attendance (This is what happens when student submits QR code)
# =============================================================================

from app.models.db_operations import AttendanceOperations

with app.app_context():
    # Simulate a student scanning the QR code
    result = AttendanceOperations.record_student_attendance(
        session_id=1,
        student_id='CS001',
        student_name='Ahmed Mohamed',
        ip_address='192.168.1.100'
    )
    
    if result['success']:
        print(f"✅ {result['message']}")
        print(f"   Record: {result['record']}")
    else:
        print(f"⚠️ {result['message']}")
    
    # Try again - should be rejected as duplicate
    result2 = AttendanceOperations.record_student_attendance(
        session_id=1,
        student_id='CS001',
        student_name='Ahmed Mohamed',
        ip_address='192.168.1.100'
    )
    print(f"   {result2['message']}")  # "Duplicate: Student already submitted attendance"


# =============================================================================
# EXAMPLE 5: Query Attendance Statistics for a Session
# =============================================================================

with app.app_context():
    stats = AttendanceOperations.get_attendance_statistics(session_id=1)
    
    print(f"📊 Session Attendance Statistics:")
    print(f"   Total Records: {stats['total_records']}")
    print(f"   Unique Students: {stats['unique_students']}")
    print(f"   First Submission: {stats['first_submission']}")
    print(f"   Last Submission: {stats['last_submission']}")


# =============================================================================
# EXAMPLE 6: Get Student Attendance History (Last 30 Days)
# =============================================================================

with app.app_context():
    # Query is FAST because:
    # 1. submitted_at column is INDEXED
    # 2. student_id column is INDEXED
    # 3. Database uses index to quickly find records between dates
    
    history = AttendanceOperations.get_student_attendance_history(
        student_id='CS001',
        days_back=30
    )
    
    print(f"📅 {len(history)} attendance records for CS001 in last 30 days:")
    for record in history:
        print(f"   - {record['submitted_at']}: {record['student_name']}")


# =============================================================================
# EXAMPLE 7: Query Attendance by Date Range (Fast Due to Indexes)
# =============================================================================

from datetime import datetime, timedelta

with app.app_context():
    # Query is optimized with database indexes
    start = datetime(2024, 1, 1)
    end = datetime(2024, 1, 31)
    
    records = AttendanceOperations.get_attendance_by_date_range(
        start_date=start,
        end_date=end,
        limit=100
    )
    
    print(f"📋 Found {len(records)} attendance records from {start} to {end}")


# =============================================================================
# EXAMPLE 8: Get Course Attendance Report
# =============================================================================

from datetime import datetime, timedelta

with app.app_context():
    start = datetime(2024, 1, 1)
    end = datetime(2024, 1, 31)
    
    report = AttendanceOperations.get_attendance_by_course_and_date(
        course_code='CS101',
        start_date=start,
        end_date=end
    )
    
    print(f"📈 Course {report['course_code']} Report:")
    print(f"   Total Submissions: {report['total_records']}")
    print(f"   Period: {report['date_range'][0]} to {report['date_range'][1]}")
    for record in report['records']:
        print(f"   - {record['student_id']}: {record['submitted_at']}")


# =============================================================================
# EXAMPLE 9: Use in Flask Route (Practical Web App Example)
# =============================================================================

from flask import Blueprint, request, jsonify
from datetime import datetime

example_bp = Blueprint('example', __name__)

@example_bp.route('/api/attend/<session_uuid>', methods=['POST'])
def submit_attendance(session_uuid):
    """Handle QR code attendance submission."""
    from app.models import AttendanceSession
    
    # 1. Find the session
    session = AttendanceSession.query.filter_by(session_uuid=session_uuid).first()
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    # 2. Check if session is still open
    if not session.is_open:
        return jsonify({'error': 'Session closed or expired'}), 400
    
    # 3. Get student info from request
    data = request.json
    student_id = data.get('student_id')
    student_name = data.get('student_name')
    
    # 4. Record attendance (FAST: uses indexed columns)
    result = AttendanceOperations.record_student_attendance(
        session_id=session.id,
        student_id=student_id,
        student_name=student_name,
        ip_address=request.remote_addr
    )
    
    return jsonify(result), (200 if result['success'] else 409)


@example_bp.route('/api/reports/student/<student_id>', methods=['GET'])
def get_student_report(student_id):
    """Get student attendance report."""
    from app.models import Student
    
    # Check student exists
    student = Student.query.filter_by(student_id=student_id).first()
    if not student:
        return jsonify({'error': 'Student not found'}), 404
    
    # Get attendance history (OPTIMIZED QUERY)
    days = request.args.get('days', 30, type=int)
    history = AttendanceOperations.get_student_attendance_history(
        student_id=student_id,
        days_back=days
    )
    
    return jsonify({
        'student': student.to_dict(),
        'attendance_count': len(history),
        'records': history
    })


# =============================================================================
# DATABASE INDEXING STRATEGY FOR PERFORMANCE
# =============================================================================

"""
INDEXED COLUMNS (for fast queries):

1. Student.student_id (UNIQUE + indexed)
   → Fast lookup: Student.query.filter_by(student_id='CS001').first()

2. AttendanceRecord.submitted_at (indexed with datetime)
   → Date range queries are O(log n):
     AttendanceRecord.query.filter(
         AttendanceRecord.submitted_at >= start_date,
         AttendanceRecord.submitted_at <= end_date
     ).all()

3. AttendanceRecord.student_id (indexed)
   → Fast student lookups:
     AttendanceRecord.query.filter_by(student_id='CS001').all()

4. AttendanceSession.session_uuid (UNIQUE + indexed)
   → Fast session lookup by UUID

5. AttendanceSession.expires_at (indexed)
   → Fast query for active/expired sessions


PERFORMANCE CHARACTERISTICS:

Operation                              | Time Complexity | Reason
--------------------------------------|-----------------|------------------
Insert Student                        | O(1)            | Direct insert
Record Attendance                      | O(log n)        | Hash lookup + insert
Find Student by ID                    | O(log n)        | Index on student_id
Get Attendance by Date Range          | O(log n + k)    | Index on submitted_at
Get Student History (30 days)         | O(log n + k)    | Indexed columns
Duplicate Check (via hash)            | O(log n)        | Unique index


WHERE k = number of results in range (much smaller than total records)
"""


# =============================================================================
# PRODUCTION DEPLOYMENT CHECKLIST
# =============================================================================

"""
✅ Database Setup Checklist:

1. Environment Variables:
   - DATABASE_URL=postgresql://user:pass@host:5432/attendance
   - SECRET_KEY=<random-secret-key>
   - FLASK_ENV=production

2. Create Tables (automatic on app start):
   with app.app_context():
       db.create_all()

3. Create Indexes (automatic from model definitions):
   - All @db.Column(index=True) creates B-tree indexes

4. Performance Optimization:
   - Use connection pooling (SQLAlchemy default: 5 connections)
   - Enable query caching for frequently accessed data
   - Monitor slow queries with:
     app.config['SQLALCHEMY_ECHO'] = True  # SQL logging

5. Backups:
   - PostgreSQL: pg_dump attendance_db > backup.sql
   - SQLite: cp instance/attendance.db backups/attendance_$(date).db

6. Monitoring:
   - Count active sessions: AttendanceSession.query.count()
   - Peak attendance time analysis
   - Detect duplicate submissions (should be 0)
"""
