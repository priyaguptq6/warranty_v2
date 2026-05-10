# Firebase Integration Setup Guide

## Overview

This guide explains how to set up Firebase Firestore as a remote backup for your warranty system database. Firebase automatically syncs all service claims, payments, images, and dealer assignments to the cloud.

---

## Part 1: Create Firebase Project

### Step 1: Create Firebase Project

1. Go to: https://console.firebase.google.com/
2. Click **"Add project"**
3. Enter project name: `mudit-warranty-system`
4. Click **"Continue"**
5. Disable Google Analytics (optional)
6. Click **"Create project"** and wait for setup

### Step 2: Enable Firestore Database

1. In Firebase Console, click **"Firestore Database"** (left sidebar)
2. Click **"Create database"**
3. Select **"Production mode"** (for security)
4. Choose region: **`asia-south1`** (for India - faster response)
5. Click **"Create"**

### Step 3: Create Service Account

1. Go to **"Project Settings"** (gear icon, top right)
2. Click **"Service Accounts"** tab
3. Select **"Python"** in "Admin SDK code snippet" dropdown
4. Click **"Generate New Private Key"**
5. A JSON file will download - **keep this safe!**

**Example service account JSON:**
```json
{
  "type": "service_account",
  "project_id": "mudit-warranty-system",
  "private_key_id": "xxxxxxxx",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIE...\n-----END PRIVATE KEY-----\n",
  "client_email": "firebase-adminsdk-xxxxx@mudit-warranty-system.iam.gserviceaccount.com",
  "client_id": "123456789",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/..."
}
```

---

## Part 2: Local Development Setup

### Step 1: Save Service Account JSON

1. Rename the downloaded JSON file to: `service-account-key.json`
2. Place it in your project root directory:
   ```
   warranty_v2/
   ├── app.py
   ├── service-account-key.json  ← Place here
   ├── config.txt
   └── ...
   ```

### Step 2: Set Environment Variable

#### On Windows (PowerShell):
```powershell
$env:FIREBASE_SERVICE_ACCOUNT = "C:\path\to\warranty_v2\service-account-key.json"
```

#### On Mac/Linux:
```bash
export FIREBASE_SERVICE_ACCOUNT="/path/to/warranty_v2/service-account-key.json"
```

#### Or create `.env` file (Recommended):
```
FIREBASE_SERVICE_ACCOUNT=/full/path/to/service-account-key.json
```

Then run:
```bash
pip install python-dotenv
```

And in `app.py` (already done), it will auto-load from `.env`

### Step 3: Test Firebase Connection

Run the app locally:
```bash
python app.py
```

Check console for:
```
[Firebase] Firestore initialized.
```

If you see this, Firebase is connected! ✅

---

## Part 3: Heroku Deployment Setup

### Step 1: Prepare Service Account JSON

You have 2 options:

**Option A: Base64 Encode (Easiest for Heroku)**

On Mac/Linux:
```bash
cat service-account-key.json | base64
```

On Windows PowerShell:
```powershell
[Convert]::ToBase64String([System.IO.File]::ReadAllBytes("service-account-key.json")) | Set-Clipboard
```

**Option B: Direct JSON (Also works)**

Keep the JSON as-is, but ensure no line breaks when setting env var.

### Step 2: Set Environment Variable on Heroku

**Using Option B (Recommended):**

```bash
# Read the JSON file and set as env var (all in one line)
heroku config:set FIREBASE_SERVICE_ACCOUNT_JSON='{"type":"service_account","project_id":"..."}'
```

**Using Option A (Base64):**

Update `modules/firebase_db.py` to decode:
```python
import base64

def _load_service_account():
    if FIREBASE_SERVICE_ACCOUNT and os.path.exists(FIREBASE_SERVICE_ACCOUNT):
        return FIREBASE_SERVICE_ACCOUNT
    
    # Try base64 encoded JSON
    firebase_b64 = os.environ.get("FIREBASE_SERVICE_ACCOUNT_BASE64")
    if firebase_b64:
        try:
            data_str = base64.b64decode(firebase_b64).decode('utf-8')
            data = json.loads(data_str)
            tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
            json.dump(data, tmp)
            tmp.close()
            return tmp.name
        except Exception as exc:
            print(f"[Firebase] Invalid base64 JSON: {exc}")
    
    if FIREBASE_SERVICE_ACCOUNT_JSON:
        # ... existing code ...
```

### Step 3: Verify on Heroku

```bash
# Check if Firebase is configured
heroku config | grep FIREBASE

# View logs to confirm connection
heroku logs --tail | grep Firebase
```

Should see:
```
[Firebase] Firestore initialized.
```

---

## Part 4: Firestore Security Rules

### Set Up Security Rules

1. In Firebase Console, click **"Firestore Database"**
2. Go to **"Rules"** tab
3. Replace default rules with:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Only allow service account (backend) to read/write
    // No direct client access
    match /service_claims/{document=**} {
      allow read, write: if request.auth != null;
    }
    match /customers/{document=**} {
      allow read, write: if request.auth != null;
    }
    match /dealers/{document=**} {
      allow read, write: if request.auth != null;
    }
  }
}
```

4. Click **"Publish"**

### Why These Rules?

- ✅ Service account can read/write (for your app)
- ❌ Clients cannot directly access (secure)
- ✅ No need for Firebase authentication in your app

---

## Part 5: Data Sync Overview

### What Gets Synced to Firebase?

1. **Service Claims** - All warranty claim data
2. **Claim History** - Status updates and timeline
3. **Images** - File paths only (not actual files)
4. **Payments** - Payment records
5. **Dealer Assignments** - Repair tracking

### Collection Structure in Firestore

```
service_claims/
├── {claim_id_1}
│   ├── customer: {name, phone, email, address}
│   ├── product: {brand, model, serial, warranty_status}
│   ├── claim: {issue, status, estimate_cost, final_cost, ...}
│   ├── history: [{old_status, new_status, changed_at, ...}, ...]
│   ├── images: [{filename, image_type, ai_extracted, ...}, ...]
│   ├── payments: [{amount, mode, type, paid_at, ...}, ...]
│   └── dealer_assignments: [{dealer_id, sent_date, status, ...}, ...]
├── {claim_id_2}
│   └── ...
```

### Real-Time Sync Timing

- ✅ Syncs automatically after each action
- ✅ No manual backup needed
- ✅ Firebase keeps 30-day history
- ✅ Can download data anytime from Firebase Console

---

## Part 6: Backup & Recovery

### Backup from Firestore

1. In Firebase Console, go **"Firestore Database"**
2. Click menu (⋮) → **"Export"**
3. Choose Cloud Storage location (or create new bucket)
4. Download exported JSON files

### Download Local Database

```bash
# Get SQLite backup
heroku run "sqlite3 warranty.db '.dump'" > backup.sql
```

### Restore from Firebase

Currently, Firebase is read-only backup. To restore:
1. Export data from Firestore
2. Import manually into SQLite

---

## Troubleshooting

### Firebase Not Connecting

**Error:** `[Firebase] FIREBASE_SERVICE_ACCOUNT not configured`

**Solution:**
```bash
# Check env var is set
printenv FIREBASE_SERVICE_ACCOUNT

# If not set, run:
export FIREBASE_SERVICE_ACCOUNT="/path/to/service-account-key.json"
```

### Invalid Service Account JSON

**Error:** `Invalid FIREBASE_SERVICE_ACCOUNT_JSON`

**Solution:**
- Ensure JSON is valid (use https://jsonlint.com/)
- No line breaks in single-line env var
- Escape quotes if necessary: `\"` → `\"`

### Firestore Permission Denied

**Error:** `PERMISSION_DENIED: 6 Permission denied`

**Solution:**
1. Check security rules are published
2. Verify service account has Firestore permissions
3. Check project_id matches in JSON

### High Firestore Costs

**Note:** Free tier includes 50K reads, 20K writes, 20K deletes per day

**To reduce costs:**
- Disable Firebase (comment out in app.py)
- Use only for backups, not real-time sync
- Set up data retention policies

---

## Monitoring Firestore

### View Usage in Firebase Console

1. Go to **"Firestore Database"**
2. Click **"Usage"** tab
3. See real-time read/write metrics

### Common Queries

**View all service claims:**
```
Collection: service_claims
```

**View specific claim:**
```
Collection: service_claims
Filter: document ID = {claim_id}
```

**Export to CSV:**
```bash
# Firebase Console → Firestore Database → Export
# Choose format: JSON or CSV
```

---

## Best Practices

✅ **Do:**
- Keep service account JSON secret (add to `.gitignore`)
- Use strong Firebase security rules
- Monitor costs on free tier
- Regular backups to Cloud Storage
- Enable Firestore audit logging

❌ **Don't:**
- Commit service account key to GitHub
- Use default security rules in production
- Sync sensitive data without encryption
- Rely only on Firebase (keep local DB as primary)

---

## Next Steps

1. ✅ Create Firebase project
2. ✅ Set up service account
3. ✅ Configure local development
4. ✅ Test on local machine
5. ✅ Deploy to Heroku with env vars
6. ✅ Monitor Firestore usage
7. ✅ Set up regular backups

---

## Support & Resources

- Firebase Docs: https://firebase.google.com/docs/firestore
- Service Account Setup: https://firebase.google.com/docs/admin/setup
- Firestore Security: https://firebase.google.com/docs/firestore/security/start
- Pricing: https://firebase.google.com/pricing

---

**Status**: ✅ Firebase Integration Complete  
**Last Updated**: May 2026  
**Version**: v2.0
