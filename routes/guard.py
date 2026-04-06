from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from models.db import db
from models.user import User
from models.outpass import Outpass
from utils.logger import Logger
from utils.sms import SMSService
from utils.face_utils import FaceUtils
from functools import wraps
import os
import base64
from werkzeug.utils import secure_filename
from datetime import datetime

guard_bp = Blueprint('guard', __name__)

def guard_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['admin', 'guard']:
            flash('Guard access required', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@guard_bp.route('/dashboard')
@login_required
@guard_required
def dashboard():
    return render_template('guard/dashboard.html')

@guard_bp.route('/scan')
@login_required
@guard_required
def scan():
    return render_template('guard/scan.html')

@guard_bp.route('/process', methods=['POST'])
@login_required
@guard_required
def process_scan():
    data = request.json
    student_id = data.get('student_id')
    mode = data.get('mode') # EXIT | RETURN
    base64_frame = data.get('image')
    
    student = User.query.filter_by(student_id=student_id).first()
    
    if not student:
        return jsonify({'success': False, 'message': f'Student ID {student_id} not found!'}), 404
        
    if student.is_blacklisted:
        Logger.log(current_user.id, f'Security: Blacklisted student {student.name} attempted to exit', severity='critical')
        return jsonify({'success': False, 'message': 'ACCESS DENIED: Student is BLACKLISTED!'}), 403
        
    if not student.face_encoded:
        return jsonify({'success': False, 'message': 'Face encoding not found. Contact Admin for enrollment.'}), 400
        
    import json
    known_encoding_list = json.loads(student.face_encoded)
    match, result_msg = FaceUtils.compare_faces(known_encoding_list, base64_frame, tolerance=current_app.config.get('FACE_TOLERANCE', 0.5))
    
    if not match:
        student.violations += 1
        
        # Check for auto-blacklist
        from config import Config
        if student.violations >= Config.VIOLATION_THRESHOLD:
            student.is_blacklisted = True
            SMSService.notify_blacklisted(student.name, student.parent_phone, student.phone)
            Logger.log(current_user.id, f'Security: Student {student.name} AUTO-BLACKLISTED after face mismatch.', severity='critical')
            msg = f'FACE MISMATCH: Student has been AUTO-BLACKLISTED due to reaching {student.violations} violations.'
        else:
            Logger.log(current_user.id, f'Security Alert: Face mismatch for {student.name}. Violation logged.', severity='warning')
            msg = f'FACE MISMATCH: Identity could not be verified. Violation {student.violations} registered.'
            
        db.session.commit()
        return jsonify({'success': False, 'message': msg}), 401

    op = Outpass.query.filter_by(student_id=student.id).order_by(Outpass.created_at.desc()).first()
    
    filename = secure_filename(f"{student_id}_{mode.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
    photo_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    header, encoded = base64_frame.split(",", 1)
    with open(photo_path, "wb") as f:
        f.write(base64.b64decode(encoded))
        
    if mode == 'EXIT':
        if not op or op.status != 'approved':
            return jsonify({'success': False, 'message': 'NO APPROVED OUTPASS. Exit blocked.'}), 400
            
        op.status = 'out'
        op.exit_time = datetime.utcnow()
        op.exit_photo = photo_path
        op.face_verified_exit = True
        db.session.commit()
        
        SMSService.notify_exit(student.name, student.parent_phone, student.phone, op.destination, op.expected_return.strftime('%H:%M'))
        Logger.log(student.id, f'Student {student.name} exited campus')
        return jsonify({'success': True, 'message': f'ACCESS GRANTED: Student {student.name} exited campus.'})
        
    elif mode == 'RETURN':
        if not op or op.status not in ['out', 'expired']:
            return jsonify({'success': False, 'message': 'System Error: Student already on campus.'}), 400
            
        op.status = 'returned'
        op.return_time = datetime.utcnow()
        op.return_photo = photo_path
        op.face_verified_return = True
        db.session.commit()
        
        SMSService.notify_return(student.name, student.parent_phone, student.phone)
        Logger.log(student.id, f'Student {student.name} returned to campus')
        return jsonify({'success': True, 'message': f'ACCESS GRANTED: Student {student.name} returned to campus.'})
        
    return jsonify({'success': False, 'message': 'Invalid mode.'}), 400
