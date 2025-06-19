import sys
import json
from pytube import Search
import time

def search_videos(query):
    try:
        # Add retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Use pytube to search for videos
                search = Search(query)
                
                # Force fetch of results
                search.results
                
                # Wait a bit if we need to retry
                if not search.results and attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                
                videos = []
                
                # Get first 10 results
                for video in search.results[:10]:
                    if video and hasattr(video, 'video_id'):
                        videos.append({
                            'id': video.video_id,
                            'title': video.title,
                            'channel': video.author,
                            'thumbnail': f'https://img.youtube.com/vi/{video.video_id}/mqdefault.jpg'
                        })
                
                # If we have at least one result, return it
                if videos:
                    print(json.dumps(videos))
                    return 0
                
                # If this was our last attempt and we have no results
                if attempt == max_retries - 1:
                    print(json.dumps([]))
                    return 0
                    
            except Exception as e:
                # If this was our last attempt, raise the error
                if attempt == max_retries - 1:
                    raise e
                time.sleep(1)
                
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        return 1

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python3 search.py "search query"', file=sys.stderr)
        sys.exit(1)
    
    query = sys.argv[1]
    sys.exit(search_videos(query)) 