import json
import os
import re
import shutil
import subprocess
import tempfile
from typing import Dict, Optional, Tuple

CREATOR = "LAVKUSH KUMAR"
GREETING = "Boss"


def atomic_write_json(path: str, payload: dict) -> None:
    folder = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(folder, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".atomic_", suffix=".json", dir=folder)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        raise


def smart_lookup(kb: Dict[str, str], query: str) -> Tuple[Optional[str], str]:
    q = " ".join(query.strip().lower().split())
    if q in kb:
        return kb[q], "exact"

    q_words = set(re.findall(r"[a-z0-9\u0900-\u097f]+", q))
    if not q_words:
        return None, "none"

    best_ans = None
    best_hits = 0
    for key, val in kb.items():
        k_words = set(re.findall(r"[a-z0-9\u0900-\u097f]+", key.lower()))
        hits = len(q_words.intersection(k_words))
        if hits > best_hits:
            best_hits = hits
            best_ans = val

    if best_ans and best_hits >= 2:
        return best_ans, "matched"
    return None, "none"


def make_video_brief(topic: str, style: str = "pov", duration: int = 5) -> Dict[str, object]:
    sec = max(3, min(int(duration), 60))
    t = " ".join(topic.strip().split()) or "3D Scene"
    if style.lower() == "pov":
        prompt = f"First-person POV shot of {t}, dynamic camera motion, clear lighting, {sec}s."
        script = f"{GREETING}, dekhiye {t} ka POV scene step by step."
    else:
        prompt = f"Clean visual explainer of {t}, smooth camera pan, high clarity, {sec}s."
        script = f"{GREETING}, aaj {t} ke mukhya points aur niyam samajhte hain."
    return {"creator": CREATOR, "topic": t, "style": style.lower(), "duration": sec, "prompt": prompt, "script": script}


def safe_mp4_render(out_mp4: str, duration: int = 4, audio_file: Optional[str] = None, res: str = "720x1280") -> Dict[str, object]:
    if shutil.which("ffmpeg") is None:
        return {"ok": False, "error": "ffmpeg not found"}

    sec = max(2, min(int(duration), 60))
    out_abs = os.path.abspath(out_mp4)
    out_dir = os.path.dirname(out_abs) or "."
    os.makedirs(out_dir, exist_ok=True)

    fd, tmp_mp4 = tempfile.mkstemp(prefix=".tmp_vid_", suffix=".mp4", dir=out_dir)
    os.close(fd)
    if os.path.exists(tmp_mp4):
        os.remove(tmp_mp4)

    has_audio = bool(audio_file and os.path.isfile(audio_file) and os.path.getsize(audio_file) > 0)
    if has_audio:
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c=0x111827:s={res}:r=30:d={sec}",
            "-i", os.path.abspath(audio_file),
            "-filter_complex", "[1:a]aresample=async=1,apad[aout]",
            "-map", "0:v:0", "-map", "[aout]",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart", "-shortest", tmp_mp4,
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c=0x111827:s={res}:r=30:d={sec}",
            "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo:d={sec}",
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart", "-shortest", tmp_mp4,
        ]

    res_proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if res_proc.returncode != 0 or not os.path.exists(tmp_mp4) or os.path.getsize(tmp_mp4) == 0:
        if os.path.exists(tmp_mp4):
            os.remove(tmp_mp4)
        return {"ok": False, "error": (res_proc.stderr or "render failed")[-300:]}

    os.replace(tmp_mp4, out_abs)
    return {"ok": True, "file": out_abs, "size": os.path.getsize(out_abs)}


if __name__ == "__main__":
    sample_kb = {"3d video me voice kaise dale": "Sequencer Audio Track ya FFmpeg se voice merge karein."}
    print("Lookup:", smart_lookup(sample_kb, "3d video me voice kaise dale"))
    print("Brief:", make_video_brief("3D Railway Track Circuit", style="explainer", duration=5))
