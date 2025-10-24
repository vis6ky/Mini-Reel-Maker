from flask import Flask, request, jsonify
import subprocess
import tempfile
import shlex
import os

app = Flask(__name__)

def run_subprocess(cmd, description):
    """Run subprocess safely and log output."""
    try:
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

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as audio_file, \
             tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as video_file:

            audio_path = audio_file.name
            video_path = video_file.name

            # Generate audio from text using espeak
            safe_text = shlex.quote(text)
            run_subprocess(
                ["espeak", text, "-w", audio_path],
                "espeak audio generation"
            )

            # Generate video with text overlay
            drawtext_filter = f"drawtext=text='{text}':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2:escape=1"
            ffmpeg_cmd = [
                "ffmpeg",
                "-f", "lavfi", "-i", "color=c=blue:s=720x1280:d=10",
                "-vf", drawtext_filter,
                "-i", audio_path,
                "-shortest",
                "-c:v", "libx264",
                "-c:a", "aac",
                "-y",  # overwrite output
                video_path
            ]
            run_subprocess(ffmpeg_cmd, "ffmpeg video generation")

            return jsonify({"video_path": video_path})

    except Exception as e:
        app.logger.exception("Unexpected error")
        return jsonify({"error": "Unexpected error", "details": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
