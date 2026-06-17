# ✅ College Deployment Checklist

Use this checklist to ensure mobile data attendance submission is fully functional.

---

## Pre-Deployment (Planning)

- [ ] **Identified college server**
  - Server IP address: `________________`
  - Server hostname: `________________`
  - Public domain (if available): `________________`

- [ ] **Python environment ready**
  - [ ] Python 3.12+ installed
  - [ ] pip available
  - [ ] Virtual environment prepared (optional but recommended)

- [ ] **Database selected**
  - [ ] SQLite (simpler, file-based) 
  - [ ] PostgreSQL (recommended for production)
    - [ ] PostgreSQL server installed
    - [ ] Database created
    - [ ] User credentials ready

- [ ] **Firewall access**
  - [ ] Can configure Windows Firewall (Windows server) OR
  - [ ] Can configure UFW/iptables (Linux server)
  - [ ] Port 5000 available (or alternate chosen)

---

## Installation (Step-by-Step)

- [ ] **Clone/download application**
  ```bash
  # Verify all files present
  ls -la /path/to/smart_attendance/
  ```
  - [ ] `app/` directory exists
  - [ ] `run.py` exists
  - [ ] `requirements.txt` exists
  - [ ] `DEPLOYMENT.md` exists

- [ ] **Install Python dependencies**
  ```bash
  pip install -r requirements.txt
  ```
  - [ ] Installation completed without errors
  - [ ] All packages listed: Flask, SQLAlchemy, qrcode, Gunicorn, etc.

- [ ] **Create configuration**
  - [ ] `BASE_URL` set to college server address:
    ```bash
    export BASE_URL=https://attendance.college.edu
    # or
    export BASE_URL=http://192.168.1.50:5000
    ```
  - [ ] `SECRET_KEY` set (change from default)
  - [ ] `DATABASE_URL` configured (if using PostgreSQL):
    ```bash
    export DATABASE_URL=postgresql://user:pass@localhost:5432/smart_attendance
    ```

---

## Database Setup

### Option A: SQLite (Default)
- [ ] SQLite3 available on system
- [ ] `instance/` directory will auto-create
- [ ] First run will auto-initialize database

### Option B: PostgreSQL (Recommended)
- [ ] PostgreSQL server installed and running
- [ ] Database created: `smart_attendance`
- [ ] User created with password
- [ ] User has full permissions on database:
  ```sql
  CREATE DATABASE smart_attendance;
  CREATE USER attendance_user WITH PASSWORD 'strong_password';
  GRANT ALL ON DATABASE smart_attendance TO attendance_user;
  ```
- [ ] Connection test successful:
  ```bash
  psql -h localhost -U attendance_user -d smart_attendance
  ```

---

## Application Testing

- [ ] **Start application in test mode**
  ```bash
  export FLASK_ENV=development
  python run.py
  ```
  - [ ] No startup errors
  - [ ] "Running on http://0.0.0.0:5000" message appears
  - [ ] Database auto-initialized

- [ ] **Access application**
  - [ ] From local machine: `http://localhost:5000` → Works ✅
  - [ ] From same network: `http://192.168.1.50:5000` → Works ✅
  - [ ] Login page loads ✅

- [ ] **Verify demo account**
  - [ ] Email: `admin@kfu.edu.eg`
  - [ ] Password: `admin123`
  - [ ] Login successful ✅

- [ ] **Test basic workflow**
  - [ ] Create attendance session ✅
  - [ ] Verify QR code uses BASE_URL (check URL) ✅
  - [ ] Student submission works ✅
  - [ ] Attendance recorded in database ✅

---

## Firewall Configuration

### Windows Firewall

- [ ] **Open Windows Defender Firewall**
  - [ ] Windows Key → Search: "Defender Firewall"
  - [ ] Click "Allow an app through firewall"
  - [ ] Click "Change settings" (if prompted)

- [ ] **Add Python/Gunicorn**
  - [ ] Click "Allow another app"
  - [ ] Select Python installation (usually `C:\Python312\python.exe`)
  - [ ] Click "Add"
  - [ ] Ensure both Private and Public are checked (or as needed)
  - [ ] Click OK

- [ ] **Verify port access**
  ```bash
  netstat -an | find "5000"
  # Should show: TCP 0.0.0.0:5000 LISTENING
  ```

### Linux Firewall (UFW)

```bash
- [ ] **Allow port 5000**
  ```bash
  sudo ufw allow 5000/tcp
  sudo ufw reload
  ```

- [ ] **Verify rule added**
  ```bash
  sudo ufw status
  # Should show: 5000/tcp ALLOW
  ```
```

---

## Production Setup

- [ ] **Install Gunicorn** (should be in requirements.txt)
  ```bash
  pip install gunicorn
  ```

- [ ] **Test Gunicorn startup**
  ```bash
  gunicorn --workers 4 --bind 0.0.0.0:5000 app:app
  ```
  - [ ] No startup errors
  - [ ] Port 5000 listening
  - [ ] Can access from another machine

- [ ] **Configure worker count**
  - [ ] System CPU count: _____ cores
  - [ ] Recommended workers: `(2 × CPUs) + 1` = _____ workers
  - [ ] Set in startup command

- [ ] **Enable service (optional but recommended)**
  - [ ] Create systemd service file (Linux)
  - [ ] OR create scheduled task (Windows)
  - [ ] OR use supervisor/pm2 for process management

---

## Mobile Data Testing

This is the critical test for college deployment!

- [ ] **Setup test scenario**
  - [ ] Lecturer creates session from college network
  - [ ] Get QR code or URL
  - [ ] Verify URL contains your BASE_URL (not localhost)

- [ ] **Student test on Wi-Fi**
  - [ ] Scan QR code while on college Wi-Fi
  - [ ] Form opens ✅
  - [ ] Submit attendance ✅
  - [ ] Verify in lecturer dashboard ✅

- [ ] **Student test on mobile data**
  - [ ] Student disconnects from college Wi-Fi
  - [ ] Student uses only mobile data (cellular)
  - [ ] Scan same QR code
  - [ ] Form opens ✅ (This confirms BASE_URL is working)
  - [ ] Submit attendance ✅
  - [ ] Verify in lecturer dashboard ✅

- [ ] **External test (optional)**
  - [ ] Student tests from home on mobile internet
  - [ ] Form opens ✅ (If BASE_URL is domain)
  - [ ] Submit attendance ✅

**If mobile data test fails:**
- [ ] Check BASE_URL is set correctly
- [ ] Check firewall allows port 5000
- [ ] Check server is publicly accessible
- [ ] Review troubleshooting in MOBILE_DATA_SETUP.md

---

## Security Configuration

- [ ] **Change default password**
  ```bash
  # Create new admin account or change demo account
  # Via application or direct database access
  ```

- [ ] **Set secure SECRET_KEY**
  ```bash
  export SECRET_KEY=your-long-random-secure-string-here
  ```

- [ ] **Use HTTPS in production** (recommended)
  - [ ] Install SSL certificate
  - [ ] Configure Nginx/Apache as reverse proxy with SSL
  - [ ] Update BASE_URL to use https://

- [ ] **Database security**
  - [ ] Strong database password (if PostgreSQL)
  - [ ] Database not accessible from internet
  - [ ] Backups configured
  - [ ] Database logs monitored

---

## Monitoring & Maintenance

- [ ] **Logging configured**
  - [ ] Flask debug logs viewable
  - [ ] Attendance submissions logged
  - [ ] Errors captured and reviewable

- [ ] **Backups setup**
  - [ ] Database backups scheduled (daily or after each lecture day)
  - [ ] Backup location secured
  - [ ] Restore process tested

- [ ] **Performance monitoring**
  - [ ] Can see system resource usage (CPU, memory, disk)
  - [ ] Alert configured if disk runs low
  - [ ] Database query logs available

- [ ] **Student access support**
  - [ ] IT support instructions prepared
  - [ ] FAQ document created
  - [ ] Help email/phone available

---

## Go-Live Checklist (Final)

- [ ] All above items checked ✅
- [ ] Mobile data test passed ✅
- [ ] Demo lecture conducted with test students ✅
- [ ] Staff trained on dashboard usage ✅
- [ ] Backup system confirmed working ✅
- [ ] Rollback plan documented ✅
- [ ] Support contact info shared with users ✅

---

## Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| "Can't connect on mobile data" | Check BASE_URL is set, check firewall |
| "Firewall blocks access" | Add Python to Windows Firewall OR `sudo ufw allow 5000/tcp` |
| "QR code shows localhost" | BASE_URL not set, application not restarted |
| "Students can't scan" | Open port 5000, check college firewall |
| "Database errors" | Check PostgreSQL running, connection string correct |
| "Application won't start" | Check Python 3.12+, all dependencies installed |

---

## Support Resources

📖 **Full Deployment:** `DEPLOYMENT.md`
🔧 **IT Setup Guide:** `MOBILE_DATA_SETUP.md`
⚡ **Quick Reference:** `MOBILE_DATA_QUICK_REFERENCE.txt`
📝 **Implementation:** `MOBILE_DATA_IMPLEMENTATION.md`

---

## Contact & Issues

For issues during deployment:
1. Check troubleshooting sections in DEPLOYMENT.md
2. Review server logs for error messages
3. Verify network/firewall configuration
4. Test endpoints manually with curl/Postman

---

**Completion Date:** `________________`
**Deployed By:** `________________`
**Notes:** `_________________________________`

✅ **When all items are checked, your college is ready for mobile data attendance!**
