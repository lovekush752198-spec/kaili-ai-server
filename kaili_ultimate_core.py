import json
import os
import re
import shutil
import subprocess
import tempfile
from typing import Dict, List, Optional

CREATOR = "LAVKUSH KUMAR"
GREETING = "Boss"
RES_4K = "3840x2160"


def _slug(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", text.strip()).strip("_")
    return cleaned[:45] or "kaili_ultimate"


def _atomic_write(path: str, payload: object) -> None:
    abs_path = os.path.abspath(path)
    folder = os.path.dirname(abs_path) or "."
    os.makedirs(folder, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".kaili_ult_", suffix=".tmp", dir=folder)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            if isinstance(payload, (dict, list)):
                json.dump(payload, f, ensure_ascii=False, indent=2)
            else:
                f.write(str(payload))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, abs_path)
    except Exception:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        raise


def self_heal_knowledge_dir(knowledge_dir: str = "knowledge") -> Dict[str, object]:
    """Verify all domain JSON files; if corrupted or missing, safely reset to {}."""
    os.makedirs(knowledge_dir, exist_ok=True)
    report: Dict[str, str] = {}
    for domain in ["chat", "study", "coding"]:
        path = os.path.join(knowledge_dir, f"{domain}.json")
        if not os.path.exists(path):
            _atomic_write(path, {})
            report[domain] = "created_empty"
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                _atomic_write(path, {})
                report[domain] = "repaired_non_dict"
            else:
                report[domain] = f"ok_entries_{len(data)}"
        except Exception:
            _atomic_write(path, {})
            report[domain] = "repaired_corrupted_json"
    return {"ok": True, "creator": CREATOR, "greeting": GREETING, "domains": report}


def build_multi_scene_package(topic: str, style: str = "pov", scenes: int = 3, sec_per_scene: int = 3) -> Dict[str, object]:
    clean_topic = " ".join(topic.strip().split()) or "KAILI 4K Vision"
    clean_style = style.strip().lower()
    scene_count = max(2, min(int(scenes), 6))
    dur_each = max(2, min(int(sec_per_scene), 15))
    total_sec = scene_count * dur_each

    scene_list: List[Dict[str, object]] = []
    for idx in range(1, scene_count + 1):
        if clean_style in {"pov", "action", "gaming"}:
            s_prompt = (
                f"Scene {idx}/{scene_count} ({dur_each}s): First-person POV view of {clean_topic}, "
                f"stage {idx} motion, dramatic lighting, {RES_4K} ultra sharp frame."
            )
            s_voice = f"{GREETING}, scene {idx}: {clean_topic} mein agla action dekhiye."
        else:
            s_prompt = (
                f"Scene {idx}/{scene_count} ({dur_each}s): Visual explainer of {clean_topic}, "
                f"point {idx}, clean layout, smooth camera transition, {RES_4K}."
            )
            s_voice = f"{GREETING}, part {idx}: {clean_topic} ka mukhya niyam samajhiye."
        scene_list.append({
            "scene": idx,
            "duration_sec": dur_each,
            "video_prompt": s_prompt,
            "voice_line": s_voice,
        })

    return {
        "ok": True,
        "creator": CREATOR,
        "greeting": GREETING,
        "topic": clean_topic,
        "style": clean_style,
        "resolution": RES_4K,
        "total_duration_sec": total_sec,
        "scenes": scene_list,
    }


def render_4k_multi_scene_video(
    topic: str,
    style: str = "pov",
    scenes: int = 3,
    sec_per_scene: int = 3,
    fps: int = 24,
    voice_audio_path: Optional[str] = None,
    output_mp4: Optional[str] = None,
) -> Dict[str, object]:
    pkg = build_multi_scene_package(topic=topic, style=style, scenes=scenes, sec_per_scene=sec_per_scene)
    if shutil.which("ffmpeg") is None:
        return {"ok": False, "error": "ffmpeg not installed", "package": pkg}

    total_sec = int(pkg["total_duration_sec"])
    frame_rate = max(15, min(int(fps), 30))
    base_dir = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.dirname(os.path.abspath(output_mp4)) if output_mp4 else os.path.join(base_dir, "renders_ultimate")
    final_mp4 = os.path.abspath(output_mp4) if output_mp4 else os.path.join(out_dir, f"{_slug(topic)}_ultimate_4k.mp4")
    os.makedirs(out_dir, exist_ok=True)

    fd, tmp_mp4 = tempfile.mkstemp(prefix=".ult_4k_", suffix=".mp4", dir=out_dir)
    os.close(fd)
    if os.path.exists(tmp_mp4):
        os.remove(tmp_mp4)

    has_voice = bool(voice_audio_path and os.path.isfile(voice_audio_path) and os.path.getsize(voice_audio_path) > 0)
    palette = ["0x0b1120", "0x111827", "0x172554", "0x1e1b4b", "0x0f172a", "0x134e4a"]

    # Build multi-scene filter_complex cleanly
    inputs = []
    filters = []
    concat_inputs = []
    for i in range(int(pkg["scenes"].__len__())):
        c = palette[i % len(palette)]
        inputs.extend(["-f", "lavfi", "-i", f"color=c={c}:s={RES_4K}:r={frame_rate}:d={sec_per_scene}"])
        filters.append(f"[{i}:v]scale={RES_4K}:flags=lanczos,setsar=1[v{i}]")
        concat_inputs.append(f"[v{i}]")

    filters.append(f"{''.join(concat_inputs)}concat=n={len(concat_inputs)}:v=1:a=0[vout]")

    if has_voice:
        v_idx = len(concat_inputs)
        inputs.extend(["-i", os.path.abspath(voice_audio_path)])
        filters.append(f"[{v_idx}:a]aresample=async=1,apad[aout]")
        map_args = ["-map", "[vout]", "-map", "[aout]"]
    else:
        a_idx = len(concat_inputs)
        inputs.extend(["-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo:d={total_sec}"])
        filters.append(f"[{a_idx}:a]aresample=async=1[aout]")
        map_args = ["-map", "[vout]", "-map", "[aout]"]

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", ";".join(filters),
        *map_args,
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        "-shortest",
        tmp_mp4,
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=360)
        if proc.returncode != 0 or not os.path.exists(tmp_mp4) or os.path.getsize(tmp_mp4) == 0:
            if os.path.exists(tmp_mp4):
                os.remove(tmp_mp4)
            return {"ok": False, "error": "multi-scene 4K render failed", "stderr_tail": (proc.stderr or "")[-350:], "package": pkg}

        os.replace(tmp_mp4, final_mp4)
        return {
            "ok": True,
            "creator": CREATOR,
            "greeting": GREETING,
            "resolution": RES_4K,
            "total_duration_sec": total_sec,
            "file": final_mp4,
            "size_bytes": os.path.getsize(final_mp4),
            "used_voice": voice_audio_path if has_voice else None,
            "package": pkg,
        }
    except Exception as exc:
        if os.path.exists(tmp_mp4):
            try:
                os.remove(tmp_mp4)
            except OSError:
                pass
        return {"ok": False, "error": str(exc), "package": pkg}


if __name__ == "__main__":
    print("Heal:", self_heal_knowledge_dir("knowledge"))
    out = render_4k_multi_scene_video(
        topic="KAILI AI Multi-Scene 4K Studio",
        style="pov",
        scenes=3,
        sec_per_scene=2,
        fps=24,
    )
    print("Result:", out)
