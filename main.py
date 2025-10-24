from flask import Flask, request, jsonify
import subprocess
from datetime import datetime
import os
import logging
import tempfile
import shlex
import traceback

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

def run_subprocess(cmd, description):
    """Run subprocess safely and log output."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        app.logger.info(f"{description} succeeded:\nstdout: {result.stdout}\nstderr: {result.stderr}")
    except subprocess.CalledProcessError as e:
        app.logger.error(f"{description} failed:\nstdout: {e.stdout}\nstderr: {e.stderr}")
        raise

@app.route('/api/make-video', methods=['POST'])
def make_video():
    try:
        data = request.get_json(force=True)
        text = data.get("text", "Default caption for reel")
        app.logger.info(f"Received text: {text}")

        # Use temporary files
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as audio_file, \
             tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as video_file:

            audio_path = audio_file.name
            video_path = video_file.name

            # 1️⃣ Generate audio from text (espeak)
            safe_text = shlex.quote(text)  # Escape special characters for shell
            run_subprocess(
                f"espeak {safe_text} -w {audio_path}",
                "espeak audio generation"
            )

            # 2️⃣ Generate video with text overlay (ffmpeg)
            drawtext_filter = f"drawtext=text='{text}':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2:escape=1"
            ffmpeg_cmd = [
                "ffmpeg",
                "-f", "lavfi", "-i", "color=c=blue:s=720x1280:d=10",
                "-vf", drawtext_filter,
                "-i", audio_path,
                "-shortest",
                "-c:v", "libx264",
                "-c:a", "aac",
                video_path,
                "-y"
            ]
            run_subprocess(ffmpeg_cmd, "ffmpeg video generation")

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
        return jsonify({
            "error": "Subprocess failed",
            "command": e.cmd,
            "returncode": e.returncode,
            "stdout": e.stdout or "",
            "stderr": e.stderr or ""
        }), 500

    except Exception as e:
        tb = traceback.format_exc()
        return jsonify({
            "error": "Unexpected error",
            "details": str(e),
            "traceback": tb
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
