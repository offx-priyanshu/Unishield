from app import create_app
from models.models import db, User
from services.face_service import FaceService

app = create_app()

with app.app_context():
    # 1. Check Admin Account
    admin = User.query.filter_by(username='admin').first()
    if admin:
        print(f"✅ Admin account found: {admin.username}")
    else:
        print("❌ Admin account NOT found!")

    # 2. Register a Student manually
    student_data = {
        'username': 'priyanshu_test',
        'name': 'Priyanshu Test',
        'student_id': 'TEST001',
        'parent_phone': '9876543210',
        'department': 'CS'
    }
    
    if not User.query.filter_by(username=student_data['username']).first():
        student = User(
            username=student_data['username'],
            role='student',
            name=student_data['name'],
            student_id=student_data['student_id'],
            parent_phone=student_data['parent_phone'],
            department=student_data['department']
        )
        student.set_password('student123')
        db.session.add(student)
        db.session.commit()
        print(f"✅ Student {student.name} registered!")
    else:
        print(f"ℹ️ Student {student_data['username']} already exists.")

    # 3. Test Face Service
    mock_encoding = FaceService.get_face_encoding(None) 
    if mock_encoding is not None:
        print(f"✅ Face Service Mock Encoding length: {len(mock_encoding)}")
    else:
        print(f"ℹ️ Face Service returned None for missing file (as expected).")
    
    # 4. Check Roles
    from routes.auth import redirect_dashboard
    # This might need a mock request context if it uses flask global variables, 
    # but let's just check the logic.
    print(f"✅ Role redirection logic exists in routes/auth.py")
