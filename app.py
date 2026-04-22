from flask import Flask, redirect, url_for, flash, jsonify
from flask_login import LoginManager
from flask_jwt_extended import JWTManager
from models.db import db
from models.user import User
from config import Config
from extensions import socketio
from apscheduler.schedulers.background import BackgroundScheduler
import os
from datetime import datetime

def check_overdue_outpasses(app):
    with app.app_context():
        from models.outpass import Outpass
        from models.user import User
        from services.sms_service import SMSService
        from models.db import db
        
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

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

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
        admin_user = User.query.filter_by(role='admin').first()
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
            admin_user.username = Config.ADMIN_USERNAME
            admin_user.email    = Config.ADMIN_EMAIL
            admin_user.set_password(Config.ADMIN_PASSWORD)
            db.session.commit()

    return app

if __name__ == '__main__':
    app = create_app()
    socketio.run(app, debug=True, port=8000)
