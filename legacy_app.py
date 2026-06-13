from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import qrcode
import io
import os
import csv
import uuid
import hashlib
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'kfu-ai-attendance-secret-2024-change-in-production')

# ─── Database Configuration ──────────────────────────────────────────────────
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///attendance.db')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ─── Models ───────────────────────────────────────────────────────────────────

class Lecturer(db.Model):
    __tablename__ = 'lecturers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sessions = db.relationship('AttendanceSession', backref='lecturer', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class AttendanceSession(db.Model):
    __tablename__ = 'attendance_sessions'
    id = db.Column(db.Integer, primary_key=True)
    session_uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(200), nullable=False)
    course_name = db.Column(db.String(200), nullable=False)
    course_code = db.Column(db.String(50), nullable=False)
    lecturer_id = db.Column(db.Integer, db.ForeignKey('lecturers.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    records = db.relationship('AttendanceRecord', backref='session', lazy=True)

    @property
    def is_expired(self):
        return datetime.utcnow() > self.expires_at

    @property
    def is_open(self):
        return self.is_active and not self.is_expired

    @property
    def student_count(self):
        return len(self.records)

    @property
    def time_remaining_seconds(self):
        if self.is_expired:
            return 0
        delta = self.expires_at - datetime.utcnow()
        return max(0, int(delta.total_seconds()))


class AttendanceRecord(db.Model):
    __tablename__ = 'attendance_records'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('attendance_sessions.id'), nullable=False)
    student_name = db.Column(db.String(150), nullable=False)
    student_id = db.Column(db.String(50), nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45))
    submission_hash = db.Column(db.String(64), unique=True)

    @staticmethod
    def make_hash(session_id, student_id):
        raw = f"{session_id}:{student_id.strip().upper()}"
        return hashlib.sha256(raw.encode()).hexdigest()


# ─── Decorators ───────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'lecturer_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def get_current_lecturer():
    if 'lecturer_id' in session:
        return Lecturer.query.get(session['lecturer_id'])
    return None


# ─── Auth Routes ──────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if 'lecturer_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'lecturer_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        lecturer = Lecturer.query.filter_by(email=email).first()
        if lecturer and lecturer.check_password(password):
            session['lecturer_id'] = lecturer.id
            session['lecturer_name'] = lecturer.name
            flash(f'Welcome back, {lecturer.name}!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid email or password.', 'danger')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        if not all([name, email, password]):
            flash('All fields are required.', 'danger')
            return render_template('register.html')
        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')
        if Lecturer.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return render_template('register.html')

        lecturer = Lecturer(name=name, email=email)
        lecturer.set_password(password)
        db.session.add(lecturer)
        db.session.commit()
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# ─── Dashboard ────────────────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    lecturer = get_current_lecturer()
    sessions_list = AttendanceSession.query.filter_by(lecturer_id=lecturer.id)\
        .order_by(AttendanceSession.created_at.desc()).all()
    
    total_sessions = len(sessions_list)
    active_sessions = sum(1 for s in sessions_list if s.is_open)
    total_students = sum(s.student_count for s in sessions_list)
    
    return render_template('dashboard.html',
        lecturer=lecturer,
        sessions=sessions_list,
        total_sessions=total_sessions,
        active_sessions=active_sessions,
        total_students=total_students
    )


# ─── Session Management ───────────────────────────────────────────────────────

@app.route('/session/new', methods=['GET', 'POST'])
@login_required
def new_session():
    lecturer = get_current_lecturer()
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        course_name = request.form.get('course_name', '').strip()
        course_code = request.form.get('course_code', '').strip()
        duration_minutes = int(request.form.get('duration', 10))

        if not all([title, course_name, course_code]):
            flash('All fields are required.', 'danger')
            return render_template('new_session.html', lecturer=lecturer)

        expires_at = datetime.utcnow() + timedelta(minutes=duration_minutes)
        sess = AttendanceSession(
            title=title,
            course_name=course_name,
            course_code=course_code,
            lecturer_id=lecturer.id,
            expires_at=expires_at
        )
        db.session.add(sess)
        db.session.commit()
        flash('Session created successfully!', 'success')
        return redirect(url_for('session_detail', session_uuid=sess.session_uuid))

    return render_template('new_session.html', lecturer=lecturer)


@app.route('/session/<session_uuid>')
@login_required
def session_detail(session_uuid):
    lecturer = get_current_lecturer()
    sess = AttendanceSession.query.filter_by(session_uuid=session_uuid, lecturer_id=lecturer.id).first_or_404()
    records = AttendanceRecord.query.filter_by(session_id=sess.id)\
        .order_by(AttendanceRecord.submitted_at.asc()).all()
    
    base_url = request.host_url.rstrip('/')
    attendance_url = f"{base_url}/attend/{session_uuid}"
    
    return render_template('session_detail.html',
        lecturer=lecturer,
        sess=sess,
        records=records,
        attendance_url=attendance_url
    )


@app.route('/session/<session_uuid>/close', methods=['POST'])
@login_required
def close_session(session_uuid):
    lecturer = get_current_lecturer()
    sess = AttendanceSession.query.filter_by(session_uuid=session_uuid, lecturer_id=lecturer.id).first_or_404()
    sess.is_active = False
    db.session.commit()
    flash('Session closed successfully.', 'info')
    return redirect(url_for('session_detail', session_uuid=session_uuid))


@app.route('/session/<session_uuid>/qr')
@login_required
def generate_qr(session_uuid):
    lecturer = get_current_lecturer()
    sess = AttendanceSession.query.filter_by(session_uuid=session_uuid, lecturer_id=lecturer.id).first_or_404()
    
    base_url = request.host_url.rstrip('/')
    attendance_url = f"{base_url}/attend/{session_uuid}"
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(attendance_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1a237e", back_color="white")
    
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png', as_attachment=False)


@app.route('/session/<session_uuid>/export')
@login_required
def export_csv(session_uuid):
    lecturer = get_current_lecturer()
    sess = AttendanceSession.query.filter_by(session_uuid=session_uuid, lecturer_id=lecturer.id).first_or_404()
    records = AttendanceRecord.query.filter_by(session_id=sess.id)\
        .order_by(AttendanceRecord.submitted_at.asc()).all()
    
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(['#', 'Student Name', 'Student ID', 'Submitted At', 'IP Address'])
    for i, r in enumerate(records, 1):
        writer.writerow([
            i,
            r.student_name,
            r.student_id,
            r.submitted_at.strftime('%Y-%m-%d %H:%M:%S'),
            r.ip_address or 'N/A'
        ])
    
    buf.seek(0)
    output = io.BytesIO(buf.getvalue().encode('utf-8-sig'))
    filename = f"attendance_{sess.course_code}_{sess.created_at.strftime('%Y%m%d_%H%M')}.csv"
    return send_file(output, mimetype='text/csv', as_attachment=True, download_name=filename)


# ─── Student Attendance Flow ──────────────────────────────────────────────────

@app.route('/attend/<session_uuid>', methods=['GET', 'POST'])
def attend(session_uuid):
    sess = AttendanceSession.query.filter_by(session_uuid=session_uuid).first_or_404()
    
    if not sess.is_open:
        reason = 'expired' if sess.is_expired else 'closed'
        return render_template('attend_closed.html', sess=sess, reason=reason)
    
    if request.method == 'POST':
        student_name = request.form.get('student_name', '').strip()
        student_id = request.form.get('student_id', '').strip()
        
        errors = []
        if not student_name or len(student_name) < 3:
            errors.append('Please enter your full name (at least 3 characters).')
        if not student_id or len(student_id) < 3:
            errors.append('Please enter a valid Student ID.')
        
        if errors:
            return render_template('attend.html', sess=sess, errors=errors,
                                   student_name=student_name, student_id=student_id)
        
        # Re-check session is still open
        if not sess.is_open:
            return render_template('attend_closed.html', sess=sess, reason='expired')
        
        # Check duplicate
        submission_hash = AttendanceRecord.make_hash(sess.id, student_id)
        existing = AttendanceRecord.query.filter_by(submission_hash=submission_hash).first()
        if existing:
            return render_template('attend_duplicate.html', sess=sess,
                                   student_name=student_name, submitted_at=existing.submitted_at)
        
        # Get IP
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ip and ',' in ip:
            ip = ip.split(',')[0].strip()
        
        record = AttendanceRecord(
            session_id=sess.id,
            student_name=student_name,
            student_id=student_id.upper(),
            ip_address=ip,
            submission_hash=submission_hash
        )
        db.session.add(record)
        db.session.commit()
        
        return render_template('attend_success.html', sess=sess,
                               student_name=student_name, student_id=student_id.upper(),
                               submitted_at=record.submitted_at)
    
    return render_template('attend.html', sess=sess, errors=[], student_name='', student_id='')


# ─── API Endpoints ────────────────────────────────────────────────────────────

@app.route('/api/session/<session_uuid>/status')
def session_status(session_uuid):
    sess = AttendanceSession.query.filter_by(session_uuid=session_uuid).first_or_404()
    return jsonify({
        'is_open': sess.is_open,
        'is_expired': sess.is_expired,
        'time_remaining': sess.time_remaining_seconds,
        'student_count': sess.student_count
    })


# ─── Init ─────────────────────────────────────────────────────────────────────

def init_db():
    with app.app_context():
        db.create_all()
        # Create demo lecturer if none exists
        if not Lecturer.query.first():
            demo = Lecturer(name='Dr. Ahmed Hassan', email='admin@kfu.edu.eg')
            demo.set_password('admin123')
            db.session.add(demo)
            db.session.commit()
            print("✅ Demo lecturer created: admin@kfu.edu.eg / admin123")


if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV', 'development') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)
