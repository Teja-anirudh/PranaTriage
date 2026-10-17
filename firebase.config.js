// firebase-config.js

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

if (typeof window !== 'undefined') {
  window.firebaseConfig = firebaseConfig;
}

if (typeof firebase !== 'undefined') {
  if (!firebase.apps || firebase.apps.length === 0) {
    firebase.initializeApp(firebaseConfig);
  }

  const db = firebase.firestore();
  if (typeof window !== 'undefined') {
    window.db = db;
  }
}

if (typeof module !== 'undefined') {
  module.exports = { firebaseConfig };
}