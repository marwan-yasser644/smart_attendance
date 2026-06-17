import hashlib
import uuid
from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from app import db


class Lecturer(db.Model):
    __tablename__ = 'lecturers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    role = db.Column(db.String(30), nullable=False, default='lecturer', server_default='lecturer')
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    sessions = db.relationship('AttendanceSession', back_populates='lecturer', lazy='select', cascade='all, delete-orphan')

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self) -> bool:
        return self.role == 'admin'


class Course(db.Model):
    __tablename__ = 'courses'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    lecturer_id = db.Column(db.Integer, db.ForeignKey('lecturers.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    lecturer = db.relationship('Lecturer', backref='courses')
    lectures = db.relationship('Lecture', back_populates='course', cascade='all, delete-orphan')


class Lecture(db.Model):
    __tablename__ = 'lectures'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False, index=True)
    lecturer_id = db.Column(db.Integer, db.ForeignKey('lecturers.id'), nullable=False, index=True)
    scheduled_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    course = db.relationship('Course', back_populates='lectures')
    lecturer = db.relationship('Lecturer', backref='lectures')
    sections = db.relationship('Section', back_populates='lecture', cascade='all, delete-orphan')


class Section(db.Model):
    __tablename__ = 'sections'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    lecture_id = db.Column(db.Integer, db.ForeignKey('lectures.id'), nullable=False, index=True)
    capacity = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    lecture = db.relationship('Lecture', back_populates='sections')
    students = db.relationship('Student', back_populates='section', cascade='all, delete-orphan')


class Student(db.Model):
    __tablename__ = 'students'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=True)
    section_id = db.Column(db.Integer, db.ForeignKey('sections.id'), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    section = db.relationship('Section', back_populates='students')

    @classmethod
    def create_student(cls, student_id: str, full_name: str, email: str = None, section_id: int = None):
        """
        Create and insert a new student into the database.
        
        Args:
            student_id: Unique student ID
            full_name: Student's full name
            email: Student's email (optional)
            section_id: Associated section ID (optional)
        
        Returns:
            Student object or None if student already exists
        """
        # Check if student already exists
        existing = cls.query.filter_by(student_id=student_id).first()
        if existing:
            return None
        
        student = cls(
            student_id=student_id,
            full_name=full_name,
            email=email,
            section_id=section_id
        )
        db.session.add(student)
        db.session.commit()
        return student
    
    def to_dict(self):
        """Convert student to dictionary for JSON responses."""
        return {
            'id': self.id,
            'student_id': self.student_id,
            'full_name': self.full_name,
            'email': self.email,
            'section_id': self.section_id,
            'created_at': self.created_at.isoformat()
        }


class AttendanceSession(db.Model):
    __tablename__ = 'attendance_sessions'

    id = db.Column(db.Integer, primary_key=True)
    session_uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()), index=True)
    title = db.Column(db.String(200), nullable=False)
    course_name = db.Column(db.String(200), nullable=False)
    course_code = db.Column(db.String(50), nullable=False, index=True)
    lecturer_id = db.Column(db.Integer, db.ForeignKey('lecturers.id'), nullable=False, index=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=True, index=True)
    lecture_id = db.Column(db.Integer, db.ForeignKey('lectures.id'), nullable=True, index=True)
    section_id = db.Column(db.Integer, db.ForeignKey('sections.id'), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    lecturer = db.relationship('Lecturer', back_populates='sessions')
    records = db.relationship('AttendanceRecord', back_populates='session', lazy='select', cascade='all, delete-orphan')

    @property
    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at

    @property
    def is_open(self) -> bool:
        return self.is_active and not self.is_expired

    @property
    def student_count(self) -> int:
        return len(self.records)

    @property
    def time_remaining_seconds(self) -> int:
        if self.is_expired:
            return 0
        delta = self.expires_at - datetime.utcnow()
        return max(0, int(delta.total_seconds()))


class AttendanceRecord(db.Model):
    __tablename__ = 'attendance_records'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('attendance_sessions.id'), nullable=False, index=True)
    student_name = db.Column(db.String(150), nullable=False)
    student_id = db.Column(db.String(50), nullable=False, index=True)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    ip_address = db.Column(db.String(45), nullable=True)
    submission_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)

    session = db.relationship('AttendanceSession', back_populates='records')

    @staticmethod
    def make_hash(session_id: int, student_id: str) -> str:
        raw = f"{session_id}:{student_id.strip().upper()}"
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()
    
    @classmethod
    def record_attendance(cls, session_id: int, student_id: str, student_name: str, ip_address: str = None):
        """
        Record student attendance for a session.
        Prevents duplicate submissions using submission_hash.
        
        Args:
            session_id: The attendance session ID
            student_id: Unique student ID
            student_name: Student's full name
            ip_address: Student's IP address (optional)
        
        Returns:
            Tuple of (AttendanceRecord object, bool success)
        """
        submission_hash = cls.make_hash(session_id, student_id)
        
        # Check if this student already submitted for this session
        existing = cls.query.filter_by(submission_hash=submission_hash).first()
        if existing:
            return (existing, False)  # Duplicate submission
        
        record = cls(
            session_id=session_id,
            student_id=student_id.strip().upper(),
            student_name=student_name,
            ip_address=ip_address,
            submission_hash=submission_hash
        )
        db.session.add(record)
        db.session.commit()
        return (record, True)  # New submission
    
    @classmethod
    def get_attendance_by_date_range(cls, start_date: datetime, end_date: datetime):
        """
        Query attendance records between two dates.
        Uses indexed submitted_at column for fast queries.
        
        Args:
            start_date: Start datetime
            end_date: End datetime
        
        Returns:
            List of AttendanceRecord objects
        """
        return cls.query.filter(
            cls.submitted_at >= start_date,
            cls.submitted_at <= end_date
        ).order_by(cls.submitted_at.desc()).all()
    
    @classmethod
    def get_student_attendance_by_date(cls, student_id: str, start_date: datetime, end_date: datetime):
        """
        Get a specific student's attendance records within a date range.
        
        Args:
            student_id: Student ID
            start_date: Start datetime
            end_date: End datetime
        
        Returns:
            List of AttendanceRecord objects
        """
        return cls.query.filter(
            cls.student_id == student_id.strip().upper(),
            cls.submitted_at >= start_date,
            cls.submitted_at <= end_date
        ).order_by(cls.submitted_at.desc()).all()
    
    def to_dict(self):
        """Convert record to dictionary for JSON responses."""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'student_id': self.student_id,
            'student_name': self.student_name,
            'submitted_at': self.submitted_at.isoformat(),
            'ip_address': self.ip_address
        }
