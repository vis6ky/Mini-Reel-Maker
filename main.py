from flask import Flask, request, jsonify
import subprocess
from datetime import datetime
import os
import logging
import tempfile

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

@app.route('/api/make-video', methods=['POST'])
def make_video():
    try:
        data = request.get_json(force=True)
        text = data.get("text", "Default caption for reel")
        app.logger.info(f"Received text: {text}")

        # Use temporary files to avoid collisions
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as audio_file, \
             tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as video_file:

            audio_path = audio_file.name
            video_path = video_file.name

            # 1️⃣ Generate audio from text safely
            subprocess.run(["espeak", text, "-w", audio_path], check=True)
            app.logger.info(f"Audio generated: {audio_path}")

            # 2️⃣ Generate video with text overlay safely
            # Use single quotes inside drawtext to avoid issues with special characters
            drawtext_filter = f"drawtext=text='{text}':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2:escape=1"
            subprocess.run([
                "ffmpeg",
                "-f", "lavfi", "-i", "color=c=blue:s=720x1280:d=10",
                "-vf", drawtext_filter,
                "-i", audio_path,
                "-shortest",
                "-c:v", "libx264", "-c:a", "aac",
                video_path,
                "-y"
            ], check=True)
            app.logger.info(f"Video generated: {video_path}")

            # 3️⃣ Upload video to transfer.sh
            upload_result = subprocess.check_output([
                "curl", "-s", "-F", f"file=@{video_path}", "https://transfer.sh/"
            ]).decode().strip()
            app.logger.info(f"Video uploaded: {upload_result}")

            # Clean up
            os.remove(audio_path)
            os.remove(video_path)

            return jsonify({"video_url": upload_result})

    except subprocess.CalledProcessError as e:
        app.logger.error(f"Subprocess failed: {e}")
        return jsonify({"error": "Subprocess failed", "details": str(e)}), 500
    except Exception as e:
        app.logger.exception("Unexpected error")
        return jsonify({"error": "Unexpected error", "details": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
