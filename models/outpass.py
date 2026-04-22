from datetime import datetime
from .db import db
from .user import User

class Outpass(db.Model):
    __tablename__ = 'outpasses'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # --- Workflow Logic ---
    # Type: 'local' (Short trips, auto) | 'home' (Home leaves, full approval)
    pass_type = db.Column(db.String(20), default='local')
    status = db.Column(db.String(30), default='pending') 
    # Statuses: pending | hod_approved | dean_approved | approved | out | returned | rejected
    
    # --- Approval Details (For 'home' leave) ---
    hod_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    hod_signed_at = db.Column(db.DateTime)
    hod_remarks = db.Column(db.Text)
    
    dean_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    dean_signed_at = db.Column(db.DateTime)
    dean_remarks = db.Column(db.Text)
    
    warden_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    warden_signed_at = db.Column(db.DateTime)
    
    # --- Parent Verification ---
    parent_verified = db.Column(db.Boolean, default=False)
    parent_otp = db.Column(db.String(10))
    parent_verification_mode = db.Column(db.String(20)) # 'otp' or 'call'
    
    # --- Core Trip Data ---
    purpose = db.Column(db.Text, nullable=False)
    destination = db.Column(db.String(200), nullable=False)
    destination_type = db.Column(db.String(50)) # Local Market, Hospital, Home Town
    
    exit_time = db.Column(db.DateTime)
    return_time = db.Column(db.DateTime)
    start_date = db.Column(db.DateTime)  # For multi-day leave
    end_date = db.Column(db.DateTime)    # For multi-day leave
    expected_return = db.Column(db.DateTime, nullable=False)
    actual_return = db.Column(db.DateTime)
    time_limit_hours = db.Column(db.Integer, default=2)
    
    # --- Biometric Logs ---
    exit_photo = db.Column(db.String(200))
    return_photo = db.Column(db.String(200))
    face_verified_exit = db.Column(db.Boolean, default=False)
    face_verified_return = db.Column(db.Boolean, default=False)
    
    # --- Security & Audit ---
    qr_token = db.Column(db.String(100), unique=True)
    leave_document = db.Column(db.String(200)) # Path to uploaded document
    university_stamp = db.Column(db.String(200)) # Path to digital stamp image used
    alert_sent = db.Column(db.Boolean, default=False)
    violation_tracked = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    student = db.relationship('User', foreign_keys=[student_id], backref='outpasses')
    hod = db.relationship('User', foreign_keys=[hod_id])
    dean = db.relationship('User', foreign_keys=[dean_id])
    warden = db.relationship('User', foreign_keys=[warden_id])
