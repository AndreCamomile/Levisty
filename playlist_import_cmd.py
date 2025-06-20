#!/usr/bin/env python3
import sys
import json
import subprocess
import re

def import_playlist_cmd(url):
    """Import YouTube playlist using yt-dlp command line tool"""
    try:
        print(f"Starting yt-dlp command line import for URL: {url}", file=sys.stderr)
        
        # Run yt-dlp to get playlist info and video list
        cmd = [
            'yt-dlp',
            '--flat-playlist',
            '--print', '%(id)s\t%(title)s\t%(uploader)s\t%(duration_string)s',
            '--playlist-items', '1:50',  # Limit to first 50 items
            url
        ]
        
        print(f"Running command: {' '.join(cmd)}", file=sys.stderr)
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            raise Exception(f"yt-dlp command failed: {result.stderr}")
        
        lines = result.stdout.strip().split('\n')
        if not lines or not lines[0]:
            raise Exception("No videos found in playlist")
        
        print(f"Found {len(lines)} videos", file=sys.stderr)
        
        # Get playlist metadata with a separate command
        meta_cmd = [
            'yt-dlp',
            '--flat-playlist',
            '--print', '%(playlist_title)s\t%(playlist_uploader)s\t%(playlist_id)s',
            '--playlist-items', '1',
            url
        ]
        
        meta_result = subprocess.run(meta_cmd, capture_output=True, text=True, timeout=10)
        
        playlist_title = "YouTube Playlist"
        playlist_author = "Unknown"
        playlist_id = "unknown"
        
        if meta_result.returncode == 0 and meta_result.stdout.strip():
            meta_parts = meta_result.stdout.strip().split('\t')
            if len(meta_parts) >= 3:
                playlist_title = meta_parts[0] or "YouTube Playlist"
                playlist_author = meta_parts[1] or "Unknown"
                playlist_id = meta_parts[2] or "unknown"
        
        print(f"Playlist: {playlist_title} by {playlist_author}", file=sys.stderr)
        
        # Format playlist data
        formatted_playlist = {
            'id': playlist_id,
            'name': playlist_title,
            'description': f"by {playlist_author}",
            'isYouTube': True,
            'author': playlist_author,
            'coverImage': None,
            'tracks': []
        }
        
        # Parse video data
        for line in lines:
            parts = line.split('\t')
            if len(parts) >= 2:
                video_id = parts[0].strip()
                title = parts[1].strip()
                uploader = parts[2].strip() if len(parts) > 2 else "Unknown Channel"
                duration = parts[3].strip() if len(parts) > 3 else "Unknown"
                
                if video_id and title:
                    track = {
                        'id': video_id,
                        'title': title,
                        'thumbnail': f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg",
                        'channel': uploader,
                        'duration': duration
                    }
                    formatted_playlist['tracks'].append(track)
                    print(f"Added track: {video_id} - {title}", file=sys.stderr)
        
        if not formatted_playlist['tracks']:
            raise Exception("No valid videos found in playlist")
        
        print(f"Successfully formatted {len(formatted_playlist['tracks'])} tracks", file=sys.stderr)
        print(json.dumps(formatted_playlist))
        return 0
        
    except subprocess.TimeoutExpired:
        print("yt-dlp command timed out", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"yt-dlp command line import error: {str(e)}", file=sys.stderr)
        return 1

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python3 playlist_import_cmd.py <playlist_url>", file=sys.stderr)
        sys.exit(1)
    
    url = sys.argv[1]
    sys.exit(import_playlist_cmd(url)) 