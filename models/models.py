from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin, guard, student
    name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100))
    phone = db.Column(db.String(15))
    parent_phone = db.Column(db.String(15))
    student_id = db.Column(db.String(50), unique=True)
    face_encoding = db.Column(db.PickleType)  # Store facial encoding
    face_image = db.Column(db.String(200))     # Path to stored face image
    is_blacklisted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    outpasses = db.relationship('Outpass', backref='student', cascade='all, delete-orphan', lazy=True)
    logs = db.relationship('Log', backref='user', cascade='all, delete-orphan', lazy=True)
    blacklist_records = db.relationship('Blacklist', foreign_keys='Blacklist.user_id', cascade='all, delete-orphan', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Outpass(db.Model):
    __tablename__ = 'outpasses'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    destination = db.Column(db.String(200), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    exit_time = db.Column(db.DateTime)
    expected_entry_time = db.Column(db.DateTime, nullable=False)
    actual_entry_time = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='pending')  # pending, approved, exited, returned, overdue
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Log(db.Model):
    __tablename__ = 'logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(200), nullable=False)
    details = db.Column(db.Text)
    type = db.Column(db.String(50))  # entry, exit, alert, auth
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Blacklist(db.Model):
    __tablename__ = 'blacklist'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
