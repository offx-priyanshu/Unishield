# UniShield | Smart AI-Based Campus Security System 🚀

![UniShield Banner](https://img.shields.io/badge/Status-Stable-success?style=for-the-badge)
![Security](https://img.shields.io/badge/Security-AI%20%26%20Biometrics-00e5ff?style=for-the-badge)
![Backend](https://img.shields.io/badge/Backend-Python%20%26%20Flask-3776AB?style=for-the-badge&logo=python)
![Theme](https://img.shields.io/badge/Theme-Dark%20Glassmorphism-black?style=for-the-badge)

**UniShield** is the official next-generation institution management and campus security platform, specifically tailored for seamless entry and outpass operations. It modernizes campus security using dynamic QR Codes, an AI-powered face/ID matching engine, multi-stage biometric registration flow, and intelligent communication protocols.

---

## 🔥 Key Features & Capabilities

*   **AI-Powered Face Recognition**: High-performance, multi-angle face scanning during all entries and exits. Uses neural encodings to verify identity with a zero-delay tolerance engine for maximum accuracy.
*   **Physical ID & Biometric Verification**: Mandatory ID card scan (QR/OCR) during automated student enrollment. The system securely pairs the student's face encodings with their physical ID to establish a highly reliable central source of truth.
*   **Dual-Recipient SMS Alerts**: Real-time automated SMS notifications with failover logic sent simultaneously to both the **Student** and their **Parent/Guardian** during critical events (Exit, Return, Overdue, Blacklist).
*   **Dynamic QR-Code Outpasses**: Students receive a secure, countdown-enabled dynamic QR token immediately upon outpass approval, ensuring reliable secondary-layer verification at the perimeter.
*   **Intelligent Auto-Blacklisting**: Built-in security logic that instantly blocks student access and overrides permissions if face verification fails at the AI Gate or if outpass validity times are severely breached.
*   **Professional Reporting & Audits**: Generate comprehensive student entry/exit and role movement logs with one-click **Excel (.xlsx)** and CSV exports using powerful Pandas mapping.
*   **Role-Based Security Control Center (RBAC)**: Comprehensive permission structure across multi-tier admin, staff, student, and guard accounts with extensive oversight tracking.

---

## 🏛️ Comprehensive Role Architecture

This suite utilizes a strict Role-Based Access Control (RBAC) hierarchy.

### 1. Security Control Center (Admin & Management)
*   **Command Overview**: Real-time, auto-updating live dashboard displaying campus occupancy limits and active outpass statuses.
*   **Approval Console**: Complete oversight for single-click approvals/rejections of digital outpass requests.
*   **Automated Provisioning Workflow**: Configure API keys, adjust SMS thresholds, and manage approval queues dynamically.
*   **Blacklist Engine**: Perform absolute overrides on access privileges or automate intelligent temporary bans based on student infraction policies.

### 2. AI Gate Terminal (Guard Node)
*   **Live Vision Verification**: A high-performance split-screen WebRTC camera interface to securely lock onto faces and outpass QR tokens.
*   **Gate Control & Logging**:
    *   **EXIT**: Validates identity and unexpired QR Code, automatically logging the departure.
    *   **RETURN**: Dual-scan logic for facial validation, allowing automatic logging of safe returns.
*   **Registration Terminal**: Interface for security staff to securely onboard new students precisely matching their identity.

### 3. Student Portal (Sandip University Portal Node)
*   **Interactive Dashboard**: Premium dark-mode interface utilizing modern glassmorphism UI for viewing violation status and requesting outpasses.
*   **Secure Submissions**: Interface with the system securely to manage their own tokens and access logs without delay.
*   **Live Boarding Pass**: Interactive QR Outpass with accurate countdowns mapping the validity of their permitted external trip.

---

## 🛠️ Installation & Setup

### System Prerequisites
Ensure your local environment provides:
- Python 3.9+
- CMake (Required for robust neural vision capabilities and the `dlib`/`face_recognition` engines)

### Step-by-Step Installation
1.  **Initialize Environment**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # macOS/Linux
    .\venv\Scripts\activate   # Windows
    ```
2.  **Install Core Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Environment Configuration**:
    Rename `.env.example` to `.env` and assign your local SQL/Postgres URI, secure secrets, and applicable SMS webhook keys.
4.  **Run Main Server Engine**:
    ```bash
    python app.py
    ```
    *The system automatically boots SocketIO integrations and the database scaffolding on its first initialization.*

---

## 🔐 System Initialization Credentials

Default credentials provided at core initialization. **Must be rotated immediately in Production.**

*   **Master Admin (Owner)**:
    *   **Username**: As defined in `.env` (`ADMIN_USERNAME` / `ADMIN_EMAIL`)
    *   **Password**: As defined in `.env` (`ADMIN_PASSWORD`)
*   **Default Guard Nodes**:
    *   Configurable via the management center upon setup.
*   **Student Initialization**: Based on imported roster records and initial sync matching.

---

## 🚀 Deployment Strategy
For optimized production deployment:
- **Application Server**: High-throughput WSGI/ASGI like Gunicorn/Uvicorn (Linux)
- **Reverse Proxy**: Nginx with SSL strictly enabled
- **Crucial Note for Hardware Cameras**: Browser security policies mandate that the `jsQR` and Face Scanning algorithms operate on an active secure context. The server **must** be deployed via `https://` or served locally over `localhost` for testing.

---

## 🔮 Future Scope
- Mobile App Integration
- Cloud Deployment
- Advanced AI Security Alerts
- Multi-campus Support

---

## 👨‍💻 Author
Priyanshu Kumar

---

*Designed and engineered as a premium, secure standard for campus safety.*

---
© 2024 UniShield | Sandip University
