import sys
import subprocess
import json

def download_mp3(video_id):
    try:
        # Use yt-dlp to download and convert to MP3
        cmd = [
            'yt-dlp',
            f'https://www.youtube.com/watch?v={video_id}',
            '-f', 'bestaudio/best',
            '-o', '-',
            '--no-playlist',
            '--no-warnings',
            '--extract-audio',
            '--audio-format', 'mp3',
            '--audio-quality', '192K'  # Good quality for sharing
        ]
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Stream the MP3 data to stdout
        while True:
            chunk = process.stdout.read(8192)
            if not chunk:
                break
            sys.stdout.buffer.write(chunk)
            sys.stdout.buffer.flush()
            
        # Check for errors
        stderr = process.stderr.read().decode()
        if stderr and 'WARNING' not in stderr:
            print(f"Download error: {stderr}", file=sys.stderr)
            
        return process.returncode
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        return 1

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python3 download_mp3.py video_id', file=sys.stderr)
        sys.exit(1)
    
    video_id = sys.argv[1]
    sys.exit(download_mp3(video_id)) 