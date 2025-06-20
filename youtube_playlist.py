#!/usr/bin/env python3
import sys
import json
import subprocess
import re
import urllib.parse
import urllib.request
import time

def extract_playlist_id(url):
    """Extract playlist ID from various YouTube URL formats"""
    patterns = [
        r'[&?]list=([^&]+)',
        r'playlist\?list=([^&]+)',
        r'music\.youtube\.com.*[&?]list=([^&]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    raise ValueError("Could not extract playlist ID from URL")

def get_playlist_with_ytdlp(url, playlist_id):
    """Get playlist using yt-dlp command line tool"""
    try:
        print(f"🎵 Getting playlist info with yt-dlp...", file=sys.stderr)
        
        # Get playlist metadata
        meta_cmd = [
            'yt-dlp', '--flat-playlist', '--no-warnings',
            '--print', '%(playlist_title)s|||%(playlist_uploader)s|||%(playlist_id)s',
            '--playlist-items', '1',
            url
        ]
        
        meta_result = subprocess.run(meta_cmd, capture_output=True, text=True, timeout=15)
        
        playlist_title = "YouTube Playlist"
        playlist_author = "Unknown"
        
        if meta_result.returncode == 0 and meta_result.stdout.strip():
            meta_parts = meta_result.stdout.strip().split('|||')
            if len(meta_parts) >= 2:
                playlist_title = meta_parts[0] or "YouTube Playlist"
                playlist_author = meta_parts[1] or "Unknown"
        
        print(f"📋 Playlist: {playlist_title} by {playlist_author}", file=sys.stderr)
        
        # Get video list
        videos_cmd = [
            'yt-dlp', '--flat-playlist', '--no-warnings',
            '--print', '%(id)s|||%(title)s|||%(uploader)s|||%(duration_string)s',
            '--playlist-items', '1:50',  # Limit to 50 videos
            url
        ]
        
        videos_result = subprocess.run(videos_cmd, capture_output=True, text=True, timeout=30)
        
        if videos_result.returncode != 0:
            raise Exception(f"yt-dlp failed: {videos_result.stderr}")
        
        lines = [line.strip() for line in videos_result.stdout.strip().split('\n') if line.strip()]
        
        if not lines:
            raise Exception("No videos found in playlist")
        
        print(f"🎬 Found {len(lines)} videos", file=sys.stderr)
        
        tracks = []
        for i, line in enumerate(lines):
            parts = line.split('|||')
            if len(parts) >= 2:
                video_id = parts[0].strip()
                title = parts[1].strip()
                uploader = parts[2].strip() if len(parts) > 2 else "Unknown Channel"
                duration = parts[3].strip() if len(parts) > 3 else "Unknown"
                
                if video_id and title and video_id != 'NA':
                    track = {
                        'id': video_id,
                        'title': title,
                        'thumbnail': f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg",
                        'channel': uploader,
                        'duration': duration
                    }
                    tracks.append(track)
                    print(f"✅ {i+1}. {title}", file=sys.stderr)
        
        if not tracks:
            raise Exception("No valid videos found")
        
        return {
            'id': playlist_id,
            'name': playlist_title,
            'description': f"by {playlist_author}",
            'isYouTube': True,
            'author': playlist_author,
            'coverImage': f"https://img.youtube.com/vi/{tracks[0]['id']}/mqdefault.jpg" if tracks else None,
            'tracks': tracks
        }
        
    except subprocess.TimeoutExpired:
        raise Exception("yt-dlp command timed out")
    except Exception as e:
        raise Exception(f"yt-dlp failed: {str(e)}")

def get_playlist_with_direct_scraping(url, playlist_id):
    """Fallback method using direct YouTube page scraping"""
    try:
        print(f"🔍 Trying direct YouTube scraping...", file=sys.stderr)
        
        # Create a simple HTTP request to get the playlist page
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        req = urllib.request.Request(url, headers=headers)
        
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8')
        
        # Extract playlist title
        title_match = re.search(r'"title":"([^"]+)".*?"ownerText"', html)
        playlist_title = title_match.group(1) if title_match else "YouTube Playlist"
        
        # Extract playlist author
        author_match = re.search(r'"ownerText":{"runs":\[{"text":"([^"]+)"', html)
        playlist_author = author_match.group(1) if author_match else "Unknown"
        
        # Extract video IDs and titles
        video_pattern = r'"videoId":"([^"]+)".*?"title":{"runs":\[{"text":"([^"]+)"'
        video_matches = re.findall(video_pattern, html)
        
        if not video_matches:
            # Try alternative pattern
            video_pattern = r'"videoId":"([^"]+)".*?"simpleText":"([^"]+)"'
            video_matches = re.findall(video_pattern, html)
        
        if not video_matches:
            raise Exception("Could not extract video information from page")
        
        print(f"📋 Playlist: {playlist_title} by {playlist_author}", file=sys.stderr)
        print(f"🎬 Found {len(video_matches)} videos", file=sys.stderr)
        
        tracks = []
        for i, (video_id, title) in enumerate(video_matches[:50]):  # Limit to 50
            if video_id and title:
                track = {
                    'id': video_id,
                    'title': title,
                    'thumbnail': f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg",
                    'channel': playlist_author,
                    'duration': "Unknown"
                }
                tracks.append(track)
                print(f"✅ {i+1}. {title}", file=sys.stderr)
        
        if not tracks:
            raise Exception("No valid videos found")
        
        return {
            'id': playlist_id,
            'name': playlist_title,
            'description': f"by {playlist_author}",
            'isYouTube': True,
            'author': playlist_author,
            'coverImage': f"https://img.youtube.com/vi/{tracks[0]['id']}/mqdefault.jpg",
            'tracks': tracks
        }
        
    except Exception as e:
        raise Exception(f"Direct scraping failed: {str(e)}")

def import_youtube_playlist(url):
    """Main function to import YouTube playlist with multiple fallback methods"""
    try:
        print(f"🚀 Starting YouTube playlist import", file=sys.stderr)
        print(f"🔗 URL: {url}", file=sys.stderr)
        
        # Extract playlist ID
        playlist_id = extract_playlist_id(url)
        print(f"🆔 Playlist ID: {playlist_id}", file=sys.stderr)
        
        # Method 1: Try yt-dlp
        try:
            result = get_playlist_with_ytdlp(url, playlist_id)
            print(f"🎉 Success with yt-dlp! {len(result['tracks'])} tracks imported", file=sys.stderr)
            return result
        except Exception as e:
            print(f"❌ yt-dlp failed: {str(e)}", file=sys.stderr)
        
        # Method 2: Try direct scraping
        try:
            result = get_playlist_with_direct_scraping(url, playlist_id)
            print(f"🎉 Success with direct scraping! {len(result['tracks'])} tracks imported", file=sys.stderr)
            return result
        except Exception as e:
            print(f"❌ Direct scraping failed: {str(e)}", file=sys.stderr)
        
        raise Exception("All import methods failed")
        
    except Exception as e:
        print(f"💥 Import failed: {str(e)}", file=sys.stderr)
        return None

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 youtube_playlist.py <playlist_url>", file=sys.stderr)
        sys.exit(1)
    
    url = sys.argv[1]
    result = import_youtube_playlist(url)
    
    if result:
        print(json.dumps(result))
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == '__main__':
    main() 