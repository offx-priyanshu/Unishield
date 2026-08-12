from flask import Flask, redirect, url\_for, flash, jsonify
from flask\_login import LoginManager
from flask\_jwt\_extended import JWTManager
from models.db import db
from models.user import User
from config import Config
from extensions import socketio
from apscheduler.schedulers.background import BackgroundScheduler
import os
from datetime import datetime

def check\_overdue\_outpasses(app):
with app.app\_context():
from models.outpass import Outpass
from models.user import User
from services.sms\_service import SMSService
from models.db import db

```
    now = datetime.utcnow()
    # Find all students who are "out" and late, and haven't been alerted yet
    late_outpasses = Outpass.query.filter(
        Outpass.status == 'out',
        Outpass.expected_return < now,
        Outpass.alert_sent == False
    ).all()
    
    for op in late_outpasses:
        student = User.query.get(op.student_id)
        if student:
            # 1. Send SMS Alert
            SMSService.notify_overdue(student.name, student.parent_phone, student.phone, op.expected_return.strftime('%H:%M'))
            
            # 2. Add Violation
            student.violations += 1
            if student.violations >= 3:
                student.is_blacklisted = True
            
            # 3. Mark alert as sent
            op.alert_sent = True
    
    db.session.commit()
```

def cleanup\_old\_system\_logs(app):
with app.app\_context():
from models.log import ActivityLog, SMSLog
from models.db import db
from datetime import timedelta

```
    threshold = datetime.utcnow() - timedelta(hours=24)
    
    # 1. Cleanup Login Logs
    ActivityLog.query.filter(
        ActivityLog.timestamp < threshold,
        db.or_(
            ActivityLog.action.ilike('%logged in%'),
            ActivityLog.action.ilike('%logout%'),
            ActivityLog.action.ilike('%terminated%')
        )
    ).delete(synchronize_session=False)
    
    # 2. Cleanup SMS Logs
    SMSLog.query.filter(
        SMSLog.sent_at < threshold
    ).delete(synchronize_session=False)
    
    db.session.commit()
```

def create\_app():
app = Flask(**name**)
app.config.from\_object(Config)

```
db.init_app(app)
socketio.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
    
jwt = JWTManager(app)

@app.template_filter('from_json')
def from_json(value):
    import json
    if not value: return []
    try:
        return json.loads(value)
    except:
        return []

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'signatures'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'stamps'), exist_ok=True)

from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.student import student_bp
from routes.guard import guard_bp
from routes.api import api_bp
from routes.gate import gate_bp
from routes.faculty import faculty_bp
from routes.warden import warden_bp

app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(student_bp, url_prefix='/student')
app.register_blueprint(guard_bp, url_prefix='/guard')
app.register_blueprint(api_bp, url_prefix='/api')
app.register_blueprint(gate_bp, url_prefix='/gate')
app.register_blueprint(faculty_bp, url_prefix='/faculty')
app.register_blueprint(warden_bp, url_prefix='/warden')

@app.before_request
def update_last_active():
    from flask_login import current_user
    if current_user.is_authenticated:
        current_user.last_active = datetime.utcnow()
        db.session.commit()

# Background Tasks
scheduler = BackgroundScheduler()
scheduler.add_job(func=check_overdue_outpasses, trigger="interval", minutes=60, args=[app])
scheduler.add_job(func=cleanup_old_system_logs, trigger="interval", minutes=60, args=[app])
scheduler.start()

@app.route('/')
def index():
    return redirect(url_for('auth.login'))

@app.context_processor
def inject_global_vars():
    return {
        'now': datetime.utcnow(),
        'app_name': 'UniShield',
        'Config': Config
    }

with app.app_context():
    db.create_all()

    # Find the owner admin by the configured username
    admin_user = User.query.filter_by(
        username=Config.ADMIN_USERNAME
    ).first()

    if not admin_user:
        admin = User(
            username=Config.ADMIN_USERNAME,
            email=Config.ADMIN_EMAIL,
            role='admin',
            name='UniShield Owner',
            student_id='OWNER001',
            admin_role='OWNER',
            status='ACTIVE',
            permissions='["ALL"]'
        )

        admin.set_password(Config.ADMIN_PASSWORD)
        db.session.add(admin)
        db.session.commit()

    else:
        # Update ONLY the owner admin's password.
        # Do not modify other approved admin accounts.
        admin_user.set_password(Config.ADMIN_PASSWORD)
        db.session.commit()

return app

if **name** == '**main**':
app = create\_app()
socketio.run(app, debug=True, port=8000)
