# 🎓 KSU Smart Attendance System
**Faculty of Artificial Intelligence · Kafrelsheikh University**

A production-ready QR-based attendance system for university lectures. Students scan a QR code with their phone (no app required), submit their name and ID, and attendance is recorded instantly online.

---

## 📐 System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        INTERNET (Public)                        │
└─────────────────┬───────────────────────────┬───────────────────┘
                  │                           │
          ┌───────▼────────┐        ┌─────────▼──────────┐
          │  Lecturer Panel │        │   Student Device   │
          │  (Browser/PC)  │        │  (Phone Camera)    │
          └───────┬────────┘        └─────────┬──────────┘
                  │                           │
          ┌───────▼───────────────────────────▼───────────┐
          │               Flask App (Gunicorn)             │
          │                                                │
          │   /dashboard     → Lecturer panel             │
          │   /session/new   → Create session + QR        │
          │   /session/<id>  → View attendance live       │
          │   /attend/<id>   → Student submission form    │
          │   /api/session/  → Live status polling        │
          └────────────────────────┬───────────────────────┘
                                   │
                          ┌────────▼────────┐
                          │   SQLite / PG   │
                          │    Database     │
                          └─────────────────┘
```

### Flow Summary
1. **Lecturer** logs in → creates a session (course, title, duration)
2. System generates a unique UUID-based URL + QR code
3. **QR code** is displayed on projector screen
4. **Students** scan with phone → browser opens → fill name + ID → submit
5. Attendance recorded with timestamp, duplicate prevention by hash
6. **Lecturer** sees live list updating every 5 seconds
7. Export to CSV anytime

---

## 🗄️ Database Schema

### `lecturers`
| Column         | Type        | Notes                       |
|----------------|-------------|-----------------------------|
| id             | INTEGER PK  | Auto-increment              |
| name           | VARCHAR(150)| Full name                   |
| email          | VARCHAR(150)| Unique, used for login      |
| password_hash  | VARCHAR(256)| Werkzeug scrypt hash        |
| created_at     | DATETIME    | Account creation time       |

### `attendance_sessions`
| Column         | Type        | Notes                       |
|----------------|-------------|-----------------------------|
| id             | INTEGER PK  |                             |
| session_uuid   | VARCHAR(36) | Unique UUID, in QR URL      |
| title          | VARCHAR(200)| e.g. "Lecture 5 – CNNs"    |
| course_name    | VARCHAR(200)|                             |
| course_code    | VARCHAR(50) | e.g. "AI301"               |
| lecturer_id    | FK          | References lecturers.id     |
| created_at     | DATETIME    |                             |
| expires_at     | DATETIME    | created_at + duration       |
| is_active      | BOOLEAN     | Manual close toggle         |

### `attendance_records`
| Column           | Type       | Notes                       |
|------------------|------------|-----------------------------|
| id               | INTEGER PK |                             |
| session_id       | FK         | References sessions.id      |
| student_name     | VARCHAR(150)|                            |
| student_id       | VARCHAR(50)| Stored UPPERCASE           |
| submitted_at     | DATETIME   | UTC timestamp               |
| ip_address       | VARCHAR(45)| For audit trail             |
| submission_hash  | VARCHAR(64)| SHA-256(session_id:student_id), UNIQUE |

> **Duplicate Prevention**: The `submission_hash` column has a UNIQUE constraint. Any second submission from the same student ID in the same session will fail at the DB level, even under concurrent load.

---

## 🚀 Running Locally

### Prerequisites
- Python 3.10+
- pip

### Setup

```bash
# 1. Clone / download the project
cd smart_attendance

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the development server
python run.py
```

Visit: **http://localhost:5000**

**Demo credentials:**
- Email: `admin@kfu.edu.eg`
- Password: `admin123`

---

## ☁️ Deploying Online (Render.com — Free Tier)

Render is the easiest platform for Flask deployment with a free tier.

### Step-by-step:

1. **Push to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial KFU attendance system"
   git remote add origin https://github.com/YOUR_USERNAME/kfu-attendance.git
   git push -u origin main
   ```

2. **Create account** at [render.com](https://render.com)

3. **New → Web Service** → Connect your GitHub repo

4. **Configure:**
   - **Name**: `kfu-smart-attendance`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python -c "from app import init_db; init_db()" && gunicorn app:app --bind 0.0.0.0:$PORT`

5. **Environment Variables** (in Render dashboard):
   ```
   SECRET_KEY = any-long-random-string-here
   FLASK_ENV  = production
   ```

6. Click **Deploy** — your app will be live at:
   `https://kfu-smart-attendance.onrender.com`

### Using PostgreSQL (recommended for production):

1. In Render: **New → PostgreSQL** → Free tier
2. Copy the **Internal Database URL**
3. Add environment variable:
   ```
   DATABASE_URL = postgresql://...
   ```
4. The app auto-detects and switches to PostgreSQL.

---

## 🔒 Security Features

| Feature | Implementation |
|---------|---------------|
| Password hashing | Werkzeug scrypt (bcrypt-equivalent) |
| Session auth | Flask signed cookies with SECRET_KEY |
| Duplicate prevention | SHA-256 hash with UNIQUE DB constraint |
| Session expiry | Server-side timestamp validation |
| IP logging | Stored for audit, supports X-Forwarded-For |
| Input validation | Server-side length + presence checks |
| CSRF protection | Flask session cookie + SameSite |

---

## 📱 Student Experience

1. Lecturer displays QR on projector
2. Student opens **Camera app** → points at QR
3. Phone browser opens the attendance URL
4. Student fills name + ID (10 seconds)
5. Taps **Submit** → sees confirmation screen
6. Done ✓

**No app download. No login. No Wi-Fi dependency (uses mobile data).**

---

## 📊 Features Summary

| Feature | Status |
|---------|--------|
| QR code generation | ✅ |
| Session time limit | ✅ |
| Duplicate prevention | ✅ |
| Live attendance list | ✅ (5s polling) |
| CSV export | ✅ |
| Lecturer authentication | ✅ |
| Mobile-optimized student form | ✅ |
| Session close manually | ✅ |
| University logos | ✅ |
| PostgreSQL support | ✅ |
| Render/Railway deploy ready | ✅ |

---

## 📁 Project Structure

```
smart_attendance/
├── app.py                    # Main Flask application
├── run.py                    # Dev server launcher
├── requirements.txt          # Python dependencies
├── Procfile                  # Gunicorn production server
├── render.yaml               # Render.com deployment config
├── README.md                 # This file
├── instance/
│   └── attendance.db         # SQLite database (auto-created)
├── static/
│   └── images/
│       ├── logo_kfs.png      # Kafrelsheikh University logo
│       └── logo_ai.png       # Faculty of AI logo
└── templates/
    ├── base.html             # Base layout with sidebar
    ├── login.html            # Lecturer login page
    ├── register.html         # Lecturer registration
    ├── dashboard.html        # Main dashboard
    ├── new_session.html      # Create session form
    ├── session_detail.html   # QR + live attendance view
    ├── attend.html           # Student submission form
    ├── attend_success.html   # Confirmation screen
    ├── attend_closed.html    # Expired/closed session
    └── attend_duplicate.html # Already submitted notice
```

---

*Built for the Faculty of Artificial Intelligence · Kafrelsheikh University*
#   s m a r t _ a t t e n d a n c e 
 
 # smart_attendance
