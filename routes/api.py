from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from models.db import db
from models.outpass import Outpass
from models.user import User
from datetime import datetime

api_bp = Blueprint('api', __name__)

@api_bp.route('/login', methods=['POST'])
def api_login():
    username = request.json.get('username')
    password = request.json.get('password')
    
    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({'error': 'Unauthorized'}), 401
        
    access_token = create_access_token(identity=user.id)
    return jsonify({'access_token': access_token, 'role': user.role})

@api_bp.route('/erp-sync', methods=['GET'])
@jwt_required()
def erp_sync():
    """ERP sync hook to fetch today's exit/return data."""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0)
    data = Outpass.query.filter(Outpass.created_at >= today_start).all()
    
    result = []
    for op in data:
        result.append({
            'outpass_id': op.id,
            'student_id': op.student_id,
            'status': op.status,
            'exit_time': op.exit_time.strftime('%Y-%m-%d %H:%M:%S') if op.exit_time else None,
            'return_time': op.return_time.strftime('%Y-%m-%d %H:%M:%S') if op.return_time else None,
            'face_verified': op.face_verified_exit and op.face_verified_return
        })
    return jsonify(result)
