# Troubleshooting Guide

## Issue 1: "Failed to load emotion detection models"

### What's Happening
The face-api.js models are failing to load from CDN sources.

### Solutions (in order of preference)

#### Solution A: Use Manual Emotion Selection (Recommended)
The app now has manual emotion selection buttons. If models fail to load:
1. Look for the emotion buttons below the camera
2. Click on any emotion (happy, sad, angry, etc.)
3. The app will still work and recommend music based on your selection

#### Solution B: Refresh and Retry
1. Refresh the page (F5 or Cmd+R)
2. Wait for models to load (check browser console for progress)
3. If still failing, try Solution A

#### Solution C: Check Browser Console
1. Open Developer Tools (F12)
2. Go to Console tab
3. Look for error messages about model loading
4. Share these errors if you need help

## Issue 2: "INVALID_CLIENT: Invalid redirect URI"

### What's Happening
Your Spotify app is not properly configured with the correct redirect URI.

### Solution: Configure Spotify App (REQUIRED)

#### Step 1: Go to Spotify Developer Dashboard
1. Visit: https://developer.spotify.com/dashboard
2. Sign in with your Spotify account

#### Step 2: Create/Select Your App
1. Click "Create an App" or select your existing app
2. Give it a name (e.g., "Music Recommendation App")
3. Add a description (optional)
4. Click "Create"

#### Step 3: Configure Redirect URIs
1. Click on your app name
2. Click "Edit Settings"
3. In the "Redirect URIs" section, add: `http://localhost:3000/callback`
4. **IMPORTANT**: Make sure there are no extra spaces or characters
5. Click "Save"

#### Step 4: Copy Credentials
1. Copy your "Client ID"
2. Copy your "Client Secret"
3. These should match what's in your `.env` file

### Verify Your Setup

#### Check .env File
Your `backend/.env` file should contain:
```
SPOTIFY_CLIENT_ID=your_actual_client_id
SPOTIFY_CLIENT_SECRET=your_actual_client_secret
REDIRECT_URI=http://localhost:3000/callback
```

#### Check Browser Console
1. Open Developer Tools (F12)
2. Go to Console tab
3. Try to connect with Spotify
4. Look for the logged information:
   - Client ID
   - Redirect URI
   - Auth URL

## Testing the Fix

### 1. Start Backend
```bash
cd backend
python app.py
```

### 2. Start Frontend (new terminal)
```bash
cd frontend
npm start
```

### 3. Test Spotify Connection
1. Open http://localhost:3000
2. Click "Connect with Spotify"
3. Check browser console for debug info
4. If successful, you'll be redirected back to the app

### 4. Test Emotion Detection
1. If models load: Use camera for automatic detection
2. If models fail: Use manual emotion buttons

## Common Mistakes

1. **Wrong Redirect URI**: Must be exactly `http://localhost:3000/callback`
2. **Missing .env file**: Backend needs environment variables
3. **Wrong port**: Make sure frontend runs on port 3000
4. **Browser cache**: Clear cache if changes don't appear

## Still Having Issues?

1. Check browser console for specific error messages
2. Verify Spotify app settings match exactly
3. Ensure both backend and frontend are running
4. Try different browser or incognito mode
