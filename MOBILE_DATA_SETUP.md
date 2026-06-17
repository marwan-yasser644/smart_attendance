# 📱 Mobile Data Access Setup Guide

## For College IT Staff

This guide explains how to configure the system so students can submit attendance using mobile data (not just college Wi-Fi).

---

## Quick Start (5 minutes)

### What You Need
- College server running Flask app
- Public IP address or domain name
- Port 5000 open to external traffic

### Step 1: Set BASE_URL

Before starting the app, set this environment variable:

```bash
# Windows Command Prompt
set BASE_URL=http://192.168.1.50:5000

# Windows PowerShell
$env:BASE_URL = "http://192.168.1.50:5000"

# Linux/macOS
export BASE_URL=http://192.168.1.50:5000

# Or with domain
export BASE_URL=https://attendance.college.edu
```

### Step 2: Start the App

```bash
gunicorn --workers 4 --bind 0.0.0.0:5000 app:app
```

### Step 3: Open Firewall

**Windows:**
1. Open Windows Defender Firewall
2. Click "Allow an app through firewall"
3. Click "Allow another app"
4. Select Python (or the Gunicorn executable)
5. Make sure TCP 5000 is allowed
6. Click OK

**Linux:**
```bash
sudo ufw allow 5000/tcp
```

### That's It!

Students can now scan QR codes and submit attendance using mobile data. ✅

---

## Why BASE_URL Matters

### Without BASE_URL (Default Behavior)
```
Lecturer creates session on local network
↓
QR code contains: http://192.168.1.50:5000/attend/<uuid>
↓
Student on campus Wi-Fi: ✅ Works
Student on mobile data: ❌ IP not accessible from internet
```

### With BASE_URL Set
```
Lecturer creates session
↓
QR code contains: https://attendance.college.edu/attend/<uuid>
↓
Student on campus Wi-Fi: ✅ Works
Student on mobile data: ✅ Works
Student off-campus: ✅ Works
```

---

## Different Deployment Scenarios

### Scenario 1: College Server with Public IP

```bash
College Server IP: 192.168.1.50
Port: 5000
```

**Configuration:**
```bash
BASE_URL=http://192.168.1.50:5000
```

**QR Code Points To:** `http://192.168.1.50:5000/attend/...`

**Students Can Scan From:**
- ✅ College Wi-Fi
- ✅ Mobile data (if IP is publicly routable)
- ✅ Outside campus (if firewall allows)

---

### Scenario 2: College Server with Domain

```bash
Domain: attendance.college.edu
Firewall: Maps 192.168.1.50:5000 to attendance.college.edu
```

**Configuration:**
```bash
BASE_URL=https://attendance.college.edu
```

**QR Code Points To:** `https://attendance.college.edu/attend/...`

**Students Can Scan From:**
- ✅ College Wi-Fi
- ✅ Mobile data
- ✅ Anywhere with internet

---

### Scenario 3: Testing with ngrok

Perfect for quick demos before full deployment.

**Step 1: Start Flask locally**
```bash
python run.py  # runs on http://localhost:5000
```

**Step 2: In another terminal, expose with ngrok**
```bash
ngrok http 5000
# Output: Forwarding https://abc123.ngrok.io -> http://localhost:5000
```

**Step 3: Set BASE_URL**
```bash
export BASE_URL=https://abc123.ngrok.io
```

**Step 4: Lecturer creates session**
- QR code now points to: `https://abc123.ngrok.io/attend/...`
- Students scan with mobile data → Works ✅

---

## Troubleshooting

### "Students can't scan QR codes from mobile data"

**Diagnosis:**
1. Check if `BASE_URL` is set:
   ```bash
   echo $BASE_URL  # Linux/macOS
   echo %BASE_URL%  # Windows
   ```
   
2. If empty, the QR code contains a local IP that's not accessible from mobile data

**Fix:**
```bash
# Set BASE_URL to college's public address
export BASE_URL=http://YOUR_COLLEGE_PUBLIC_IP:5000
# or
export BASE_URL=https://your-domain.com

# Restart the app
```

---

### "Firewall blocks access"

**Diagnosis:**
- Try visiting `http://192.168.1.50:5000` from a phone on mobile data
- If it times out or refuses connection, firewall is blocking it

**Fix (Windows):**
1. Open Windows Defender Firewall → Advanced Settings
2. Click Inbound Rules → New Rule
3. Protocol: TCP, Port: 5000
4. Action: Allow
5. Click Finish

**Fix (Linux):**
```bash
sudo ufw allow 5000/tcp
sudo ufw reload
```

---

### "Page loads but attendance submission fails"

**Diagnosis:**
- Check Flask logs for errors
- Verify database is accessible

**Fix:**
- Ensure database (PostgreSQL or SQLite) is running
- Check database connection string

---

## Performance Notes

### For Large Deployments

Use Gunicorn with multiple workers:

```bash
gunicorn --workers 8 --worker-class sync --bind 0.0.0.0:5000 app:app
```

- `--workers 8`: Increase if you have many concurrent students
- Rule of thumb: `workers = (2 × CPUs) + 1`

For example, on a 4-core server:
```bash
gunicorn --workers 9 --bind 0.0.0.0:5000 app:app
```

---

## Security Recommendations

1. **Always use HTTPS in production:**
   ```bash
   # Use a reverse proxy like Nginx with SSL
   BASE_URL=https://attendance.college.edu
   ```

2. **Restrict firewall to known networks:**
   ```bash
   # Only allow from college IP ranges
   sudo ufw allow from 192.168.1.0/24 to any port 5000
   ```

3. **Change SECRET_KEY:**
   ```bash
   export SECRET_KEY=your-long-random-secure-key
   ```

4. **Use strong database passwords:**
   ```bash
   export DATABASE_URL=postgresql://user:STRONG_PASSWORD@localhost:5432/smart_attendance
   ```

---

## Support

For issues or questions:
- See [DEPLOYMENT.md](DEPLOYMENT.md) for full setup guide
- Check Flask logs: `tail -f app.log`
- Review database health: Query `attendance_sessions` and `attendance_records`

---

## Checklist Before Going Live

- [ ] `BASE_URL` set to college's public address
- [ ] Firewall allows inbound traffic on port 5000 (or configured port)
- [ ] Database (PostgreSQL or SQLite) is running
- [ ] Gunicorn/Waitress is running with multiple workers
- [ ] Test: Scan QR code from mobile data, verify submission works
- [ ] HTTPS configured (recommended)
- [ ] Backups configured for database
- [ ] Logging configured for monitoring

✅ All set! Students can now submit attendance from anywhere with internet.
