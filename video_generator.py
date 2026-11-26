import os
import re
import shutil
import subprocess
import tempfile
from typing import Dict, Optional


def build_prompt_and_script(topic: str, style: str = "explainer", duration: int = 6) -> Dict[str, object]:
    clean_topic = " ".join(topic.strip().split()) or "3D Visual Scene"
    clean_style = style.strip().lower()
    sec = max(3, min(int(duration), 60))

    if clean_style in {"pov", "action", "gaming"}:
        video_prompt = (
            f"First-person POV shot looking at {clean_topic}; sudden dynamic motion, "
            f"cinematic camera movement, sharp lighting, high detail, smooth {sec}s clip."
        )
        voice_script = (
            f"Boss, dekhiye {clean_topic} ka POV action scene—pehle setup, phir achanak movement aur timing."
        )
    else:
        video_prompt = (
            f"Clear visual explainer scene showing {clean_topic}; clean framing, "
            f"smooth camera pan, well-lit readable layout, {sec}s duration."
        )
        voice_script = (
            f"Boss, aaj {clean_topic} ko aasan bhasha mein samajhte hain—mukhya points aur kaaran step by step."
        )

    return {
        "topic": clean_topic,
        "style": clean_style,
        "duration": sec,
        "video_prompt": video_prompt,
        "voice_script": voice_script,
    }


def _has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def _safe_filename(name: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9_-]+", "_", name.strip()).strip("_")
    return base[:40] or "kaili_video"


def generate_smooth_video(
    topic: str,
    output_path: Optional[str] = None,
    style: str = "explainer",
    duration: int = 6,
    voice_audio_path: Optional[str] = None,
    bg_color: str = "0x101828",
    resolution: str = "720x1280",
) -> Dict[str, object]:
    pack = build_prompt_and_script(topic=topic, style=style, duration=duration)
    sec = int(pack["duration"])

    if not _has_ffmpeg():
        return {
            "ok": False,
            "error": "ffmpeg not installed. Install with: pkg install ffmpeg",
            "pack": pack,
        }

    if output_path:
        final_path = os.path.abspath(output_path)
        out_dir = os.path.dirname(final_path) or "."
    else:
        out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "renders")
        final_path = os.path.join(out_dir, f"{_safe_filename(topic)}.mp4")

    os.makedirs(out_dir, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".render_", suffix=".mp4", dir=out_dir)
    os.close(fd)
    if os.path.exists(tmp_path):
        os.remove(tmp_path)

    has_valid_voice = bool(voice_audio_path and os.path.isfile(voice_audio_path) and os.path.getsize(voice_audio_path) > 0)

    if has_valid_voice:
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c={bg_color}:s={resolution}:r=30:d={sec}",
            "-i", os.path.abspath(voice_audio_path),
            "-filter_complex", "[1:a]aresample=async=1,apad[aout]",
            "-map", "0:v:0", "-map", "[aout]",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            "-shortest",
            tmp_path,
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c={bg_color}:s={resolution}:r=30:d={sec}",
            "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo:d={sec}",
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            "-shortest",
            tmp_path,
        ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if proc.returncode != 0 or not os.path.exists(tmp_path) or os.path.getsize(tmp_path) == 0:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            return {
                "ok": False,
                "error": "ffmpeg render failed",
                "stderr_tail": (proc.stderr or "")[-400:],
                "pack": pack,
            }

        os.replace(tmp_path, final_path)
        return {
            "ok": True,
            "output_path": final_path,
            "size_bytes": os.path.getsize(final_path),
            "used_voice_file": voice_audio_path if has_valid_voice else None,
            "pack": pack,
        }
    except Exception as exc:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        return {"ok": False, "error": str(exc), "pack": pack}


if __name__ == "__main__":
    result = generate_smooth_video(
        topic="POV Controller Truck Action",
        style="pov",
        duration=4,
    )
    print(result)
