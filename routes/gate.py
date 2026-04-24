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

@socketio.on('sos_alert', namespace='/gate')
def handle_sos(data):
    gate = data.get('gate', 'Main Gate')
    guard = data.get('guard', 'Security Personnel')
    time = data.get('time', datetime.now().strftime('%H:%M'))
    
    # Broadcast to all gate terminals
    socketio.emit('gate_log', {
        'time': time,
        'msg': f"CRITICAL SOS: Emergency triggered at {gate} by {guard}!",
        'type': 'DANGER'
    }, namespace='/gate')
    
    # Here you would typically also trigger SMS/Push notifications
    print(f"SOS ALERT: Emergency at {gate} triggered by {guard}")

gate_bp = Blueprint('gate', __name__, url_prefix='/gate')

@gate_bp.route('/terminal')
@login_required
def terminal():
    if current_user.role not in ['admin', 'guard']:
        return "Unauthorized", 403
    return render_template('guard/gate_terminal.html')

@gate_bp.route('/qr-scanner')
@login_required
def qr_scanner():
    if current_user.role not in ['admin', 'guard']:
        return "Unauthorized", 403
    return render_template('guard/qr_scanner.html')

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
                result_data['message'] = 'DEPARTURE DENIED: No authorized outpass or official leave found.'
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


@gate_bp.route('/scan-id', methods=['POST'])
@login_required
def scan_id():
    """
    POST /gate/scan-id
    Accepts a base64 image of student ID card.
    Tries QR decode first, falls back to OCR.
    Returns extracted student data + DB lookup result.
    """
    data        = request.json or {}
    image_b64   = data.get('image', '')
    client_qr   = data.get('client_qr')

    if not image_b64 and not client_qr:
        return jsonify({'success': False, 'message': 'No image received'}), 400

    from utils.id_card import extract_id_card_data
    
    # Unified extraction: tries client_qr first, then server QR, then OCR
    result = extract_id_card_data(image_b64, client_qr_data=client_qr)

    if not result['success']:
        return jsonify({'success': False, 'message': 'Could not read ID card. Try again or fill manually.'})

    extracted = result['data']

    # Normalise PRN field (id_card.py returns 'prn')
    sid = (extracted.get('prn') or extracted.get('student_id') or '').strip()

    # DB lookup
    student      = User.query.filter_by(student_id=sid).first() if sid else None
    has_face     = bool(student.face_encoded) if student else False
    db_data      = None
    if student:
        db_data = {
            'name':         student.name,
            'department':   student.department,
            'course':       student.course,
            'session_year': student.session_year,
            'phone':        student.phone,
            'parent_phone': student.parent_phone,
        }

    return jsonify({
        'success':      True,
        'method':       result['method'],        # 'qr' | 'ocr'
        'data':         extracted,               # raw extracted fields
        'sid':          sid,
        'exists':       bool(student),
        'has_face':     has_face,
        'db_data':      db_data,
    })


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

@gate_bp.route('/today-report')
@login_required
def today_report():
    today = datetime.utcnow().date()
    # Fetch all outpasses that were either exited or returned today
    movements = Outpass.query.filter(
        (db.func.date(Outpass.exit_time) == today) | 
        (db.func.date(Outpass.return_time) == today)
    ).all()
    
    report_data = []
    for m in movements:
        report_data.append({
            'name': m.student.name,
            'sid': m.student.student_id,
            'exit_time': m.exit_time.strftime('%H:%M') if m.exit_time else '-',
            'return_time': m.return_time.strftime('%H:%M') if m.return_time else '-',
            'status': m.status.upper()
        })
    
    return jsonify(report_data)

@gate_bp.route('/export/excel')
@login_required
def export_excel():
    from utils.export import ExportService
    today = datetime.utcnow().date()
    movements = Outpass.query.filter(
        (db.func.date(Outpass.exit_time) == today) | 
        (db.func.date(Outpass.return_time) == today)
    ).all()
    
    headers = ['Student Name', 'Student ID', 'Purpose', 'Destination', 'Status', 'Exit Time', 'Return Time']
    data = []
    for m in movements:
        data.append([
            m.student.name,
            m.student.student_id,
            m.purpose,
            m.destination,
            m.status.upper(),
            m.exit_time.strftime('%H:%M') if m.exit_time else '-',
            m.return_time.strftime('%H:%M') if m.return_time else '-'
        ])
    
    filename = f"Guard_Report_{datetime.now().strftime('%Y%m%d')}"
    return ExportService.export_excel(headers, data, filename)
