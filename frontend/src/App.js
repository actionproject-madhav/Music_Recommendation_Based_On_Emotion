import React, { useState, useEffect, useRef, useCallback } from 'react';
import * as tf from '@tensorflow/tfjs';
import Webcam from 'react-webcam';
import './App.css';

// This will be fetched from backend
const REDIRECT_URI = 'http://127.0.0.1:3000/callback';
const SCOPES = 'user-read-private user-read-email user-modify-playback-state user-read-playback-state user-top-read streaming';
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

const EmotionMusicApp = () => {
  const [clientId, setClientId] = useState('');
  const [accessToken, setAccessToken] = useState(null);
  const [currentEmotion, setCurrentEmotion] = useState('neutral');
  const [previousEmotion, setPreviousEmotion] = useState('neutral');
  const [emotionConfidence, setEmotionConfidence] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTracks, setCurrentTracks] = useState([]);
  const [currentTrackIndex, setCurrentTrackIndex] = useState(0);
  const [isDetecting, setIsDetecting] = useState(false);
  const [model, setModel] = useState(null);
  const [userProfile, setUserProfile] = useState(null);
  const [devices, setDevices] = useState([]);
  const [selectedDevice, setSelectedDevice] = useState(null);
  const [autoPlay, setAutoPlay] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [emotionHistory, setEmotionHistory] = useState([]);
  const [cameraPermission, setCameraPermission] = useState(null);
  
  const webcamRef = useRef(null);
  const detectionIntervalRef = useRef(null);
  const canvasRef = useRef(null);
  const exchangeCodeForToken = async (code) => {
    try {
      setLoading(true);
      const response = await fetch(`${API_URL}/api/spotify/exchange-token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code })
      });
      
      if (response.ok) {
        const data = await response.json();
        setAccessToken(data.access_token);
        localStorage.setItem('spotify_token', data.access_token);
        fetchUserProfile(data.access_token);
        fetchDevices(data.access_token);
      } else {
        setError('Failed to exchange authorization code for token');
      }
    } catch (error) {
      console.error('Error exchanging code:', error);
      setError('Failed to authenticate with Spotify');
    } finally {
      setLoading(false);
    }
  };
  // Fetch client ID from backend
  useEffect(() => {
    fetch(`${API_URL}/api/spotify/client-id`)
      .then(res => res.json())
      .then(data => setClientId(data.client_id))
      .catch(err => console.error('Error fetching client ID:', err));
  }, []);

  // Load face-api.js models for emotion detection
  useEffect(() => {
    const loadModels = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Load the emotion detection model
        // Using face-api.js with emotion recognition
        const MODEL_URL = 'https://cdn.jsdelivr.net/npm/@vladmandic/face-api@1.7.12/model';
        
        await tf.ready();
        
        // Dynamically import face-api
        const faceapi = await import('@vladmandic/face-api');
        
        // Load models with better error handling
        const modelPromises = [
          faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL),
          faceapi.nets.faceLandmark68Net.loadFromUri(MODEL_URL),
          faceapi.nets.faceRecognitionNet.loadFromUri(MODEL_URL),
          faceapi.nets.faceExpressionNet.loadFromUri(MODEL_URL)
        ];
        
        await Promise.all(modelPromises);
        
        setModel(faceapi);
        setLoading(false);
        console.log('Emotion detection models loaded successfully');
      } catch (error) {
        console.error('Error loading models:', error);
        setError('Failed to load emotion detection models. Please refresh the page and try again.');
        setLoading(false);
      }
    };
    
    loadModels();
  }, []);

 // Handle Spotify authentication
useEffect(() => {
  const urlParams = new URLSearchParams(window.location.search);
  const code = urlParams.get('code');
  const error = urlParams.get('error');
  
  if (error) {
    setError(`Spotify authentication error: ${error}`);
    return;
  }
  
  if (code) {
    // Exchange code for access token via backend
    exchangeCodeForToken(code);
    // Clean up URL
    window.history.replaceState({}, document.title, window.location.pathname);
  } else {
    // Check for stored token
    const storedToken = localStorage.getItem('spotify_token');
    if (storedToken) {
      setAccessToken(storedToken);
      fetchUserProfile(storedToken);
      fetchDevices(storedToken);
    }
  }
}, []);

  const fetchUserProfile = async (token) => {
    try {
      const response = await fetch('https://api.spotify.com/v1/me', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setUserProfile(data);
      } else if (response.status === 401) {
        // Token expired
        localStorage.removeItem('spotify_token');
        setAccessToken(null);
      }
    } catch (error) {
      console.error('Error fetching user profile:', error);
    }
  };

  const fetchDevices = async (token) => {
    try {
      const response = await fetch(`${API_URL}/api/spotify/devices`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setDevices(data.devices || []);
        if (data.devices && data.devices.length > 0) {
          setSelectedDevice(data.devices[0].id);
        }
      }
    } catch (error) {
      console.error('Error fetching devices:', error);
    }
  };

  const loginToSpotify = () => {
    if (!clientId) {
      setError('Spotify client ID not configured');
      return;
    }
    
    // Use Authorization Code flow instead of Implicit flow
    const authUrl = `https://accounts.spotify.com/authorize?client_id=${clientId}&response_type=code&redirect_uri=${encodeURIComponent(REDIRECT_URI)}&scope=${encodeURIComponent(SCOPES)}&show_dialog=true`;
    window.location.href = authUrl;
  };

  const logout = () => {
    localStorage.removeItem('spotify_token');
    setAccessToken(null);
    setUserProfile(null);
    setCurrentTracks([]);
    setIsPlaying(false);
  };

  // Real emotion detection using face-api.js
  const detectEmotion = async () => {
    if (!webcamRef.current || !model || !webcamRef.current.video) return null;

    try {
      const video = webcamRef.current.video;
      
      if (video.readyState !== 4) return null;

      // Detect faces with expressions
      const detections = await model
        .detectAllFaces(video, new model.TinyFaceDetectorOptions())
        .withFaceLandmarks()
        .withFaceExpressions();

      if (detections && detections.length > 0) {
        const expressions = detections[0].expressions;
        
        // Get the dominant emotion
        let maxEmotion = 'neutral';
        let maxConfidence = 0;
        
        // Map face-api emotions to our emotion categories
        const emotionMapping = {
          'happy': 'happy',
          'sad': 'sad',
          'angry': 'angry',
          'surprised': 'surprised',
          'neutral': 'neutral',
          'fearful': 'fearful',
          'disgusted': 'disgusted'
        };
        
        for (const [emotion, confidence] of Object.entries(expressions)) {
          if (confidence > maxConfidence) {
            maxConfidence = confidence;
            maxEmotion = emotionMapping[emotion] || 'neutral';
          }
        }
        
        // Draw detection on canvas (optional visualization)
        if (canvasRef.current) {
          const canvas = canvasRef.current;
          const displaySize = { width: video.width, height: video.height };
          model.matchDimensions(canvas, displaySize);
          
          const resizedDetections = model.resizeResults(detections, displaySize);
          canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);
          
          // Draw face detection box
          model.draw.drawDetections(canvas, resizedDetections);
          // Draw facial landmarks
          model.draw.drawFaceLandmarks(canvas, resizedDetections);
        }
        
        return { emotion: maxEmotion, confidence: maxConfidence };
      }
    } catch (error) {
      console.error('Error detecting emotion:', error);
    }
    
    return null;
  };

  // Fallback emotion detection using manual selection
  const manualEmotionSelection = (emotion) => {
    setCurrentEmotion(emotion);
    setEmotionConfidence(0.8);
    setEmotionHistory(prev => [...prev.slice(-9), emotion]);
    
    if (autoPlay && accessToken) {
      fetchAndPlayMusic(emotion);
    }
  };

  // Start continuous emotion detection
  const startEmotionDetection = useCallback(() => {
    if (!accessToken) {
      setError('Please log in to Spotify first');
      return;
    }
    
    if (!model) {
      setError('Emotion detection models not loaded. You can still manually select emotions below.');
      return;
    }
    
    // Check camera permission
    navigator.mediaDevices.getUserMedia({ video: true })
      .then(() => {
        setCameraPermission(true);
        setIsDetecting(true);
        setError(null);
        
        // Detection loop
        detectionIntervalRef.current = setInterval(async () => {
          const result = await detectEmotion();
          
          if (result && result.confidence > 0.5) {
            setEmotionConfidence(result.confidence);
            
            // Update emotion history
            setEmotionHistory(prev => [...prev.slice(-9), result.emotion]);
            
            // Only update if emotion changed significantly
            if (result.emotion !== currentEmotion) {
              setPreviousEmotion(currentEmotion);
              setCurrentEmotion(result.emotion);
              
              // Auto-play music if enabled and emotion is stable
              if (autoPlay && result.confidence > 0.7) {
                fetchAndPlayMusic(result.emotion);
              }
            }
          }
        }, 2000); // Check every 2 seconds
      })
      .catch(err => {
        console.error('Camera permission denied:', err);
        setCameraPermission(false);
        setError('Camera access is required for emotion detection. You can still manually select emotions below.');
      });
  }, [model, accessToken, currentEmotion, autoPlay]);

  const stopEmotionDetection = () => {
    setIsDetecting(false);
    if (detectionIntervalRef.current) {
      clearInterval(detectionIntervalRef.current);
    }
  };

  // Fetch personalized music based on emotion
  const fetchAndPlayMusic = async (emotion) => {
    try {
      setLoading(true);
      
      const response = await fetch(`${API_URL}/api/emotion/recommendations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          emotion, 
          access_token: accessToken 
        })
      });
      
      if (!response.ok) {
        throw new Error('Failed to get music recommendations');
      }
      
      const data = await response.json();
      setCurrentTracks(data.tracks || []);
      
      if (data.track_uris && data.track_uris.length > 0) {
        // Play the tracks
        await playTracks(data.track_uris);
      }
      
      setLoading(false);
    } catch (error) {
      console.error('Error fetching music:', error);
      setError('Failed to get music recommendations. Please try again.');
      setLoading(false);
    }
  };

  // Play tracks on Spotify
  const playTracks = async (trackUris) => {
    try {
      const response = await fetch(`${API_URL}/api/spotify/play`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          access_token: accessToken,
          track_uris: trackUris,
          device_id: selectedDevice
        })
      });
      
      const data = await response.json();
      
      if (response.ok) {
        setIsPlaying(true);
        setError(null);
      } else {
        setError(data.message || data.error || 'Failed to play music');
        
        // If no devices, refresh device list
        if (response.status === 404) {
          fetchDevices(accessToken);
        }
      }
    } catch (error) {
      console.error('Error playing tracks:', error);
      setError('Failed to play music. Please ensure Spotify is open on a device.');
    }
  };

  const pauseMusic = async () => {
    try {
      const response = await fetch(`${API_URL}/api/spotify/pause`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ access_token: accessToken })
      });
      
      if (response.ok) {
        setIsPlaying(false);
      }
    } catch (error) {
      console.error('Error pausing music:', error);
    }
  };

  const skipTrack = () => {
    if (currentTracks.length > 0) {
      const nextIndex = (currentTrackIndex + 1) % currentTracks.length;
      setCurrentTrackIndex(nextIndex);
      playTracks([currentTracks[nextIndex].uri]);
    }
  };

  const getEmotionEmoji = (emotion) => {
    const emojiMap = {
      happy: '😊',
      sad: '😢',
      angry: '😠',
      surprised: '😮',
      neutral: '😐',
      fearful: '😨',
      disgusted: '🤢',
      relaxed: '😌'
    };
    return emojiMap[emotion] || '🎵';
  };

  const getEmotionColor = (emotion) => {
    const colorMap = {
      happy: 'linear-gradient(135deg, #FFD700, #FFA500)',
      sad: 'linear-gradient(135deg, #4169E1, #1E90FF)',
      angry: 'linear-gradient(135deg, #DC143C, #FF0000)',
      surprised: 'linear-gradient(135deg, #FF69B4, #FF1493)',
      neutral: 'linear-gradient(135deg, #808080, #A9A9A9)',
      fearful: 'linear-gradient(135deg, #4B0082, #8A2BE2)',
      disgusted: 'linear-gradient(135deg, #556B2F, #6B8E23)',
      relaxed: 'linear-gradient(135deg, #98FB98, #90EE90)'
    };
    return colorMap[emotion] || 'linear-gradient(135deg, #667eea, #764ba2)';
  };

  // Login screen
  if (!accessToken) {
    return (
      <div className="login-container">
        <div className="login-card">
          <h1>🎵 Emotion Music Player</h1>
          <p>Experience music that matches your mood with real-time AI emotion detection</p>
          
          <div className="features-grid">
            <div className="feature-item">
              <span className="feature-icon">🤖</span>
              <h3>AI-Powered</h3>
              <p>Advanced facial emotion recognition</p>
            </div>
            <div className="feature-item">
              <span className="feature-icon">🎧</span>
              <h3>Your Music</h3>
              <p>Personalized from your Spotify library</p>
            </div>
            <div className="feature-item">
              <span className="feature-icon">🔒</span>
              <h3>Private</h3>
              <p>All processing happens in your browser</p>
            </div>
            <div className="feature-item">
              <span className="feature-icon">⚡</span>
              <h3>Real-time</h3>
              <p>Instant mood-based recommendations</p>
            </div>
          </div>
          
          <button onClick={loginToSpotify} className="spotify-login-btn">
            <svg className="spotify-logo" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path fill="currentColor" d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
            </svg>
            Connect with Spotify
          </button>
          
          {error && (
            <div className="error-message">{error}</div>
          )}
        </div>
      </div>
    );
  }

  // Main app interface
  return (
    <div className="app-container">
      <header className="app-header">
        <div className="header-left">
          <h1>🎵 Emotion Music</h1>
          {userProfile && (
            <span className="user-info">
              {userProfile.images && userProfile.images[0] && (
                <img src={userProfile.images[0].url} alt="Profile" className="user-avatar" />
              )}
              {userProfile.display_name}
            </span>
          )}
        </div>
        <button onClick={logout} className="logout-btn">Logout</button>
      </header>

      <div className="main-content">
        <div className="video-section">
          <div className="webcam-container">
            <Webcam
              ref={webcamRef}
              audio={false}
              screenshotFormat="image/jpeg"
              className="webcam"
              videoConstraints={{
                width: 640,
                height: 480,
                facingMode: "user"
              }}
            />
            <canvas
              ref={canvasRef}
              className="overlay-canvas"
              width={640}
              height={480}
            />
            
            <div className="emotion-overlay">
              <div 
                className="current-emotion-badge"
                style={{ background: getEmotionColor(currentEmotion) }}
              >
                <span className="emotion-emoji">{getEmotionEmoji(currentEmotion)}</span>
                <div className="emotion-details">
                  <span className="emotion-label">{currentEmotion}</span>
                  {emotionConfidence > 0 && (
                    <span className="emotion-confidence">
                      {Math.round(emotionConfidence * 100)}% confident
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>

          <div className="controls-panel">
            <div className="main-controls">
              {!isDetecting ? (
                <button 
                  onClick={startEmotionDetection} 
                  className="control-btn start"
                  disabled={loading || !model}
                >
                  {loading ? 'Loading AI...' : 'Start Detection'}
                </button>
              ) : (
                <button onClick={stopEmotionDetection} className="control-btn stop">
                  Stop Detection
                </button>
              )}
              
              <label className="toggle-switch">
                <input
                  type="checkbox"
                  checked={autoPlay}
                  onChange={(e) => setAutoPlay(e.target.checked)}
                />
                <span className="toggle-slider"></span>
                <span className="toggle-label">Auto-play</span>
              </label>
            </div>

            {devices.length > 0 && (
              <div className="device-selector">
                <label>Play on:</label>
                <select 
                  value={selectedDevice || ''} 
                  onChange={(e) => setSelectedDevice(e.target.value)}
                  className="device-dropdown"
                >
                  {devices.map(device => (
                    <option key={device.id} value={device.id}>
                      {device.name} ({device.type})
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          {error && (
            <div className="error-panel">
              <span className="error-icon">⚠️</span>
              {error}
            </div>
          )}
        </div>

        <div className="info-section">
          <div className="now-playing-card">
            <h2>Now Playing</h2>
            {currentTracks.length > 0 ? (
              <div className="track-display">
                {currentTracks[currentTrackIndex] && (
                  <>
                    {currentTracks[currentTrackIndex].image && (
                      <img 
                        src={currentTracks[currentTrackIndex].image} 
                        alt="Album art"
                        className="album-art"
                      />
                    )}
                    <div className="track-info">
                      <div className="track-name">{currentTracks[currentTrackIndex].name}</div>
                      <div className="track-artist">{currentTracks[currentTrackIndex].artist}</div>
                      <div className="track-emotion">
                        Playing {currentEmotion} music
                      </div>
                    </div>
                  </>
                )}
                
                <div className="playback-controls">
                  {isPlaying ? (
                    <button onClick={pauseMusic} className="playback-btn">
                      <span className="control-icon">⏸</span>
                    </button>
                  ) : (
                    <button 
                      onClick={() => playTracks(currentTracks.map(t => t.uri))} 
                      className="playback-btn"
                    >
                      <span className="control-icon">▶</span>
                    </button>
                  )}
                  <button onClick={skipTrack} className="playback-btn">
                    <span className="control-icon">⏭</span>
                  </button>
                </div>
              </div>
            ) : (
              <div className="no-track">
                {isDetecting ? 'Detecting your mood...' : 'Start detection to play music'}
              </div>
            )}
          </div>

          <div className="playlist-card">
            <h2>Current Playlist</h2>
            <div className="playlist-tracks">
              {currentTracks.length > 0 ? (
                currentTracks.map((track, index) => (
                  <div 
                    key={track.id} 
                    className={`playlist-item ${index === currentTrackIndex ? 'active' : ''}`}
                    onClick={() => {
                      setCurrentTrackIndex(index);
                      playTracks([track.uri]);
                    }}
                  >
                    <span className="track-number">{index + 1}</span>
                    <div className="track-details">
                      <span className="track-title">{track.name}</span>
                      <span className="track-artist-small">{track.artist}</span>
                    </div>
                  </div>
                ))
              ) : (
                <p className="empty-playlist">No tracks loaded</p>
              )}
            </div>
          </div>

          <div className="emotion-history-card">
            <h2>Emotion Timeline</h2>
            <div className="emotion-timeline">
              {emotionHistory.length > 0 ? (
                emotionHistory.map((emotion, index) => (
                  <div key={index} className="timeline-item">
                    <span className="timeline-emoji">{getEmotionEmoji(emotion)}</span>
                    <span className="timeline-label">{emotion}</span>
                  </div>
                ))
              ) : (
                <p className="no-history">Your emotion history will appear here</p>
              )}
            </div>
          </div>

          <div className="manual-control-card">
            <h2>Manual Mood Selection</h2>
            <div className="emotion-grid">
              {['happy', 'sad', 'angry', 'relaxed', 'surprised', 'neutral'].map(emotion => (
                <button
                  key={emotion}
                  onClick={() => manualEmotionSelection(emotion)}
                  className="emotion-select-btn"
                  style={{ background: getEmotionColor(emotion) }}
                  disabled={loading}
                >
                  <span className="btn-emoji">{getEmotionEmoji(emotion)}</span>
                  <span className="btn-label">{emotion}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {loading && (
        <div className="loading-overlay">
          <div className="loading-spinner"></div>
          <p>Loading your personalized music...</p>
        </div>
      )}

      {cameraPermission === false && (
        <div className="permission-modal">
          <div className="modal-content">
            <h2>Camera Permission Required</h2>
            <p>This app needs camera access to detect your emotions and play matching music.</p>
            <ol>
              <li>Click the camera icon in your browser's address bar</li>
              <li>Select "Allow" for camera access</li>
              <li>Refresh this page</li>
            </ol>
            <button onClick={() => window.location.reload()} className="refresh-btn">
              Refresh Page
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default EmotionMusicApp;