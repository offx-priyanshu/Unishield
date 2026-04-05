import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'snox-secret-99-ai'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///snox.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'static', 'uploads')
    
    # SMS Config (Fast2SMS)
    FAST2SMS_API_KEY = os.environ.get('FAST2SMS_API_KEY') or 'YOUR_FAST2_SMS_KEY'
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
    TWILIO_PHONE = os.environ.get('TWILIO_PHONE')
    
    # JWT Config
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-snox-ultra-secret'
    
    # App Settings
    SESSION_TIMEOUT = 30 # minutes
    VIOLATION_THRESHOLD = 3
    FACE_TOLERANCE = 0.5
