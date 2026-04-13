from flask import request
from models.db import db
from models.log import ActivityLog

class Logger:
    @staticmethod
    def log(user_id, action, description=None, severity='info'):
        """Logs a new activity to the database."""
        from models.user import User
        try:
            ip_address = request.remote_addr if request else '0.0.0.0'
            log_entry = ActivityLog(
                user_id=user_id,
                action=action,
                description=description,
                ip_address=ip_address,
                severity=severity
            )
            db.session.add(log_entry)
            
            # Update user's heartrate/action
            if user_id:
                user = User.query.get(user_id)
                if user:
                    user.last_action = action
            
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error logging activity: {e}")
            return False

            
    @staticmethod
    def notify_admin(user_id, title, message, type='system'):
        from models.log import Notification
        try:
            not_entry = Notification(
                user_id=user_id,
                title=title,
                message=message,
                type=type
            )
            db.session.add(not_entry)
            db.session.commit()
            return True
        except Exception as e:
            print(f"Error creating notification: {e}")
            return False
