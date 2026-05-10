# 🖥️ MUDIT COMPUTERS — Professional Warranty System v2
## Production-Ready with Firebase & Heroku Integration ✅
```
warranty_system/
├── app.py                    ← Main file — YAHI RUN KARNA HAI
├── requirements.txt
├── config.txt                ← API Key & Gmail config yahan daalen
├── generate_qr.py            ← QR code generator
├── warranty.db               ← SQLite database (auto-banta hai)
├── modules/
│   ├── database.py           ← All DB tables & queries
│   ├── ai_helper.py          ← Claude AI integration
│   └── notifications.py      ← WhatsApp + Email
├── templates/                ← 16 HTML pages
│   ├── index.html            ← Landing page
│   ├── customer_form.html    ← AI-powered self-service form
│   ├── submitted.html        ← Confirmation
│   ├── track.html            ← Customer tracking
│   ├── track_timeline.html   ← Full status history
│   ├── kiosk.html            ← Touch-screen shop kiosk ⭐
│   ├── feedback.html         ← Customer rating
│   ├── feedback_thanks.html
│   ├── admin_login.html
│   ├── admin_dashboard.html  ← Main admin panel
│   ├── admin_claim_detail.html ← Full claim management ⭐
│   ├── dealers.html          ← Dealer list ⭐
│   ├── dealer_form.html      ← Add/edit dealer
│   ├── dealer_detail.html    ← Dealer report ⭐
│   └── technicians.html      ← Staff management
└── static/
    └── uploads/              ← Device photos (auto-created)
```

---

## ⚡ Setup — 5 Steps

### 1. Python Install karein
https://python.org/downloads → Install karte waqt **"Add to PATH"** tick zaroor karein

### 2. Folder mein jaayein
```
cmd kholen → cd C:\Users\YourName\Downloads\warranty_system
```

### 3. Dependencies install karein
```
pip install -r requirements.txt
```

### 4. Config fill karein (optional but recommended)
`config.txt` file kholen aur fill karein:
- `ANTHROPIC_API_KEY` — AI features ke liye (console.anthropic.com)
- `SMTP_USER` + `SMTP_PASSWORD` — Email notifications ke liye

### 5. Firebase + Railway setup (best)
अगर आप चाहते हैं कि कोई भी कहीं से भी app चलाए और data cloud में रहे, तो यह सबसे अच्छा तरीका है.

- `requirements.txt` में `firebase-admin` और `gunicorn` पहले से शामिल हैं
- Firebase Console में Firestore बनाएं
- Firebase Service Account JSON डाउनलोड करें
- Railway पर नया project बनाएं और GitHub repo connect करें
- Railway की Environment Variables में ये डालें:
  - `FIREBASE_SERVICE_ACCOUNT_JSON` → service account JSON पूरा text
  - या `FIREBASE_SERVICE_ACCOUNT` → यदि आप JSON फ़ाइल path देते हैं
  - `ANTHROPIC_API_KEY` → AI फोटो analysis के लिए
  - `HOST` → `0.0.0.0`
  - `PORT` → Railway खुद सेट करता है

Railway पर deploy करने के लिए यह `Procfile` use होगा:
```
web: gunicorn app:app --bind 0.0.0.0:$PORT
```

> ध्यान: Firebase configured होने पर app SQLite के साथ-साथ Firestore में data भी sync करेगी।

### 6. Run karein locally
```
python app.py
```

> यह app अब PWA compatible है। browser में URL खोलिये, फिर “Install App” या “Add to Home screen” चुन सकते हैं.

---

## 🌐 URLs

| Kaun | URL |
|------|-----|
| 🙋 Customer Form | `http://YOUR-IP:5000/submit` |
| 📍 Claim Tracker | `http://YOUR-IP:5000/track` |
| 🖥️ Shop Kiosk | `http://YOUR-IP:5000/kiosk` |
| 👨‍💼 Admin Panel | `http://YOUR-IP:5000/admin` |

**Admin Login:** `admin` / `mudit@123`

---

## ✨ Features

| Feature | Details |
|---------|---------|
| 🤖 AI Auto-Fill | Device photo → Brand/Model/Serial auto-detect |
| 📸 Intake Photos | Condition record with AI damage analysis |
| 🚀 Delivery Photos | Proof upload on handover |
| 🏪 Dealer Management | Add dealers, assign claims, track returns |
| 📊 Dealer Reports | Kis dealer ke paas kitne items, cost tracking |
| 💰 Payment Tracking | Advance, final, balance due |
| 👨‍🔧 Technician Assignment | Per-claim technician assign |
| 📱 WhatsApp Notifications | Auto-send on status change |
| ✉️ Email Notifications | HTML email with claim details |
| 🖥️ Shop Kiosk | Touch-screen status check |
| ⭐ Customer Feedback | Post-delivery rating system |
| 📋 Full Audit Trail | Every status change logged |

---

## 🗄️ Database Tables (9 Tables)

```
customers         → Name, phone, email, address
products          → Brand, model, serial, warranty dates
service_claims    → Status, issues, costs, timestamps
dealers           → Name, address, specialization, GST
dealer_assignments→ Which item sent to which dealer, when
claim_images      → Intake/delivery/damage photos + AI data
payments          → Cash/UPI/Card records
technicians       → Staff members
status_history    → Complete audit trail
```

---

## 💡 Tips

- **CMD window band mat karna** — app tab tak chale jab tak band na karo
- **Same WiFi** — agar app locally chal raha ho to browser ko same network par hona chahiye
- **Daily backup** — `warranty.db` file copy karein Google Drive par
- **Static IP** — Router mein shop PC ka IP fix karein taaki URL same rahe

## 🌍 Remote / Anywhere access

यह ऐप अभी `warranty.db` और `static/uploads/` को आपके लोकल कंप्यूटर पर ही सेव करता है।

- डेटा फ़ाइल: `c:\Users\DELL\Downloads\warranty_v2\warranty.db`
- फोटो/इमेजेस: `c:\Users\DELL\Downloads\warranty_v2\static\uploads\`

अगर आप चाहते हैं कि कोई भी कहीं से भी लिंक डालकर खुल सके, तो यह लोकल मशीन पर्याप्त नहीं है। इसके लिए आपको ऐप को क्लाउड या पब्लिक सर्वर पर होस्ट करना होगा:

1. **Railway** या **Render** पर deploy करें (Python Flask app की तरह)
2. या अपने router में पोर्ट फारवर्डिंग और पब्लिक IP/डायनेमिक DNS सेट करें
3. फिर browser में होस्टेड URL डालें, जैसे `https://yourappname.onrender.com`

> ध्यान दें: अभी आपके डेटा का बचाव `warranty.db` पर हो रहा है। क्लाउड पर deploy करने पर यह होस्ट सर्वर पर `warranty.db` में चलेगा, या बेहतर होगा कि बाद में Firestore/Cloud DB में migrate करें।

---

## 🔧 Customization

- Admin password: `app.py` mein `ADMIN_PASS = "mudit@123"` change karein
- Shop name/address: `modules/notifications.py` mein update karein
- Brands list: `customer_form.html` mein `<select name="brand">` mein add karein

---
Made with ❤️ for MUDIT COMPUTERS, Shahjahanpur
