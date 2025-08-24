from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
from dotenv import load_dotenv
from datetime import datetime
import logging

load_dotenv()

app = Flask(__name__)
CORS(app, origins=['http://localhost:3000', 'https://localhost:3000', 'http://localhost:3001', 'https://localhost:3001'])

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Spotify credentials - users will use their own
CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
REDIRECT_URI = os.getenv('REDIRECT_URI', 'https://localhost:3000/callback')

# Emotion to music characteristics mapping (Spotify audio features)
EMOTION_FEATURES = {
    'happy': {
        'min_valence': 0.6,
        'min_energy': 0.6,
        'target_danceability': 0.7,
        'genres': ['happy', 'pop', 'dance', 'summer'],
        'moods': ['happy', 'cheerful', 'upbeat', 'positive']
    },
    'sad': {
        'max_valence': 0.4,
        'max_energy': 0.5,
        'target_acousticness': 0.7,
        'genres': ['sad', 'acoustic', 'piano', 'rain'],
        'moods': ['sad', 'melancholy', 'lonely', 'heartbreak']
    },
    'angry': {
        'max_valence': 0.4,
        'min_energy': 0.7,
        'target_loudness': -5,
        'genres': ['metal', 'rock', 'punk', 'aggressive'],
        'moods': ['angry', 'aggressive', 'intense', 'rage']
    },
    'relaxed': {
        'min_valence': 0.4,
        'max_energy': 0.4,
        'target_acousticness': 0.6,
        'genres': ['chill', 'ambient', 'lofi', 'meditation'],
        'moods': ['calm', 'peaceful', 'relaxing', 'serene']
    },
    'surprised': {
        'min_energy': 0.6,
        'target_danceability': 0.6,
        'genres': ['edm', 'electronic', 'party', 'festival'],
        'moods': ['energetic', 'exciting', 'uplifting', 'party']
    },
    'fearful': {
        'max_valence': 0.3,
        'target_instrumentalness': 0.5,
        'genres': ['dark ambient', 'atmospheric', 'cinematic'],
        'moods': ['dark', 'tense', 'mysterious', 'suspense']
    },
    'disgusted': {
        'max_valence': 0.3,
        'min_energy': 0.5,
        'genres': ['alternative', 'grunge', 'industrial'],
        'moods': ['dark', 'gritty', 'raw', 'underground']
    },
    'neutral': {
        'min_valence': 0.4,
        'max_valence': 0.6,
        'min_energy': 0.4,
        'max_energy': 0.6,
        'genres': ['focus', 'study', 'work', 'background'],
        'moods': ['focus', 'neutral', 'balanced', 'concentration']
    }
}

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()}), 200

@app.route('/api/spotify/client-id', methods=['GET'])
def get_client_id():
    """Return the client ID for frontend to use"""
    return jsonify({'client_id': CLIENT_ID}), 200

@app.route('/api/emotion/recommendations', methods=['POST'])
def get_recommendations():
    """Get personalized track recommendations based on emotion and user's listening history"""
    data = request.json
    emotion = data.get('emotion', 'neutral').lower()
    access_token = data.get('access_token')
    
    if not access_token:
        return jsonify({'error': 'No access token provided'}), 401
    
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    
    try:
        # Get user's top tracks for seed
        top_tracks_url = 'https://api.spotify.com/v1/me/top/tracks'
        top_tracks_response = requests.get(
            top_tracks_url, 
            headers=headers,
            params={'limit': 5, 'time_range': 'short_term'}
        )
        
        seed_tracks = []
        seed_artists = []
        
        if top_tracks_response.status_code == 200:
            top_tracks = top_tracks_response.json()
            # Get up to 2 seed tracks
            for track in top_tracks.get('items', [])[:2]:
                seed_tracks.append(track['id'])
                if track['artists']:
                    seed_artists.append(track['artists'][0]['id'])
        
        # Get user's top artists for better personalization
        if len(seed_artists) < 2:
            top_artists_url = 'https://api.spotify.com/v1/me/top/artists'
            top_artists_response = requests.get(
                top_artists_url,
                headers=headers,
                params={'limit': 3, 'time_range': 'short_term'}
            )
            
            if top_artists_response.status_code == 200:
                top_artists = top_artists_response.json()
                for artist in top_artists.get('items', [])[:2]:
                    if artist['id'] not in seed_artists:
                        seed_artists.append(artist['id'])
        
        # Get emotion-based music features
        features = EMOTION_FEATURES.get(emotion, EMOTION_FEATURES['neutral'])
        
        # Build recommendation parameters
        rec_params = {
            'limit': 20,
            'market': 'US'
        }
        
        # Add seeds (Spotify requires at least one seed)
        if seed_tracks:
            rec_params['seed_tracks'] = ','.join(seed_tracks[:2])
        if seed_artists:
            rec_params['seed_artists'] = ','.join(seed_artists[:2])
        
        # If no seeds from user history, use genre seeds
        if not seed_tracks and not seed_artists:
            rec_params['seed_genres'] = ','.join(features['genres'][:2])
        
        # Add audio features for emotion
        if 'min_valence' in features:
            rec_params['min_valence'] = features['min_valence']
        if 'max_valence' in features:
            rec_params['max_valence'] = features['max_valence']
        if 'min_energy' in features:
            rec_params['min_energy'] = features['min_energy']
        if 'max_energy' in features:
            rec_params['max_energy'] = features['max_energy']
        if 'target_danceability' in features:
            rec_params['target_danceability'] = features['target_danceability']
        if 'target_acousticness' in features:
            rec_params['target_acousticness'] = features['target_acousticness']
        
        # Get recommendations from Spotify
        recommendations_url = 'https://api.spotify.com/v1/recommendations'
        rec_response = requests.get(recommendations_url, headers=headers, params=rec_params)
        
        if rec_response.status_code == 200:
            recommendations = rec_response.json()
            tracks = recommendations.get('tracks', [])
            
            if tracks:
                # Format response with track details
                track_list = []
                track_uris = []
                
                for track in tracks[:10]:  # Limit to 10 tracks
                    track_info = {
                        'id': track['id'],
                        'name': track['name'],
                        'artist': track['artists'][0]['name'] if track['artists'] else 'Unknown',
                        'uri': track['uri'],
                        'preview_url': track.get('preview_url'),
                        'image': track['album']['images'][0]['url'] if track['album']['images'] else None
                    }
                    track_list.append(track_info)
                    track_uris.append(track['uri'])
                
                return jsonify({
                    'emotion': emotion,
                    'tracks': track_list,
                    'track_uris': track_uris,
                    'features_used': features,
                    'playlist_name': f"{emotion.capitalize()} Mood - Personalized"
                }), 200
        
        # Fallback: Search for playlists if recommendations fail
        return search_mood_playlists(emotion, headers)
        
    except Exception as e:
        logger.error(f"Error getting recommendations: {str(e)}")
        # Fallback to playlist search
        return search_mood_playlists(emotion, headers)

def search_mood_playlists(emotion, headers):
    """Fallback: Search for mood-based playlists"""
    try:
        features = EMOTION_FEATURES.get(emotion, EMOTION_FEATURES['neutral'])
        search_query = f"{emotion} mood {features['moods'][0]}"
        
        search_url = 'https://api.spotify.com/v1/search'
        search_params = {
            'q': search_query,
            'type': 'playlist',
            'limit': 5
        }
        
        search_response = requests.get(search_url, headers=headers, params=search_params)
        
        if search_response.status_code == 200:
            results = search_response.json()
            playlists = results.get('playlists', {}).get('items', [])
            
            if playlists:
                # Get tracks from the first playlist
                playlist = playlists[0]
                tracks_url = f"https://api.spotify.com/v1/playlists/{playlist['id']}/tracks"
                tracks_response = requests.get(tracks_url, headers=headers, params={'limit': 10})
                
                if tracks_response.status_code == 200:
                    playlist_tracks = tracks_response.json()
                    tracks = []
                    track_uris = []
                    
                    for item in playlist_tracks.get('items', [])[:10]:
                        if item['track']:
                            track = item['track']
                            track_info = {
                                'id': track['id'],
                                'name': track['name'],
                                'artist': track['artists'][0]['name'] if track['artists'] else 'Unknown',
                                'uri': track['uri'],
                                'preview_url': track.get('preview_url'),
                                'image': track['album']['images'][0]['url'] if track['album']['images'] else None
                            }
                            tracks.append(track_info)
                            track_uris.append(track['uri'])
                    
                    return jsonify({
                        'emotion': emotion,
                        'tracks': tracks,
                        'track_uris': track_uris,
                        'playlist_name': playlist['name'],
                        'source': 'playlist_search'
                    }), 200
        
        return jsonify({'error': 'Could not find music for this mood'}), 404
        
    except Exception as e:
        logger.error(f"Error searching playlists: {str(e)}")
        return jsonify({'error': 'Failed to search for music'}), 500

@app.route('/api/spotify/play', methods=['POST'])
def play_tracks():
    """Start playback on user's active device"""
    data = request.json
    access_token = data.get('access_token')
    track_uris = data.get('track_uris', [])
    device_id = data.get('device_id')
    
    if not access_token:
        return jsonify({'error': 'No access token'}), 401
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    try:
        # Get available devices
        devices_url = 'https://api.spotify.com/v1/me/player/devices'
        devices_response = requests.get(devices_url, headers=headers)
        
        if devices_response.status_code == 200:
            devices = devices_response.json().get('devices', [])
            
            if not devices:
                return jsonify({
                    'error': 'No active Spotify devices found',
                    'message': 'Please open Spotify on your phone, computer, or web player'
                }), 404
            
            # Use provided device or first available
            if not device_id:
                device_id = devices[0]['id']
        
        # Start playback
        play_url = 'https://api.spotify.com/v1/me/player/play'
        if device_id:
            play_url += f'?device_id={device_id}'
        
        play_data = {
            'uris': track_uris,
            'position_ms': 0
        }
        
        response = requests.put(play_url, headers=headers, json=play_data)
        
        if response.status_code in [204, 202]:
            return jsonify({'status': 'playing', 'device_id': device_id}), 200
        elif response.status_code == 403:
            return jsonify({
                'error': 'Spotify Premium required',
                'message': 'You need Spotify Premium to control playback'
            }), 403
        else:
            return jsonify({'error': 'Failed to start playback'}), response.status_code
            
    except Exception as e:
        logger.error(f"Error starting playback: {str(e)}")
        return jsonify({'error': 'Failed to start playback'}), 500

@app.route('/api/spotify/devices', methods=['GET'])
def get_devices():
    """Get user's available Spotify devices"""
    access_token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    if not access_token:
        return jsonify({'error': 'No access token'}), 401
    
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    
    try:
        devices_url = 'https://api.spotify.com/v1/me/player/devices'
        response = requests.get(devices_url, headers=headers)
        
        if response.status_code == 200:
            return jsonify(response.json()), 200
        else:
            return jsonify({'devices': []}), 200
            
    except Exception as e:
        logger.error(f"Error getting devices: {str(e)}")
        return jsonify({'devices': []}), 200

@app.route('/api/user/preferences', methods=['POST'])
def save_preferences():
    """Save user's music preferences for better recommendations"""
    data = request.json
    # In production, save to database
    # For now, just acknowledge
    return jsonify({'status': 'saved'}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')