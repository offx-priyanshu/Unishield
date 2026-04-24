from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models.db import db
from models.outpass import Outpass
from models.log import Notification
from datetime import datetime
from extensions import socketio
import uuid, random

warden_bp = Blueprint('warden', __name__, url_prefix='/warden')

@warden_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'warden':
        return redirect(url_for('auth.login'))
    
    today = datetime.utcnow().replace(hour=0, minute=0, second=0)
    all_home = Outpass.query.filter_by(pass_type='home')
    
    stats = {
        'approved_today': all_home.filter(Outpass.status == 'approved', Outpass.warden_signed_at >= today).count(),
        'rejected_today': all_home.filter(Outpass.status == 'rejected', Outpass.created_at >= today).count(),
        'emergency_count': all_home.filter(Outpass.priority == 'emergency', Outpass.status == 'dean_approved').count(),
        'parent_pending': all_home.filter(Outpass.parent_verified == False, Outpass.status == 'dean_approved').count(),
        'total_passes_issued': Outpass.query.filter_by(status='approved').count()
    }
    
    # Warden sees home-leave requests that Dean has approved
    pending_requests = Outpass.query.filter_by(pass_type='home', status='dean_approved').all()
    return render_template('warden/dashboard.html', requests=pending_requests, stats=stats)

@warden_bp.route('/send-otp/<int:outpass_id>', methods=['POST'])
@login_required
def send_otp(outpass_id):
    if current_user.role != 'warden':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    outpass = Outpass.query.get_or_404(outpass_id)
    student = outpass.student
    
    if not student.parent_phone:
        return jsonify({'success': False, 'error': 'Parent phone number not registered for this student.'})
    
    # Generate 6-digit OTP
    otp = str(random.randint(100000, 999999))
    outpass.parent_otp = otp
    outpass.parent_verification_mode = 'otp'
    db.session.commit()
    
    # Send SMS to parent
    from services.sms_service import SMSService
    msg = (f"UniShield OTP: Your ward {student.name}'s home leave request has been approved "
           f"by HOD and Dean. Verification OTP: {otp}. Share with Warden to authorize gate pass.")
    success, result = SMSService.send_sms(student.parent_phone, msg, 'PARENT_OTP')
    
    if success:
        masked = student.parent_phone[:-4].replace(student.parent_phone[3:-4], 'X' * len(student.parent_phone[3:-4])) + student.parent_phone[-4:]
        return jsonify({'success': True, 'masked_phone': masked, 'message': f'OTP sent to {masked}'})
    else:
        # For demo/dev without SMS configured — still save OTP and return it
        masked = student.parent_phone[-4:].rjust(len(student.parent_phone), 'X')
        return jsonify({'success': True, 'masked_phone': masked, 'otp_debug': otp,
                        'message': f'SMS failed ({result}). Dev OTP: {otp}'})

@warden_bp.route('/verify-otp/<int:outpass_id>', methods=['POST'])
@login_required
def verify_otp(outpass_id):
    if current_user.role != 'warden':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    outpass = Outpass.query.get_or_404(outpass_id)
    entered_otp = request.json.get('otp', '').strip()
    
    if not outpass.parent_otp:
        return jsonify({'success': False, 'error': 'OTP not generated yet. Send OTP first.'})
    
    if entered_otp == outpass.parent_otp:
        outpass.parent_verified = True
        db.session.commit()
        return jsonify({'success': True, 'message': 'Parent verified successfully! QR generation unlocked.'})
    else:
        return jsonify({'success': False, 'error': 'Incorrect OTP. Please check and try again.'})

@warden_bp.route('/approve/<int:outpass_id>', methods=['POST'])
@login_required
def approve_request(outpass_id):
    if current_user.role != 'warden':
        return redirect(url_for('auth.login'))
    
    outpass = Outpass.query.get_or_404(outpass_id)
    
    if not outpass.parent_verified:
        flash("Parent OTP verification is mandatory before generating Gate Pass.", "danger")
        return redirect(url_for('warden.dashboard'))
        
    outpass.warden_id = current_user.id
    outpass.warden_signed_at = datetime.utcnow()
    outpass.parent_verified = True
    outpass.status = "approved"
    outpass.qr_token = str(uuid.uuid4())
    
    # Add persistent notification for student
    new_notif = Notification(
        user_id=outpass.student_id,
        title="Gate Pass Active",
        message=f"Final authorization granted by Warden {current_user.name}. Your QR Gate Pass is now active.",
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
        'role': 'WARDEN',
        'time': outpass.warden_signed_at.strftime('%H:%M')
    }, namespace='/gate')

    flash(f"Final approval granted. Gate pass generated for Request #{outpass_id}.", "success")
    return redirect(url_for('warden.dashboard'))

@warden_bp.route('/reject/<int:outpass_id>', methods=['POST'])
@login_required
def reject_request(outpass_id):
    if current_user.role != 'warden':
        return redirect(url_for('auth.login'))
    
    outpass = Outpass.query.get_or_404(outpass_id)
    remark = request.form.get('remark', 'Rejected by Warden')
    
    outpass.status = 'rejected'
    outpass.dean_remarks = remark  # store in remarks
    
    new_notif = Notification(
        user_id=outpass.student_id,
        title="Gate Pass Denied",
        message=f"Warden {current_user.name} has rejected your leave request. Reason: {remark}",
        type='danger'
    )
    db.session.add(new_notif)
    db.session.commit()
    
    socketio.emit('status_update', {
        'outpass_id': outpass.id,
        'student_id': outpass.student_id,
        'status': 'rejected',
        'approver': current_user.name,
        'role': 'WARDEN',
        'reason': remark
    }, namespace='/gate')
    
    flash(f"Request #{outpass_id} rejected by Warden.", "danger")
    return redirect(url_for('warden.dashboard'))

