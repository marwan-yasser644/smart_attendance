# Deployment and Operations Guide

## Overview
The system is designed for colleges with servers. Students can scan QR codes and submit attendance using their mobile data, as long as the server is externally accessible.

---

## 1. Local Development (Localhost Testing)
```bash
python -m venv .venv
source .venv/bin/activate  # or .\.venv\Scripts\activate on Windows
pip install -r requirements.txt
python run.py
```
- Open http://localhost:5000
- Demo login: `admin@kfu.edu.eg` / `admin123`
- **Note**: Students can only attend from localhost (not from external mobile data)

---

## 2. College Server Deployment (Windows Server or Linux)

### Prerequisites
- Python 3.12+
- PostgreSQL (recommended for production) or SQLite
- College server with public IP or domain
- Port 5000 (or your chosen port) open to external traffic

### Step 1: Install Dependencies
```bash
python -m venv venv
venv\Scripts\activate  # Windows
# or
source venv/bin/activate  # Linux/macOS

pip install -r requirements.txt
```

### Step 2: Configure Environment Variables

Create a `.env` file or set system environment variables:

```bash
# Critical: Set BASE_URL to your college's public address
# This makes QR codes work for students on mobile data
BASE_URL=http://192.168.1.100:5000
# or with a domain:
BASE_URL=https://attendance.college.edu
# or with a port:
BASE_URL=http://attendance.college.edu:8000

# Database (default is SQLite)
DATABASE_URL=sqlite:///instance/attendance.db
# or PostgreSQL:
DATABASE_URL=postgresql://user:password@localhost:5432/smart_attendance

# Security
SECRET_KEY=your-secure-random-key-here
FLASK_ENV=production
```

### Step 3: Run with Gunicorn (Production)

```bash
gunicorn --workers 4 --bind 0.0.0.0:5000 --timeout 60 app:app
```

Or on Windows with Waitress:
```bash
waitress-serve --port=5000 app:app
```

### Step 4: Configure Firewall

**Windows Server:**
1. Open **Windows Defender Firewall → Inbound Rules**
2. Create new rule:
   - Protocol: TCP
   - Port: 5000
   - Action: Allow
3. Click OK

**Linux:**
```bash
sudo ufw allow 5000/tcp
```

### Step 5: Verify External Access

Students can now scan QR codes from:
- ✅ Same college network (Wi-Fi)
- ✅ Mobile data (external access)
- ✅ Remote locations (if college has public IP/domain)

---

## 3. ngrok Tunnel (Quick Testing with Mobile Data)

Perfect for demonstrating to college staff before full deployment.

### Step 1: Install & Authenticate ngrok
```bash
# Download from https://ngrok.com/download
ngrok config add-authtoken YOUR_AUTH_TOKEN
```

### Step 2: Start Flask App
```bash
python run.py
# Server runs on http://localhost:5000
```

### Step 3: Expose via ngrok (in another terminal)
```bash
ngrok http 5000
```

### Step 4: Set BASE_URL Before Generating QR

In your Flask app or config:
```bash
export BASE_URL=https://abc123.ngrok.io
# or in Python:
# BASE_URL = "https://abc123.ngrok.io"
```

Then:
1. Lecturer logs in
2. Creates a session
3. QR code now points to: `https://abc123.ngrok.io/attend/<session_uuid>`
4. Students scan with mobile data → Attendance recorded ✓

---

## 4. How QR Codes Work

### QR Generation Flow
1. Lecturer creates attendance session
2. System checks `BASE_URL` environment variable
3. If `BASE_URL` is set → QR points to college's public server
4. If `BASE_URL` is empty → QR points to `request.host_url` (local IP)

### Student Attendance Flow
1. Student scans QR code with phone camera
2. Browser opens attendance form
3. Student enters name + student ID
4. Submission goes to `/attend/<session_uuid>`
5. Server validates and records attendance
6. Student sees confirmation page

---

## 5. Production Setup for College

### Recommended Architecture
```
┌─────────────────────────────────────┐
│   College Network                   │
├─────────────────────────────────────┤
│  Windows/Linux Server               │
│  ├─ Flask App (Gunicorn/Waitress)   │
│  ├─ PostgreSQL Database             │
│  └─ Port 5000 (Firewall Open)       │
└─────────────────────────────────────┘
         ↑
         │ External Access
         │
┌─────────────────────────────────────┐
│   Students (Mobile Data)            │
│   ├─ Scan QR Code                   │
│   ├─ Browser opens https://...      │
│   └─ Submit Attendance              │
└─────────────────────────────────────┘
```

### Configuration Checklist
- [ ] `BASE_URL` set to college's public IP/domain
- [ ] Firewall allows inbound traffic on port 5000
- [ ] PostgreSQL database created (or SQLite configured)
- [ ] `SECRET_KEY` changed to a secure random string
- [ ] `FLASK_ENV=production`
- [ ] Gunicorn running with multiple workers (e.g., `--workers 4`)
- [ ] HTTPS enabled (recommended for production)

---

## 6. PostgreSQL Setup (Recommended for College)

### Windows Server
1. Install PostgreSQL from https://www.postgresql.org/download/windows/
2. Create database:
   ```sql
   CREATE DATABASE smart_attendance;
   CREATE USER attendance_user WITH PASSWORD 'secure_password';
   GRANT ALL PRIVILEGES ON DATABASE smart_attendance TO attendance_user;
   ```
3. Set environment variable:
   ```
   DATABASE_URL=postgresql://attendance_user:secure_password@localhost:5432/smart_attendance
   ```

### Linux
```bash
sudo apt install postgresql postgresql-contrib
sudo -u postgres psql
```

Then in PostgreSQL:
```sql
CREATE DATABASE smart_attendance;
CREATE USER attendance_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE smart_attendance TO attendance_user;
\q
```

Then set:
```bash
export DATABASE_URL=postgresql://attendance_user:secure_password@localhost:5432/smart_attendance
```

---

## 7. Lecturer & Student Access

### First Time Setup
1. Start the app
2. Demo lecturer automatically created: `admin@kfu.edu.eg` / `admin123`
3. Lecturer logs in and creates sessions
4. Students scan QR codes (works on mobile data if `BASE_URL` is set)

### Adding More Lecturers
1. Lecturer visits `/register`
2. Creates account (email + password)
3. Can now create attendance sessions

---

## 8. Troubleshooting

### "QR code doesn't work from mobile data"
- **Issue**: `BASE_URL` not set
- **Fix**: Set `BASE_URL=http://YOUR_COLLEGE_IP:5000` or `https://your-domain.com`

### "Firewall blocks access"
- **Issue**: Port 5000 not open
- **Fix**: Add inbound rule in Windows Defender Firewall (see Step 4 above)

### "Database errors on startup"
- **Issue**: Old SQLite schema incompatible with new models
- **Fix**: App automatically rebuilds SQLite on first run with new schema

### "Attendance submission fails"
- **Issue**: Server URL in QR code is wrong
- **Fix**: Verify `BASE_URL` points to publicly accessible server

---

## 9. Monitoring & Maintenance

### Check Running Services
```bash
ps aux | grep gunicorn    # Linux
tasklist | grep python     # Windows
```

### View Logs
- Gunicorn logs to console by default
- Use `--access-logfile -` and `--error-logfile -` to see requests

### Backup Database
```bash
# PostgreSQL
pg_dump smart_attendance > backup.sql

# SQLite
cp instance/attendance.db instance/attendance.db.backup
```

---

## 10. Summary

| Scenario | BASE_URL | Works? |
|----------|----------|--------|
| Local network (Wi-Fi) | Not required | ✅ Yes |
| Mobile data on campus | `http://192.168.1.100:5000` | ✅ Yes |
| Remote access | `https://attendance.college.edu` | ✅ Yes |
| ngrok demo | `https://abc123.ngrok.io` | ✅ Yes |

**Key takeaway**: Set `BASE_URL` to your college's public server address, and students anywhere can submit attendance via mobile data.
