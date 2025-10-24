from flask import Flask, request, jsonify
import subprocess
from datetime import datetime
import shlex
import logging
import os

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

@app.route('/api/make-video', methods=['POST'])
def make_video():
    try:
        data = request.get_json(force=True)
        text = data.get("text", "Default caption for reel")
        app.logger.info(f"Received text: {text}")

        # Escape text for ffmpeg drawtext
        escaped_text = shlex.quote(text)
        filename = f"reel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        audio_file = "audio.wav"

        # Generate audio from text
        subprocess.run(["espeak", text, "-w", audio_file], check=True)
        app.logger.info("Audio generated successfully.")

        # Create video with colored background and text overlay
        ffmpeg_cmd = [
            "ffmpeg",
            "-f", "lavfi", "-i", "color=c=blue:s=720x1280:d=10",
            "-vf", f"drawtext=text={escaped_text}:fontcolor=white:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2",
            "-i", audio_file,
            "-shortest",
            "-c:v", "libx264", "-c:a", "aac",
            filename,
            "-y"
        ]
        subprocess.run(ffmpeg_cmd, check=True)
        app.logger.info("Video generated successfully.")

        # Upload video to transfer.sh
        upload_result = subprocess.check_output([
            "curl",
            "-F", f"file=@{filename}",
            "https://transfer.sh/"
        ]).decode().strip()
        app.logger.info(f"Video uploaded successfully: {upload_result}")

        # Clean up local files
        if os.path.exists(audio_file):
            os.remove(audio_file)
        if os.path.exists(filename):
            os.remove(filename)

        return jsonify({"video_url": upload_result})

    except subprocess.CalledProcessError as e:
        app.logger.error(f"Subprocess error: {e}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        app.logger.error(f"Unexpected error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
