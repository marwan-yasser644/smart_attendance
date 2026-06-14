# Vercel Deployment Fix Guide

## Problem Analysis
Your `/session/new` 500 error on Vercel is caused by:

1. **Incompatible entry point** - `run.py` uses `app.run()` which doesn't work on serverless
2. **Missing `api/index.py`** - Vercel expects WSGI app in this location
3. **Outdated `vercel.json`** - Uses deprecated Vercel Python builder config
4. **SQLite on Vercel** - Default SQLite doesn't persist on Vercel (resets after each deployment)

## Files Updated

### ✅ Created: `api/index.py`
- Proper WSGI entry point for Vercel
- Initializes Flask app correctly for serverless

### ✅ Updated: `vercel.json`
- Uses modern Vercel configuration format
- Points to `api/index.py` instead of `run.py`
- Sets Python runtime to 3.11

### ✅ Updated: `app/__init__.py`
- Error handling for database initialization
- Won't crash if database is temporarily unavailable

## Environment Variables Required on Vercel

Go to **Vercel Project Settings → Environment Variables** and add:

```
DATABASE_URL = postgresql://user:password@host:port/dbname
SECRET_KEY = your-secret-key-here
BASE_URL = https://your-vercel-app.vercel.app
FLASK_ENV = production
```

## Database Configuration

### Option 1: PostgreSQL (Recommended for Production)
Use a managed PostgreSQL service:
- **Recommended:** Railway.app, Render.com, or Supabase
- Update `DATABASE_URL` environment variable

Example PostgreSQL connection string:
```
postgresql://postgres:password@db.example.com:5432/smart_attendance
```

### Option 2: MongoDB (Your mention)
If you want to switch to MongoDB:

**Step 1:** Add pymongo to `requirements.txt`:
```
pymongo==4.6.0
```

**Step 2:** Update `app/config.py`:
```python
import pymongo

class Config:
    # ... existing config ...
    
    MONGODB_URI = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/')
    DB_NAME = 'smart_attendance'
```

**Step 3:** Add to Vercel environment variables:
```
MONGODB_URI = mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
```

### Option 3: SQLite with Persistent Storage
SQLite works but won't persist between Vercel deployments. If you want to use it:
- Data will be reset on each deployment (not recommended for production)

## Deployment Steps

1. **Update local code:**
   ```bash
   git add api/index.py vercel.json app/__init__.py
   git commit -m "Fix Vercel deployment configuration"
   git push origin main
   ```

2. **Set environment variables on Vercel:**
   - Go to Vercel Project → Settings → Environment Variables
   - Add `DATABASE_URL` and other required variables

3. **Redeploy:**
   ```bash
   vercel --prod
   ```
   Or push to GitHub and Vercel will auto-deploy

4. **Test the `/session/new` route:**
   ```
   https://your-app.vercel.app/session/new
   ```

## Troubleshooting

### Still getting 500 error?
1. Check Vercel logs: `vercel logs --prod`
2. Look for database connection errors
3. Verify all environment variables are set
4. Ensure `DATABASE_URL` is valid

### Session route shows database error?
- Verify `DATABASE_URL` environment variable is correct
- For PostgreSQL, test connection string locally first
- For MongoDB, ensure IP whitelist includes Vercel's IPs (use 0.0.0.0/0 as temporary test)

### Can't upload files?
- Vercel serverless has no persistent file system
- For QR codes and exports, use temporary in-memory buffers (already configured ✓)

## Verification

After deployment, test these endpoints:
- `https://your-app.vercel.app/` → Should redirect to login
- `https://your-app.vercel.app/login` → Login page loads
- `https://your-app.vercel.app/session/new` → Should work after login (no 500 error)

## Next Steps

1. **Choose your database** (PostgreSQL recommended for simplicity)
2. **Set environment variables** on Vercel
3. **Test locally first:**
   ```bash
   export DATABASE_URL="your-test-connection-string"
   python run.py
   ```
4. **Deploy and verify logs:**
   ```bash
   vercel logs --prod
   ```
