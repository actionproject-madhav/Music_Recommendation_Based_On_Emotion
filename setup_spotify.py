#!/usr/bin/env python3
"""
Spotify Setup Helper Script
This script helps you set up your Spotify API credentials for the Music Recommendation app.
"""

import os
import sys

def create_env_file():
    """Create a .env file with Spotify credentials"""
    
    print("🎵 Spotify API Setup for Music Recommendation App")
    print("=" * 50)
    
    # Check if .env already exists
    if os.path.exists('.env'):
        print("⚠️  .env file already exists!")
        response = input("Do you want to overwrite it? (y/N): ").lower()
        if response != 'y':
            print("Setup cancelled.")
            return
    
    print("\n📋 You need to get your Spotify API credentials:")
    print("1. Go to: https://developer.spotify.com/dashboard")
    print("2. Create a new app or select existing one")
    print("3. Copy your Client ID and Client Secret")
    print("4. In app settings, add redirect URI: http://localhost:3000/callback")
    
    print("\n🔑 Enter your Spotify credentials:")
    
    client_id = input("Spotify Client ID: ").strip()
    if not client_id:
        print("❌ Client ID is required!")
        return
    
    client_secret = input("Spotify Client Secret: ").strip()
    if not client_secret:
        print("❌ Client Secret is required!")
        return
    
    # Create .env content
    env_content = f"""# Spotify API Configuration
SPOTIFY_CLIENT_ID={client_id}
SPOTIFY_CLIENT_SECRET={client_secret}
REDIRECT_URI=http://localhost:3000/callback
"""
    
    # Write to .env file
    try:
        with open('.env', 'w') as f:
            f.write(env_content)
        print("\n✅ .env file created successfully!")
        print("📁 Location: backend/.env")
        print("\n🚀 Next steps:")
        print("1. cd backend")
        print("2. pip install -r requirements.txt")
        print("3. python app.py")
        print("\n4. In another terminal:")
        print("   cd frontend")
        print("   npm install")
        print("   npm start")
        
    except Exception as e:
        print(f"❌ Error creating .env file: {e}")

if __name__ == "__main__":
    # Change to backend directory if it exists
    if os.path.exists('backend'):
        os.chdir('backend')
    
    create_env_file()

