# Quick Start Guide - Firebase & Heroku

## 5-Minute Firebase Setup (Local)

### 1. Get Firebase Service Account
```
Firebase Console → Project Settings → Service Accounts → Generate Key
```

### 2. Save in Project Root
```
warranty_v2/
├── app.py
├── service-account-key.json  ← Save here
```

### 3. Set Environment Variable
```powershell
# Windows PowerShell
$env:FIREBASE_SERVICE_ACCOUNT = "C:\Users\DELL\Downloads\warranty_v2\service-account-key.json"

# Then run
python app.py
```

✅ If you see `[Firebase] Firestore initialized.` in console, it works!

---

## 10-Minute Heroku Deployment

### 1. Create Heroku App
```bash
heroku login
heroku create your-app-name
```

### 2. Set Firebase (Pick ONE method)

**Method A - Direct JSON (Easiest):**
```bash
heroku config:set FIREBASE_SERVICE_ACCOUNT_JSON='{"type":"service_account","project_id":"..."}'
```

**Method B - File Path:**
```bash
heroku config:set FIREBASE_SERVICE_ACCOUNT=/path/to/serviceAccountKey.json
```

### 3. Deploy
```bash
git add .
git commit -m "Deploy to Heroku with Firebase"
git push heroku main
```

### 4. Verify
```bash
heroku logs --tail | grep Firebase
# Should see: [Firebase] Firestore initialized.
```

### 5. Access App
```bash
heroku open
```

---

## Configuration Files Reference

| File | Purpose |
|------|---------|
| `.env.example` | Example environment variables |
| `config.txt` | Documentation for each setting |
| `FIREBASE_SETUP.md` | Detailed Firebase guide |
| `HEROKU_DEPLOYMENT.md` | Complete Heroku guide |
| `Procfile` | Tells Heroku how to run app |
| `requirements.txt` | Python dependencies |
| `runtime.txt` | Python version |

---

## Environment Variables Checklist

For local development:
```
FIREBASE_SERVICE_ACCOUNT=/full/path/to/service-account-key.json
ANTHROPIC_API_KEY=sk-ant-xxxxx (optional)
SMTP_USER=your-email@gmail.com (optional)
SMTP_PASSWORD=app-password (optional)
```

For Heroku:
```bash
heroku config:set FIREBASE_SERVICE_ACCOUNT_JSON='...'
heroku config:set ANTHROPIC_API_KEY='sk-ant-xxxxx'
heroku config:set SMTP_USER='your-email@gmail.com'
heroku config:set SMTP_PASSWORD='app-password'
```

---

## Admin Access

**URL**: `https://your-app-name.herokuapp.com/admin`

**Default Credentials**:
- Username: `admin`
- Password: `mudit@123`

⚠️ **Change password in app.py before production!**

---

## Customer Access

- **Submit Claim**: `/submit`
- **Track Status**: `/track`
- **Feedback**: `/feedback/<claim_id>`
- **Kiosk**: `/kiosk`

---

## Emergency Fixes

### Firebase Not Working?
```bash
# Check if configured
heroku config | grep FIREBASE

# View logs
heroku logs --tail

# Restart app
heroku restart
```

### Clear Environment Variables
```bash
heroku config:unset FIREBASE_SERVICE_ACCOUNT_JSON
```

### SSH into Heroku
```bash
heroku ps:exec
ls -la
cat warranty.db  # View local database
```

---

## Key Files for Firebase Integration

1. **`modules/firebase_db.py`** - Firebase connection & sync functions
   - `is_firebase_enabled()` - Check if Firebase configured
   - `create_remote_claim()` - Sync new claim to Firebase
   - `update_remote_claim_status()` - Sync status changes
   - `append_remote_image()` - Sync uploaded images
   - `append_remote_payment()` - Sync payments

2. **`app.py`** - Main Flask app
   - Automatically syncs data to Firebase when enabled
   - No code changes needed, works out of the box

3. **`config.txt`** - Configuration reference
   - Firebase setup instructions

---

## Success Indicators

✅ Local test:
```
[Firebase] Firestore initialized.
```

✅ Heroku logs:
```
2026-05-09 10:00:00.000000+00:00 app[web.1]: [Firebase] Firestore initialized.
```

✅ Data synced:
- New claims appear in Firestore within seconds
- Firestore Console shows data collections

---

## Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| `FIREBASE_SERVICE_ACCOUNT not configured` | Set env var with full path to JSON |
| `Permission denied` | Check Firebase security rules |
| `Invalid JSON` | Validate JSON with jsonlint.com |
| `Connection refused` | Check internet connection, Firebase enabled |
| `Data not syncing` | Check `is_firebase_enabled()` returns True |

---

## Testing Commands

```bash
# Test Firebase connection
heroku run "python -c \"from modules.firebase_db import is_firebase_enabled; print(is_firebase_enabled())\""

# View all config
heroku config

# Check database
heroku run "sqlite3 warranty.db 'SELECT COUNT(*) FROM service_claims;'"

# Watch logs
heroku logs --tail -f
```

---

## Rollback Changes

```bash
# If deployment fails
git revert HEAD
git push heroku main

# Or restore previous version
heroku releases
heroku rollback v5  # Use previous version number
```

---

## Performance Tips

- Use `heroku-postgresql` for better performance than SQLite
- Firebase reads/writes happen asynchronously (won't slow down your app)
- Monitor Firestore usage to avoid exceeding free tier

---

## Cost Summary (Free Tier)

- **Heroku**: Free dyno (sleeps after 30 mins)
- **Firebase**: 50K reads, 20K writes, 20K deletes per day
- **Total Cost**: $0/month unless you upgrade

---

**Version**: 2.0  
**Last Updated**: May 2026  
**Status**: Production Ready ✅
