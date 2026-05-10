# MUDIT COMPUTERS Warranty PWA

## Zero Server Firebase PWA

This is the Progressive Web App version of the warranty system that runs entirely on Firebase - no Python server needed!

## Features
- ✅ Firebase Firestore (cloud data with offline sync)
- ✅ Firebase Auth (secure admin login)
- ✅ Firebase Storage (photos)
- ✅ PWA (installable app)
- ✅ WhatsApp API (automatic messages via Cloud Functions)

## Setup Steps

### 1. Firebase Project Setup
1. Go to https://console.firebase.google.com/
2. Create new project "mudit-computers-warranty"
3. Enable Firestore Database
4. Enable Authentication (Email/Password)
5. Enable Storage
6. Enable Hosting

### 2. Update Firebase Config
Edit `pwa/index.html` and replace the firebaseConfig with your project's config from Firebase Console > Project Settings > General > Your apps > Web app.

### 3. Deploy to Firebase
```bash
npm install -g firebase-tools
firebase login
firebase init hosting  # Select existing project
firebase deploy
```

### 4. Create Admin User
In Firebase Console > Authentication > Users, add admin@muditcomputers.com with a password.

### 5. WhatsApp Setup (Optional)
- Get Twilio account
- Set up WhatsApp Business API
- Create Cloud Function to send messages

## Development
- Open `pwa/index.html` in browser for testing
- Use Firebase Emulator for local development: `firebase emulators:start`

## Migration from Flask
The PWA version replaces the Flask server. All data operations now happen client-side with Firebase.

Next steps: Add more features like claim submission, tracking, etc.