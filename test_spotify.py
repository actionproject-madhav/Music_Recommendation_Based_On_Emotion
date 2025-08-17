#!/usr/bin/env python3
"""
Test Spotify API Connection
This script tests if your Spotify credentials are working correctly.
"""

import requests
import os
from dotenv import load_dotenv

def test_spotify_connection():
    """Test Spotify API connection with your credentials"""
    
    print("🎵 Testing Spotify API Connection")
    print("=" * 40)
    
    # Load environment variables
    load_dotenv()
    
    client_id = os.getenv('SPOTIFY_CLIENT_ID')
    client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
    redirect_uri = os.getenv('REDIRECT_URI')
    
    print(f"Client ID: {client_id}")
    print(f"Client Secret: {'*' * len(client_secret) if client_secret else 'NOT SET'}")
    print(f"Redirect URI: {redirect_uri}")
    print()
    
    if not client_id or not client_secret:
        print("❌ Missing Spotify credentials in .env file!")
        return False
    
    # Test getting access token
    try:
        print("🔄 Testing Spotify authentication...")
        
        # Get client credentials token (for testing purposes)
        auth_url = 'https://accounts.spotify.com/api/token'
        auth_data = {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret
        }
        
        response = requests.post(auth_url, data=auth_data)
        
        if response.status_code == 200:
            print("✅ Spotify API connection successful!")
            print("✅ Your credentials are valid")
            print("✅ You can now use the web app")
            return True
        else:
            print(f"❌ Spotify API connection failed!")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing Spotify connection: {e}")
        return False

def check_redirect_uri():
    """Check if redirect URI is properly configured"""
    
    print("\n🔗 Checking Redirect URI Configuration")
    print("=" * 40)
    
    redirect_uri = os.getenv('REDIRECT_URI', 'https://localhost:3000/callback')
    
    print(f"Current Redirect URI: {redirect_uri}")
    print()
    
    print("📋 To fix 'INVALID_CLIENT: Invalid redirect URI' error:")
    print("1. Go to: https://developer.spotify.com/dashboard")
    print("2. Select your app")
    print("3. Click 'Edit Settings'")
    print("4. Add this exact redirect URI:")
    print(f"   {redirect_uri}")
    print("5. Click 'Save'")
    print()
    
    return redirect_uri

if __name__ == "__main__":
    print("🎵 Spotify Connection Test for Music Recommendation App")
    print("=" * 60)
    print()
    
    # Test connection
    connection_ok = test_spotify_connection()
    
    # Check redirect URI
    check_redirect_uri()
    
    if connection_ok:
        print("\n🎉 All tests passed! Your Spotify setup should work.")
        print("Try running the web app now.")
    else:
        print("\n⚠️  Some tests failed. Check the issues above.")
    
    print("\n" + "=" * 60)
