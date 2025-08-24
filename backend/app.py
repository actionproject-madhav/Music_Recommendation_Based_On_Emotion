from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
from dotenv import load_dotenv
from datetime import datetime
import logging

load_dotenv()

app = Flask(__name__)
CORS(app, origins=['http://localhost:3000', 'https://localhost:3000', 'http://localhost:3001', 'https://localhost:3001', 'http://127.0.0.1:3000'])

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Spotify credentials - users will use their own
CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
REDIRECT_URI = os.getenv('REDIRECT_URI', 'http://127.0.0.1:3000/callback')
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
    
    print(f"Getting recommendations for emotion: {emotion}")  # Debug
    
    if not access_token:
        return jsonify({'error': 'No access token provided'}), 401
    
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    
    try:
        # Test if token is valid
        test_response = requests.get('https://api.spotify.com/v1/me', headers=headers)
        if test_response.status_code != 200:
            print(f"Token validation failed: {test_response.status_code}")
            return jsonify({'error': 'Invalid access token'}), 401
        
        # Get user's top tracks for seed
        print("Getting user's top tracks...")
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
            print(f"Found {len(top_tracks.get('items', []))} top tracks")
            
            # Get up to 2 seed tracks
            for track in top_tracks.get('items', [])[:2]:
                if track and 'id' in track:
                    seed_tracks.append(track['id'])
                    if track.get('artists') and len(track['artists']) > 0:
                        seed_artists.append(track['artists'][0]['id'])
        else:
            print(f"Failed to get top tracks: {top_tracks_response.status_code}")
        
        # Get user's top artists if we need more seeds
        if len(seed_artists) < 2:
            print("Getting user's top artists...")
            top_artists_url = 'https://api.spotify.com/v1/me/top/artists'
            top_artists_response = requests.get(
                top_artists_url,
                headers=headers,
                params={'limit': 3, 'time_range': 'short_term'}
            )
            
            if top_artists_response.status_code == 200:
                top_artists = top_artists_response.json()
                for artist in top_artists.get('items', [])[:2]:
                    if artist and 'id' in artist and artist['id'] not in seed_artists:
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
            print("No user seeds found, using genre seeds")
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
        
        print(f"Recommendation params: {rec_params}")
        
        # Get recommendations from Spotify
        recommendations_url = 'https://api.spotify.com/v1/recommendations'
        rec_response = requests.get(recommendations_url, headers=headers, params=rec_params)
        
        print(f"Recommendations response status: {rec_response.status_code}")
        
        if rec_response.status_code == 200:
            recommendations = rec_response.json()
            tracks = recommendations.get('tracks', [])
            
            if tracks:
                # Format response with track details
                track_list = []
                track_uris = []
                
                for track in tracks[:10]:  # Limit to 10 tracks
                    if track and 'id' in track:
                        track_info = {
                            'id': track['id'],
                            'name': track.get('name', 'Unknown'),
                            'artist': track['artists'][0]['name'] if track.get('artists') and len(track['artists']) > 0 else 'Unknown',
                            'uri': track.get('uri', ''),
                            'preview_url': track.get('preview_url'),
                            'image': track.get('album', {}).get('images', [{}])[0].get('url') if track.get('album', {}).get('images') else None
                        }
                        track_list.append(track_info)
                        track_uris.append(track['uri'])
                
                if track_list:
                    return jsonify({
                        'emotion': emotion,
                        'tracks': track_list,
                        'track_uris': track_uris,
                        'features_used': features,
                        'playlist_name': f"{emotion.capitalize()} Mood - Personalized"
                    }), 200
        else:
            print(f"Recommendations failed: {rec_response.status_code} - {rec_response.text}")
        
        # Fallback: Search for playlists if recommendations fail
        print("Falling back to playlist search...")
        return search_mood_playlists(emotion, headers)
        
    except Exception as e:
        logger.error(f"Error getting recommendations: {str(e)}")
        import traceback
        traceback.print_exc()
        # Fallback to playlist search
        return search_mood_playlists(emotion, headers)
def search_mood_playlists(emotion, headers):
    """Fallback: Search for mood-based playlists"""
    try:
        features = EMOTION_FEATURES.get(emotion, EMOTION_FEATURES['neutral'])
        search_query = f"{emotion} mood"
        
        search_url = 'https://api.spotify.com/v1/search'
        search_params = {
            'q': search_query,
            'type': 'playlist',
            'limit': 10  # Increased limit to have more options
        }
        
        print(f"Searching for playlists with query: {search_query}")  # Debug
        
        search_response = requests.get(search_url, headers=headers, params=search_params)
        
        print(f"Search response status: {search_response.status_code}")  # Debug
        
        if search_response.status_code == 200:
            results = search_response.json()
            print(f"Search results keys: {results.keys()}")  # Debug
            
            # Add null checks here
            if 'playlists' not in results or results['playlists'] is None:
                print("No playlists key in response or playlists is None")
                return jsonify({'error': 'No playlists found for this mood'}), 404
                
            playlists = results['playlists'].get('items', [])
            print(f"Found {len(playlists)} playlists")  # Debug
            
            if not playlists:
                print("No playlist items found")
                return jsonify({'error': 'No playlists found for this mood'}), 404
            
            # Filter out None playlists and find a valid one
            valid_playlist = None
            for playlist in playlists:
                if playlist is not None and isinstance(playlist, dict) and 'id' in playlist:
                    # Additional checks for playlist validity
                    playlist_id = playlist.get('id')
                    playlist_name = playlist.get('name', 'Unknown')
                    
                    if playlist_id and playlist_name:
                        print(f"Found valid playlist: {playlist_name} (ID: {playlist_id})")
                        valid_playlist = playlist
                        break
                else:
                    print(f"Skipping invalid playlist: {playlist}")
            
            if not valid_playlist:
                print("No valid playlists found")
                return jsonify({'error': 'No valid playlists found for this mood'}), 404
            
            print(f"Using playlist: {valid_playlist.get('name', 'Unknown')}")  # Debug
            
            # Get tracks from the valid playlist
            tracks_url = f"https://api.spotify.com/v1/playlists/{valid_playlist['id']}/tracks"
            tracks_response = requests.get(tracks_url, headers=headers, params={'limit': 20})
            
            print(f"Tracks response status: {tracks_response.status_code}")  # Debug
            
            if tracks_response.status_code == 200:
                playlist_tracks = tracks_response.json()
                
                if 'items' not in playlist_tracks or playlist_tracks['items'] is None:
                    print("No items in playlist tracks response")
                    return jsonify({'error': 'Playlist has no tracks'}), 404
                
                tracks = []
                track_uris = []
                
                for item in playlist_tracks.get('items', []):
                    # Multiple null checks for each item
                    if (item is None or 
                        'track' not in item or 
                        item['track'] is None or
                        not isinstance(item['track'], dict)):
                        continue
                        
                    track = item['track']
                    
                    # Check if track has required fields
                    if (not track.get('id') or 
                        not track.get('name') or 
                        not track.get('uri')):
                        continue
                    
                    # Get artist name safely
                    artist_name = 'Unknown'
                    if (track.get('artists') and 
                        isinstance(track['artists'], list) and 
                        len(track['artists']) > 0 and
                        track['artists'][0] is not None and
                        isinstance(track['artists'][0], dict)):
                        artist_name = track['artists'][0].get('name', 'Unknown')
                    
                    # Get album image safely
                    image_url = None
                    if (track.get('album') and 
                        isinstance(track['album'], dict) and
                        track['album'].get('images') and
                        isinstance(track['album']['images'], list) and
                        len(track['album']['images']) > 0 and
                        track['album']['images'][0] is not None and
                        isinstance(track['album']['images'][0], dict)):
                        image_url = track['album']['images'][0].get('url')
                    
                    track_info = {
                        'id': track['id'],
                        'name': track['name'],
                        'artist': artist_name,
                        'uri': track['uri'],
                        'preview_url': track.get('preview_url'),
                        'image': image_url
                    }
                    
                    tracks.append(track_info)
                    track_uris.append(track['uri'])
                    
                    # Stop after getting 10 valid tracks
                    if len(tracks) >= 10:
                        break
                
                if tracks:
                    print(f"Successfully found {len(tracks)} valid tracks")
                    return jsonify({
                        'emotion': emotion,
                        'tracks': tracks,
                        'track_uris': track_uris,
                        'playlist_name': valid_playlist.get('name', f"{emotion.capitalize()} Mood"),
                        'source': 'playlist_search'
                    }), 200
                else:
                    print("No valid tracks found in playlist")
                    return jsonify({'error': 'No playable tracks found in playlist'}), 404
            else:
                print(f"Failed to get playlist tracks: {tracks_response.status_code}")
                print(f"Tracks response text: {tracks_response.text}")
                return jsonify({'error': 'Failed to get playlist tracks'}), 500
        else:
            print(f"Search failed with status: {search_response.status_code}")
            print(f"Search response: {search_response.text}")
            return jsonify({'error': 'Failed to search for playlists'}), 500
        
    except Exception as e:
        print(f"Exception in search_mood_playlists: {str(e)}")
        import traceback
        traceback.print_exc()
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
@app.route('/api/spotify/exchange-token', methods=['POST'])
def exchange_token():
    """Exchange authorization code for access token"""
    data = request.json
    code = data.get('code')
    
    if not code:
        return jsonify({'error': 'No authorization code provided'}), 400
    
    # Token exchange request
    token_url = 'https://accounts.spotify.com/api/token'
    token_data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'client_id': CLIENT_ID,
        'client_secret': os.getenv('SPOTIFY_CLIENT_SECRET')
    }
    
    token_headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    
    try:
        response = requests.post(token_url, data=token_data, headers=token_headers)
        
        if response.status_code == 200:
            return jsonify(response.json()), 200
        else:
            logger.error(f"Token exchange failed: {response.text}")
            return jsonify({'error': 'Failed to exchange code for token'}), 400
            
    except Exception as e:
        logger.error(f"Error exchanging token: {str(e)}")
        return jsonify({'error': 'Token exchange failed'}), 500
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