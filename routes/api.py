from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from models.db import db
from models.outpass import Outpass
from models.user import User
from datetime import datetime

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

@api_bp.route('/outpass/exit/<int:oid>', methods=['POST'])
def mark_exit(oid):
    op = Outpass.query.get_or_404(oid)
    op.status = 'out'
    op.exit_time = datetime.utcnow()
    db.session.commit()
    return jsonify({'success': True})

@api_bp.route('/outpass/return/<int:oid>', methods=['POST'])
def mark_return(oid):
    op = Outpass.query.get_or_404(oid)
    op.status = 'returned'
    op.return_time = datetime.utcnow()
    db.session.commit()
    return jsonify({'success': True})
