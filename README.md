# UniShield — AI-Powered Campus Security & Outpass Management System 🛡️

![Status](https://img.shields.io/badge/Status-Active%20Development-success?style=for-the-badge)
![Backend](https://img.shields.io/badge/Backend-Python%20%7C%20Flask-3776AB?style=for-the-badge&logo=python)
![Realtime](https://img.shields.io/badge/Realtime-Socket.io-010101?style=for-the-badge&logo=socketdotio)
![Security](https://img.shields.io/badge/Security-AI%20%7C%20Biometrics%20%7C%20QR-00d2ff?style=for-the-badge)
![Theme](https://img.shields.io/badge/UI-Cyber%20Neon%20Glassmorphism-black?style=for-the-badge)

**UniShield** is a next-generation, enterprise-grade campus security and student outpass management platform built for Sandip University. It combines AI face recognition, dynamic QR gate passes, a multi-stage approval workflow, real-time Socket.io dashboards, and SMS-based parent verification into a unified cyber-security-themed control center.

---

## 🔥 Core Features

### 🧠 AI & Biometrics
- **Face Recognition Engine** — Multi-angle neural face encoding using `face_recognition` + `dlib`. Verifies identity on every EXIT and RETURN at the gate.
- **Physical ID Card Scan** — Automated QR/OCR scanning of student ID cards during enrolment at the AI Gate Terminal.
- **AI Risk Scoring** — Each student is dynamically tagged `LOW / MEDIUM / HIGH` risk based on violation history and blacklist status, visible to all authority dashboards.

### 🔐 Multi-Stage Approval Workflow
```
Student Apply → HOD Approve → Dean Approve → Warden (OTP + Parent Verify) → QR Gate Pass → Guard Scan + Face Match → EXIT ✅
```
- **HOD Dashboard** — Stage 1 authorization. Reviews pending Home Leave requests.
- **Dean Dashboard** — Stage 2 authorization. Reviews HOD-approved requests.
- **Warden Command Center** — Final seal. OTP dispatched to parent phone; Warden enters OTP to verify, then generates QR Gate Pass.

### 📱 Parent OTP Verification (Warden Stage)
- Warden clicks **"Send OTP to Parent"** — 6-digit OTP sent via SMS to registered parent number.
- Masked phone number displayed on dashboard (e.g. `+91 98XXXXX210`).
- Warden enters OTP received from parent → **"Seal & Generate QR"** button unlocks.
- Gate Pass cannot be generated without successful parent OTP verification.

### 📲 SMS Notification System
- **Dual-failover SMS**: Fast2SMS (primary) → Twilio (fallback).
- Automated alerts for: **Exit, Return, Overdue, Blacklist, Parent OTP**.
- Full SMS log maintained in admin SMS Center.

### 🔲 QR Gate Pass
- Unique `uuid4` token generated on Warden final approval.
- Guard scans QR → system validates outpass status in real-time.
- Followed by face biometric match before EXIT is logged.

### 📊 Real-Time Dashboards (Socket.io)
All authority dashboards are live-connected via `/gate` Socket.io namespace:
- **Live Activity Feed** — Every system event appears in real-time.
- **Dynamic Context Bar** — Contextual system messages based on queue state.
- **Stats Cards** — Pending, Approved Today, Emergency, Parent Pending counts.
- **Request Cards** — Student photo, department, destination, AI Risk badge, approval timeline, supporting document link.

### 🏛️ Role-Based Access Control (RBAC)

| Role | Access |
|---|---|
| **Admin** | Full system — Students, Guards, Faculty, Outpasses, Analytics, SMS, AI Gate |
| **HOD** | Stage 1 approval dashboard |
| **Dean** | Stage 2 approval dashboard |
| **Warden** | Final seal + OTP parent verification + QR generation |
| **Guard** | AI Gate Terminal + QR Scanner + Face Match |
| **Student** | Leave application + QR Pass + Notification history |

### 🖥️ AI Gate Terminal (Guard)
- Live WebRTC camera feed with face scan.
- QR Scanner using `jsQR` library.
- Exit → QR Verify → Face Match → Log departure.
- Return → Face Match → Log return.

### 🚨 Auto-Violation & Blacklist Engine
- Background scheduler checks overdue outpasses every 60 minutes.
- SMS alert sent to student + parent when overdue.
- 3+ violations → auto-blacklist (campus access blocked).

### 📑 Supporting Document Upload
- Students can attach Medical Certificate, Wedding Invite, or Permission Letter.
- Document viewable by HOD, Dean, and Warden during approval.

### 📈 Analytics & Reporting
- Admin Analytics dashboard with charts.
- Excel (.xlsx) + CSV export via Pandas.
- Full activity log with role-action tracking.

---

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.9+
- CMake (required for `dlib` / `face_recognition`)

### Step-by-Step

```bash
# 1. Clone the repository
git clone https://github.com/your-repo/unishield.git
cd unishield

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate        # macOS/Linux
.\venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your keys (SMS API, Admin credentials, etc.)

# 5. Run the application
python app.py
# → Server starts at http://127.0.0.1:8000
# → Database auto-scaffolded on first run
# → Default admin created from .env credentials
```

---

## 🔐 Default Credentials

> ⚠️ **Change these immediately in production!**

Credentials are set via `.env` file:

```env
ADMIN_USERNAME=your_username
ADMIN_EMAIL=your@email.com
ADMIN_PASSWORD=your_password
```

Other roles (HOD, Dean, Warden, Guard, Student) are created by the Admin through the Faculty Authority and Student Registry panels.

---

## 📁 Project Structure

```
UniShield/
├── app.py                  # Application factory + scheduler
├── config.py               # Configuration from .env
├── extensions.py           # Socket.io instance
├── models/
│   ├── user.py             # User model (all roles)
│   ├── outpass.py          # Outpass model (full workflow)
│   └── log.py              # Notification, SMSLog, SMSConfig
├── routes/
│   ├── auth.py             # Login, logout, profile
│   ├── admin.py            # Admin control center
│   ├── student.py          # Student portal
│   ├── faculty.py          # HOD/Dean approval dashboards
│   ├── warden.py           # Warden command center + OTP
│   ├── guard.py            # Guard terminal
│   ├── gate.py             # AI Gate + Socket.io events
│   └── api.py              # REST API endpoints
├── services/
│   ├── sms_service.py      # Fast2SMS + Twilio failover
│   └── face_intelligence.py
├── utils/
│   └── id_card.py          # ID card QR/OCR extraction
├── templates/
│   ├── base.html           # Global layout + sidebar (RBAC nav)
│   ├── admin/
│   ├── student/
│   ├── faculty/
│   ├── warden/
│   ├── guard/
│   └── common/
└── static/
    └── uploads/            # Face photos, documents (gitignored)
```

---

## 🚀 Deployment

- **App Server**: Gunicorn + eventlet (for Socket.io)
- **Reverse Proxy**: Nginx with SSL (HTTPS required for camera/QR access)
- **Database**: SQLite (dev) → PostgreSQL (production recommended)

```bash
# Production run
gunicorn --worker-class eventlet -w 1 "app:create_app()" --bind 0.0.0.0:8000
```

> ⚠️ Camera and QR scanning require **HTTPS** or `localhost` due to browser security policies.

---

## 🔮 Roadmap

- [ ] Mobile App (React Native)
- [ ] Multi-campus Support
- [ ] Cloud Deployment (AWS / GCP)
- [ ] WhatsApp OTP Integration
- [ ] Fingerprint Biometric Support

---

## 👨‍💻 Author

**Priyanshu Kumar**
Sandip University, Nashik

---

*Designed and engineered as a premium, secure standard for campus safety.*

© 2026 UniShield | Sandip University
