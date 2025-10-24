from flask import Flask, request, jsonify
import subprocess
import tempfile
import os
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

def run_subprocess(cmd, description):
    """Run subprocess safely and log output."""
    try:
        app.logger.info(f"Running {description}: {cmd}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        app.logger.info(f"{description} succeeded:\nstdout: {result.stdout}\nstderr: {result.stderr}")
    except subprocess.CalledProcessError as e:
        app.logger.error(f"{description} failed:\nstdout: {e.stdout}\nstderr: {e.stderr}")
        raise

@app.route("/api/make-video", methods=["POST"])
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

            # 1️⃣ Generate audio with espeak
            run_subprocess(
                ["espeak", text, "-w", audio_path],
                "espeak audio generation"
            )

            # 2️⃣ Generate video with ffmpeg and text overlay
            drawtext_filter = (
                f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
                f"text='{text}':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2:escape=1"
            )
            ffmpeg_cmd = [
                "ffmpeg",
                "-f", "lavfi", "-i", "color=c=blue:s=720x1280:d=10",
                "-i", audio_path,
                "-vf", drawtext_filter,
                "-shortest",
                "-c:v", "libx264",
                "-c:a", "aac",
                "-y",
                video_path
            ]
            run_subprocess(ffmpeg_cmd, "ffmpeg video generation")

            # 3️⃣ Upload video to transfer.sh
            upload_result = subprocess.check_output([
                "curl", "-s", "-F", f"file=@{video_path}", "https://transfer.sh/"
            ]).decode().strip()
            app.logger.info(f"Video uploaded: {upload_result}")

            # Clean up temp files
            os.remove(audio_path)
            os.remove(video_path)

            return jsonify({"video_url": upload_result})

    except subprocess.CalledProcessError as e:
        return jsonify({
            "error": "Subprocess failed",
            "stdout": e.stdout,
            "stderr": e.stderr
        }), 500
    except Exception as e:
        app.logger.exception("Unexpected error")
        return jsonify({"error": "Unexpected error", "details": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
