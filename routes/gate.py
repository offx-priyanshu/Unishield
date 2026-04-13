from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from models.db import db
from models.user import User
from models.outpass import Outpass
from models.log import ActivityLog
from services.sms_service import SMSService
from services.face_intelligence import FaceIntelligence
from extensions import socketio
from datetime import datetime
import json
import os

gate_bp = Blueprint('gate', __name__, url_prefix='/gate')

@gate_bp.route('/terminal')
@login_required
def terminal():
    if current_user.role not in ['admin', 'guard']:
        return "Unauthorized", 403
    return render_template('guard/gate_terminal.html')

@gate_bp.route('/auto-scan', methods=['POST'])
@login_required
def auto_scan():
    data = request.json
    image_b64 = data.get('image')
    
    if not image_b64:
        return jsonify({'success': False, 'message': 'No frame received'}), 400

    img = FaceIntelligence.base64_to_cv2(image_b64)
    embedding, face_conf = FaceIntelligence.get_embedding(img)
    
    if not embedding:
        return jsonify({'success': True, 'data': {'state': 'IDLE', 'message': 'Searching for face...'}})

    student, confidence = FaceIntelligence.match_face(embedding)
    
    result_data = {
        'name': student.name if student else 'Unknown',
        'sid': student.student_id if student else None,
        'confidence': confidence,
        'photo': student.face_image if student else None,
        'state': 'UNKNOWN',
        'message': 'Face not in our registry.'
    }

    if confidence >= 80 and student:
        # Check blacklist
        if student.is_blacklisted:
            result_data['state'] = 'DENIED'
            result_data['message'] = 'SECURITY ALERT: Student is BLACKLISTED!'
            socketio.emit('gate_event', result_data, namespace='/gate')
            return jsonify({'success': True, 'data': result_data})

        # Process Movement
        last_op = Outpass.query.filter_by(student_id=student.id).order_by(Outpass.created_at.desc()).first()
        state = 'RETURN' if last_op and last_op.status == 'out' else 'EXIT'
        
        if state == 'EXIT':
            if not last_op or last_op.status != 'approved':
                result_data['state'] = 'DENIED'
                result_data['message'] = 'No approved outpass found.'
            else:
                last_op.status = 'out'
                last_op.exit_time = datetime.utcnow()
                last_op.face_verified_exit = True
                result_data['state'] = 'EXIT'
                result_data['message'] = f'Exit Authorized for {student.name}'
                try:
                    SMSService.notify_exit(student.name, student.parent_phone, student.phone, last_op.destination, last_op.expected_return.strftime('%H:%M'))
                except: pass
        else: # RETURN
            if last_op:
                last_op.status = 'returned'
                last_op.return_time = datetime.utcnow()
                last_op.face_verified_return = True
                result_data['state'] = 'RETURN'
                result_data['message'] = f'Welcome back, {student.name}'
                try:
                    SMSService.notify_return(student.name, student.parent_phone, student.phone)
                except: pass
            else:
                result_data['state'] = 'DENIED'
                result_data['message'] = 'No outpass history found for return.'
            
        db.session.commit()
    elif confidence >= 50 and student:
        result_data['state'] = 'VERIFY'
        result_data['message'] = 'Low confidence. Please verify manually.'
    else:
        result_data['state'] = 'UNKNOWN'
        
    socketio.emit('gate_event', result_data, namespace='/gate')
    return jsonify({'success': True, 'data': result_data})

@gate_bp.route('/enroll', methods=['POST'])
@login_required
def enroll():
    data = request.json
    images = data.get('images', []) 
    student_data = data.get('student_data', {})
    
    success, message = FaceIntelligence.register_student(student_data, images)
    
    if success:
        socketio.emit('gate_log', {
            'time': datetime.now().strftime('%H:%M:%S'),
            'msg': f"REGISTERED: {student_data.get('name')}",
            'type': 'SUCCESS'
        }, namespace='/gate')
        
    return jsonify({'success': success, 'message': message})

@gate_bp.route('/check-student/<sid>', methods=['GET'])
@login_required
def check_student(sid):
    user = User.query.filter_by(student_id=sid).first()
    if not user:
        return jsonify({'exists': False})
    
    return jsonify({
        'exists': True,
        'has_face': bool(user.face_encoded),
        'data': {
            'name': user.name,
            'department': user.department,
            'course': user.course,
            'session_year': user.session_year,
            'phone': user.phone,
            'parent_phone': user.parent_phone
        }
    })

@gate_bp.route('/status')
@login_required
def get_stats():
    today = datetime.utcnow().date()
    exits = Outpass.query.filter(Outpass.status == 'out').count()
    returns = Outpass.query.filter(Outpass.status == 'returned').count()
    out = Outpass.query.filter_by(status='out').count()
    return jsonify({
        'exits_today': exits,
        'returns_today': returns,
        'currently_out': out
    })
