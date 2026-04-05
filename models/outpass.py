from datetime import datetime
from .db import db

class Outpass(db.Model):
    __tablename__ = 'outpasses'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    purpose = db.Column(db.Text, nullable=False)
    destination = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending|approved|out|returned|rejected|expired
    
    exit_time = db.Column(db.DateTime)
    return_time = db.Column(db.DateTime)
    expected_return = db.Column(db.DateTime, nullable=False)
    actual_return = db.Column(db.DateTime)
    time_limit_hours = db.Column(db.Integer, default=2)
    
    exit_photo = db.Column(db.String(200))
    return_photo = db.Column(db.String(200))
    
    face_verified_exit = db.Column(db.Boolean, default=False)
    face_verified_return = db.Column(db.Boolean, default=False)
    alert_sent = db.Column(db.Boolean, default=False)
    
    remarks = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
