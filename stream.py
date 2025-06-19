import sys
import subprocess
import json

def stream_audio(video_id):
    try:
        # Use yt-dlp to stream audio directly
        cmd = [
            'yt-dlp',
            f'https://www.youtube.com/watch?v={video_id}',
            '-f', 'bestaudio[ext=m4a]/bestaudio/best',  # Try m4a first, then best audio, then best available
            '-o', '-',
            '--no-playlist',
            '--no-warnings',  # Reduce noise in stderr
            '--extract-audio',
            '--audio-format', 'm4a',
            '--audio-quality', '0'  # Best quality
        ]
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Stream the audio data
        while True:
            chunk = process.stdout.read(8192)
            if not chunk:
                break
            sys.stdout.buffer.write(chunk)
            sys.stdout.buffer.flush()
            
        # Check for errors
        stderr = process.stderr.read().decode()
        if stderr:
            print(f"Streaming error: {stderr}", file=sys.stderr)
            
        return process.returncode
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        return 1

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: python3 stream.py video_id', file=sys.stderr)
        sys.exit(1)
    
    video_id = sys.argv[1]
    sys.exit(stream_audio(video_id)) 