from flask import Blueprint, request, redirect, url_for, flash, render_template
from flask_login import login_required, current_user
from models.db import db
from models.outpass import Outpass
from models.log import Notification
from datetime import datetime
from extensions import socketio

faculty_bp = Blueprint('faculty', __name__, url_prefix='/faculty')

@faculty_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role not in ['hod', 'dean']:
        return redirect(url_for('auth.login'))
    
    # Calculate stats
    today = datetime.utcnow().replace(hour=0, minute=0, second=0)
    
    # All home-leave requests for stats
    all_home = Outpass.query.filter_by(pass_type='home')
    
    stats = {
        'approved_today': all_home.filter(Outpass.status != 'rejected', Outpass.status != 'pending', Outpass.created_at >= today).count(),
        'rejected_today': all_home.filter(Outpass.status == 'rejected', Outpass.created_at >= today).count(),
        'emergency_count': all_home.filter(Outpass.priority == 'emergency', Outpass.status != 'approved', Outpass.status != 'rejected').count(),
        'parent_pending': all_home.filter(Outpass.parent_verified == False, Outpass.status != 'approved', Outpass.status != 'rejected').count()
    }
    
    # Show home-leave requests based on role and correct status
    if current_user.role == 'hod':
        pending_requests = Outpass.query.filter_by(pass_type='home', status='pending').all()
    else: # dean
        pending_requests = Outpass.query.filter_by(pass_type='home', status='hod_approved').all()
        
    return render_template('faculty/dashboard.html', requests=pending_requests, stats=stats)

@faculty_bp.route('/approve/<int:outpass_id>', methods=['POST'])
@login_required
def approve_request(outpass_id):
    outpass = Outpass.query.get_or_404(outpass_id)
    remark = request.form.get('remark', '')
    
    if current_user.role == 'hod':
        outpass.hod_id = current_user.id
        outpass.hod_signed_at = datetime.utcnow()
        outpass.hod_remarks = remark
        outpass.status = 'hod_approved'         # ← intermediate status
    elif current_user.role == 'dean':
        outpass.dean_id = current_user.id
        outpass.dean_signed_at = datetime.utcnow()
        outpass.dean_remarks = remark
        outpass.status = 'dean_approved'         # ← intermediate status
        
    # Add persistent notification for student
    new_notif = Notification(
        user_id=outpass.student_id,
        title=f"Leave Update: {current_user.role.upper()} Approved",
        message=f"Your outpass for {outpass.destination} has been approved by {current_user.name}. Proceeding to next stage.",
        type='success'
    )
    db.session.add(new_notif)
    db.session.commit()

    # Emit status update for real-time tracking
    socketio.emit('status_update', {
        'outpass_id': outpass.id,
        'student_id': outpass.student_id,
        'status': outpass.status,
        'approver': current_user.name,
        'role': current_user.role.upper(),
        'time': outpass.hod_signed_at.strftime('%H:%M') if current_user.role == 'hod' else outpass.dean_signed_at.strftime('%H:%M')
    }, namespace='/gate')

    flash(f"Request #{outpass_id} approved successfully.", "success")
    return redirect(url_for('faculty.dashboard'))

@faculty_bp.route('/reject/<int:outpass_id>', methods=['POST'])
@login_required
def reject_request(outpass_id):
    outpass = Outpass.query.get_or_404(outpass_id)
    remark = request.form.get('remark', 'Rejected by Faculty')
    
    outpass.status = 'rejected'
    if current_user.role == 'hod':
        outpass.hod_remarks = remark
    else:
        outpass.dean_remarks = remark
        
    db.session.commit()
    
    socketio.emit('status_update', {
        'outpass_id': outpass.id,
        'student_id': outpass.student_id,
        'status': 'rejected',
        'approver': current_user.name,
        'role': current_user.role.upper(),
        'reason': remark
    }, namespace='/gate')

    flash(f"Request #{outpass_id} has been rejected.", "danger")
    return redirect(url_for('faculty.dashboard'))

