from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models.db import db
from models.outpass import Outpass
from datetime import datetime
import uuid

warden_bp = Blueprint('warden', __name__, url_prefix='/warden')

@warden_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'warden':
        return redirect(url_for('auth.login'))
    
    # Warden sees home-leave requests that Dean has approved
    pending_requests = Outpass.query.filter_by(pass_type='home', status='dean_approved').all()
    return render_template('warden/dashboard.html', requests=pending_requests)

@warden_bp.route('/approve/<int:outpass_id>', methods=['POST'])
@login_required
def approve_request(outpass_id):
    if current_user.role != 'warden':
        return redirect(url_for('auth.login'))
    
    outpass = Outpass.query.get_or_404(outpass_id)
    parent_verified = request.form.get('parent_verified') == 'on'
    
    if not parent_verified:
        flash("Parent verification is mandatory for Warden approval.", "danger")
        return redirect(url_for('warden.dashboard'))
        
    outpass.warden_id = current_user.id
    outpass.warden_signed_at = datetime.utcnow()
    outpass.parent_verified = True
    outpass.status = "approved"
    outpass.qr_token = str(uuid.uuid4())
    
    db.session.commit()
    flash(f"Final approval granted. Gate pass generated for Request #{outpass_id}.", "success")
    return redirect(url_for('warden.dashboard'))
