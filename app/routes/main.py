import csv
import io
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)

from app import csrf, db
from app.models import (
    ROLE_DEAN,
    ROLE_TA,
    VALID_ROLES,
    AttendanceRecord,
    AttendanceSession,
    Lecturer,
    normalize_role,
)
from app.services.attendance_service import build_attendance_url, generate_qr_image

main_bp = Blueprint('main', __name__)


# ── Auth / RBAC helpers ──────────────────────────────────────────────────────
def get_current_lecturer():
    lecturer_id = session.get('lecturer_id')
    return Lecturer.query.get(lecturer_id) if lecturer_id else None


def login_required(f):
    """Require an authenticated, active user. Also enforces the forced
    password change before any protected page can be reached."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_lecturer()
        if user is None:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('main.login'))
        # An account disabled mid-session must lose access immediately.
        if not user.is_active:
            session.clear()
            abort(403)
        # Force the first-login password change before anything else.
        if user.must_change_password and request.endpoint not in ('main.change_password', 'main.logout'):
            return redirect(url_for('main.change_password'))
        return f(*args, **kwargs)

    return decorated


def role_required(*roles):
    """Restrict a route to the given canonical roles (e.g. "DEAN", "TA").

    Returns HTTP 403 for an authenticated user whose role is not permitted,
    and redirects anonymous users to the login page. Roles are compared
    against the server-side stored value only — never anything from the
    request — so the client cannot escalate privileges."""
    allowed = set(roles)

    def wrapper(f):
        @wraps(f)
        @login_required
        def decorated(*args, **kwargs):
            user = get_current_lecturer()
            if user is None:
                return redirect(url_for('main.login'))
            if user.effective_role not in allowed:
                abort(403)
            return f(*args, **kwargs)

        return decorated

    return wrapper


def dashboard_url_for(user) -> str:
    """The landing dashboard endpoint for a given user's role."""
    if user and user.effective_role == ROLE_DEAN:
        return url_for('main.dean_dashboard')
    return url_for('main.ta_dashboard')


# ── Public / auth routes ─────────────────────────────────────────────────────
@main_bp.route('/')
def index():
    user = get_current_lecturer()
    if user:
        return redirect(dashboard_url_for(user))
    return redirect(url_for('main.login'))


@main_bp.route('/login', methods=['GET', 'POST'], endpoint='login')
def login():
    existing = get_current_lecturer()
    if existing:
        return redirect(dashboard_url_for(existing))

    if request.method == 'POST':
        identifier = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        # Accept either email or username as the login identifier.
        lecturer = (
            Lecturer.query.filter_by(email=identifier).first()
            or Lecturer.query.filter(db.func.lower(Lecturer.username) == identifier).first()
        )
        if lecturer and lecturer.check_password(password):
            if not lecturer.is_active:
                # Inactive accounts may not log in.
                abort(403)
            session.clear()
            session['lecturer_id'] = lecturer.id
            session['lecturer_name'] = lecturer.name
            session['lecturer_role'] = lecturer.effective_role
            if lecturer.must_change_password:
                flash('Please set a new password before continuing.', 'warning')
                return redirect(url_for('main.change_password'))
            flash(f'Welcome back, {lecturer.name}!', 'success')
            return redirect(dashboard_url_for(lecturer))
        flash('Invalid credentials.', 'danger')

    return render_template('login.html')


@main_bp.route('/logout', endpoint='logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.login'))


@main_bp.route('/change-password', methods=['GET', 'POST'], endpoint='change_password')
@login_required
def change_password():
    user = get_current_lecturer()
    if request.method == 'POST':
        current = request.form.get('current_password', '')
        new = request.form.get('new_password', '')
        confirm = request.form.get('confirm_password', '')

        errors = []
        # When forced to change, the temporary password is the current one.
        if not user.check_password(current):
            errors.append('Current password is incorrect.')
        if len(new) < 8:
            errors.append('New password must be at least 8 characters.')
        if new != confirm:
            errors.append('New passwords do not match.')
        if new and user.check_password(new):
            errors.append('New password must be different from the current one.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('change_password.html', user=user, forced=user.must_change_password)

        user.set_password(new)
        user.must_change_password = False
        db.session.commit()
        session['lecturer_role'] = user.effective_role
        flash('Password updated successfully.', 'success')
        return redirect(dashboard_url_for(user))

    return render_template('change_password.html', user=user, forced=user.must_change_password)


# ── Role dashboards ──────────────────────────────────────────────────────────
@main_bp.route('/dashboard', endpoint='dashboard')
@login_required
def dashboard():
    # Backwards-compatible entry point: dispatch to the role's dashboard.
    return redirect(dashboard_url_for(get_current_lecturer()))


@main_bp.route('/dean/dashboard', endpoint='dean_dashboard')
@role_required(ROLE_DEAN)
def dean_dashboard():
    dean = get_current_lecturer()

    total_tas = Lecturer.query.filter_by(role=ROLE_TA).count()
    active_tas = Lecturer.query.filter_by(role=ROLE_TA, is_active=True).count()
    total_sessions = AttendanceSession.query.count()

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    attendance_today = AttendanceRecord.query.filter(
        AttendanceRecord.submitted_at >= today_start
    ).count()
    total_attendance = AttendanceRecord.query.count()

    recent_records = (
        AttendanceRecord.query.order_by(AttendanceRecord.submitted_at.desc()).limit(10).all()
    )

    # Last 7 days check-in counts for a simple chart.
    chart_labels, chart_values = [], []
    for offset in range(6, -1, -1):
        day = today_start - timedelta(days=offset)
        next_day = day + timedelta(days=1)
        count = AttendanceRecord.query.filter(
            AttendanceRecord.submitted_at >= day,
            AttendanceRecord.submitted_at < next_day,
        ).count()
        chart_labels.append(day.strftime('%d %b'))
        chart_values.append(count)

    return render_template(
        'dean_dashboard.html',
        dean=dean,
        total_tas=total_tas,
        active_tas=active_tas,
        total_sessions=total_sessions,
        attendance_today=attendance_today,
        total_attendance=total_attendance,
        recent_records=recent_records,
        chart_labels=chart_labels,
        chart_values=chart_values,
    )


@main_bp.route('/ta/dashboard', endpoint='ta_dashboard')
@role_required(ROLE_DEAN, ROLE_TA)
def ta_dashboard():
    lecturer = get_current_lecturer()
    sessions_list = (
        AttendanceSession.query.filter_by(lecturer_id=lecturer.id)
        .order_by(AttendanceSession.created_at.desc())
        .all()
    )

    total_sessions = len(sessions_list)
    active_sessions = sum(1 for s in sessions_list if s.is_open)
    total_students = sum(s.student_count for s in sessions_list)

    return render_template(
        'dashboard.html',
        lecturer=lecturer,
        sessions=sessions_list,
        total_sessions=total_sessions,
        active_sessions=active_sessions,
        total_students=total_students,
    )


# ── User management (DEAN only) ──────────────────────────────────────────────
def _dean_count() -> int:
    return Lecturer.query.filter_by(role=ROLE_DEAN, is_active=True).count()


@main_bp.route('/users', endpoint='users_list')
@role_required(ROLE_DEAN)
def users_list():
    users = Lecturer.query.order_by(Lecturer.created_at.desc()).all()
    return render_template('users/list.html', users=users)


@main_bp.route('/users/create', methods=['GET', 'POST'], endpoint='users_create')
@role_required(ROLE_DEAN)
def users_create():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', ROLE_TA).strip()

        errors = []
        if not name:
            errors.append('Full name is required.')
        if not email:
            errors.append('Email is required.')
        if not username:
            errors.append('Username is required.')
        if len(password) < 8:
            errors.append('Temporary password must be at least 8 characters.')
        if role not in VALID_ROLES:
            errors.append('Invalid role selected.')
        if email and Lecturer.query.filter_by(email=email).first():
            errors.append('A user with that email already exists.')
        if username and Lecturer.query.filter(
            db.func.lower(Lecturer.username) == username.lower()
        ).first():
            errors.append('A user with that username already exists.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template(
                'users/form.html', mode='create', user=None, roles=VALID_ROLES,
                form={'name': name, 'email': email, 'username': username, 'role': role},
            )

        user = Lecturer(name=name, email=email, username=username, is_active=True,
                        must_change_password=True)
        user.set_role(role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash(f'Account for {name} created. They must change the password on first login.', 'success')
        return redirect(url_for('main.users_list'))

    return render_template('users/form.html', mode='create', user=None, roles=VALID_ROLES, form={})


@main_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'], endpoint='users_edit')
@role_required(ROLE_DEAN)
def users_edit(user_id):
    user = Lecturer.query.get_or_404(user_id)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        username = request.form.get('username', '').strip()
        role = request.form.get('role', user.effective_role).strip()

        errors = []
        if not name:
            errors.append('Full name is required.')
        if not email:
            errors.append('Email is required.')
        if not username:
            errors.append('Username is required.')
        if role not in VALID_ROLES:
            errors.append('Invalid role selected.')

        clash = Lecturer.query.filter(Lecturer.email == email, Lecturer.id != user.id).first()
        if email and clash:
            errors.append('Another user already uses that email.')
        uclash = Lecturer.query.filter(
            db.func.lower(Lecturer.username) == username.lower(), Lecturer.id != user.id
        ).first()
        if username and uclash:
            errors.append('Another user already uses that username.')

        # Prevent demoting/locking out the final DEAN.
        if user.effective_role == ROLE_DEAN and role != ROLE_DEAN and _dean_count() <= 1:
            errors.append('Cannot change the role of the last active DEAN.')

        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template(
                'users/form.html', mode='edit', user=user, roles=VALID_ROLES,
                form={'name': name, 'email': email, 'username': username, 'role': role},
            )

        user.name = name
        user.email = email
        user.username = username
        user.set_role(role)
        db.session.commit()
        flash('User updated successfully.', 'success')
        return redirect(url_for('main.users_list'))

    return render_template(
        'users/form.html', mode='edit', user=user, roles=VALID_ROLES,
        form={'name': user.name, 'email': user.email, 'username': user.username or '',
              'role': user.effective_role},
    )


@main_bp.route('/users/<int:user_id>/disable', methods=['POST'], endpoint='users_disable')
@role_required(ROLE_DEAN)
def users_disable(user_id):
    user = Lecturer.query.get_or_404(user_id)
    # Toggle active state, with a guard so the last DEAN cannot be disabled.
    if user.is_active:
        if user.effective_role == ROLE_DEAN and _dean_count() <= 1:
            flash('Cannot disable the last active DEAN account.', 'danger')
            return redirect(url_for('main.users_list'))
        user.is_active = False
        flash(f'{user.name} has been deactivated.', 'info')
    else:
        user.is_active = True
        flash(f'{user.name} has been reactivated.', 'success')
    db.session.commit()
    return redirect(url_for('main.users_list'))


@main_bp.route('/users/<int:user_id>/reset-password', methods=['POST'], endpoint='users_reset_password')
@role_required(ROLE_DEAN)
def users_reset_password(user_id):
    user = Lecturer.query.get_or_404(user_id)
    temp_password = request.form.get('temp_password', '').strip()
    if len(temp_password) < 8:
        flash('Temporary password must be at least 8 characters.', 'danger')
        return redirect(url_for('main.users_list'))
    user.set_password(temp_password)
    user.must_change_password = True
    db.session.commit()
    flash(f"{user.name}'s password was reset. They must change it on next login.", 'success')
    return redirect(url_for('main.users_list'))


# ── Attendance session management (TA + DEAN) ────────────────────────────────
@main_bp.route('/session/new', methods=['GET', 'POST'], endpoint='new_session')
@role_required(ROLE_DEAN, ROLE_TA)
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

        expires_at = datetime.utcnow() + timedelta(minutes=duration_minutes)
        sess = AttendanceSession(title=title, course_name=course_name, course_code=course_code,
                                 lecturer_id=lecturer.id, expires_at=expires_at)
        db.session.add(sess)
        db.session.commit()
        flash('Session created successfully!', 'success')
        return redirect(url_for('main.session_detail', session_uuid=sess.session_uuid))

    return render_template('new_session.html', lecturer=lecturer)


@main_bp.route('/session/<session_uuid>', endpoint='session_detail')
@role_required(ROLE_DEAN, ROLE_TA)
def session_detail(session_uuid):
    lecturer = get_current_lecturer()
    sess = _owned_session_or_404(session_uuid, lecturer)
    records = AttendanceRecord.query.filter_by(session_id=sess.id).order_by(AttendanceRecord.submitted_at.asc()).all()

    attendance_url = build_attendance_url(request, session_uuid)

    return render_template('session_detail.html', lecturer=lecturer, sess=sess, records=records, attendance_url=attendance_url)


@main_bp.route('/session/<session_uuid>/close', methods=['POST'], endpoint='close_session')
@role_required(ROLE_DEAN, ROLE_TA)
def close_session(session_uuid):
    lecturer = get_current_lecturer()
    sess = _owned_session_or_404(session_uuid, lecturer)
    sess.is_active = False
    db.session.commit()
    flash('Session closed successfully.', 'info')
    return redirect(url_for('main.session_detail', session_uuid=session_uuid))


@main_bp.route('/session/<session_uuid>/qr', endpoint='generate_qr')
@role_required(ROLE_DEAN, ROLE_TA)
def generate_qr(session_uuid):
    lecturer = get_current_lecturer()
    sess = _owned_session_or_404(session_uuid, lecturer)

    attendance_url = build_attendance_url(request, session_uuid)
    buf = generate_qr_image(attendance_url)
    return send_file(buf, mimetype='image/png', as_attachment=False)


@main_bp.route('/session/<session_uuid>/export', endpoint='export_csv')
@role_required(ROLE_DEAN, ROLE_TA)
def export_csv(session_uuid):
    lecturer = get_current_lecturer()
    sess = _owned_session_or_404(session_uuid, lecturer)
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


def _owned_session_or_404(session_uuid, lecturer):
    """Fetch a session the current user is allowed to manage.

    A TA may only touch their own sessions; a DEAN may manage any session."""
    query = AttendanceSession.query.filter_by(session_uuid=session_uuid)
    if not lecturer.is_dean:
        query = query.filter_by(lecturer_id=lecturer.id)
    return query.first_or_404()


# ── Public student attendance (no account, CSRF-exempt) ──────────────────────
@main_bp.route('/attend/<session_uuid>', methods=['GET', 'POST'], endpoint='attend')
@csrf.exempt
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
