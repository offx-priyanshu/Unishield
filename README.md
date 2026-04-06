# SNOX | Smart AI-Based Outpass Management System 🚀

![SNOX Banner](https://img.shields.io/badge/Status-Stable-success?style=for-the-badge)
![Security](https://img.shields.io/badge/Security-QR%20Enabled-00e5ff?style=for-the-badge)
![Backend](https://img.shields.io/badge/Backend-Python%20%26%20Flask-3776AB?style=for-the-badge&logo=python)
![Theme](https://img.shields.io/badge/Theme-Dark%20Glassmorphism-black?style=for-the-badge)

**SNOX** stands for **Secure Network Outpass X-System**. It is a next-generation institution management tool that modernizes campus security using dynamic QR Codes, an AI-powered face/ID matching engine, and intelligent communication protocols.

---

## 🔥 Newly Integrated Features

*   **AI-Powered Face Recognition**: Mandatory face scanning during both Exit and Return. Uses neural encodings to verify identity with a configurable tolerance engine.
*   **Physical ID Card Verification**: Mandatory ID card scan during student enrollment. The system stores both the face encoding and the physical card image for cross-verification.
*   **Dual-Recipient SMS Alerts**: Real-time automated SMS notifications sent simultaneously to both the **Student** and their **Parent/Guardian** during all critical events (Exit, Return, Overdue, Blacklist).
*   **Professional Reporting & Excel Export**: Generate comprehensive student and movement reports with one-click **Excel (.xlsx)** and CSV exporting capabilities using Pandas/OpenPyxl.
*   **Security Credential Management**: 
    *   **Self-Service**: All roles (Student, Guard, Admin) can securely update their own passwords via the "Edit Credentials" portal.
    *   **Administrative Reset**: Admins can override and reset any user's password directly from the management directory.
*   **Immediate Auto-Blacklisting**: Built-in security logic that automatically blocks student access and notifies parents instantly if face verification fails at the gate or if return limits are exceeded.
*   **Dynamic QR-Code Outpasses**: Students receive a secure, countdown-enabled QR token immediately upon approval for secondary verification.

---

## 🏛️ Comprehensive Role Architecture

This system is built with a strictly role-based access control (RBAC) mechanism.

### 1. Administrative Node (Admin)
*   **Total Oversight**: Live analytics dashboard to monitor students currently out and pending requests.
*   **Departure Control**: Single-click approval/rejection of digital outpass requests from the main departure board.
*   **SMS Testing & Configuration**: Configure API keys and test SMS templates dynamically from the UI.
*   **Intelligent Blacklisting**: Permanently or temporarily block students manually or configure the auto-blacklist system based on violation count.

### 2. Security Guard Node (Guard)
*   **Live Vision Scanner**: A web-based camera scanner (using jsQR) to verify student outpass validity.
*   **Gate Control**:
    *   **EXIT**: Validates the unexpired QR Code and marks the student out.
    *   **RETURN**: Scans token and marks the student's safe return to campus.
*   **Manual Entry Validation**: Allows manual entry of tokens in case the camera fails to lock onto a QR code.

### 3. Student Node (Student)
*   **Personal Dashboard**: View violation standing and track digital outpass requests.
*   **Request Outpass**: Submit requests via Fetch API to the core backend engine.
*   **Live Boarding Pass (QR)**: Watch real-time countdown clocks marking exact expected return times associated with the generated QR token.

---

## 🛠️ Installation & Setup (Full Procedure)

### System Prerequisites
Ensure your machine has the following installed:
- Python 3.9+
- CMake (Required for any neural vision engines processing)

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
3.  **Run Application**:
    ```bash
    python app.py
    ```

---

## 🔐 Initial Access Credentials

To access the system locally, use the following default credentials. **Change them in Production.**

*   **Master Admin**:
    *   **Username**: `priyanshugse`
    *   **Password**: `vipul@123`
*   **Default Guard**:
    *   **Username**: `guard1`
    *   **Password**: `guard123`
*   **Default Student Password**: `student123` (Username is their Student ID).

---

## 🚀 Deployment Guide
For production deployment, it is recommended to use:
- **Web Server**: Gunicorn (for Linux)
- **Proxy**: Nginx (with SSL enabled)
- **Note**: QR scanning logic via device cameras using WebRTC mandates secure contexts (`https://` or `localhost`). 

---

Developed with ❤️ by the **SNOX Development Team**.
*Focus: Security. Transparency. Automation.*

---
© 2024 SNOX | Smart AI Dashboard
