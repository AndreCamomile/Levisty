#!/usr/bin/env python3
import sys
import json

def test_simple_playlist():
    """Create a simple test playlist to verify the system works"""
    try:
        # Create a test playlist with dummy data
        test_playlist = {
            'id': 'test123',
            'name': 'Test Playlist',
            'description': 'Test playlist to verify import functionality',
            'isYouTube': True,
            'author': 'Test Author',
            'coverImage': 'https://img.youtube.com/vi/dQw4w9WgXcQ/mqdefault.jpg',
            'tracks': [
                {
                    'id': 'dQw4w9WgXcQ',
                    'title': 'Test Video 1',
                    'thumbnail': 'https://img.youtube.com/vi/dQw4w9WgXcQ/mqdefault.jpg',
                    'channel': 'Test Channel',
                    'duration': '3:32'
                },
                {
                    'id': 'oHg5SJYRHA0',
                    'title': 'Test Video 2',
                    'thumbnail': 'https://img.youtube.com/vi/oHg5SJYRHA0/mqdefault.jpg',
                    'channel': 'Test Channel',
                    'duration': '4:12'
                }
            ]
        }
        
        print(json.dumps(test_playlist))
        return 0
        
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(test_simple_playlist()) 