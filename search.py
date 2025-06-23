import sys
import json
from pytube import Search
import time

def search_videos(query):
    try:
        print(f"🔍 Searching for: {query}", file=sys.stderr)
        
        # Add retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"📡 Attempt {attempt + 1}/{max_retries}", file=sys.stderr)
                
                # Use pytube to search for videos
                search = Search(query)
                
                # Force fetch of results
                search.results
                
                # Wait a bit if we need to retry
                if not search.results and attempt < max_retries - 1:
                    print("⏳ No results, retrying...", file=sys.stderr)
                    time.sleep(2)
                    continue
                
                videos = []
                
                # Get first 10 results
                for video in search.results[:10]:
                    if video and hasattr(video, 'video_id'):
                        try:
                        videos.append({
                            'id': video.video_id,
                                'title': video.title or 'Untitled',
                                'channel': video.author or 'Unknown Channel',
                            'thumbnail': f'https://img.youtube.com/vi/{video.video_id}/mqdefault.jpg'
                        })
                        except Exception as video_error:
                            print(f"⚠️ Skipping video due to error: {video_error}", file=sys.stderr)
                            continue
                
                print(f"✅ Found {len(videos)} valid videos", file=sys.stderr)
                
                # If we have at least one result, return it
                if videos:
                    print(json.dumps(videos))
                    return 0
                
                # If this was our last attempt and we have no results
                if attempt == max_retries - 1:
                    print("🚫 No results found after all attempts", file=sys.stderr)
                    print(json.dumps([]))
                    return 0
                    
            except Exception as e:
                print(f"❌ Attempt {attempt + 1} failed: {str(e)}", file=sys.stderr)
                # If this was our last attempt, raise the error
                if attempt == max_retries - 1:
                    raise e
                time.sleep(2)
                
    except Exception as e:
        print(f"💥 Search failed: {str(e)}", file=sys.stderr)
        # Return empty results instead of error to prevent frontend crashes
        print(json.dumps([]))
        return 0

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python3 search.py "search query"', file=sys.stderr)
        sys.exit(1)
    
    query = sys.argv[1]
    sys.exit(search_videos(query)) 