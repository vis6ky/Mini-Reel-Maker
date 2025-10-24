from flask import Flask, request, jsonify
import subprocess
from datetime import datetime
import os
import logging
import tempfile
import shlex
import re
import traceback

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# ------------------------------
# Helpers
# ------------------------------

def escape_ffmpeg_text(s: str) -> str:
    """
    Escape characters that break ffmpeg drawtext filters.
    Handles quotes, colons, hashtags, and backslashes.
    """
    return re.sub(r"([\\':#])", r"\\\1", s)

def run_subprocess(cmd, description):
    """
    Run subprocess safely and log stdout/stderr.
    Works for both list and string commands.
    """
    shell = isinstance(cmd, str)
    app.logger.info(f"Running command ({description}): {cmd}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, shell=shell)
        app.logger.info(f"{description} succeeded:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")
        return result
    except subprocess.CalledProcessError as e:
        app.logger.error(f"{description} failed:\nCommand: {cmd}\nReturn code: {e.returncode}\nstdout:\n{e.stdout}\nstderr:\n{e.stderr}")
        raise

# ------------------------------
# Main API Route
# ------------------------------

@app.route('/api/make-video', methods=['POST'])
def make_video():
    try:
        data = request.get_json(force=True)
        text = data.get("text", "Default caption for reel")
        app.logger.info(f"Received text: {text}")

        # Temporary file setup
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as audio_file, \
             tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as video_file:

            audio_path = audio_file.name
            video_path = video_file.name

            # 1️⃣ Generate audio with espeak
            safe_text_shell = shlex.quote(text)
            run_subprocess(
                f"espeak {safe_text_shell} -w {audio_path}",
                "espeak audio generation"
            )

            # 2️⃣ Generate video with ffmpeg
            safe_text_ffmpeg = escape_ffmpeg_text(text)
            drawtext_filter = (
                f"drawtext=text='{safe_text_ffmpeg}':"
                f"fontcolor=white:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2:escape=1"
            )
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

            # 3️⃣ Upload to transfer.sh
            upload_result = subprocess.check_output(
                ["curl", "-s", "-F", f"file=@{video_path}", "https://transfer.sh/"]
            ).decode().strip()
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
        app.logger.error(f"Unexpected error: {e}\n{tb}")
        return jsonify({
            "error": "Unexpected error",
            "details": str(e),
            "traceback": tb
        }), 500

# ------------------------------
# Global fallback error handler
# ------------------------------

@app.errorhandler(Exception)
def handle_exception(e):
    tb = traceback.format_exc()
    response = jsonify({
        "error": "Internal Server Error",
        "type": type(e).__name__,
        "message": str(e),
        "traceback": tb
    })
    response.status_code = 500
    return response

# ------------------------------
# Entry Point
# ------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
