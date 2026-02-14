import os
import subprocess
import json
import re
from flask import Flask, render_template, request, Response, stream_with_context

app = Flask(__name__)

def sanitize_filename(title):
    """Remove unsafe characters from filename."""
    return re.sub(r'[\\/*?:"<>|]', "", title)

def get_video_info(url):
    """Fetch video metadata using yt-dlp."""
    cmd = ['yt-dlp', '--dump-json', url]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception("Failed to fetch video info")
    return json.loads(result.stdout)

def stream_ytdlp_command(cmd, filename):
    """Stream yt-dlp output as a downloadable file."""
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1024*1024)

    def generate():
        while True:
            chunk = process.stdout.read(8192)
            if not chunk:
                break
            yield chunk

    headers = {
        'Content-Disposition': f'attachment; filename="{filename}"',
        'Content-Type': 'application/octet-stream'
    }
    return Response(stream_with_context(generate()), headers=headers)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    url = request.form.get('url')
    format_choice = request.form.get('format')

    if not url:
        return "Missing URL", 400

    try:
        info = get_video_info(url)
        title = sanitize_filename(info['title'])
    except Exception as e:
        return f"Error: {str(e)}", 500

    if format_choice == 'mp4':
        filename = f"{title}.mp4"
        cmd = ['yt-dlp', '-f', 'best', '-o', '-', url]
        return stream_ytdlp_command(cmd, filename)

    elif format_choice == 'mp3':
        filename = f"{title}.mp3"
        cmd = [
            'yt-dlp',
            '-f', 'bestaudio',
            '--extract-audio',
            '--audio-format', 'mp3',
            '-o', '-',
            url
        ]
        return stream_ytdlp_command(cmd, filename)

    else:
        return "Invalid format", 400

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
