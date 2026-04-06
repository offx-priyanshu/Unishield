from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import datetime
from app import create_app
from models.db import db
from models.user import User
from models.outpass import Outpass
from models.log import ActivityLog
from utils.sms import SMSService
from config import Config

def check_overdue():
    """APScheduler task to find outpasses that are overdue and notify."""
    app = create_app()
    with app.app_context():
        now = datetime.utcnow()
        overdue_outpasses = Outpass.query.filter(
            (Outpass.status == 'out') & 
            (Outpass.expected_return < now) &
            (Outpass.alert_sent == False)
        ).all()
        
        for op in overdue_outpasses:
            student = User.query.get(op.student_id)
            if student:
                op.status = 'expired'
                op.alert_sent = True
                
                student.violations += 1
                
                if student.violations >= Config.VIOLATION_THRESHOLD:
                    student.is_blacklisted = True
                    SMSService.notify_blacklisted(student.name, student.parent_phone, student.phone)
                else:
                    SMSService.notify_overdue(student.name, student.parent_phone, student.phone, op.expected_return.strftime('%H:%M'))
                
                log = ActivityLog(
                    user_id=student.id, 
                    action=f'OVERDUE Alert: {student.name}', 
                    severity='critical',
                    description=f'Student is overdue. Total violations: {student.violations}'
                )
                db.session.add(log)
            db.session.commit()
            print(f"[{datetime.now()}] Processed overdue for {student.name if student else 'Unknown'}")

if __name__ == '__main__':
    scheduler = BlockingScheduler()
    scheduler.add_job(check_overdue, 'interval', minutes=5)
    print("SNOX Scheduler started...")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass
