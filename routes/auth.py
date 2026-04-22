from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from models.db import db
from models.user import User
from utils.logger import Logger
from datetime import datetime


auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif current_user.role == 'guard':
            return redirect(url_for('guard.dashboard'))
        elif current_user.role in ['hod', 'dean']:
            return redirect(url_for('faculty.dashboard'))
        elif current_user.role == 'warden':
            return redirect(url_for('warden.dashboard'))
        else:
            return redirect(url_for('student.dashboard'))
            
    if request.method == 'POST':
        # Handle AJAX JSON request or standard form request
        if request.is_json:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
            role_claim = data.get('role')
            remember = data.get('remember', False)
        else:
            username = request.form.get('username')
            password = request.form.get('password')
            role_claim = request.form.get('role') # Premium UI might send this via form too
            remember = True if request.form.get('remember') else False
        
        user = User.query.filter_by(username=username).first()
        
        # Validation Logic
        if not user or not user.check_password(password):
            Logger.log(None, f'Failed login attempt from {username}', severity='warning')
            message = 'Invalid credentials.'
            if request.is_json:
                return jsonify({'success': False, 'message': message}), 401
            flash(message, 'danger')
            return redirect(url_for('auth.login'))
            
        # Role Validation (Flexible for Faculty)
        actual_role = user.role.lower()
        claimed_role = role_claim.lower() if role_claim else None
        
        is_faculty = actual_role in ['hod', 'dean', 'warden']
        is_staff_claim = claimed_role == 'guard'
        
        if claimed_role and actual_role != claimed_role:
            # Allow faculty to login via the 'Staff' (guard) claim
            if not (is_faculty and is_staff_claim):
                message = f'Role mismatch. This account is registered as {user.role.upper()}.'
                if request.is_json:
                    return jsonify({'success': False, 'message': message}), 403
                flash(message, 'warning')
                return redirect(url_for('auth.login'))

        # Check Approval Status for Admins
        if user.role == 'admin' and user.status == 'PENDING':
            message = 'Authorization Pending: Your account is awaiting Owner approval.'
            if request.is_json:
                return jsonify({'success': False, 'message': message}), 403
            flash(message, 'warning')
            return redirect(url_for('auth.login'))

        login_user(user, remember=remember)
        
        # Update login stats
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        Logger.log(user.id, f'User {username} logged in')

        
        # Define redirect URL based on role
        if user.role == 'admin':
            redirect_url = url_for('admin.dashboard')
        elif user.role == 'guard':
            redirect_url = url_for('guard.dashboard')
        elif user.role in ['hod', 'dean']:
            redirect_url = url_for('faculty.dashboard')
        elif user.role == 'warden':
            redirect_url = url_for('warden.dashboard')
        else:
            redirect_url = url_for('student.dashboard')

        if request.is_json:
            return jsonify({'success': True, 'redirect': redirect_url})
            
        return redirect(redirect_url)
            
    return render_template('auth/login.html')

@auth_bp.route('/profile')
@login_required
def profile():
    from models.outpass import Outpass
    from datetime import datetime

    if current_user.role == 'student':
        # Students only see their own activity
        active_students = Outpass.query.filter_by(student_id=current_user.id, status='out').count()
        pending_approvals = Outpass.query.filter_by(student_id=current_user.id, status='pending').count()
        late_students = Outpass.query.filter(
            Outpass.student_id == current_user.id,
            Outpass.status == 'out',
            Outpass.expected_return < datetime.utcnow()
        ).count()
    else:
        # Admin/Guard see system-wide stats
        active_students = Outpass.query.filter_by(status='out').count()
        pending_approvals = Outpass.query.filter_by(status='pending').count()
        late_students = Outpass.query.filter(
            Outpass.status == 'out',
            Outpass.expected_return < datetime.utcnow()
        ).count()

    return render_template('common/profile.html',
                         active_students=active_students,
                         pending_approvals=pending_approvals,
                         late_students=late_students)

@auth_bp.route('/update_profile_photo', methods=['POST'])
@login_required
def update_profile_photo():
    if 'profile_photo' not in request.files:
        flash('No photo selected.', 'danger')
        return redirect(url_for('auth.profile'))
    
    file = request.files['profile_photo']
    if file.filename == '':
        flash('No file selected.', 'danger')
        return redirect(url_for('auth.profile'))
    
    if file:
        from werkzeug.utils import secure_filename
        import os
        filename = secure_filename(f"{current_user.role}_{current_user.id}_{int(datetime.utcnow().timestamp())}.jpg")
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        current_user.photo_path = filename 
        db.session.commit()
        
        Logger.log(current_user.id, f'{current_user.role.capitalize()} updated their profile photo')
        flash('Profile photo updated successfully!', 'success')
    
    return redirect(url_for('auth.profile'))

@auth_bp.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()

    if not name:
        flash('Name cannot be empty.', 'danger')
        return redirect(url_for('auth.profile'))

    # Check email uniqueness (only if changed)
    if email and email != current_user.email:
        existing = User.query.filter_by(email=email).first()
        if existing and existing.id != current_user.id:
            flash('That email is already in use by another account.', 'danger')
            return redirect(url_for('auth.profile'))

    current_user.name = name
    if email:
        current_user.email = email
    db.session.commit()

    Logger.log(current_user.id, f'{current_user.role.capitalize()} updated their profile info')
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('auth.profile'))

@auth_bp.route('/logout')
@login_required
def logout():
    Logger.log(current_user.id, 'System Session Terminated (Logout)')
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not current_user.check_password(old_password):
            flash('Invalid current password.', 'danger')
            return redirect(url_for('auth.change_password'))
            
        if new_password != confirm_password:
            flash('New passwords do not match.', 'danger')
            return redirect(url_for('auth.change_password'))
            
        if len(new_password) < 6:
            flash('New password must be at least 6 characters.', 'warning')
            return redirect(url_for('auth.change_password'))
            
        current_user.set_password(new_password)
        db.session.commit()
        
        Logger.log(current_user.id, f'User {current_user.username} changed their password')
        flash('Password updated successfully!', 'success')
        return redirect(url_for('auth.logout'))
        
    return render_template('auth/change_password.html')
