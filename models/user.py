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
    course = db.Column(db.String(100))
    session_year = db.Column(db.String(50))
    year = db.Column(db.Integer)
    hostel_room = db.Column(db.String(20))
    
    face_encoded = db.Column(db.Text)          # JSON string of encoding
    face_image = db.Column(db.String(200))     # Full path to encoded photo
    photo_path = db.Column(db.String(200))     # Path to stored photo
    id_card_photo = db.Column(db.String(200))  # Path to ID card scan
    
    is_blacklisted = db.Column(db.Boolean, default=False)
    violations = db.Column(db.Integer, default=0)
    
    # Advanced Admin Fields
    admin_role = db.Column(db.String(30), default='VIEWER') # OWNER | SUPER_ADMIN | SECURITY_ADMIN | VIEWER
    permissions = db.Column(db.Text) # JSON list of permissions
    status = db.Column(db.String(20), default='PENDING') # PENDING | ACTIVE | INACTIVE
    last_login = db.Column(db.DateTime)
    last_action = db.Column(db.String(200)) # Last readable action performed
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Guard Specific Fields
    assigned_gate = db.Column(db.String(50))
    shift_timing = db.Column(db.String(100))
    emergency_contact = db.Column(db.String(15))
    aadhar_document = db.Column(db.String(200))  # Self-attested document
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
        
    def check_password(self, passwordhash):
        return check_password_hash(self.password_hash, passwordhash)

    def has_perm(self, perm):
        import json
        if not self.permissions: return False
        try:
            perms_list = json.loads(self.permissions)
            return perm in perms_list or 'ALL' in perms_list
        except: return False
