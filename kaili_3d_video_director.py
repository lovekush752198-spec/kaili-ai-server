import os
import re
import shutil
import subprocess
import tempfile
from typing import Dict, List, Optional

from kaili_studio_engine import synthesize_voice_safe
from kaili_ultimate_core import CREATOR, GREETING, RES_4K

CAMERA_MOVES = [
    "3D orbital dolly-in",
    "3D low-angle tracking shot",
    "3D macro cutaway camera",
    "3D sweeping crane pan",
    "3D first-person POV glide",
    "3D slow-motion hero push",
]

LIGHTING_MODES = [
    "cinematic volumetric rim light",
    "neon cyber studio lighting",
    "golden hour raytraced sunlight",
    "dramatic dark lab spotlight",
]

PALETTES = [
    "0x090d16",
    "0x111827",
    "0x0f172a",
    "0x1e1b4b",
    "0x172554",
    "0x134e4a",
]


def _slug(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", (text or "").strip()).strip("_")
    return cleaned[:45] or "kaili_3d_video"


def plan_any_3d_video(
    prompt: str,
    scenes: int = 4,
    sec_per_scene: int = 3,
    aspect: str = "vertical",
) -> Dict[str, object]:
    """Turn ANY user topic into a multi-shot 3D storyboard, 3D generator prompts, and voice script."""
    topic = " ".join((prompt or "").strip().split()) or "KAILI 3D World"
    n_scenes = max(1, min(int(scenes), 8))
    dur = max(2, min(int(sec_per_scene), 12))
    res = "2160x3840" if aspect.lower() in {"vertical", "shorts", "reels", "9:16"} else RES_4K

    shots: List[Dict[str, object]] = []
    for i in range(n_scenes):
        cam = CAMERA_MOVES[i % len(CAMERA_MOVES)]
        light = LIGHTING_MODES[i % len(LIGHTING_MODES)]
        role = "Hook / Intro" if i == 0 else ("Climax / Core Action" if i == n_scenes - 1 else f"3D Detail Shot {i + 1}")
        render_prompt = (
            f"3D CGI scene of {topic}, {role}, {cam}, {light}, physically based materials, "
            f"depth of field, {res}, sharp 3D render."
        )
        voice_line = f"{GREETING}, shot {i + 1}: {topic} ka {role.lower()} dekhiye."
        shots.append({
            "shot": i + 1,
            "role": role,
            "duration_sec": dur,
            "camera": cam,
            "lighting": light,
            "3d_prompt": render_prompt,
            "voice_line": voice_line,
        })

    return {
        "ok": True,
        "creator": CREATOR,
        "greeting": GREETING,
        "topic": topic,
        "aspect": aspect,
        "resolution": res,
        "total_shots": n_scenes,
        "sec_per_shot": dur,
        "total_duration_sec": n_scenes * dur,
        "shots": shots,
    }


def build_3d_video_reel(
    prompt: str,
    scenes: int = 4,
    sec_per_scene: int = 3,
    fps: int = 24,
    aspect: str = "vertical",
    voice: str = "hi-IN-SwaraNeural",
    external_3d_clips: Optional[List[str]] = None,
    output_mp4: Optional[str] = None,
) -> Dict[str, object]:
    """
    Build a multi-shot video from ANY prompt.
    If valid external 3D .mp4 clips are passed, stitches them in 3D/HD/4K;
    otherwise generates a clean multi-shot visual reel + optional voice audio.
    """
    plan = plan_any_3d_video(prompt=prompt, scenes=scenes, sec_per_scene=sec_per_scene, aspect=aspect)
    if shutil.which("ffmpeg") is None:
        return {"ok": False, "error": "ffmpeg not found", "plan": plan}

    res = str(plan["resolution"])
    dur = int(plan["sec_per_shot"])
    n_shots = int(plan["total_shots"])
    total_sec = int(plan["total_duration_sec"])
    rate = max(15, min(int(fps), 30))

    base_dir = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.dirname(os.path.abspath(output_mp4)) if output_mp4 else os.path.join(base_dir, "renders_3d")
    os.makedirs(out_dir, exist_ok=True)
    final_mp4 = os.path.abspath(output_mp4) if output_mp4 else os.path.join(out_dir, f"{_slug(prompt)}_3d.mp4")

    full_voice_text = " ".join(str(s["voice_line"]) for s in plan["shots"])
    voice_out = os.path.join(out_dir, "voice", f"{_slug(prompt)}.mp3")
    voice_info = synthesize_voice_safe(full_voice_text, voice_out, voice=voice)
    has_voice = bool(voice_info.get("ok") and voice_info.get("file") and os.path.isfile(str(voice_info["file"])))

    valid_clips = [os.path.abspath(p) for p in (external_3d_clips or []) if p and os.path.isfile(p) and os.path.getsize(p) > 0]

    fd, tmp_mp4 = tempfile.mkstemp(prefix=".k3d_", suffix=".mp4", dir=out_dir)
    os.close(fd)
    if os.path.exists(tmp_mp4):
        os.remove(tmp_mp4)

    inputs: List[str] = []
    filters: List[str] = []
    v_labels: List[str] = []

    if valid_clips:
        for idx, clip_path in enumerate(valid_clips):
            inputs.extend(["-i", clip_path])
            filters.append(f"[{idx}:v]scale={res}:force_original_aspect_ratio=decrease,pad={res}:(ow-iw)/2:(oh-ih)/2,fps={rate},setsar=1[v{idx}]")
            v_labels.append(f"[v{idx}]")
        filters.append(f"{''.join(v_labels)}concat=n={len(v_labels)}:v=1:a=0[vout]")
    else:
        for idx in range(n_shots):
            color_hex = PALETTES[idx % len(PALETTES)]
            inputs.extend(["-f", "lavfi", "-i", f"color=c={color_hex}:s={res}:r={rate}:d={dur}"])
            filters.append(f"[{idx}:v]scale={res}:flags=lanczos,setsar=1[v{idx}]")
            v_labels.append(f"[v{idx}]")
        filters.append(f"{''.join(v_labels)}concat=n={len(v_labels)}:v=1:a=0[vout]")

    a_idx = len(v_labels)
    if has_voice:
        inputs.extend(["-i", str(voice_info["file"])])
        filters.append(f"[{a_idx}:a]aresample=async=1,apad[aout]")
    else:
        inputs.extend(["-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo:d={max(2, total_sec)}"])
        filters.append(f"[{a_idx}:a]aresample=async=1[aout]")

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", ";".join(filters),
        "-map", "[vout]",
        "-map", "[aout]",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        "-shortest",
        tmp_mp4,
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=420)
        if proc.returncode != 0 or not os.path.exists(tmp_mp4) or os.path.getsize(tmp_mp4) == 0:
            if os.path.exists(tmp_mp4):
                os.remove(tmp_mp4)
            return {
                "ok": False,
                "error": "3D video render failed",
                "stderr_tail": (proc.stderr or "")[-350:],
                "plan": plan,
            }

        os.replace(tmp_mp4, final_mp4)
        return {
            "ok": True,
            "creator": CREATOR,
            "greeting": GREETING,
            "mode": "external_3d_clips_stitched" if valid_clips else "multi_shot_3d_plan_reel",
            "resolution": res,
            "file": final_mp4,
            "size_bytes": os.path.getsize(final_mp4),
            "voice_attached": has_voice,
            "plan": plan,
        }
    except Exception as exc:
        if os.path.exists(tmp_mp4):
            try:
                os.remove(tmp_mp4)
            except OSError:
                pass
        return {"ok": False, "error": str(exc), "plan": plan}


if __name__ == "__main__":
    res1 = build_3d_video_reel(
        prompt="3D futuristic car engine & turbo cutaway",
        scenes=4,
        sec_per_scene=2,
        fps=24,
        aspect="vertical",
    )
    print("3D Reel 1:", {k: v for k, v in res1.items() if k != "plan"})
    print("Shots count:", len(res1.get("plan", {}).get("shots", [])))
