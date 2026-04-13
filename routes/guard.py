from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from models.db import db
from models.user import User
from models.outpass import Outpass
from utils.logger import Logger
from services.sms_service import SMSService
from utils.face_utils import FaceUtils
from functools import wraps
import os
import base64
import numpy as np
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

from utils.id_card import extract_id_card_data

@guard_bp.route('/scan-id', methods=['POST'])
@login_required
@guard_required
def scan_id_card():
    data  = request.get_json() or {}
    b64   = data.get('id_card_image', '')

    if not b64:
        return jsonify({'success': False, 'message': 'No image provided.'}), 400

    result = extract_id_card_data(b64)

    if result['success']:
        Logger.log(current_user.id, f"ID card scanned via {result['method'].upper()}. Name: {result['data'].get('name', 'Unknown')}")
        return jsonify({
            'success': True,
            'method':  result['method'],
            'data':    result['data'],
            'message': f"Data extracted via {result['method'].upper()}"
        })
    else:
        Logger.log(current_user.id, 'ID card scan failed — QR and OCR both failed.', severity='warning')
        return jsonify({
            'success': False,
            'method':  'failed',
            'data':    {},
            'message': 'Could not read ID card. Please enter data manually.'
        })

@guard_bp.route('/enroll', methods=['POST'])
@login_required
@guard_required
def enroll_student():
    data = request.json
    student_id = data.get('student_id')
    name = data.get('name')
    department = data.get('department')
    phone = data.get('phone')
    parent_phone = data.get('parent_phone')
    base64_face = data.get('face_image')
    base64_id = data.get('id_image')
    
    if not all([student_id, name, base64_face]):
        return jsonify({'success': False, 'message': 'Missing required fields or face.'}), 400
        
    student = User.query.filter_by(student_id=student_id).first()
    if student:
        return jsonify({'success': False, 'message': 'Student ID already exists.'}), 400
        
    # Process face
    header, encoded = base64_face.split(",", 1)
    match, result_msg = FaceUtils.compare_faces([], base64_face, tolerance=0.5)
    # compare_faces against empty array will return "No face detected" if empty
    if result_msg == "No face detected":
         return jsonify({'success': False, 'message': 'No face detected in camera.'}), 400
         
    # We just need the encoding
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp:
        temp.write(base64.b64decode(encoded))
        temp_path = temp.name
        
    encodings = FaceUtils.get_encoding(temp_path)
    if not encodings:
        os.remove(temp_path)
        return jsonify({'success': False, 'message': 'Failed to extract face encoding.'}), 400
        
    encoded_json = FaceUtils.encode_to_json(np.array(encodings))
    
    # Save photos
    face_filename = secure_filename(f"{student_id}_face_{datetime.now().strftime('%Y%m%d')}.jpg")
    face_path = os.path.join(current_app.config['UPLOAD_FOLDER'], face_filename)
    os.rename(temp_path, face_path)
    
    id_path = None
    if base64_id:
        id_header, id_encoded = base64_id.split(",", 1)
        id_filename = secure_filename(f"{student_id}_id_{datetime.now().strftime('%Y%m%d')}.jpg")
        id_path = os.path.join(current_app.config['UPLOAD_FOLDER'], id_filename)
        with open(id_path, "wb") as f:
            f.write(base64.b64decode(id_encoded))
            
    new_student = User(
        username=student_id,
        email=f"{student_id}@institute.edu",
        role='student',
        name=name,
        student_id=student_id,
        department=department,
        phone=phone,
        parent_phone=parent_phone,
        face_encoded=encoded_json,
        face_image=face_path,
        id_card_photo=id_path
    )
    new_student.set_password(student_id) # Default password is ID
    db.session.add(new_student)
    db.session.commit()
    
    Logger.log(current_user.id, f'Security: Enrolled new student {name} at gate.')
    return jsonify({'success': True, 'message': f'{name} successfully registered at gate!'})
