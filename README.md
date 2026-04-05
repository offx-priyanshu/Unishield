# SNOX | Smart AI-Based Outpass Management System 🚀

![SNOX Banner](https://img.shields.io/badge/Status-Stable-success?style=for-the-badge)
![AI-Vision](https://img.shields.io/badge/AI--Powered-Face%20Recognition-blue?style=for-the-badge)
![Python-Flask](https://img.shields.io/badge/Built%20With-Python%20%26%20Flask-3776AB?style=for-the-badge&logo=python)

**SNOX** stands for **Secure Network Outpass X-System**. It is a next-generation institution management tool that replaces traditional paper outpasses with a fully automated, AI-driven facial recognition pipeline. 

---

## 🏛️ Comprehensive Role Architecture

This system is built with a strictly role-based access control (RBAC) mechanism.

### 1. Administrative Node (Admin)
*   **Total Oversight**: Monitor real-time campus statistics and movement.
*   **User Management**: Enroll new students with AI-face calibration, add security guards, and create sub-admins.
*   **Approval Authority**: Single-click approval/rejection of digital outpass requests.
*   **Intelligence Reports**: Export movement logs and security violations in CSV format.
*   **Blacklist Management**: Permanently or temporarily block students from leaving the campus.

### 2. Security Guard Node (Guard)
*   **Live Vision Matcher**: A high-speed scanning interface to verify student identities.
*   **SID Authentication**: SID-based lookup integrated with live camera frames.
*   **Dual Mode Operation**:
    *   **EXIT**: Verifies if the student has an approved outpass and records the time.
    *   **RETURN**: Marks the student's safe return to campus.
*   **Violation Logging**: Automated alerts if an unauthorized face is detected for an ID.

### 3. Student Node (Student)
*   **Personal Dashboard**: View violation status, outpass history, and active approvals.
*   **Outpass Requests**: Submit detailed outpass requests (Destination, Reason, Expected Return).
*   **Notification Node**: In-app alerts for approval, rejection, or security warnings.

---

## 🧠 Neural Processing Flow

1.  **Request**: Student submits a digital request.
2.  **Validation**: Admin reviews and approves the request.
3.  **Authentication**: At the gate, the Guard enters the SID.
4.  **Face Search**: System fetches the stored **128-dimensional face-encoding** for that ID.
5.  **Matching**: Live camera input is compared against the database.
6.  **Notification**: On successful Exit/Return, a **Secure SMS** is fired to the registered parent's number.

---

## 🛠️ Installation & Setup (Full Procedure)

### System Prerequisites
Ensure your machine has the following installed:
- Python 3.9+
- CMake (Required for `dlib` compilation)
- VS Build Tools (Windows) / XCode Command Line Tools (macOS)

### Step-by-Step Installation
1.  **Initialize Environment**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # macOS/Linux
    .\venv\Scripts\activate   # Windows
    ```
2.  **Install Essential Libraries**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Configure API Services**:
    Edit `config.py` and add your **Fast2SMS API Key** or **Twilio** credentials to enable automated messaging.

4.  **Database Migration**:
    The system uses SQLite. To re-initialize, delete `snox.db` and run the app; tables will auto-generate.

---

## 📝 Database Architecture

*   **Users Table**: Identity details, role, and **JSON-stored face encodings**.
*   **Outpasses Table**: Links students to their requests, timestamps, and guard verification status.
*   **Logs Table**: Comprehensive records of every admin/guard action for audit trails.
*   **Notifications Table**: User-specific alerts and messages.

---

## 📂 Project Organization

```
SNOX/
├── app.py              # Main Flask Application Object
├── config.py           # Configuration (Database, SMS, JWT, Secrets)
├── models/             # Database Models (SQLAlchemy Classes)
│   ├── db.py           # DB Instance
│   ├── user.py         # User & Auth Model
│   └── outpass.py      # Request & Flow Model
├── routes/             # Controller Logic (Blueprints)
│   ├── auth.py         # Login/Logout & Sessions
│   ├── admin.py        # Admin Operations & Management
│   └── guard.py        # Face Scanning & Gate Control
├── services/           # Backend Business Logic
│   └── face_service.py # Neural Matching & Calibration
├── templates/          # Modern UI (Jinja2 Components)
└── utils/              # Utility Scripts (SMS, Export, Logging)
```

---

## 🔐 Initial Access Credentials

To access the system locally, use the following default credentials. **Change them in Production.**

*   **New Master Admin**:
    *   **Username**: `priyanshugse`
    *   **Password**: `vipul@123`
    *   **Email**: `priyanshugse@gmail.com`
*   **Default Guard**:
    *   **Username**: `guard1`
    *   **Password**: `guard123`
*   **Default Student Password**: `student123` (Username is their Student ID).

---

## 🚀 Deployment Guide
For production deployment, it is recommended to use:
- **Web Server**: Gunicorn (for Linux)
- **Proxy**: Nginx (with SSL enabled)
- **Database**: PostgreSQL (Recommended if scaling beyond 1000 users)

---

Developed with ❤️ by the **SNOX Development Team**.
*Focus: Security. Transparency. Automation.*

---
© 2024 SNOX | Smart AI Dashboard
