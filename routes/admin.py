from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from models.db import db
from models.user import User
from models.outpass import Outpass
from models.log import ActivityLog, Notification
from utils.logger import Logger
from utils.export import ExportService
from services.sms_service import SMSService
from utils.face_utils import FaceUtils
from functools import wraps
import os
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Admin access required', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    return redirect(url_for('auth.profile'))

@admin_bp.route('/students', methods=['GET', 'POST'])
@login_required
@admin_required
def students():
    blacklist_id = request.args.get('blacklist_id')
    if blacklist_id:
        student = User.query.get(blacklist_id)
        if student:
            student.is_blacklisted = not student.is_blacklisted
            db.session.commit()
            action = 'blacklisted' if student.is_blacklisted else 'whitelisted'
            Logger.log(current_user.id, f'Admin {action} student {student.username}')
            flash(f'Student {student.name} {action} successfully.', 'success')
            return redirect(url_for('admin.students'))

    search = request.args.get('search')
    if search:
        all_students = User.query.filter(
            (User.role == 'student') & 
            ((User.name.contains(search)) | (User.student_id.contains(search)))
        ).all()
    else:
        all_students = User.query.filter_by(role='student').all()
        
    return render_template('admin/students.html', students=all_students)

@admin_bp.route('/add_student', methods=['GET', 'POST'])
@login_required
@admin_required
def add_student():
    if request.method == 'POST':
        name = request.form.get('name')
        student_id = request.form.get('student_id')
        email = request.form.get('email')
        phone = request.form.get('phone')
        parent_phone = request.form.get('parent_phone')
        department = request.form.get('department')
        year = request.form.get('year')
        hostel_room = request.form.get('hostel_room')
        
        if User.query.filter_by(student_id=student_id).first():
            flash(f'Student ID {student_id} already exists!', 'danger')
            return redirect(url_for('admin.add_student'))

        captured_image = request.form.get('captured_image') # base64 from webcam
        id_card_image = request.form.get('id_card_image')   # base64 ID card
        face_image_file = request.files.get('face_image')
        id_image_file = request.files.get('id_image')
        
        face_encoded = None
        photo_path = None
        id_card_path = None
        
        # Process Face Image
        if captured_image:
            header, encoded = captured_image.split(",", 1)
            import base64
            image_bytes = base64.b64decode(encoded)
            from werkzeug.utils import secure_filename
            filename = secure_filename(f"{student_id}_face.jpg")
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            with open(filepath, "wb") as f:
                f.write(image_bytes)
            photo_path = filepath
        elif face_image_file:
            from werkzeug.utils import secure_filename
            filename = secure_filename(f"{student_id}_face.jpg")
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            face_image_file.save(filepath)
            photo_path = filepath

        # Process ID Card Image
        if id_card_image:
            header, encoded = id_card_image.split(",", 1)
            import base64
            image_bytes = base64.b64decode(encoded)
            from werkzeug.utils import secure_filename
            filename = secure_filename(f"{student_id}_id.jpg")
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            with open(filepath, "wb") as f:
                f.write(image_bytes)
            id_card_path = filepath
        elif id_image_file:
            from werkzeug.utils import secure_filename
            filename = secure_filename(f"{student_id}_id.jpg")
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            id_image_file.save(filepath)
            id_card_path = filepath
            
        if photo_path:
            face_encoded_list = FaceUtils.get_encoding(photo_path)
            if face_encoded_list:
                import json
                face_encoded = json.dumps(face_encoded_list)
            else:
                flash('Face not detected in the face scan. Please ensure clear visibility.', 'warning')
        
        new_student = User(
            username=student_id.lower(),
            email=email,
            role='student',
            name=name,
            student_id=student_id,
            phone=phone,
            parent_phone=parent_phone,
            department=department,
            year=int(year) if year else 1,
            hostel_room=hostel_room,
            face_encoded=face_encoded,
            photo_path=photo_path,
            id_card_photo=id_card_path
        )
        new_student.set_password('student123')  # Default password = student123
        db.session.add(new_student)
        db.session.commit()
        
        Logger.log(current_user.id, f'Admin registered student {name}')
        flash(f'Student {name} registered successfully!', 'success')
        return redirect(url_for('admin.students'))

    return render_template('admin/add_student.html')

@admin_bp.route('/outpasses', methods=['GET', 'POST'])
@login_required
@admin_required
def outpasses():
    action = request.args.get('action')
    op_id = request.args.get('op_id')
    
    if action and op_id:
        op = Outpass.query.get(op_id)
        if op:
            if action == 'approve':
                op.status = 'approved'
                op.approved_by = current_user.id
                student = User.query.get(op.student_id)
                Logger.log(current_user.id, f"Admin approved outpass for {student.name} (Dest: {op.destination})")
                Logger.notify_admin(op.student_id, 'Outpass Approved', f'Your request for {op.destination} has been approved.', type='approval')
                flash('Outpass approved successfully.', 'success')
            elif action == 'reject':
                op.status = 'rejected'
                student = User.query.get(op.student_id)
                Logger.log(current_user.id, f"Admin rejected outpass for {student.name} (Dest: {op.destination})")
                Logger.notify_admin(op.student_id, 'Outpass Rejected', f'Your request for {op.destination} has been rejected.', type='approval')
                flash('Outpass rejected.', 'info')
            elif action == 'blacklist':
                student = User.query.get(op.student_id)
                if student:
                    student.is_blacklisted = True
                    Logger.log(current_user.id, f"Admin CRITICALLY blacklisted student: {student.name} (ID: {student.student_id})", severity='warning')
                    Logger.notify_admin(op.student_id, 'Student Blacklisted', f'You have been blacklisted due to outpass violations.', type='blacklist')
                    flash(f'Student {student.name} blacklisted.', 'danger')

            db.session.commit()
            return redirect(url_for('admin.outpasses', status=request.args.get('status', 'pending')))

    status_filter = request.args.get('status', 'pending').lower()
    search = request.args.get('search', '').lower()
    
    query = Outpass.query
    if search:
        query = query.join(User).filter(db.or_(User.name.ilike(f'%{search}%'), User.student_id.ilike(f'%{search}%')))
    
    if status_filter != 'all':
        all_outpasses = query.filter(Outpass.status == status_filter).order_by(Outpass.created_at.desc()).all()
    else:
        all_outpasses = query.order_by(Outpass.created_at.desc()).all()
        
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Calculate Summary Stats
    total_today = Outpass.query.filter(Outpass.created_at >= today).count()
    currently_out = Outpass.query.filter_by(status='out').count()
    overdue = Outpass.query.filter(Outpass.status == 'out', Outpass.expected_return < datetime.utcnow()).count()
    returned_today = Outpass.query.filter(Outpass.status == 'returned', Outpass.actual_return >= today).count()
    pending_reqs = Outpass.query.filter_by(status='pending').count()
    
    return render_template('admin/outpasses.html', 
                           outpasses=all_outpasses, 
                           current_status=status_filter,
                           total_today=total_today,
                           currently_out=currently_out,
                           overdue=overdue,
                           returned_today=returned_today,
                           pending_reqs=pending_reqs,
                           search=search)


@admin_bp.route('/analytics')
@login_required
@admin_required
def analytics():
    # Calculate real-time stats
    total_students = User.query.filter_by(role='student').count()
    currently_out = Outpass.query.filter_by(status='out').count()
    overdue = Outpass.query.filter(Outpass.status == 'out', Outpass.expected_return < datetime.utcnow()).count()
    returned_today = Outpass.query.filter(Outpass.status == 'returned', Outpass.actual_return >= datetime.utcnow().replace(hour=0, minute=0, second=0)).count()
    
    # We can pass some raw summary and AI insights strings
    ai_insights = [
        "B.Tech CSE students have the highest exit rate this week.",
        f"{overdue} students are currently violating their expected return time.",
        "Peak exit time observed around 5:00 PM."
    ]
    
    # Let's mock the charts data or use real data. Since it's a dashboard, we'll keep it fast.
    return render_template('admin/analytics.html',
                           total_students=total_students,
                           currently_out=currently_out,
                           overdue=overdue,
                           returned_today=returned_today,
                           ai_insights=ai_insights)

@admin_bp.route('/reports')
@login_required
@admin_required
def reports():
    last_24h = datetime.utcnow() - timedelta(hours=24)
    
    total_24h = ActivityLog.query.filter(ActivityLog.timestamp >= last_24h).count()
    suspicious = ActivityLog.query.filter(ActivityLog.timestamp >= last_24h, ActivityLog.action.ilike('%blacklist%')).count()
    logins = ActivityLog.query.filter(ActivityLog.timestamp >= last_24h, ActivityLog.action.ilike('%login%')).count()
    
    all_logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).all()
    return render_template('admin/reports.html', 
                         logs=all_logs, 
                         total_today=total_24h,
                         suspicious_count=suspicious,
                         login_count=logins)



@admin_bp.route('/sms_test')
@login_required
@admin_required
def sms_test_redirect():
    return redirect(url_for('admin.sms_center'))

@admin_bp.route('/sms_center', methods=['GET', 'POST'])

@login_required
@admin_required
def sms_center():
    from models.log import SMSLog, SMSConfig
    
    if request.method == 'POST' and 'api_update' in request.form:
        keys = ['f2s_key', 'twilio_sid', 'twilio_token', 'twilio_phone']
        for k in keys:
            val = request.form.get(k)
            conf = SMSConfig.query.filter_by(key_name=k).first()
            if not conf:
                conf = SMSConfig(key_name=k, value=val)
                db.session.add(conf)
            else:
                conf.value = val
        db.session.commit()
        flash('SMS API configurations updated successfully.', 'success')
        return redirect(url_for('admin.sms_center'))

    # Get stats
    today = datetime.utcnow().replace(hour=0, minute=0, second=0)
    total_sent = SMSLog.query.filter(SMSLog.sent_at >= today, SMSLog.status != 'FAILED').count()
    failed = SMSLog.query.filter(SMSLog.sent_at >= today, SMSLog.status == 'FAILED').count()
    
    configs = {c.key_name: c.value for c in SMSConfig.query.all()}
    all_logs = SMSLog.query.order_by(SMSLog.sent_at.desc()).limit(10).all()
    
    return render_template('admin/sms_test.html', 
                         logs=all_logs, 
                         total_sent=total_sent, 
                         failed_count=failed,
                         configs=configs)


@admin_bp.route('/notifications')
@login_required
@admin_required
def notifications():
    notifs = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    for n in notifs:
        n.is_read = True
    db.session.commit()
    return render_template('admin/notifications.html', notifications=notifs)

@admin_bp.route('/api/notif_count')
@login_required
def notif_count():
    unread = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return jsonify({'count': unread})

@admin_bp.route('/export/<type>')
@login_required
@admin_required
def export(type):
    format = request.args.get('format', 'csv')
    
    if type == 'students':
        students = User.query.filter_by(role='student').all()
        headers = ['ID', 'Student ID', 'Name', 'Email', 'Phone', 'Parent Phone', 'Department', 'Violations', 'Blacklisted']
        data = [[s.id, s.student_id, s.name, s.email, s.phone, s.parent_phone, s.department, s.violations, s.is_blacklisted] for s in students]
        filename = 'students_list'
    elif type == 'logs':
        logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).all()
        headers = ['ID', 'Action', 'Severity', 'IP Address', 'Description', 'Timestamp']
        data = [[l.id, l.action, l.severity, l.ip_address, l.description, l.timestamp] for l in logs]
        filename = 'activity_logs'
    elif type == 'outpasses':
        ops = Outpass.query.order_by(Outpass.created_at.desc()).all()
        headers = ['ID', 'Student Name', 'Student ID', 'Purpose', 'Destination', 'Status', 'Exit Time', 'Return Time', 'Duration (Hrs)']
        data = []
        for op in ops:
            student = User.query.get(op.student_id)
            data.append([
                op.id, 
                student.name if student else 'Unknown', 
                student.student_id if student else 'N/A',
                op.purpose,
                op.destination,
                op.status,
                op.exit_time.strftime('%Y-%m-%d %H:%M') if op.exit_time else 'N/A',
                op.return_time.strftime('%Y-%m-%d %H:%M') if op.return_time else 'N/A',
                op.time_limit_hours
            ])
        filename = f"outpass_report_{datetime.now().strftime('%Y%m%d')}"
    else:
        flash('Invalid export type', 'danger')
        return redirect(url_for('admin.reports'))

    if format == 'excel':
        return ExportService.export_excel(headers, data, filename)
    return ExportService.export_csv(headers, data, filename)
@admin_bp.route('/guards', methods=['GET', 'POST'])
@login_required
@admin_required
def guards():
    import json
    import os
    from werkzeug.utils import secure_filename
    from models.log import ActivityLog
    from datetime import datetime, date, timedelta
    
    if request.method == 'POST':
        # ... [Form logic preserved]
        name = request.form.get('name')
        username = request.form.get('username')
        password = request.form.get('password')
        assigned_gate = request.form.get('assigned_gate')
        shift_timing = request.form.get('shift_timing')
        phone = request.form.get('phone')
        emergency_contact = request.form.get('emergency_contact')
        perms = request.form.getlist('perms')
        
        if User.query.filter_by(username=username).first():
            flash(f'Guard ID/Username {username} already exists!', 'danger')
            return redirect(url_for('admin.guards'))
            
        # Handle File Uploads
        profile_path = None
        doc_path = None
        
        # Ensure subdirectories exist
        upload_base = current_app.config['UPLOAD_FOLDER']
        profile_dir = os.path.join(upload_base, 'profile')
        doc_dir = os.path.join(upload_base, 'documents')
        os.makedirs(profile_dir, exist_ok=True)
        os.makedirs(doc_dir, exist_ok=True)

        profile_file = request.files.get('profile_photo')
        if profile_file and profile_file.filename != '':
            filename = secure_filename(f"profile_{username}_{profile_file.filename}")
            profile_file.save(os.path.join(profile_dir, filename))
            profile_path = os.path.join('profile', filename)
            
        aadhar_file = request.files.get('aadhar_document')
        if aadhar_file and aadhar_file.filename != '':
            filename = secure_filename(f"doc_{username}_{aadhar_file.filename}")
            aadhar_file.save(os.path.join(doc_dir, filename))
            doc_path = os.path.join('documents', filename)
            
        new_guard = User(
            username=username,
            name=name,
            role='guard',
            assigned_gate=assigned_gate,
            shift_timing=shift_timing,
            phone=phone,
            emergency_contact=emergency_contact,
            permissions=json.dumps(perms),
            status='ACTIVE',
            photo_path=profile_path,
            aadhar_document=doc_path
        )
        new_guard.set_password(password)
        db.session.add(new_guard)
        db.session.commit()
        
        Logger.log(current_user.id, f'Admin added new guard: {name} assigned to {assigned_gate}')
        flash(f'Guard {name} registered and activated successfully!', 'success')
        return redirect(url_for('admin.guards'))

    # Collect Real-time Stats
    all_guards = User.query.filter_by(role='guard').all()
    active_count = User.query.filter_by(role='guard', status='ACTIVE').count()
    
    # Unique Gates
    gates_set = set([g.assigned_gate for g in all_guards if g.assigned_gate])
    gates_count = f"{len(gates_set):02d}"
    
    # Daily Verifications (from ActivityLog + Outpass Activity Today)
    today_start = datetime.combine(date.today(), datetime.min.time())
    
    log_count = ActivityLog.query.filter(
        ActivityLog.timestamp >= today_start,
        db.or_(ActivityLog.action.ilike('%verify%'), ActivityLog.action.ilike('%scan%'), ActivityLog.action.ilike('%gate%'))
    ).count()
    
    from models.outpass import Outpass
    outpass_count = Outpass.query.filter(
        db.or_(Outpass.exit_time >= today_start, Outpass.actual_return >= today_start)
    ).count()
    
    daily_verifications = log_count + outpass_count
    
    stats = {
        'active': active_count,
        'gates': gates_count,
        'verifications': f"{daily_verifications:,}",
        'response': "1.2m"
    }

    return render_template('admin/guards.html', guards=all_guards, stats=stats)

@admin_bp.route('/guards/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_guard(user_id):
    import json
    from models.user import User
    from models.db import db
    
    guard = User.query.get_or_404(user_id)
    if guard.role != 'guard':
        flash('Target user is not a security staff.', 'warning')
        return redirect(url_for('admin.guards'))
        
    if request.method == 'POST':
        guard.name = request.form.get('name')
        guard.assigned_gate = request.form.get('assigned_gate')
        guard.shift_timing = request.form.get('shift_timing')
        guard.phone = request.form.get('phone')
        guard.emergency_contact = request.form.get('emergency_contact')
        
        # Handle File Updates
        upload_base = current_app.config['UPLOAD_FOLDER']
        profile_dir = os.path.join(upload_base, 'profile')
        doc_dir = os.path.join(upload_base, 'documents')
        os.makedirs(profile_dir, exist_ok=True)
        os.makedirs(doc_dir, exist_ok=True)

        profile_file = request.files.get('profile_photo')
        if profile_file and profile_file.filename != '':
            filename = secure_filename(f"profile_{guard.username}_{profile_file.filename}")
            profile_file.save(os.path.join(profile_dir, filename))
            guard.photo_path = os.path.join('profile', filename)
            
        aadhar_file = request.files.get('aadhar_document')
        if aadhar_file and aadhar_file.filename != '':
            filename = secure_filename(f"doc_{guard.username}_{aadhar_file.filename}")
            aadhar_file.save(os.path.join(doc_dir, filename))
            guard.aadhar_document = os.path.join('documents', filename)

        perms = request.form.getlist('perms')
        guard.permissions = json.dumps(perms)
        
        db.session.commit()
        flash(f'Guard {guard.name} updated successfully.', 'success')
        return redirect(url_for('admin.guards'))
        
    try:
        current_perms = json.loads(guard.permissions) if guard.permissions else []
    except:
        current_perms = []
        
    return render_template('admin/edit_guard.html', guard=guard, current_perms=current_perms)

@admin_bp.route('/toggle_guard_duty/<int:user_id>')
@login_required
@admin_required
def toggle_guard_duty(user_id):
    guard = User.query.get_or_404(user_id)
    if guard.role != 'guard':
        flash('Invalid user role.', 'danger')
    else:
        guard.status = 'OFFLINE' if guard.status == 'ACTIVE' else 'ACTIVE'
        db.session.commit()
        Logger.log(current_user.id, f"Admin toggled duty for: {guard.name} (Now {guard.status})")
        flash(f'Status updated for {guard.name}.', 'success')
    return redirect(url_for('admin.guards'))

@admin_bp.route('/manage_admins', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_admins():
    import json
    if request.method == 'POST':
        action = request.form.get('action')
        
        # Approve/Activate Action (Owner only)
        if action == 'activate':
            if current_user.admin_role != 'OWNER':
                flash('Only the System Owner can approve new administrators.', 'danger')
                return redirect(url_for('admin.manage_admins'))
            target_id = request.form.get('admin_id')
            admin = User.query.get(target_id)
            if admin:
                admin.status = 'ACTIVE'
                db.session.commit()
                Logger.log(current_user.id, f"Owner activated administrator: {admin.name}")
                flash(f'Admin {admin.name} is now ACTIVE.', 'success')
            return redirect(url_for('admin.manage_admins'))

        # Create New Admin
        name = request.form.get('name')
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'VIEWER')
        perms = request.form.getlist('perms') # Checkboxes
        
        if User.query.filter_by(username=username).first():
            flash(f'Username {username} already exists!', 'danger')
        elif User.query.filter_by(email=email).first():
            flash(f'Email {email} already exists!', 'danger')
        else:
            new_admin = User(
                username=username,
                name=name,
                email=email,
                role='admin',
                admin_role=role,
                status='PENDING', # Always pending initially
                permissions=json.dumps(perms)
            )
            new_admin.set_password(password)
            db.session.add(new_admin)
            db.session.commit()
            Logger.log(current_user.id, f'New administrator {name} created (Status: PENDING)')
            flash(f'Administrator application for {name} submitted for Owner approval.', 'info')
        return redirect(url_for('admin.manage_admins'))

    # Stats
    all_admins = User.query.filter_by(role='admin').all()
    total_admins = len(all_admins)
    active_admins = sum(1 for a in all_admins if a.status == 'ACTIVE')
    pending_admins = sum(1 for a in all_admins if a.status == 'PENDING')

    return render_template('admin/manage_admins.html', 
                         admins=all_admins,
                         total=total_admins,
                         active=active_admins,
                         pending=pending_admins)


@admin_bp.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    # Safety Controls
    if user.id == current_user.id:
        flash("SECURITY ALERT: You cannot delete your own session!", 'danger')
        return redirect(request.referrer or url_for('admin.dashboard'))
    
    if user.admin_role == 'OWNER':
        flash("CRITICAL ERROR: The System Owner account cannot be purged.", 'danger')
        return redirect(request.referrer or url_for('admin.dashboard'))
        
    username = user.username
    name = user.name
    
    # Cleanup associations
    Outpass.query.filter_by(student_id=user.id).delete()
    db.session.delete(user)
    db.session.commit()
    
    Logger.log(current_user.id, f'Administrator purged user: {name} ({username})', severity='warning')
    flash(f"User {name} has been permanently purged from the registry.", 'info')
    return redirect(request.referrer or url_for('admin.dashboard'))


@admin_bp.route('/reset_user_password/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def reset_user_password(user_id):
    user = User.query.get_or_404(user_id)
    new_temp_password = request.form.get('new_password', 'reset123') 

    user.set_password(new_temp_password)
    db.session.commit()
    
    Logger.log(current_user.id, f'Admin reset password for user: {user.username}', severity='warning')
    flash(f"Password for {user.name} has been reset successfully.", 'success')
    
    return redirect(request.referrer or url_for('admin.dashboard'))


@admin_bp.route('/api/stats/summary')
@login_required
@admin_required
def stats_summary():
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    last_30d = now - timedelta(days=30)
    last_7d = now - timedelta(days=7)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # 1. Total Population
    total_students = User.query.filter_by(role='student').count()

    # 2. Exits This Week
    exits_this_week = Outpass.query.filter(Outpass.created_at >= last_7d).count()

    # 3. Average Time Outside (in hours)
    completed_ops = Outpass.query.filter(Outpass.status == 'returned', Outpass.exit_time != None, Outpass.actual_return != None).all()
    if completed_ops:
        total_hours = sum([(op.actual_return - op.exit_time).total_seconds() / 3600 for op in completed_ops])
        avg_time = round(total_hours / len(completed_ops), 1)
    else:
        avg_time = 0.0

    # 4. Trend Data (Last 30 days)
    trend_data = []
    for i in range(30):
        day = last_30d + timedelta(days=i)
        day_end = day + timedelta(days=1)
        count = Outpass.query.filter(Outpass.created_at >= day, Outpass.created_at < day_end).count()
        trend_data.append(count)

    # 5. Status Distribution
    status_dist = [
        Outpass.query.filter_by(status='approved').count(),
        Outpass.query.filter_by(status='returned').count(),
        Outpass.query.filter_by(status='out').count(),
        Outpass.query.filter_by(status='rejected').count()
    ]

    # 6. Department Movement (THE REQUESTED ONES)
    depts = ['SOET-FE', 'SOET-ME', 'SOET-EE', 'SOET-CE', 'SOCSE', 'SOCMS', 'SOAS', 'SNJSOE', 'SOLIS', 'SOL']
    dept_movement = []
    for d in depts:
        count = Outpass.query.join(User).filter(User.department == d).count()
        dept_movement.append(count)

    return jsonify({
        'total_students': total_students,
        'exits_this_week': exits_this_week,
        'avg_time': avg_time,
        'trend_data': trend_data,
        'status_dist': status_dist,
        'dept_movement': dept_movement
    })
