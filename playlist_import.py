import sys
import json
import re
from pytube import Playlist
import time

def extract_playlist_id(url):
    """Extract playlist ID from YouTube or YouTube Music URL"""
    patterns = [
        r'[&?]list=([^&]+)',                           # Standard YouTube playlist
        r'playlist\?list=([^&]+)',                     # Direct playlist link
        r'playlist/([a-zA-Z0-9_-]+)',                  # Alternative format
        r'music\.youtube\.com\/playlist\?list=([^&]+)' # YouTube Music playlist
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def import_playlist(url):
    try:
        print(f"Importing playlist from URL: {url}", file=sys.stderr)
        
        # Extract playlist ID
        playlist_id = extract_playlist_id(url)
        if not playlist_id:
            print("Error: Could not extract playlist ID from URL", file=sys.stderr)
            return 1
            
        print(f"Extracted playlist ID: {playlist_id}", file=sys.stderr)
        
        # Convert YouTube Music URL to standard YouTube URL for better compatibility
        if 'music.youtube.com' in url:
            url = f"https://www.youtube.com/playlist?list={playlist_id}"
            print(f"Converted YouTube Music URL to: {url}", file=sys.stderr)
        
        # Create Playlist object
        playlist = Playlist(url)
        
        # Force load playlist data
        playlist_title = playlist.title
        playlist_owner = playlist.owner
        
        print(f"Playlist title: {playlist_title}", file=sys.stderr)
        print(f"Playlist owner: {playlist_owner}", file=sys.stderr)
        
        tracks = []
        video_count = 0
        
        # Get videos with retry logic
        for attempt in range(3):
            try:
                for video in playlist.videos:
                    if video_count >= 50:  # Limit to 50 videos
                        break
                        
                    try:
                        track = {
                            'id': video.video_id,
                            'title': video.title or 'Untitled',
                            'thumbnail': f'https://img.youtube.com/vi/{video.video_id}/mqdefault.jpg',
                            'channel': video.author or 'Unknown Channel',
                            'duration': str(video.length) if video.length else 'Unknown'
                        }
                        tracks.append(track)
                        video_count += 1
                        
                    except Exception as video_error:
                        print(f"Error processing video: {video_error}", file=sys.stderr)
                        continue
                
                break  # Success, exit retry loop
                
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}", file=sys.stderr)
                if attempt < 2:
                    time.sleep(2)  # Wait before retry
                else:
                    raise e
        
        # Create result object
        result = {
            'id': playlist_id,
            'name': playlist_title or 'Untitled Playlist',
            'description': f'by {playlist_owner}' if playlist_owner else 'YouTube Playlist',
            'isYouTube': True,
            'author': playlist_owner or 'Unknown',
            'coverImage': tracks[0]['thumbnail'] if tracks else None,
            'tracks': tracks
        }
        
        print(json.dumps(result))
        return 0
        
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        return 1

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python3 playlist_import.py "playlist_url"', file=sys.stderr)
        sys.exit(1)
    
    url = sys.argv[1]
    sys.exit(import_playlist(url)) 