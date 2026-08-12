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
        db.create_all()

        # Find the owner admin specifically
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
            # Keep the existing owner admin.
            # Do not modify other approved admin accounts.
            admin_user.set_password(Config.ADMIN_PASSWORD)
            db.session.commit()

    return app
