from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from models.db import db
from models.user import User
from models.outpass import Outpass
from models.log import ActivityLog, Notification
from utils.logger import Logger
from functools import wraps
from datetime import datetime, timedelta

student_bp = Blueprint('student', __name__)

def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'student':
            flash('Student access required', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@student_bp.route('/dashboard')
@login_required
@student_required
def dashboard():
    outpass_history = Outpass.query.filter_by(student_id=current_user.id).order_by(Outpass.created_at.desc()).all()
    
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(5).all()
    
    active_outpass = next((op for op in outpass_history if op.status in ['pending', 'hod_approved', 'dean_approved', 'approved', 'out']), None)
    
    return render_template('student/dashboard.html', 
                         history=outpass_history, 
                         notifications=notifications,
                         active_outpass=active_outpass,
                         current_time=datetime.utcnow())

@student_bp.route('/request_outpass', methods=['GET', 'POST'])
@login_required
@student_required
def request_outpass():
    if current_user.is_blacklisted:
        flash('You are BLACKLISTED from requesting outpasses. Contact Admin.', 'danger')
        return redirect(url_for('student.dashboard'))
        
    if request.method == 'POST':
        purpose = request.form.get('purpose', '').strip()
        destination = request.form.get('destination', '').strip()
        hours = int(request.form.get('hours', 2))
        pass_type = request.form.get('pass_type', 'local')

        # ── Server-side validation ──
        errors = []
        if not destination:
            errors.append('Destination address is required.')
        if not purpose or len(purpose) < 5:
            errors.append('Purpose must be at least 5 characters.')
        if pass_type == 'home':
            if not request.form.get('start_date'):
                errors.append('Start date is required for Home Leave.')
            if not request.form.get('end_date'):
                errors.append('End date is required for Home Leave.')
            elif request.form.get('start_date') and request.form.get('end_date'):
                if request.form.get('end_date') < request.form.get('start_date'):
                    errors.append('End date cannot be before start date.')
        if errors:
            for e in errors:
                flash(e, 'danger')
            return redirect(url_for('student.request_outpass', type=pass_type))

        active = Outpass.query.filter(
            (Outpass.student_id == current_user.id) & 
            (Outpass.status.in_(['pending', 'hod_approved', 'dean_approved', 'approved', 'out']))
        ).first()
        
        if active:
            flash(f'You already have an active/pending request for {active.destination}.', 'warning')
            return redirect(url_for('student.dashboard'))

        expected_return = datetime.utcnow() + timedelta(hours=hours)
        
        # Parse multi-day dates if present
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        start_dt = None
        end_dt = None
        
        if pass_type == 'home' and start_date_str and end_date_str:
            start_dt = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=21, minute=0) # 9 PM return
            expected_return = end_dt

        # Home Leave → pending for HOD/Dean/Warden approval
        # Local Transit → auto-approved with QR token
        import uuid
        if pass_type == 'home' or hours > 6:
            new_status = 'pending'
            qr = None
            if hours > 6 and pass_type == 'local':
                flash('Requests exceeding 6 hours require manual Warden authorization.', 'info')
        else:
            new_status = 'approved'
            qr = str(uuid.uuid4())
        
        # Handle Optional Document Upload
        leave_doc_path = None
        if 'leave_document' in request.files:
            file = request.files['leave_document']
            if file and file.filename != '':
                from werkzeug.utils import secure_filename
                import os
                filename = secure_filename(f"leave_{current_user.student_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
                upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'documents', filename)
                os.makedirs(os.path.dirname(upload_path), exist_ok=True)
                file.save(upload_path)
                leave_doc_path = os.path.join('documents', filename)

        new_outpass = Outpass(
            student_id=current_user.id,
            purpose=purpose,
            destination=destination,
            expected_return=expected_return,
            start_date=start_dt,
            end_date=end_dt,
            time_limit_hours=hours,
            pass_type=pass_type,
            status=new_status,
            qr_token=qr,
            leave_document=leave_doc_path
        )
        db.session.add(new_outpass)
        db.session.commit()
        
        Logger.log(current_user.id, f'Student requested {pass_type} outpass for {destination}')
        Logger.notify_admin(1, 'New Outpass Request', f'Student {current_user.name} requested a {pass_type} outpass for {destination}.', type='request')
        
        if pass_type == 'home':
            flash('Home Leave request submitted! Awaiting HOD → Dean → Warden approval.', 'info')
        else:
            flash('Local transit approved! QR code generated.', 'success')
        return redirect(url_for('student.dashboard'))

        
    return render_template('student/request_outpass.html', now=datetime.utcnow())


@student_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
@student_required
def edit_profile():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        parent_phone = request.form.get('parent_phone')
        hostel_room = request.form.get('hostel_room')
        
        current_user.name = name
        current_user.email = email
        current_user.phone = phone
        current_user.parent_phone = parent_phone
        current_user.hostel_room = hostel_room
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('student.dashboard'))
        
    return render_template('student/edit_profile.html')

@student_bp.route('/certificate/<int:outpass_id>')
@login_required
@student_required
def view_certificate(outpass_id):
    outpass = Outpass.query.get_or_404(outpass_id)
    if outpass.student_id != current_user.id:
        return "Unauthorized", 403
    
    if outpass.status not in ['approved', 'out', 'returned']:
        flash('Certificate only available for approved requests.', 'warning')
        return redirect(url_for('student.dashboard'))
        
    return render_template('student/certificate.html', outpass=outpass)

@student_bp.route('/cancel_outpass/<int:outpass_id>', methods=['POST'])
@login_required
@student_required
def cancel_outpass(outpass_id):
    outpass = Outpass.query.get_or_404(outpass_id)
    
    # Security check: Student can only cancel their own outpass
    if outpass.student_id != current_user.id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('student.dashboard'))
    
    # Safety check: Cannot cancel if already checked out
    if outpass.status == 'out':
        flash('Cannot cancel a pass after exit. Please return to campus normally.', 'warning')
        return redirect(url_for('student.dashboard'))
        
    outpass.status = 'rejected'
    outpass.hod_remarks = "Cancelled by student (Changed plans)"
    db.session.commit()
    
    Logger.log(current_user.id, f'Student cancelled their outpass request #{outpass_id}')
    flash('Your outpass request has been cancelled.', 'info')
    return redirect(url_for('student.dashboard'))
