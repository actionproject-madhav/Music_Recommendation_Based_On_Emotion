# Music Recommendation App Setup Guide

## Fixing the Issues

### 1. Emotion Detection Models Issue
The error "Failed to load emotion detection models" has been fixed by:
- Using a specific version of face-api.js (1.7.12) instead of 'latest'
- Adding better error handling and logging
- Using a more reliable CDN

### 2. Spotify INVALID_CLIENT Issue
The "INVALID_CLIENT: Invalid redirect URI" error occurs because:

**You need to configure your Spotify App properly:**

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create a new app or select your existing app
3. Click "Edit Settings"
4. In "Redirect URIs", add: `http://localhost:3000/callback`
5. Save the changes

**Set up environment variables:**

Create a `.env` file in the `backend/` directory with:
```
SPOTIFY_CLIENT_ID=your_actual_client_id_here
SPOTIFY_CLIENT_SECRET=your_actual_client_secret_here
REDIRECT_URI=http://localhost:3000/callback
```

## Running the App

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
python app.py
```

### Frontend Setup
```bash
cd frontend
npm install
npm start
```

## How It Works

1. **Emotion Detection**: Uses your webcam and face-api.js to detect emotions
2. **Spotify Integration**: Connects to your Spotify account to get music recommendations
3. **Music Matching**: Maps detected emotions to music characteristics and finds matching songs

## Troubleshooting

- **Models not loading**: Refresh the page, check browser console for errors
- **Spotify connection issues**: Verify your client ID and redirect URI in Spotify Dashboard
- **Camera issues**: Ensure camera permissions are granted in your browser

