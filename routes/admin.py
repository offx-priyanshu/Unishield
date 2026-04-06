from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from models.db import db
from models.user import User
from models.outpass import Outpass
from models.log import ActivityLog, Notification
from utils.logger import Logger
from utils.export import ExportService
from utils.sms import SMSService
from utils.face_utils import FaceUtils
from functools import wraps
import os
from werkzeug.utils import secure_filename
from datetime import datetime

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
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    total_students = User.query.filter_by(role='student').count()
    currently_out = Outpass.query.filter(Outpass.status.in_(['out', 'expired'])).count()
    pending_approval = Outpass.query.filter_by(status='pending').count()
    blacklisted_count = User.query.filter_by(is_blacklisted=True).count()
    
    today_exits = Outpass.query.filter(Outpass.exit_time >= today).count()
    today_returns = Outpass.query.filter(Outpass.return_time >= today).count()
    
    recent_logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(10).all()
    recent_outpasses = Outpass.query.order_by(Outpass.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html', 
                         total_students=total_students,
                         currently_out=currently_out,
                         pending_approval=pending_approval,
                         blacklisted_count=blacklisted_count,
                         today_exits=today_exits,
                         today_returns=today_returns,
                         recent_logs=recent_logs,
                         recent_outpasses=recent_outpasses)

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
            image_bytes = base64.b64decode(encoded)
            filename = secure_filename(f"{student_id}_face.jpg")
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            with open(filepath, "wb") as f:
                f.write(image_bytes)
            photo_path = filepath
        elif face_image_file:
            filename = secure_filename(f"{student_id}_face.jpg")
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            face_image_file.save(filepath)
            photo_path = filepath

        # Process ID Card Image
        if id_card_image:
            header, encoded = id_card_image.split(",", 1)
            image_bytes = base64.b64decode(encoded)
            filename = secure_filename(f"{student_id}_id.jpg")
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            with open(filepath, "wb") as f:
                f.write(image_bytes)
            id_card_path = filepath
        elif id_image_file:
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
        new_student.set_password('student123')
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
                Logger.notify_admin(op.student_id, 'Outpass Approved', f'Your request for {op.destination} has been approved.', type='approval')
                flash('Outpass approved successfully.', 'success')
            else:
                op.status = 'rejected'
                Logger.notify_admin(op.student_id, 'Outpass Rejected', f'Your request for {op.destination} has been rejected.', type='approval')
                flash('Outpass rejected.', 'info')
            db.session.commit()
            return redirect(url_for('admin.outpasses'))

    status_filter = request.args.get('status', 'pending')
    all_outpasses = Outpass.query.filter_by(status=status_filter).order_by(Outpass.created_at.desc()).all()
    
    return render_template('admin/outpasses.html', outpasses=all_outpasses, current_status=status_filter)

@admin_bp.route('/analytics')
@login_required
@admin_required
def analytics():
    return render_template('admin/analytics.html')

@admin_bp.route('/reports')
@login_required
@admin_required
def reports():
    all_logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).all()
    all_outpasses = Outpass.query.order_by(Outpass.created_at.desc()).all()
    return render_template('admin/reports.html', logs=all_logs, outpasses=all_outpasses)

@admin_bp.route('/sms_test', methods=['GET', 'POST'])
@login_required
@admin_required
def sms_test():
    if request.method == 'POST':
        phone = request.form.get('phone')
        msg_type = request.form.get('type')
        
        if msg_type == 'exit':
            success, msg = SMSService.notify_exit("Test Student", phone, phone, "Local Market", "22:00")
        elif msg_type == 'return':
            success, msg = SMSService.notify_return("Test Student", phone, phone)
        elif msg_type == 'overdue':
            success, msg = SMSService.notify_overdue("Test Student", phone, phone, "21:00")
        elif msg_type == 'blacklist':
            success, msg = SMSService.notify_blacklisted("Test Student", phone, phone)
        else:
            success, msg = SMSService.send_fast2sms(request.form.get('custom'), phone)
            
        flash(f"{'Success' if success else 'Failed'}: {msg}", 'success' if success else 'danger')
        Logger.log(current_user.id, f'Admin performed SMS Test for {phone}')
        
    return render_template('admin/sms_test.html')

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
    if request.method == 'POST':
        name = request.form.get('name')
        username = request.form.get('username')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash(f'Username {username} already exists!', 'danger')
            return redirect(url_for('admin.guards'))
            
        new_guard = User(
            username=username,
            name=name,
            role='guard'
        )
        new_guard.set_password(password)
        db.session.add(new_guard)
        db.session.commit()
        
        Logger.log(current_user.id, f'Admin added new guard: {name}')
        flash(f'Guard {name} added successfully!', 'success')
        return redirect(url_for('admin.guards'))

    all_guards = User.query.filter_by(role='guard').all()
    return render_template('admin/guards.html', guards=all_guards)

@admin_bp.route('/manage_admins', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_admins():
    if request.method == 'POST':
        name = request.form.get('name')
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash(f'Admin Username {username} already exists!', 'danger')
            return redirect(url_for('admin.manage_admins'))
            
        if User.query.filter_by(email=email).first():
            flash(f'Email address {email} is already registered!', 'danger')
            return redirect(url_for('admin.manage_admins'))
            
        new_admin = User(
            username=username,
            name=name,
            email=email,
            role='admin'
        )
        new_admin.set_password(password)
        db.session.add(new_admin)
        db.session.commit()
        
        Logger.log(current_user.id, f'Admin added new administrator: {name}')
        flash(f'Admin {name} created successfully!', 'success')
        return redirect(url_for('admin.manage_admins'))

    all_admins = User.query.filter_by(role='admin').all()
    return render_template('admin/manage_admins.html', admins=all_admins)

@admin_bp.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash("CRITICAL: You cannot delete your own administrative account!", 'danger')
        return redirect(request.referrer or url_for('admin.dashboard'))
        
    username = user.username
    name = user.name
    
    Outpass.query.filter_by(student_id=user.id).delete()
    
    db.session.delete(user)
    db.session.commit()
    
    Logger.log(current_user.id, f'Admin purged user: {name} ({username})', severity='warning')
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
