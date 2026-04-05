from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from .db import db

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin | guard | student
    name = db.Column(db.String(100), nullable=False)
    
    student_id = db.Column(db.String(50), unique=True)
    phone = db.Column(db.String(15))
    parent_phone = db.Column(db.String(15))
    department = db.Column(db.String(200))
    year = db.Column(db.Integer)
    hostel_room = db.Column(db.String(20))
    
    face_encoded = db.Column(db.Text)          # JSON string of encoding
    face_image = db.Column(db.String(200))     # Full path to encoded photo
    photo_path = db.Column(db.String(200))     # Path to stored photo
    
    is_blacklisted = db.Column(db.Boolean, default=False)
    violations = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, passwordhash):
        return check_password_hash(self.password_hash, passwordhash)
