"""
DATABASE QUERY OPTIMIZATION GUIDE
For Smart Attendance System using SQLAlchemy + PostgreSQL/SQLite
"""

# =============================================================================
# PART 1: INDEX STRATEGY FOR DATE-BASED QUERIES
# =============================================================================

"""
WHY INDEXES ARE CRITICAL FOR DATE QUERIES:

Without index:
    SELECT * FROM attendance_records WHERE submitted_at >= '2024-01-01' AND submitted_at <= '2024-01-31';
    ↓
    Database MUST scan ALL rows (O(n)) - SLOW!

With B-tree index on submitted_at:
    SELECT * FROM attendance_records WHERE submitted_at >= '2024-01-01' AND submitted_at <= '2024-01-31';
    ↓
    Database uses index to jump to first matching row (O(log n))
    Then reads only matching rows in order
    FAST!

YOUR CURRENT INDEXES (from models.py):
    1. submitted_at → db.Column(db.DateTime, ..., index=True)
    2. student_id → db.Column(db.String(50), ..., index=True)
    3. session_id → db.Column(db.Integer, ..., index=True)
    4. expires_at → db.Column(db.DateTime, ..., index=True)
"""

# =============================================================================
# PART 2: OPTIMIZED QUERIES FOR DATE RANGES
# =============================================================================

"""
SCENARIO 1: Get all attendance records for a specific date
"""
from datetime import datetime, timedelta
from app import db
from app.models import AttendanceRecord

def get_attendance_for_date(date: datetime):
    """
    Get all attendance records for a specific date.
    
    ✅ OPTIMIZED: Uses index on submitted_at
    Time: O(log n + k) where k = records on that day (usually small)
    """
    start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    end = date.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    return AttendanceRecord.query.filter(
        AttendanceRecord.submitted_at >= start,
        AttendanceRecord.submitted_at <= end
    ).order_by(AttendanceRecord.submitted_at.asc()).all()


"""
SCENARIO 2: Get attendance records between two dates (e.g., monthly report)
"""
def get_monthly_attendance(year: int, month: int):
    """
    Get all attendance records for a specific month.
    
    ✅ OPTIMIZED: 
       - Index on submitted_at allows quick range lookup
       - order_by uses index (already sorted in index)
    Time: O(log n + k)
    """
    from datetime import date
    import calendar
    
    # Get first and last day of month
    first_day = date(year, month, 1)
    _, last_day = calendar.monthrange(year, month)
    last_date = date(year, month, last_day)
    
    start = datetime.combine(first_day, datetime.min.time())
    end = datetime.combine(last_date, datetime.max.time())
    
    return AttendanceRecord.query.filter(
        AttendanceRecord.submitted_at >= start,
        AttendanceRecord.submitted_at <= end
    ).order_by(AttendanceRecord.submitted_at.desc()).all()


"""
SCENARIO 3: Get a specific student's attendance in date range
"""
def get_student_attendance_in_range(student_id: str, start: datetime, end: datetime):
    """
    Get a student's attendance records in a date range.
    
    ✅ OPTIMIZED:
       - COMPOSITE index would be ideal: (student_id, submitted_at)
       - Current: Uses index on student_id first, then filters by date
    Time: O(log n + k)
    
    NOTE: For production, consider adding composite index:
          db.Index('ix_student_date', 
                   AttendanceRecord.student_id, 
                   AttendanceRecord.submitted_at)
    """
    return AttendanceRecord.query.filter(
        AttendanceRecord.student_id == student_id.upper(),
        AttendanceRecord.submitted_at >= start,
        AttendanceRecord.submitted_at <= end
    ).order_by(AttendanceRecord.submitted_at.desc()).all()


"""
SCENARIO 4: ❌ SLOW QUERY - What NOT to do
"""
def get_attendance_by_date_string(date_str: str):
    """
    ❌ BAD: String matching on datetime column
    This CANNOT use index efficiently!
    
    Database will:
    1. Convert datetime to string for each row (O(n))
    2. Compare strings
    3. Very SLOW!
    
    AVOID THIS PATTERN!
    """
    # DON'T DO THIS:
    # return AttendanceRecord.query.filter(
    #     db.func.date(AttendanceRecord.submitted_at) == date_str
    # ).all()
    pass


"""
SCENARIO 5: Get paginated results with date range
"""
def get_attendance_paginated(start: datetime, end: datetime, page: int = 1, per_page: int = 50):
    """
    Paginate attendance records in a date range.
    
    ✅ OPTIMIZED:
       - Index allows quick range lookup
       - limit/offset work efficiently on indexed results
    Time: O(log n + k) where k = records per page
    """
    return AttendanceRecord.query.filter(
        AttendanceRecord.submitted_at >= start,
        AttendanceRecord.submitted_at <= end
    ).order_by(
        AttendanceRecord.submitted_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)


# =============================================================================
# PART 3: CREATING COMPOSITE INDEXES FOR PRODUCTION
# =============================================================================

"""
For PRODUCTION deployment with heavy date queries, add composite indexes.

Composite indexes are MORE efficient when filtering by multiple columns.
"""

# In models.py, add these to AttendanceRecord class:

from sqlalchemy import Index

class AttendanceRecord(db.Model):
    __tablename__ = 'attendance_records'
    
    # ... existing columns ...
    
    # Add composite indexes after relationships:
    __table_args__ = (
        # Index for: (student_id, submitted_at) queries
        Index('ix_student_submitted', 'student_id', 'submitted_at'),
        
        # Index for: (session_id, submitted_at) queries  
        Index('ix_session_submitted', 'session_id', 'submitted_at'),
    )


"""
To apply composite indexes:
1. Add __table_args__ to model (shown above)
2. Run migration or create_all() in development
3. Verify in database:

   PostgreSQL:
   \d attendance_records
   
   SQLite:
   PRAGMA index_info(ix_student_submitted);
"""


# =============================================================================
# PART 4: QUERY PERFORMANCE MONITORING
# =============================================================================

"""
Enable SQL Query Logging in Development
"""
def enable_query_logging(app):
    """Enable detailed SQL logging."""
    app.config['SQLALCHEMY_ECHO'] = True
    app.config['SQLALCHEMY_RECORD_QUERIES'] = True


def print_slow_queries(app):
    """Print queries that took longer than 0.5 seconds."""
    from flask import get_flashed_messages
    
    @app.after_request
    def after_request(response):
        from flask_sqlalchemy import get_debug_queries
        
        for query in get_debug_queries():
            if query.duration >= 0.5:
                print(f'\n⚠️ SLOW QUERY ({query.duration:.3f}s):')
                print(query.statement)
                print(f'Parameters: {query.parameters}')
                print()
        
        return response


# =============================================================================
# PART 5: PERFORMANCE TESTING - Before/After
# =============================================================================

"""
How to benchmark your queries:
"""
import time
from datetime import datetime, timedelta

def benchmark_date_query():
    """Benchmark attendance query by date range."""
    
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 1, 31)
    
    # Warm up (first query is slower due to cache)
    AttendanceRecord.query.filter(
        AttendanceRecord.submitted_at >= start_date,
        AttendanceRecord.submitted_at <= end_date
    ).all()
    
    # Benchmark
    start_time = time.time()
    for _ in range(1000):
        records = AttendanceRecord.query.filter(
            AttendanceRecord.submitted_at >= start_date,
            AttendanceRecord.submitted_at <= end_date
        ).all()
    elapsed = time.time() - start_time
    
    print(f"1000 queries completed in {elapsed:.3f}s")
    print(f"Average: {(elapsed/1000)*1000:.2f}ms per query")
    
    # Expected:
    # With index: ~5-10ms per query
    # Without index: ~100-500ms per query


# =============================================================================
# PART 6: COMMON DATE QUERY PATTERNS
# =============================================================================

"""
Pattern 1: "Last N days" queries
"""
def get_last_n_days(n_days: int):
    """Get attendance from last N days."""
    end = datetime.utcnow()
    start = end - timedelta(days=n_days)
    
    return AttendanceRecord.query.filter(
        AttendanceRecord.submitted_at >= start,
        AttendanceRecord.submitted_at <= end
    ).order_by(AttendanceRecord.submitted_at.desc()).all()


"""
Pattern 2: "Between hours of day" queries
"""
def get_peak_hours_attendance(start_hour: int, end_hour: int):
    """Get attendance between specific hours (e.g., 9 AM to 5 PM)."""
    today = datetime.utcnow().date()
    
    start = datetime.combine(today, datetime.min.time()).replace(hour=start_hour)
    end = datetime.combine(today, datetime.max.time()).replace(hour=end_hour)
    
    return AttendanceRecord.query.filter(
        AttendanceRecord.submitted_at >= start,
        AttendanceRecord.submitted_at <= end
    ).all()


"""
Pattern 3: "Date histogram" (count by date)
"""
def get_attendance_histogram(start: datetime, end: datetime):
    """Count attendance submissions per day."""
    from sqlalchemy import func
    
    result = db.session.query(
        func.date(AttendanceRecord.submitted_at).label('date'),
        func.count(AttendanceRecord.id).label('count')
    ).filter(
        AttendanceRecord.submitted_at >= start,
        AttendanceRecord.submitted_at <= end
    ).group_by(
        func.date(AttendanceRecord.submitted_at)
    ).all()
    
    return {row[0].isoformat(): row[1] for row in result}


# =============================================================================
# PART 7: PRODUCTION CHECKLIST
# =============================================================================

"""
✅ Date Query Optimization Checklist:

[ ] 1. Ensure indexes exist:
       - submitted_at (indexed on AttendanceRecord)
       - student_id (indexed on AttendanceRecord)
       - session_id (indexed on AttendanceRecord)

[ ] 2. For high-volume apps, add composite indexes:
       - (student_id, submitted_at)
       - (session_id, submitted_at)

[ ] 3. Use parameterized queries (SQLAlchemy does this):
       ✅ Good: query.filter(date_col >= param)
       ❌ Bad: query.filter(f"date_col >= '{param}'")

[ ] 4. Avoid these anti-patterns:
       ❌ String conversion: func.date(submitted_at) == "2024-01-01"
       ❌ LIKE queries on timestamps: submitted_at LIKE "2024-01%"
       ❌ Functions in WHERE: where year(submitted_at) = 2024
       ✅ Use: where submitted_at >= start AND submitted_at < end

[ ] 5. Set up monitoring:
       - Enable SQLALCHEMY_ECHO in development
       - Use SQLALCHEMY_RECORD_QUERIES for benchmarking
       - Monitor query execution times in logs

[ ] 6. Plan for scaling:
       - If > 1M records: Add monthly table partitioning
       - If > 10M records: Consider archiving old records
       - Use materialized views for reporting
"""


# =============================================================================
# PART 8: EXAMPLE FLASK ROUTE WITH OPTIMIZED QUERIES
# =============================================================================

"""
Complete example of a report endpoint with optimal queries:
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from app.models.db_operations import AttendanceOperations

reports_bp = Blueprint('reports', __name__, url_prefix='/api/reports')

@reports_bp.route('/attendance/<course_code>')
def course_attendance_report(course_code):
    """
    Get attendance report for a course in a date range.
    
    Query params:
        - start_date: YYYY-MM-DD (default: 30 days ago)
        - end_date: YYYY-MM-DD (default: today)
    """
    
    # Parse query parameters
    end_date = request.args.get('end_date', datetime.utcnow().date().isoformat())
    days = request.args.get('days', 30, type=int)
    
    try:
        end = datetime.fromisoformat(end_date).replace(hour=23, minute=59, second=59)
        start = end - timedelta(days=days)
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400
    
    # OPTIMIZED QUERY: Uses indexed columns
    report = AttendanceOperations.get_attendance_by_course_and_date(
        course_code=course_code,
        start_date=start,
        end_date=end
    )
    
    return jsonify(report)


@reports_bp.route('/student/<student_id>/history')
def student_attendance_history(student_id):
    """
    Get a student's attendance history.
    
    Query params:
        - days: Number of days to look back (default: 30)
    """
    
    days = request.args.get('days', 30, type=int)
    
    # OPTIMIZED QUERY: Uses indexes on both student_id and submitted_at
    history = AttendanceOperations.get_student_attendance_history(
        student_id=student_id,
        days_back=days
    )
    
    return jsonify({
        'student_id': student_id,
        'days_lookback': days,
        'records': history,
        'total': len(history)
    })
