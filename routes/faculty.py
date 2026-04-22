from flask import Blueprint, request, redirect, url_for, flash, render_template
from flask_login import login_required, current_user
from models.db import db
from models.outpass import Outpass
from datetime import datetime

faculty_bp = Blueprint('faculty', __name__, url_prefix='/faculty')

@faculty_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role not in ['hod', 'dean']:
        return redirect(url_for('auth.login'))
    
    # Show home-leave requests based on role and correct status
    if current_user.role == 'hod':
        # HOD sees requests that are still pending (not yet HOD-approved)
        pending_requests = Outpass.query.filter_by(pass_type='home', status='pending').all()
    else: # dean
        # Dean sees requests that HOD has approved
        pending_requests = Outpass.query.filter_by(pass_type='home', status='hod_approved').all()
        
    return render_template('faculty/dashboard.html', requests=pending_requests)

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
        
    db.session.commit()
    flash(f"Request #{outpass_id} approved successfully.", "success")
    return redirect(url_for('faculty.dashboard'))

