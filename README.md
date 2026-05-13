<div align="center">

# 🎓 KSU Smart Attendance System

### Faculty of Artificial Intelligence · Kafrelsheikh University

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/Flask-Production_Ready-000000?style=for-the-badge&logo=flask&logoColor=white"/>
  <img src="https://img.shields.io/badge/PostgreSQL-Supported-316192?style=for-the-badge&logo=postgresql&logoColor=white"/>
  <img src="https://img.shields.io/badge/Render-Deployed-46E3B7?style=for-the-badge&logo=render&logoColor=black"/>
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/Status-Production_Ready-success?style=for-the-badge"/>
</p>

### 🚀 Production-Ready QR-Based Attendance Platform for Universities

A modern, secure, and scalable attendance management system that enables lecturers to create QR-based attendance sessions while students instantly submit attendance using only their smartphone camera — no mobile app required.

---

### 🔗 Quick Links

[Features](#-features) •
[Architecture](#-system-architecture) •
[Installation](#-running-locally) •
[Deployment](#-deploying-online-rendercom--free-tier) •
[Security](#-security-features) •
[Project Structure](#-project-structure)

</div>

---

# 📖 Overview

The **KSU Smart Attendance System** is an enterprise-grade university attendance platform designed to modernize lecture attendance workflows using QR technology.

Instead of traditional manual attendance sheets, lecturers generate a secure QR code session that students scan directly from their phones. Attendance is then validated, recorded, and monitored in real time.

This project was built for the **Faculty of Artificial Intelligence — Kafrelsheikh University**, with a strong focus on:

* ⚡ Simplicity
* 🔒 Security
* 📱 Mobile accessibility
* ☁️ Cloud deployment readiness
* 📊 Real-time monitoring
* 🏗 Production scalability

---

# ✨ Key Highlights

<table>
<tr>
<td width="50%">

## ⚡ Fast Attendance Workflow

* QR-based attendance sessions
* Real-time attendance updates
* Instant student confirmation
* Live session tracking

</td>
<td width="50%">

## 🔒 Enterprise Security

* Password hashing
* Duplicate prevention
* Session expiration validation
* Audit-friendly IP logging

</td>
</tr>

<tr>
<td width="50%">

## 📱 Mobile Optimized

* No mobile app required
* Works with phone camera
* Responsive attendance form
* Fast submission experience

</td>
<td width="50%">

## ☁️ Cloud Ready

* Render deployment support
* PostgreSQL integration
* Gunicorn production server
* Environment-based configuration

</td>
</tr>
</table>

---

# 🎯 Features

## 👨‍🏫 Lecturer Features

| Feature                  | Description                                 |
| ------------------------ | ------------------------------------------- |
| QR Session Generation    | Create secure attendance sessions instantly |
| Live Attendance Tracking | Monitor students joining in real time       |
| Session Expiration       | Automatic attendance session closing        |
| CSV Export               | Export attendance records anytime           |
| Dashboard                | Centralized lecturer management panel       |
| Session Control          | Manually activate/deactivate sessions       |

---

## 🎓 Student Experience

| Feature              | Description                          |
| -------------------- | ------------------------------------ |
| QR Scanning          | Scan QR code directly from camera    |
| No App Required      | Browser-only attendance flow         |
| Fast Submission      | Name + Student ID submission         |
| Mobile Friendly      | Optimized for smartphones            |
| Instant Confirmation | Immediate attendance success message |

---

## 📊 System Features

| Feature                 | Status |
| ----------------------- | ------ |
| QR Code Generation      | ✅      |
| Real-Time Attendance    | ✅      |
| Duplicate Prevention    | ✅      |
| PostgreSQL Support      | ✅      |
| CSV Export              | ✅      |
| Lecturer Authentication | ✅      |
| Session Expiration      | ✅      |
| Render Deployment       | ✅      |
| Mobile Responsive UI    | ✅      |
| Audit Logging           | ✅      |

---

# 📐 System Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│                        INTERNET (Public)                        │
└─────────────────┬───────────────────────────┬───────────────────┘
                  │                           │
          ┌───────▼────────┐        ┌─────────▼──────────┐
          │ Lecturer Panel │        │  Student Device    │
          │ (Browser / PC) │        │ (Phone Camera)     │
          └───────┬────────┘        └─────────┬──────────┘
                  │                           │
          ┌───────▼───────────────────────────▼───────────┐
          │              Flask App (Gunicorn)             │
          │                                                │
          │  /dashboard      → Lecturer Dashboard          │
          │  /session/new    → Create Session + QR         │
          │  /session/<id>   → Live Attendance Monitor     │
          │  /attend/<id>    → Student Attendance Form     │
          │  /api/session/   → Real-Time Polling API       │
          └────────────────────────┬───────────────────────┘
                                   │
                          ┌────────▼────────┐
                          │ SQLite / PGSQL  │
                          │    Database     │
                          └─────────────────┘
```

---

# 🔄 Attendance Workflow

## 👨‍🏫 Lecturer Workflow

1. Lecturer logs into dashboard
2. Creates attendance session
3. Defines:

   * Course name
   * Lecture title
   * Duration
4. System generates:

   * UUID session
   * Unique QR code
5. QR code displayed on projector

---

## 🎓 Student Workflow

1. Student scans QR code
2. Browser opens attendance page
3. Student enters:

   * Full name
   * Student ID
4. Attendance submitted instantly
5. Confirmation page displayed

---

## 📡 Real-Time Updates

* Attendance list refreshes every 5 seconds
* Lecturer dashboard updates automatically
* Duplicate submissions blocked instantly
* Session status validated server-side

---

# 🗄️ Database Schema

## `lecturers`

| Column        | Type         | Description                |
| ------------- | ------------ | -------------------------- |
| id            | INTEGER PK   | Auto increment             |
| name          | VARCHAR(150) | Lecturer full name         |
| email         | VARCHAR(150) | Unique login email         |
| password_hash | VARCHAR(256) | Secure password hash       |
| created_at    | DATETIME     | Account creation timestamp |

---

## `attendance_sessions`

| Column       | Type         | Description           |
| ------------ | ------------ | --------------------- |
| id           | INTEGER PK   | Session identifier    |
| session_uuid | VARCHAR(36)  | QR session UUID       |
| title        | VARCHAR(200) | Lecture title         |
| course_name  | VARCHAR(200) | Course name           |
| course_code  | VARCHAR(50)  | Academic course code  |
| lecturer_id  | FK           | Linked lecturer       |
| created_at   | DATETIME     | Session creation time |
| expires_at   | DATETIME     | Session expiration    |
| is_active    | BOOLEAN      | Session state         |

---

## `attendance_records`

| Column          | Type         | Description          |
| --------------- | ------------ | -------------------- |
| id              | INTEGER PK   | Record ID            |
| session_id      | FK           | Linked session       |
| student_name    | VARCHAR(150) | Student full name    |
| student_id      | VARCHAR(50)  | Uppercase student ID |
| submitted_at    | DATETIME     | UTC timestamp        |
| ip_address      | VARCHAR(45)  | Audit IP logging     |
| submission_hash | VARCHAR(64)  | SHA-256 unique hash  |

> ⚠️ Duplicate prevention is enforced at the database level using a UNIQUE constraint on `submission_hash`.

---

# 🔒 Security Features

| Security Layer       | Implementation                 |
| -------------------- | ------------------------------ |
| Password Hashing     | Werkzeug scrypt hashing        |
| Authentication       | Flask signed sessions          |
| Duplicate Prevention | SHA-256 + UNIQUE DB constraint |
| Session Expiry       | Server-side validation         |
| Input Validation     | Length & presence checks       |
| IP Logging           | Audit-friendly tracking        |
| CSRF Protection      | SameSite cookie strategy       |

---

# 🚀 Running Locally

## Prerequisites

* Python 3.10+
* pip

---

## Installation

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/kfu-smart-attendance.git

# Navigate into project
cd kfu-smart-attendance

# Create virtual environment
python -m venv venv

# Activate environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run development server
python run.py
```

---

## Access Application

```text
http://localhost:5000
```

### Demo Credentials

```text
Email:    admin@kfu.edu.eg
Password: admin123
```

---

# ☁️ Deploying Online (Render.com — Free Tier)

## Deployment Steps

### 1️⃣ Push Project to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/kfu-smart-attendance.git
git push -u origin main
```

---

### 2️⃣ Create Render Account

Visit:

```text
https://render.com
```

---

### 3️⃣ Configure Web Service

| Setting       | Value                                 |
| ------------- | ------------------------------------- |
| Runtime       | Python 3                              |
| Build Command | pip install -r requirements.txt       |
| Start Command | gunicorn app:app --bind 0.0.0.0:$PORT |

---

### 4️⃣ Environment Variables

```env
SECRET_KEY=your_secret_key
FLASK_ENV=production
DATABASE_URL=postgresql://...
```

---

# 📁 Project Structure

```text
smart_attendance/
├── app.py
├── run.py
├── requirements.txt
├── Procfile
├── render.yaml
├── README.md
├── instance/
│   └── attendance.db
├── static/
│   └── images/
│       ├── logo_kfs.png
│       └── logo_ai.png
└── templates/
    ├── base.html
    ├── login.html
    ├── register.html
    ├── dashboard.html
    ├── new_session.html
    ├── session_detail.html
    ├── attend.html
    ├── attend_success.html
    ├── attend_closed.html
    └── attend_duplicate.html
```

---

# 📈 Future Improvements

* 🔔 Push notifications
* 📱 Native mobile app
* 📊 Advanced analytics dashboard
* 🎓 LMS integration
* ☁️ Multi-university support
* 🤖 AI-powered attendance insights
* 📍 Geolocation validation
* 🧠 Face recognition integration

---

# 🤝 Contributing

Contributions, issues, and feature requests are welcome.

Feel free to:

* Fork the repository
* Create a feature branch
* Submit pull requests
* Improve documentation
* Suggest enhancements

---

# 📜 License

This project is licensed under the MIT License.

---

# 👨‍💻 Author

### Marwan Yasser Lotfy

Faculty of Artificial Intelligence
Kafrelsheikh University

* GitHub: https://github.com/marwan-yasser644
* LinkedIn: https://www.linkedin.com/in/marawan-yasser-3005742a0/
* Gmail:marawanyasser644@gmail.com

---

<div align="center">

### ⭐ If you like this project, consider giving it a star on GitHub!

Built with ❤️ for smarter university education systems.

</div>
