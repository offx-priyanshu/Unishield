from flask import Blueprint, render_template, redirect, url_for, flash, request
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
    # User info and outpass history
    outpass_history = Outpass.query.filter_by(student_id=current_user.id).order_by(Outpass.created_at.desc()).all()
    
    # Recent notifications
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(5).all()
    
    return render_template('student/dashboard.html', 
                         history=outpass_history, 
                         notifications=notifications,
                         current_time=datetime.utcnow())

@student_bp.route('/request_outpass', methods=['GET', 'POST'])
@login_required
@student_required
def request_outpass():
    if current_user.is_blacklisted:
        flash('You are BLACKLISTED from requesting outpasses. Contact Admin.', 'danger')
        return redirect(url_for('student.dashboard'))
        
    if request.method == 'POST':
        purpose = request.form.get('purpose')
        destination = request.form.get('destination')
        hours = int(request.form.get('hours', 2))
        
        # Check for existing pending/out requests
        active = Outpass.query.filter(
            (Outpass.student_id == current_user.id) & 
            (Outpass.status.in_(['pending', 'approved', 'out']))
        ).first()
        
        if active:
            flash(f'You already have an active/pending request for {active.destination}.', 'warning')
            return redirect(url_for('student.dashboard'))

        # Create outpass request
        expected_return = datetime.utcnow() + timedelta(hours=hours)
        
        new_outpass = Outpass(
            student_id=current_user.id,
            purpose=purpose,
            destination=destination,
            expected_return=expected_return,
            time_limit_hours=hours,
            status='pending'
        )
        db.session.add(new_outpass)
        db.session.commit()
        
        Logger.log(current_user.id, f'Student requested outpass for {destination}')
        Logger.notify_admin(1, 'New Outpass Request', f'Student {current_user.name} requested an outpass for {destination}.', type='request')
        flash('Outpass request submitted successfully!', 'success')
        return redirect(url_for('student.dashboard'))

    return render_template('student/request_outpass.html')
