# Heroku Deployment Guide - MUDIT COMPUTERS Warranty System v2

## Prerequisites
- Heroku account (free account works)
- Heroku CLI installed (`npm install -g heroku`)
- Git installed
- Firebase project created (optional but recommended)

---

## Step 1: Prepare Heroku App

### 1.1 Install Heroku CLI
```bash
npm install -g heroku
heroku login
```

### 1.2 Create Heroku App
```bash
# Navigate to your project directory
cd warranty_v2

# Create new app on Heroku
heroku create your-app-name

# Or if you already have an app
heroku git:remote -a your-app-name
```

---

## Step 2: Configure Environment Variables on Heroku

### 2.1 Set Basic Configuration
```bash
# Flask configuration
heroku config:set FLASK_ENV=production
heroku config:set FLASK_DEBUG=False

# Shop details
heroku config:set SHOP_NAME="MUDIT COMPUTERS"
heroku config:set SHOP_PHONE="+91-XXXXXXXXXX"
```

### 2.2 Set Firebase Configuration (IMPORTANT!)

**Option A: Firebase Service Account JSON (Recommended)**

1. Go to: https://console.firebase.google.com/
2. Select your project → Project Settings → Service Accounts
3. Click "Generate New Private Key"
4. A JSON file will download - open it and copy its content

Then run:
```bash
# Paste the entire JSON content (one line, no line breaks)
heroku config:set FIREBASE_SERVICE_ACCOUNT_JSON='{"type":"service_account","project_id":"xxx",...}'
```

**Option B: Upload JSON file to Heroku**
```bash
# Create a directory for secrets
mkdir -p config

# Copy your service account JSON file
cp /path/to/serviceAccountKey.json config/service-account-key.json

# Add to Heroku (using buildpack)
heroku buildpacks:add heroku/python
# Then manually copy file during deployment using git
```

### 2.3 Set API Keys (Optional but Recommended)

**Anthropic API (for AI features):**
```bash
heroku config:set ANTHROPIC_API_KEY='sk-ant-xxxxx'
```

**Gmail SMTP (for notifications):**
```bash
heroku config:set SMTP_USER='your-email@gmail.com'
heroku config:set SMTP_PASSWORD='your-16-char-app-password'
```

### 2.4 Verify Configuration
```bash
heroku config
# Should show all your environment variables
```

---

## Step 3: Database Setup

The app uses SQLite by default (stored in the dyno). To persist data across dyno restarts:

### Option A: Use Heroku Postgres (Recommended for Production)

```bash
# Add PostgreSQL add-on (free tier available)
heroku addons:create heroku-postgresql:hobby-dev

# Modify app.py to use PostgreSQL (optional)
# Current SQLite implementation works fine for hobby tier
```

### Option B: Keep SQLite (Warning: Data lost on dyno restart)

Current setup uses SQLite which is fine for testing. In production, use PostgreSQL.

---

## Step 4: Deploy to Heroku

### 4.1 Ensure Procfile is Correct
```bash
# View current Procfile
cat Procfile

# Should contain:
# web: gunicorn app:app --bind 0.0.0.0:$PORT
```

### 4.2 Deploy via Git

```bash
# Add all files
git add .

# Commit
git commit -m "Deploy to Heroku"

# Push to Heroku
git push heroku main
# (or 'master' if your default branch is master)
```

### 4.3 View Deployment Logs
```bash
heroku logs --tail
```

---

## Step 5: Access Your App

### Get Your Heroku App URL
```bash
heroku open
```

### App Routes
- **Customer Form**: `https://your-app-name.herokuapp.com/submit`
- **Shop Kiosk**: `https://your-app-name.herokuapp.com/kiosk`
- **Admin Panel**: `https://your-app-name.herokuapp.com/admin`
- **Reminders**: `https://your-app-name.herokuapp.com/admin/reminders`

### Default Admin Credentials
- **Username**: `admin`
- **Password**: `mudit@123`
- ⚠️ **CHANGE IN PRODUCTION!** Edit ADMIN_USER and ADMIN_PASS in app.py before first deployment

---

## Step 6: Troubleshooting

### Check Logs
```bash
heroku logs --tail
```

### Common Issues

**1. Firebase Not Connecting**
```bash
# Verify Firebase config is set
heroku config | grep FIREBASE

# If empty, re-run:
heroku config:set FIREBASE_SERVICE_ACCOUNT_JSON='{"type":"service_account"...}'
```

**2. Database Issues**
```bash
# SSH into the dyno
heroku ps:exec

# Check database
ls -la warranty.db
```

**3. Port Issues**
The Procfile automatically binds to the Heroku PORT. If you get port errors:
```bash
# Verify PORT is available
heroku config | grep PORT
```

### Restart Dyno
```bash
heroku restart
```

---

## Step 7: Additional Configuration

### Enable WhatsApp Notifications (Optional)
1. Set up Twilio or your WhatsApp provider
2. Update `modules/notifications.py` with API credentials
3. Deploy changes to Heroku

### SSL/HTTPS (Automatic on Heroku)
- Heroku provides free SSL for all apps
- Your app is automatically HTTPS at `https://your-app-name.herokuapp.com`

### Custom Domain (Optional)
```bash
# Point your domain to Heroku
heroku domains:add www.yourdomain.com

# Update your domain DNS records with Heroku's DNS
```

---

## Step 8: Regular Maintenance

### View Dyno Status
```bash
heroku ps
```

### Download Database Backup
```bash
# Download SQLite database from Heroku
heroku run "sqlite3 warranty.db '.dump'" > backup.sql
```

### Scale Dynos (If Needed)
```bash
# Default: 1 free dyno (sleeps after 30 mins of inactivity)
# Upgrade to paid for 24/7 operation
heroku ps:scale web=1
```

---

## Deployment Checklist

- [ ] Heroku account created
- [ ] Heroku app created (`heroku create app-name`)
- [ ] Environment variables configured:
  - [ ] FIREBASE_SERVICE_ACCOUNT_JSON or FIREBASE_SERVICE_ACCOUNT
  - [ ] ANTHROPIC_API_KEY (optional)
  - [ ] SMTP_USER and SMTP_PASSWORD (optional)
  - [ ] SHOP_NAME and SHOP_PHONE
- [ ] Git repository initialized
- [ ] Procfile exists and is correct
- [ ] requirements.txt has all dependencies
- [ ] runtime.txt has correct Python version
- [ ] Code pushed to Heroku: `git push heroku main`
- [ ] App is running: `heroku ps`
- [ ] Admin password changed from default
- [ ] Tested all features (submit claim, track, admin panel, etc.)

---

## Firebase Firestore Setup (Optional)

To use Firebase for cloud backup:

1. Create Firestore database in Firebase Console
2. Set security rules to require authentication
3. Service account will automatically sync data

**Security Rules Example:**
```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Only allow service accounts to write
    match /service_claims/{document=**} {
      allow read, write: if request.auth != null;
    }
  }
}
```

---

## Performance Tips

- Use `heroku-postgresql` for better performance than SQLite
- Enable CDN for static files (CSS, JS)
- Consider upgrading from free dyno for 24/7 uptime
- Monitor dyno resource usage: `heroku ps:exec`

---

## Support & Issues

For issues:
1. Check logs: `heroku logs --tail`
2. SSH into dyno: `heroku ps:exec`
3. Verify all env vars: `heroku config`
4. Review Heroku documentation: https://devcenter.heroku.com/

---

**Last Updated**: May 2026
**Version**: v2.0
**Status**: Production Ready ✅
