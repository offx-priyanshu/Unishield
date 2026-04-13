import os
from dotenv import load_dotenv

# Load .env file automatically
load_dotenv()

class Config:
    # ── Flask ──────────────────────────────────────────────
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'snox-secret-99-ai'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'database', 'snox.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'static', 'uploads')

    # ── JWT ───────────────────────────────────────────────
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-snox-ultra-secret'

    # ── Fast2SMS (Primary SMS) ────────────────────────────
    FAST2SMS_API_KEY = os.environ.get('FAST2SMS_API_KEY') or ''

    # ── Twilio (Fallback SMS) ─────────────────────────────
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID') or ''
    TWILIO_AUTH_TOKEN  = os.environ.get('TWILIO_AUTH_TOKEN') or ''
    TWILIO_PHONE       = os.environ.get('TWILIO_PHONE') or ''

    # ── Admin Defaults ────────────────────────────────────
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME') or 'priyanshugse'
    ADMIN_EMAIL    = os.environ.get('ADMIN_EMAIL') or 'priyanshugse@gmail.com'
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD') or 'vipul@123'

    # ── Security Settings ─────────────────────────────────
    SESSION_TIMEOUT      = int(os.environ.get('SESSION_TIMEOUT', 30))
    VIOLATION_THRESHOLD  = int(os.environ.get('VIOLATION_THRESHOLD', 3))
    FACE_TOLERANCE       = float(os.environ.get('FACE_TOLERANCE', 0.5))
