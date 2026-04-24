from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from models.db import db
from models.outpass import Outpass
from models.user import User
from datetime import datetime, timedelta

api_bp = Blueprint('api', __name__)

@api_bp.route('/outpass/verify-qr', methods=['POST'])
def verify_qr():
    token = request.json.get('token', '').strip()
    # In this system, we use the Outpass ID as the token for simplicity in manual entry,
    # but normally we'd have a separate token field.
    # Let's assume the QR contains the Outpass ID.
    try:
        op_id = int(token)
        op = Outpass.query.get(op_id)
    except:
        return jsonify({'valid': False, 'reason': 'Invalid Token Format'}), 400

    if not op:
        return jsonify({'valid': False, 'reason': 'Outpass not found'}), 404
        
    student = User.query.get(op.student_id)
    if not student:
        return jsonify({'valid': False, 'reason': 'Student record missing'}), 404

    if student.is_blacklisted:
        return jsonify({'valid': False, 'reason': 'STUDENT IS BLACKLISTED'}), 403

    if op.status not in ['approved', 'out', 'expired']:
        return jsonify({'valid': False, 'reason': f'Status is {op.status.upper()}'}), 400

    return jsonify({
        'valid': True,
        'outpass_id': op.id,
        'sid': student.student_id,
        'student_id': student.id,
        'student_name': student.name,
        'destination': op.destination,
        'expected_return': op.expected_return.strftime('%Y-%m-%d %H:%M'),
        'status': op.status
    })

@api_bp.route('/verify-outpass/<int:op_id>', methods=['GET'])
def verify_outpass_id(op_id):
    op = Outpass.query.get(op_id)
    if not op:
        return jsonify({'success': False, 'message': 'Outpass not found'}), 404
        
    student = User.query.get(op.student_id)
    if not student:
        return jsonify({'success': False, 'message': 'Student record missing'}), 404

    return jsonify({
        'success': True,
        'data': {
            'outpass_id': op.id,
            'student_id': student.student_id,
            'student_name': student.name,
            'student_pic': student.face_image.split('/')[-1] if student.face_image else None,
            'destination': op.destination,
            'purpose': op.purpose,
            'status': op.status,
            'expected_return': op.expected_return.strftime('%H:%M %d/%m/%Y')
        }
    })

@api_bp.route('/outpass/exit/<int:oid>', methods=['POST'])
def mark_exit(oid):
    op = Outpass.query.get_or_404(oid)
    student = User.query.get(op.student_id)
    op.status = 'out'
    op.exit_time = datetime.utcnow()
    
    from utils.logger import Logger
    from services.sms_service import SMSService
    Logger.log(student.id, f"{student.name} exited campus via Gate Authorization (Dest: {op.destination})")
    
    # Automated Protocol: Notify Parents
    SMSService.notify_exit(student.name, student.phone, None, op.destination, op.expected_return.strftime('%H:%M'))
    
    db.session.commit()
    return jsonify({'success': True})

@api_bp.route('/outpass/return/<int:oid>', methods=['POST'])
def mark_return(oid):
    op = Outpass.query.get_or_404(oid)
    student = User.query.get(op.student_id)
    op.status = 'returned'
    op.return_time = datetime.utcnow()
    
    from utils.logger import Logger
    from services.sms_service import SMSService
    Logger.log(student.id, f"{student.name} returned to campus safely.")
    
    # Automated Protocol: Notify Parents
    SMSService.notify_return(student.name, student.phone, None)
    
    db.session.commit()
    return jsonify({'success': True})


@api_bp.route('/outpass/all', methods=['GET'])
def all_outpasses():
    status = request.args.get('status', 'pending').lower()
    if status == 'all':
        ops = Outpass.query.order_by(Outpass.created_at.desc()).all()
    else:
        ops = Outpass.query.filter_by(status=status).order_by(Outpass.created_at.desc()).all()
    
    return jsonify([{
        'id': op.id,
        'sid': User.query.get(op.student_id).student_id if User.query.get(op.student_id) else 'N/A',
        'student_name': User.query.get(op.student_id).name if User.query.get(op.student_id) else 'Unknown',
        'destination': op.destination,
        'purpose': op.purpose,
        'duration_hours': op.time_limit_hours,
        'status': op.status.upper(),
        'requested_at': op.created_at.isoformat() if op.created_at else None,
        'rejection_reason': getattr(op, 'rejection_reason', '')
    } for op in ops])

@api_bp.route('/sms/logs', methods=['GET'])
def sms_logs():
    # In this simplified integrated version, we might not have a dedicated SMS log table yet,
    # so we return mockup data for the UI to render.
    return jsonify([
        {
            'recipient_phone': '9876543210',
            'template_type': 'EXIT_ALERT',
            'message': 'UniShield ALERT: Vipul (Student ID:123) left campus...',
            'provider': 'fast2sms',
            'status': 'SENT',
            'sent_at': datetime.utcnow().isoformat()
        }
    ])

@api_bp.route('/sms/send', methods=['POST'])
def send_sms():
    data = request.get_json()
    phone = data.get('phone')
    template = data.get('template', 'CUSTOM')
    message = data.get('message', '')
    
    from models.log import SMSLog
    new_log = SMSLog(phone=phone, template=template, message=message, provider='fast2sms', status='SENT')
    db.session.add(new_log)
    db.session.commit()
    
    # Mock delivery update after 2 seconds
    return jsonify({'success': True, 'log_id': new_log.id})

@api_bp.route('/sms/logs/active', methods=['GET'])
def active_sms_logs():
    from models.log import SMSLog
    logs = SMSLog.query.order_by(SMSLog.sent_at.desc()).limit(20).all()
    return jsonify([{
        'id': l.id,
        'phone': l.phone,
        'template': l.template,
        'message': l.message,
        'provider': l.provider,
        'status': l.status,
        'timestamp': l.sent_at.strftime('%H:%M:%S')
    } for l in logs])

@api_bp.route('/sms/stats', methods=['GET'])
def sms_stats_api():
    from models.log import SMSLog
    today = datetime.utcnow().replace(hour=0, minute=0, second=0)
    total_sent = SMSLog.query.filter(SMSLog.sent_at >= today, SMSLog.status != 'FAILED').count()
    failed = SMSLog.query.filter(SMSLog.sent_at >= today, SMSLog.status == 'FAILED').count()
    return jsonify({
        'total_sent': total_sent,
        'failed_count': failed,
        'avg_speed': '1.2s',
        'provider_status': 'ACTIVE'
    })


@api_bp.route('/stats/summary', methods=['GET'])
def stats_summary():
    dept_filter = request.args.get('dept', 'ALL')
    now = datetime.utcnow()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today - timedelta(days=now.weekday())
    
    # Setup base queries with department filtering
    student_query = User.query.filter_by(role='student')
    op_query = Outpass.query
    
    if dept_filter != 'ALL':
        student_query = student_query.filter(User.department.ilike(f"%{dept_filter}%"))
        op_query = op_query.join(User).filter(User.department.ilike(f"%{dept_filter}%"))
        
    # 1. Basic Counts
    total_students = student_query.count()
    exits_this_week = op_query.filter(Outpass.exit_time >= week_start).count()
    
    # 2. Avg Time Outside (for returned outpasses)
    returned_ops = op_query.filter(Outpass.status == 'returned', Outpass.exit_time != None, Outpass.actual_return != None).all()
    if returned_ops:
        total_hours = sum((op.actual_return - op.exit_time).total_seconds() / 3600 for op in returned_ops)
        avg_time = round(total_hours / len(returned_ops), 1)
    else:
        avg_time = 0.0

    # 3. Status Distribution
    status_counts = {
        'approved': op_query.filter(Outpass.status=='approved').count(),
        'returned': op_query.filter(Outpass.status=='returned').count(),
        'out': op_query.filter(Outpass.status=='out').count(),
        'rejected': op_query.filter(Outpass.status=='rejected').count(),
    }

    # 4. Daily Trend (Last 30 days)
    trend_data = []
    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        next_day = day + timedelta(days=1)
        count = op_query.filter(Outpass.exit_time >= day, Outpass.exit_time < next_day).count()
        trend_data.append(count)

    # 5. Dept Movement
    depts = ['SOET-FE', 'SOET-ME', 'SOET-EE', 'SOET-CE', 'SOCSE', 'SOCMS', 'SOAS', 'SNJSOE', 'SOLIS', 'SOL']
    dept_movement = []
    for d in depts:
        count = Outpass.query.join(User).filter(User.department.ilike(f'%{d}%')).count()
        dept_movement.append(count)

    return jsonify({
        'total_students': total_students,
        'exits_this_week': exits_this_week,
        'avg_time': avg_time,
        'status_dist': [status_counts['approved'], status_counts['returned'], status_counts['out'], status_counts['rejected']],
        'trend_data': trend_data,
        'dept_movement': dept_movement
    })

@api_bp.route('/logs/active', methods=['GET'])
def active_logs():
    last_24h = datetime.utcnow() - timedelta(hours=24)
    
    # 24h Summary Counts
    total_24h = ActivityLog.query.filter(ActivityLog.timestamp >= last_24h).count()
    suspicious = ActivityLog.query.filter(ActivityLog.timestamp >= last_24h, ActivityLog.action.ilike('%blacklist%')).count()
    logins = ActivityLog.query.filter(ActivityLog.timestamp >= last_24h, ActivityLog.action.ilike('%login%')).count()

    # Only return the last 50 logs for performance
    logs = ActivityLog.query.order_by(ActivityLog.timestamp.desc()).limit(50).all()
    
    return jsonify({
        'logs': [{
            'id': l.id,
            'user_id': l.user_id,
            'action': l.action,
            'ip_address': l.ip_address,
            'timestamp': l.timestamp.strftime('%H:%M:%S'),
            'date': l.timestamp.strftime('%Y-%m-%d'),
            'severity': 'CRITICAL' if 'blacklist' in l.action.lower() or 'overdue' in l.action.lower() else 'INFO'
        } for l in logs],
        'summary': {
            'total': total_24h,
            'suspicious': suspicious,
            'logins': logins
        }
    })



