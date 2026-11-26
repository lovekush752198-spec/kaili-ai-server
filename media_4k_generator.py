import os
import re
import shutil
import subprocess
import tempfile
from typing import Dict, Optional

CREATOR = "LAVKUSH KUMAR"
GREETING = "Boss"
RES_4K = "3840x2160"


def _slug(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", name.strip()).strip("_")
    return cleaned[:45] or "kaili_4k"


def _has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def generate_4k_photo(
    title: str,
    output_path: Optional[str] = None,
    bg_color: str = "0x0f172a",
    accent_color: str = "0x38bdf8",
) -> Dict[str, object]:
    if not _has_ffmpeg():
        return {"ok": False, "error": "ffmpeg not installed. Run: pkg install ffmpeg"}

    base_dir = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.dirname(os.path.abspath(output_path)) if output_path else os.path.join(base_dir, "renders_4k")
    final_path = os.path.abspath(output_path) if output_path else os.path.join(out_dir, f"{_slug(title)}_4k.png")
    os.makedirs(out_dir, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(prefix=".4k_img_", suffix=".png", dir=out_dir)
    os.close(fd)
    if os.path.exists(tmp_path):
        os.remove(tmp_path)

    # 4K (3840x2160) gradient + subtle border frame via lavfi
    vf_chain = (
        f"scale={RES_4K}:flags=lanczos,"
        f"drawbox=x=120:y=120:w=3600:h=1920:color={accent_color}@0.35:t=8"
    )
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c={bg_color}:s={RES_4K}:d=1",
        "-vf", vf_chain,
        "-frames:v", "1",
        tmp_path,
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if proc.returncode != 0 or not os.path.exists(tmp_path) or os.path.getsize(tmp_path) == 0:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            return {"ok": False, "error": "4K photo render failed", "stderr_tail": (proc.stderr or "")[-300:]}

        os.replace(tmp_path, final_path)
        return {
            "ok": True,
            "creator": CREATOR,
            "greeting": GREETING,
            "resolution": RES_4K,
            "title": title,
            "file": final_path,
            "size_bytes": os.path.getsize(final_path),
        }
    except Exception as exc:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        return {"ok": False, "error": str(exc)}


def generate_4k_video(
    topic: str,
    output_path: Optional[str] = None,
    duration: int = 4,
    fps: int = 24,
    audio_file: Optional[str] = None,
    bg_color: str = "0x0b1120",
) -> Dict[str, object]:
    if not _has_ffmpeg():
        return {"ok": False, "error": "ffmpeg not installed. Run: pkg install ffmpeg"}

    sec = max(2, min(int(duration), 30))
    frame_rate = max(15, min(int(fps), 30))
    base_dir = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.dirname(os.path.abspath(output_path)) if output_path else os.path.join(base_dir, "renders_4k")
    final_path = os.path.abspath(output_path) if output_path else os.path.join(out_dir, f"{_slug(topic)}_4k.mp4")
    os.makedirs(out_dir, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(prefix=".4k_vid_", suffix=".mp4", dir=out_dir)
    os.close(fd)
    if os.path.exists(tmp_path):
        os.remove(tmp_path)

    has_audio = bool(audio_file and os.path.isfile(audio_file) and os.path.getsize(audio_file) > 0)
    if has_audio:
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c={bg_color}:s={RES_4K}:r={frame_rate}:d={sec}",
            "-i", os.path.abspath(audio_file),
            "-filter_complex", "[1:a]aresample=async=1,apad[aout]",
            "-map", "0:v:0", "-map", "[aout]",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            "-shortest",
            tmp_path,
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c={bg_color}:s={RES_4K}:r={frame_rate}:d={sec}",
            "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo:d={sec}",
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            "-shortest",
            tmp_path,
        ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if proc.returncode != 0 or not os.path.exists(tmp_path) or os.path.getsize(tmp_path) == 0:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            return {"ok": False, "error": "4K video render failed", "stderr_tail": (proc.stderr or "")[-300:]}

        os.replace(tmp_path, final_path)
        return {
            "ok": True,
            "creator": CREATOR,
            "greeting": GREETING,
            "resolution": RES_4K,
            "topic": topic,
            "file": final_path,
            "size_bytes": os.path.getsize(final_path),
        }
    except Exception as exc:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        return {"ok": False, "error": str(exc)}


if __name__ == "__main__":
    print("4K Photo:", generate_4k_photo("KAILI 4K Frame"))
    print("4K Video:", generate_4k_video("KAILI 4K Clip", duration=3, fps=24))
