#!/usr/bin/env python3
import sys
import json
import subprocess
import re

def search_videos_ytdlp(query):
    """Search YouTube videos using yt-dlp"""
    try:
        print(f"🔍 Searching for: {query}", file=sys.stderr)
        
        # Use yt-dlp to search for videos
        cmd = [
            'yt-dlp',
            '--flat-playlist',
            '--no-warnings',
            '--print', '%(id)s|||%(title)s|||%(uploader)s|||%(duration_string)s',
            f'ytsearch10:{query}'  # Search for top 10 results
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        
        if result.returncode != 0:
            raise Exception(f"yt-dlp search failed: {result.stderr}")
        
        lines = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
        
        if not lines:
            print("🚫 No results found", file=sys.stderr)
            print(json.dumps([]))
            return 0
        
        print(f"✅ Found {len(lines)} results", file=sys.stderr)
        
        videos = []
        for line in lines:
            parts = line.split('|||')
            if len(parts) >= 2:
                video_id = parts[0].strip()
                title = parts[1].strip()
                channel = parts[2].strip() if len(parts) > 2 else "Unknown Channel"
                duration = parts[3].strip() if len(parts) > 3 else "Unknown"
                
                if video_id and title and video_id != 'NA':
                    video = {
                        'id': video_id,
                        'title': title,
                        'channel': channel,
                        'thumbnail': f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg",
                        'duration': duration
                    }
                    videos.append(video)
                    print(f"📹 {len(videos)}. {title} - {channel}", file=sys.stderr)
        
        if not videos:
            print("🚫 No valid videos found", file=sys.stderr)
            print(json.dumps([]))
            return 0
        
        print(json.dumps(videos))
        return 0
        
    except subprocess.TimeoutExpired:
        print("⏰ Search timed out", file=sys.stderr)
        print(json.dumps([]))
        return 1
    except Exception as e:
        print(f"💥 Search error: {str(e)}", file=sys.stderr)
        print(json.dumps([]))
        return 1

def search_videos_fallback(query):
    """Fallback search method using direct YouTube search URL scraping"""
    try:
        print(f"🔄 Trying fallback search for: {query}", file=sys.stderr)
        
        import urllib.parse
        import urllib.request
        
        # Create search URL
        encoded_query = urllib.parse.quote_plus(query)
        search_url = f"https://www.youtube.com/results?search_query={encoded_query}"
        
        # Create request with headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        req = urllib.request.Request(search_url, headers=headers)
        
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8')
        
        # Extract video IDs and titles using regex
        video_pattern = r'"videoId":"([^"]+)".*?"title":{"runs":\[{"text":"([^"]+)".*?"ownerText":{"runs":\[{"text":"([^"]+)"'
        matches = re.findall(video_pattern, html)
        
        if not matches:
            # Try alternative pattern
            video_pattern = r'"videoId":"([^"]+)".*?"simpleText":"([^"]+)"'
            matches = re.findall(video_pattern, html)
            matches = [(m[0], m[1], "Unknown Channel") for m in matches]
        
        if not matches:
            print("🚫 No videos found with fallback method", file=sys.stderr)
            print(json.dumps([]))
            return 0
        
        print(f"✅ Fallback found {len(matches)} results", file=sys.stderr)
        
        videos = []
        for video_id, title, channel in matches[:10]:  # Limit to 10 results
            if video_id and title:
                video = {
                    'id': video_id,
                    'title': title,
                    'channel': channel,
                    'thumbnail': f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg"
                }
                videos.append(video)
                print(f"📹 {len(videos)}. {title} - {channel}", file=sys.stderr)
        
        if not videos:
            print("🚫 No valid videos found with fallback", file=sys.stderr)
            print(json.dumps([]))
            return 0
        
        print(json.dumps(videos))
        return 0
        
    except Exception as e:
        print(f"💥 Fallback search error: {str(e)}", file=sys.stderr)
        print(json.dumps([]))
        return 1

def main():
    if len(sys.argv) != 2:
        print('Usage: python3 search_ytdlp.py "search query"', file=sys.stderr)
        sys.exit(1)
    
    query = sys.argv[1]
    
    # Try yt-dlp first
    try:
        result = search_videos_ytdlp(query)
        if result == 0:
            sys.exit(0)
    except Exception as e:
        print(f"❌ yt-dlp search failed: {str(e)}", file=sys.stderr)
    
    # Try fallback method
    try:
        result = search_videos_fallback(query)
        sys.exit(result)
    except Exception as e:
        print(f"❌ All search methods failed: {str(e)}", file=sys.stderr)
        print(json.dumps([]))
        sys.exit(1)

if __name__ == '__main__':
    main() 