from flask import Flask, redirect, url_for, flash, jsonify
from flask_login import LoginManager
from flask_jwt_extended import JWTManager
from models.db import db
from models.user import User
from config import Config
import os
from datetime import datetime

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
        
    jwt = JWTManager(app)

    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    from routes.auth import auth_bp
    from routes.admin import admin_bp
    from routes.student import student_bp
    from routes.guard import guard_bp
    from routes.api import api_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(student_bp, url_prefix='/student')
    app.register_blueprint(guard_bp, url_prefix='/guard')
    app.register_blueprint(api_bp, url_prefix='/api')

    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))

    @app.context_processor
    def inject_global_vars():
        return {
            'now': datetime.utcnow(),
            'app_name': 'SNOX',
            'Config': Config
        }

    with app.app_context():
        db.create_all()
        admin_user = User.query.filter_by(role='admin').first()
        if not admin_user:
            admin = User(
                username='priyanshugse',
                email='priyanshugse@gmail.com',
                role='admin',
                name='Super Admin',
                student_id='ADMIN001'
            )
            admin.set_password('vipul@123')
            db.session.add(admin)
            db.session.commit()
        else:
            admin_user.username = 'priyanshugse'
            admin_user.email = 'priyanshugse@gmail.com'
            admin_user.set_password('vipul@123')
            db.session.commit()

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)
