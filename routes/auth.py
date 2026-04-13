from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
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
            
        # Role Validation (Optional but recommended since UI allows selection)
        if role_claim and user.role.lower() != role_claim.lower():
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
        else:
            redirect_url = url_for('student.dashboard')

        if request.is_json:
            return jsonify({'success': True, 'redirect': redirect_url})
            
        return redirect(redirect_url)
            
    return render_template('auth/login.html')

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
