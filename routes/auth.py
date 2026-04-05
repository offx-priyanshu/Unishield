from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models.db import db
from models.user import User
from utils.logger import Logger

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
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter_by(username=username).first()
        
        if not user or not user.check_password(password):
            Logger.log(None, f'Failed login attempt from {username}', severity='warning')
            flash('Login failed. Please check your credentials.', 'danger')
            return redirect(url_for('auth.login'))
            
        login_user(user, remember=remember)
        Logger.log(user.id, f'User {username} logged in')
        
        if user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif user.role == 'guard':
            return redirect(url_for('guard.dashboard'))
        else:
            return redirect(url_for('student.dashboard'))
            
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    Logger.log(current_user.id, f'User {current_user.username} logged out')
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('auth.login'))
