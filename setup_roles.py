import sys
import os

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models.db import db
from models.user import User

app = create_app()

with app.app_context():
    # Create HOD
    if not User.query.filter_by(username='hod_test').first():
        hod = User(
            username='hod_test',
            email='hod@unishield.edu',
            role='hod',
            name='Dr. Sharma (HOD)',
            department='Computer Science',
            employee_id='EMP-HOD-01',
            status='ACTIVE'
        )
        hod.set_password('password123')
        db.session.add(hod)

    # Create Dean
    if not User.query.filter_by(username='dean_test').first():
        dean = User(
            username='dean_test',
            email='dean@unishield.edu',
            role='dean',
            name='Dr. Verma (Dean)',
            employee_id='EMP-DEAN-01',
            status='ACTIVE'
        )
        dean.set_password('password123')
        db.session.add(dean)

    # Create Warden
    if not User.query.filter_by(username='warden_test').first():
        warden = User(
            username='warden_test',
            email='warden@unishield.edu',
            role='warden',
            name='Mr. Gupta (Warden)',
            employee_id='EMP-WARDEN-01',
            status='ACTIVE'
        )
        warden.set_password('password123')
        db.session.add(warden)

    # Create a Student for testing
    if not User.query.filter_by(username='student_test').first():
        student = User(
            username='student_test',
            email='student@unishield.edu',
            role='student',
            name='Priyanshu Kumar',
            student_id='STU001',
            course='B.Tech CSE',
            year=3,
            status='ACTIVE'
        )
        student.set_password('password123')
        db.session.add(student)

    db.session.commit()
    print("Test accounts created successfully!")
    print("HOD: hod_test / password123")
    print("Dean: dean_test / password123")
    print("Warden: warden_test / password123")
    print("Student: student_test / password123")
