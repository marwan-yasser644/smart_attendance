import csv
import io

import qrcode
from flask import Blueprint, flash, jsonify, redirect, render_template, request, send_file, session, url_for

from app import db
from app.models import AttendanceRecord, AttendanceSession, Lecturer
from app.services.attendance_service import build_attendance_url, generate_qr_image

main_bp = Blueprint('main', __name__)


def login_required(f):
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        if 'lecturer_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('main.login'))
        return f(*args, **kwargs)

    return decorated


def get_current_lecturer():
    lecturer_id = session.get('lecturer_id')
    return Lecturer.query.get(lecturer_id) if lecturer_id else None


@main_bp.route('/')
def index():
    if 'lecturer_id' in session:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('main.login'))


@main_bp.route('/login', methods=['GET', 'POST'], endpoint='login')
def login():
    if 'lecturer_id' in session:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        lecturer = Lecturer.query.filter_by(email=email).first()
        if lecturer and lecturer.check_password(password):
            session['lecturer_id'] = lecturer.id
            session['lecturer_name'] = lecturer.name
            session['lecturer_role'] = lecturer.role
            flash(f'Welcome back, {lecturer.name}!', 'success')
            return redirect(url_for('main.dashboard'))
        flash('Invalid email or password.', 'danger')

    return render_template('login.html')


@main_bp.route('/register', methods=['GET', 'POST'], endpoint='register')
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

        lecturer = Lecturer(name=name, email=email, role='lecturer')
        lecturer.set_password(password)
        db.session.add(lecturer)
        db.session.commit()
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('main.login'))
    return render_template('register.html')


@main_bp.route('/logout', endpoint='logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.login'))


@main_bp.route('/dashboard', endpoint='dashboard')
@login_required
def dashboard():
    lecturer = get_current_lecturer()
    sessions_list = AttendanceSession.query.filter_by(lecturer_id=lecturer.id).order_by(AttendanceSession.created_at.desc()).all()

    total_sessions = len(sessions_list)
    active_sessions = sum(1 for s in sessions_list if s.is_open)
    total_students = sum(s.student_count for s in sessions_list)

    return render_template('dashboard.html', lecturer=lecturer, sessions=sessions_list,
                           total_sessions=total_sessions, active_sessions=active_sessions,
                           total_students=total_students)


@main_bp.route('/session/new', methods=['GET', 'POST'], endpoint='new_session')
@login_required
def new_session():
    lecturer = get_current_lecturer()
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        course_name = request.form.get('course_name', '').strip()
        course_code = request.form.get('course_code', '').strip()
        duration_minutes = int(request.form.get('duration', 10) or 10)

        if not all([title, course_name, course_code]):
            flash('All fields are required.', 'danger')
            return render_template('new_session.html', lecturer=lecturer)

        expires_at = __import__('datetime').datetime.utcnow() + __import__('datetime').timedelta(minutes=duration_minutes)
        sess = AttendanceSession(title=title, course_name=course_name, course_code=course_code,
                                 lecturer_id=lecturer.id, expires_at=expires_at)
        db.session.add(sess)
        db.session.commit()
        flash('Session created successfully!', 'success')
        return redirect(url_for('main.session_detail', session_uuid=sess.session_uuid))

    return render_template('new_session.html', lecturer=lecturer)


@main_bp.route('/session/<session_uuid>', endpoint='session_detail')
@login_required
def session_detail(session_uuid):
    lecturer = get_current_lecturer()
    sess = AttendanceSession.query.filter_by(session_uuid=session_uuid, lecturer_id=lecturer.id).first_or_404()
    records = AttendanceRecord.query.filter_by(session_id=sess.id).order_by(AttendanceRecord.submitted_at.asc()).all()

    attendance_url = build_attendance_url(request, session_uuid)

    return render_template('session_detail.html', lecturer=lecturer, sess=sess, records=records, attendance_url=attendance_url)


@main_bp.route('/session/<session_uuid>/close', methods=['POST'], endpoint='close_session')
@login_required
def close_session(session_uuid):
    lecturer = get_current_lecturer()
    sess = AttendanceSession.query.filter_by(session_uuid=session_uuid, lecturer_id=lecturer.id).first_or_404()
    sess.is_active = False
    db.session.commit()
    flash('Session closed successfully.', 'info')
    return redirect(url_for('main.session_detail', session_uuid=session_uuid))


@main_bp.route('/session/<session_uuid>/qr', endpoint='generate_qr')
@login_required
def generate_qr(session_uuid):
    lecturer = get_current_lecturer()
    sess = AttendanceSession.query.filter_by(session_uuid=session_uuid, lecturer_id=lecturer.id).first_or_404()

    attendance_url = build_attendance_url(request, session_uuid)
    buf = generate_qr_image(attendance_url)
    return send_file(buf, mimetype='image/png', as_attachment=False)


@main_bp.route('/session/<session_uuid>/export', endpoint='export_csv')
@login_required
def export_csv(session_uuid):
    lecturer = get_current_lecturer()
    sess = AttendanceSession.query.filter_by(session_uuid=session_uuid, lecturer_id=lecturer.id).first_or_404()
    records = AttendanceRecord.query.filter_by(session_id=sess.id).order_by(AttendanceRecord.submitted_at.asc()).all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(['#', 'Student Name', 'Student ID', 'Submitted At', 'IP Address'])
    for i, record in enumerate(records, 1):
        writer.writerow([i, record.student_name, record.student_id,
                         record.submitted_at.strftime('%Y-%m-%d %H:%M:%S'), record.ip_address or 'N/A'])

    output = io.BytesIO(buf.getvalue().encode('utf-8-sig'))
    filename = f"attendance_{sess.course_code}_{sess.created_at.strftime('%Y%m%d_%H%M')}.csv"
    return send_file(output, mimetype='text/csv', as_attachment=True, download_name=filename)


@main_bp.route('/attend/<session_uuid>', methods=['GET', 'POST'], endpoint='attend')
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
            return render_template('attend.html', sess=sess, errors=errors, student_name=student_name, student_id=student_id)

        if not sess.is_open:
            return render_template('attend_closed.html', sess=sess, reason='expired')

        submission_hash = AttendanceRecord.make_hash(sess.id, student_id)
        existing = AttendanceRecord.query.filter_by(submission_hash=submission_hash).first()
        if existing:
            return render_template('attend_duplicate.html', sess=sess, student_name=student_name,
                                   submitted_at=existing.submitted_at)

        ip = request.headers.get('X-Forwarded-For', request.remote_addr) or ''
        if ',' in ip:
            ip = ip.split(',')[0].strip()

        record = AttendanceRecord(session_id=sess.id, student_name=student_name,
                                  student_id=student_id.upper(), ip_address=ip,
                                  submission_hash=submission_hash)
        db.session.add(record)
        db.session.commit()

        return render_template('attend_success.html', sess=sess, student_name=student_name,
                               student_id=student_id.upper(), submitted_at=record.submitted_at)

    return render_template('attend.html', sess=sess, errors=[], student_name='', student_id='')


@main_bp.route('/api/session/<session_uuid>/status', endpoint='session_status')
def session_status(session_uuid):
    sess = AttendanceSession.query.filter_by(session_uuid=session_uuid).first_or_404()
    return jsonify({'is_open': sess.is_open, 'is_expired': sess.is_expired,
                    'time_remaining': sess.time_remaining_seconds, 'student_count': sess.student_count})
