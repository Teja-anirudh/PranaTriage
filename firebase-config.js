// firebase-config.js
// --- PASTE YOUR FIREBASE CREDENTIALS HERE ---
const firebaseConfig = {
     apiKey: 'AIzaSyDlGelOJE4rwFElr6rGUfhLzwJiE2r4sFs',
  authDomain: 'triage-5a021.firebaseapp.com',
  databaseURL: 'https://triage-5a021-default-rtdb.firebaseio.com',
  projectId: 'triage-5a021',
  storageBucket: 'triage-5a021.firebasestorage.app',
  messagingSenderId: '399820391961',
  appId: '1:399820391961:web:c2ec59abcfd78b25b74c88',
  measurementId: 'G-TX98FWL98N'
};

// Initialize Firebase
firebase.initializeApp(firebaseConfig);
const db = firebase.firestore();

// Export for global access
window.db = db;
