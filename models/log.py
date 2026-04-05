from datetime import datetime
from .db import db

class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    severity = db.Column(db.String(20), default='info')  # info|warning|critical
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50))  # request|approval|alert|system
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
