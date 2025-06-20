#!/usr/bin/env python3
import sys
import json
import yt_dlp
import re

def import_playlist_ytdlp(url):
    """Import YouTube playlist using yt-dlp as alternative method"""
    try:
        print(f"Starting yt-dlp import for URL: {url}", file=sys.stderr)
        
        # Configure yt-dlp options
        ydl_opts = {
            'quiet': False,
            'extract_flat': True,  # Only extract metadata, don't download
            'playlist_items': '1:50',  # Limit to first 50 items
            'ignoreerrors': True,  # Continue on errors
            'no_warnings': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print("Extracting playlist info with yt-dlp...", file=sys.stderr)
            info = ydl.extract_info(url, download=False)
            
            if not info:
                raise Exception("No playlist information extracted")
            
            print(f"Extracted info type: {info.get('_type', 'unknown')}", file=sys.stderr)
            print(f"Entries count: {len(info.get('entries', []))}", file=sys.stderr)
            
            if info.get('_type') != 'playlist':
                raise Exception("URL does not point to a playlist")
            
            entries = info.get('entries', [])
            if not entries:
                raise Exception("Playlist has no entries")
            
            # Filter out unavailable videos
            valid_entries = []
            for entry in entries:
                if entry and entry.get('id'):
                    valid_entries.append(entry)
                    print(f"Added entry: {entry.get('id')} - {entry.get('title', 'Unknown')}", file=sys.stderr)
                else:
                    print(f"Skipped invalid entry: {entry}", file=sys.stderr)
            
            if not valid_entries:
                raise Exception("No valid videos found in playlist")
            
            # Format playlist data
            formatted_playlist = {
                'id': info.get('id', 'unknown'),
                'name': info.get('title', 'Untitled Playlist'),
                'description': info.get('description', '') or f"by {info.get('uploader', 'Unknown')}",
                'isYouTube': True,
                'author': info.get('uploader', 'Unknown'),
                'coverImage': None,  # yt-dlp doesn't provide playlist thumbnails easily
                'tracks': []
            }
            
            # Add tracks
            for entry in valid_entries:
                track = {
                    'id': entry.get('id', ''),
                    'title': entry.get('title', 'Untitled'),
                    'thumbnail': f"https://img.youtube.com/vi/{entry.get('id', '')}/mqdefault.jpg",
                    'channel': entry.get('uploader', 'Unknown Channel'),
                    'duration': entry.get('duration_string', 'Unknown')
                }
                formatted_playlist['tracks'].append(track)
            
            print(f"Successfully formatted {len(formatted_playlist['tracks'])} tracks", file=sys.stderr)
            print(json.dumps(formatted_playlist))
            return 0
            
    except Exception as e:
        print(f"yt-dlp import error: {str(e)}", file=sys.stderr)
        return 1

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python3 playlist_import_ytdlp.py <playlist_url>", file=sys.stderr)
        sys.exit(1)
    
    url = sys.argv[1]
    sys.exit(import_playlist_ytdlp(url)) 