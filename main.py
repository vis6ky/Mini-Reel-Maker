from flask import Flask, request, jsonify
import subprocess
import tempfile
import os
import logging
import shlex

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

def run_subprocess(cmd, description):
    """Run subprocess safely and log output."""
    try:
        app.logger.info(f"Running {description}: {' '.join(cmd)}")
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
            # Note: espeak expects -w before the text
            run_subprocess(
                ["espeak", "-w", audio_path, text],
                "espeak audio generation"
            )

            # 2️⃣ Get audio duration
            audio_duration = float(subprocess.check_output([
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                audio_path
            ]).decode().strip())
            app.logger.info(f"Audio duration: {audio_duration}s")

            # 3️⃣ Generate video with ffmpeg and text overlay
            font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            safe_text = text.replace("'", r"\'")  # escape single quotes for ffmpeg
            drawtext_filter = (
                f"drawtext=fontfile={font_path}:text='{safe_text}':"
                "fontcolor=white:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2:escape=1"
            )

            ffmpeg_cmd = [
                "ffmpeg",
                "-f", "lavfi", f"-i", f"color=c=blue:s=720x1280:d={audio_duration}",
                "-i", audio_path,
                "-vf", drawtext_filter,
                "-shortest",
                "-c:v", "libx264",
                "-c:a", "aac",
                "-y",
                video_path
            ]
            run_subprocess(ffmpeg_cmd, "ffmpeg video generation")

            # 4️⃣ Upload video to transfer.sh
            upload_result = subprocess.check_output([
                "curl", "-s", "-F", f"file=@{video_path}", "https://transfer.sh/"
            ]).decode().strip()
            app.logger.info(f"Video uploaded: {upload_result}")

            # 5️⃣ Clean up temp files
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
