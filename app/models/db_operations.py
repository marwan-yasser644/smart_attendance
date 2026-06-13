"""
Database Operations Helper Module
Provides convenient methods for common database operations.
"""

from datetime import datetime, timedelta
from typing import List, Optional
from app import db
from .models import Student, AttendanceSession, AttendanceRecord, Section, Lecturer


class StudentOperations:
    """Helper methods for student management."""
    
    @staticmethod
    def bulk_import_students(section_id: int, students_data: List[dict]) -> dict:
        """
        Bulk import students from a list of dictionaries.
        
        Args:
            section_id: Section to add students to
            students_data: List of dicts with keys: student_id, full_name, email (optional)
        
        Returns:
            Dict with success count and failed records
        """
        created = 0
        failed = []
        
        for student_info in students_data:
            try:
                student = Student.create_student(
                    student_id=student_info['student_id'],
                    full_name=student_info['full_name'],
                    email=student_info.get('email'),
                    section_id=section_id
                )
                if student:
                    created += 1
                else:
                    failed.append(f"Duplicate: {student_info['student_id']}")
            except Exception as e:
                failed.append(f"{student_info['student_id']}: {str(e)}")
        
        return {
            'created': created,
            'failed': len(failed),
            'failed_records': failed
        }
    
    @staticmethod
    def get_student_by_id(student_id: str) -> Optional[Student]:
        """Get student by student_id (indexed for fast lookup)."""
        return Student.query.filter_by(student_id=student_id.strip().upper()).first()
    
    @staticmethod
    def get_students_in_section(section_id: int) -> List[Student]:
        """Get all students in a specific section."""
        return Student.query.filter_by(section_id=section_id).all()


class AttendanceOperations:
    """Helper methods for attendance management."""
    
    @staticmethod
    def record_student_attendance(
        session_id: int, 
        student_id: str, 
        student_name: str, 
        ip_address: str = None
    ) -> dict:
        """
        Record attendance for a student.
        
        Returns:
            {
                'success': bool,
                'message': str,
                'record': AttendanceRecord dict
            }
        """
        record, is_new = AttendanceRecord.record_attendance(
            session_id=session_id,
            student_id=student_id,
            student_name=student_name,
            ip_address=ip_address
        )
        
        if not is_new:
            return {
                'success': False,
                'message': 'Duplicate: Student already submitted attendance',
                'record': record.to_dict()
            }
        
        return {
            'success': True,
            'message': 'Attendance recorded successfully',
            'record': record.to_dict()
        }
    
    @staticmethod
    def get_session_attendance(session_id: int) -> List[dict]:
        """Get all attendance records for a session."""
        records = AttendanceRecord.query.filter_by(session_id=session_id).all()
        return [record.to_dict() for record in records]
    
    @staticmethod
    def get_attendance_statistics(session_id: int) -> dict:
        """Get attendance statistics for a session."""
        records = AttendanceRecord.query.filter_by(session_id=session_id).all()
        return {
            'total_records': len(records),
            'unique_students': len(set(r.student_id for r in records)),
            'first_submission': min(r.submitted_at for r in records) if records else None,
            'last_submission': max(r.submitted_at for r in records) if records else None
        }
    
    @staticmethod
    def get_student_attendance_history(
        student_id: str, 
        days_back: int = 30
    ) -> List[dict]:
        """
        Get a student's attendance history for the past N days.
        Uses indexed queries for performance.
        
        Args:
            student_id: Student ID
            days_back: Number of days to look back (default: 30)
        
        Returns:
            List of attendance records
        """
        start_date = datetime.utcnow() - timedelta(days=days_back)
        end_date = datetime.utcnow()
        
        records = AttendanceRecord.get_student_attendance_by_date(
            student_id=student_id,
            start_date=start_date,
            end_date=end_date
        )
        return [record.to_dict() for record in records]
    
    @staticmethod
    def get_attendance_by_date_range(
        start_date: datetime, 
        end_date: datetime,
        limit: int = 1000
    ) -> List[dict]:
        """
        Get all attendance records within a date range.
        Uses indexed submitted_at column for O(log n) lookup.
        
        Args:
            start_date: Start datetime
            end_date: End datetime
            limit: Maximum records to return (for pagination)
        
        Returns:
            List of attendance records
        """
        records = AttendanceRecord.get_attendance_by_date_range(start_date, end_date)
        return [record.to_dict() for record in records[:limit]]
    
    @staticmethod
    def get_attendance_by_course_and_date(
        course_code: str,
        start_date: datetime,
        end_date: datetime
    ) -> dict:
        """
        Get attendance stats for a course within a date range.
        
        Returns:
            {
                'course_code': str,
                'total_records': int,
                'date_range': (start, end),
                'records': list
            }
        """
        sessions = AttendanceSession.query.filter_by(course_code=course_code).all()
        session_ids = [s.id for s in sessions]
        
        records = AttendanceRecord.query.filter(
            AttendanceRecord.session_id.in_(session_ids),
            AttendanceRecord.submitted_at >= start_date,
            AttendanceRecord.submitted_at <= end_date
        ).all()
        
        return {
            'course_code': course_code,
            'total_records': len(records),
            'date_range': (start_date.isoformat(), end_date.isoformat()),
            'records': [r.to_dict() for r in records]
        }


class SessionOperations:
    """Helper methods for session management."""
    
    @staticmethod
    def get_active_sessions(lecturer_id: int) -> List[dict]:
        """Get all active (not expired) sessions for a lecturer."""
        sessions = AttendanceSession.query.filter(
            AttendanceSession.lecturer_id == lecturer_id,
            AttendanceSession.is_active == True,
            AttendanceSession.expires_at > datetime.utcnow()
        ).order_by(AttendanceSession.created_at.desc()).all()
        
        return [
            {
                'id': s.id,
                'uuid': s.session_uuid,
                'title': s.title,
                'course': s.course_name,
                'is_open': s.is_open,
                'student_count': s.student_count,
                'time_remaining': s.time_remaining_seconds
            }
            for s in sessions
        ]
    
    @staticmethod
    def get_session_details(session_uuid: str) -> Optional[dict]:
        """Get detailed information about a session."""
        session = AttendanceSession.query.filter_by(session_uuid=session_uuid).first()
        if not session:
            return None
        
        records = AttendanceRecord.query.filter_by(session_id=session.id).all()
        
        return {
            'id': session.id,
            'uuid': session.session_uuid,
            'title': session.title,
            'course': session.course_name,
            'course_code': session.course_code,
            'is_open': session.is_open,
            'is_expired': session.is_expired,
            'created_at': session.created_at.isoformat(),
            'expires_at': session.expires_at.isoformat(),
            'attendance_count': len(records),
            'attendees': [r.to_dict() for r in records]
        }
