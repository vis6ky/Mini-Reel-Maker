from flask import Flask, request, jsonify
import subprocess
from datetime import datetime

app = Flask(__name__)

@app.route('/api/make-video', methods=['POST'])
def make_video():
    data = request.get_json()
    text = data.get("text", "Default caption for reel")
    filename = f"reel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"

    try:
        # Generate audio from text
        subprocess.run(["espeak", text, "-w", "audio.wav"], check=True)

        # Create a simple video with colored background and text overlay
        subprocess.run([
            "ffmpeg",
            "-f", "lavfi", "-i", "color=c=blue:s=720x1280:d=10",
            "-vf", f"drawtext=text='{text}':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2",
            "-i", "audio.wav",
            "-shortest",
            "-c:v", "libx264", "-c:a", "aac",
            filename,
            "-y"
        ], check=True)

        # Upload video to free file host
        upload_result = subprocess.check_output([
            "curl",
            "-F", f"file=@{filename}",
            "https://transfer.sh/"
        ]).decode().strip()

        return jsonify({"video_url": upload_result})

    except subprocess.CalledProcessError as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
