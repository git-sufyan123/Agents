

import os
import json
import base64
import shutil
import platform
import subprocess
import tempfile

from flask import Flask, request, send_file, jsonify


app = Flask(__name__)

_DEFAULT_FONTS = {
    "Windows": "C:/Windows/Fonts/arialbd.ttf",
    "Darwin": "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
}
FONT_PATH = os.environ.get(
    "CAPTION_FONT",
    _DEFAULT_FONTS.get(platform.system(), "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
)


def escape_path_for_filter(path):
    """FFmpeg's filter syntax uses ':' as an option separator, which collides
    with Windows drive letters (C:) and any ':' in a path. Escape them and
    normalize slashes so the fontfile option parses correctly on every OS."""
    return path.replace("\\", "/").replace(":", "\\:")


def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError("ffmpeg failed:\n" + result.stderr[-3000:])


def get_duration(path):
    out = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            path,
        ],
        capture_output=True, text=True,
    )
    return float(out.stdout.strip())


def escape_drawtext(text):
    return (
        text.replace("\\", "\\\\")
        .replace("'", "\u2019")   
        .replace(":", "\\:")
        .replace("%", "\\%")
    )


@app.route("/health")
def health():
    return {"status": "ok"}


@app.route("/tts", methods=["POST"])
def tts():
    data = request.get_json(force=True, silent=True) or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "missing 'text' field in JSON body"}), 400

    workdir = tempfile.mkdtemp(prefix="tts_")
    try:
        out_path = os.path.join(workdir, "narration.mp3")
        gTTS(text=text, lang=data.get("lang", "en"), slow=False).save(out_path)
        return send_file(out_path, mimetype="audio/mpeg", as_attachment=True, download_name="narration.mp3")
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


@app.route("/build", methods=["POST"])
def build():
    workdir = tempfile.mkdtemp(prefix="short_")
    try:
        data = request.get_json(force=True, silent=True)
        if not data:
            return jsonify({"error": "expected a JSON body"}), 400

        audio_b64 = data.get("audio_base64")
        images_b64 = data.get("images")
        scenes = data.get("scenes")
        captions_text = data.get("captions_text", "")

        if not audio_b64:
            return jsonify({"error": "missing 'audio_base64'"}), 400
        if not images_b64 or not scenes:
            return jsonify({"error": "missing 'images' or 'scenes'"}), 400
        if len(images_b64) != len(scenes):
            return jsonify({
                "error": f"got {len(images_b64)} images but {len(scenes)} scenes — these must match 1:1"
            }), 400

        audio_path = os.path.join(workdir, "audio.mp3")
        with open(audio_path, "wb") as f:
            f.write(base64.b64decode(audio_b64))
        audio_duration = get_duration(audio_path)

        raw_total = sum(float(s.get("duration_seconds", 5)) for s in scenes) or 1
        scale = audio_duration / raw_total

        words = captions_text.split()
        chunks, idx = [], 0
        for s in scenes:
            n_words = max(1, round(len(words) * (float(s.get("duration_seconds", 5)) / raw_total)))
            chunks.append(" ".join(words[idx: idx + n_words]))
            idx += n_words
        if idx < len(words) and chunks:
            chunks[-1] += " " + " ".join(words[idx:])

        fps = 30
        segment_paths = []
        for i, (img_b64, scene, caption) in enumerate(zip(images_b64, scenes, chunks)):
            img_path = os.path.join(workdir, f"img_{i}.png")
            with open(img_path, "wb") as f:
                f.write(base64.b64decode(img_b64))

            dur = max(0.5, round(float(scene.get("duration_seconds", 5)) * scale, 2))
            frames = max(1, int(dur * fps))
            seg_path = os.path.join(workdir, f"seg_{i}.mp4")
            cap = escape_drawtext(caption)

            vf = (
                "scale=1080:1920:force_original_aspect_ratio=increase,"
                "crop=1080:1920,"
                f"zoompan=z='min(zoom+0.0008,1.15)':d={frames}:s=1080x1920:fps={fps},"
                f"drawtext=text='{cap}':fontfile='{escape_path_for_filter(FONT_PATH)}':fontcolor=white:fontsize=52:"
                "line_spacing=6:box=1:boxcolor=black@0.55:boxborderw=20:"
                "x=(w-text_w)/2:y=h-280"
            )

            run([
                "ffmpeg", "-y", "-loop", "1", "-i", img_path,
                "-t", str(dur), "-vf", vf,
                "-c:v", "libx264", "-pix_fmt", "yuv420p", seg_path,
            ])
            segment_paths.append(seg_path)

        concat_list = os.path.join(workdir, "concat.txt")
        with open(concat_list, "w") as f:
            for p in segment_paths:
                f.write(f"file '{p}'\n")

        video_only = os.path.join(workdir, "video_only.mp4")
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list, "-c", "copy", video_only])

        final_path = os.path.join(workdir, "final.mp4")
        run([
            "ffmpeg", "-y", "-i", video_only, "-i", audio_path,
            "-c:v", "copy", "-c:a", "aac", "-shortest", final_path,
        ])

        return send_file(final_path, mimetype="video/mp4", as_attachment=True, download_name="short.mp4")

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)