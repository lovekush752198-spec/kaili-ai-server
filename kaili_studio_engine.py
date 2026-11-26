import asyncio
import os
import re
import shutil
import subprocess
import tempfile
from typing import Dict, Optional

from kaili_ultimate_core import (
    CREATOR,
    GREETING,
    RES_4K,
    build_multi_scene_package,
    render_4k_multi_scene_video,
    self_heal_knowledge_dir,
)
from math_science_engine import eval_expression, solve_science, solve_trigonometry, square_and_root


def _slug(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", name.strip()).strip("_")
    return cleaned[:45] or "kaili_voice_4k"


def synthesize_voice_safe(text: str, out_mp3: str, voice: str = "hi-IN-SwaraNeural") -> Dict[str, object]:
    """Generate voice audio using edge-tts if installed; never crash if unavailable."""
    clean_text = " ".join(text.strip().split())
    if not clean_text:
        return {"ok": False, "error": "Empty voice text"}

    if shutil.which("edge-tts") is None:
        try:
            import edge_tts  # type: ignore
        except Exception:
            return {"ok": False, "error": "edge-tts not installed (optional: pip install edge-tts)"}
    else:
        edge_tts = None

    abs_mp3 = os.path.abspath(out_mp3)
    os.makedirs(os.path.dirname(abs_mp3) or ".", exist_ok=True)
    fd, tmp_mp3 = tempfile.mkstemp(prefix=".voice_", suffix=".mp3", dir=os.path.dirname(abs_mp3) or ".")
    os.close(fd)
    if os.path.exists(tmp_mp3):
        os.remove(tmp_mp3)

    try:
        if edge_tts is not None:
            async def _run_tts():
                comm = edge_tts.Communicate(clean_text, voice=voice)
                await comm.save(tmp_mp3)
            asyncio.run(_run_tts())
        else:
            cmd = ["edge-tts", "--voice", voice, "--text", clean_text, "--write-media", tmp_mp3]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if proc.returncode != 0:
                if os.path.exists(tmp_mp3):
                    os.remove(tmp_mp3)
                return {"ok": False, "error": (proc.stderr or "edge-tts failed")[-250:]}

        if not os.path.exists(tmp_mp3) or os.path.getsize(tmp_mp3) == 0:
            if os.path.exists(tmp_mp3):
                os.remove(tmp_mp3)
            return {"ok": False, "error": "Generated voice file is empty"}

        os.replace(tmp_mp3, abs_mp3)
        return {"ok": True, "voice": voice, "file": abs_mp3, "size_bytes": os.path.getsize(abs_mp3)}
    except Exception as exc:
        if os.path.exists(tmp_mp3):
            try:
                os.remove(tmp_mp3)
            except OSError:
                pass
        return {"ok": False, "error": str(exc)}


def produce_4k_video_with_voice(
    topic: str,
    style: str = "pov",
    scenes: int = 3,
    sec_per_scene: int = 3,
    fps: int = 24,
    voice: str = "hi-IN-SwaraNeural",
) -> Dict[str, object]:
    health = self_heal_knowledge_dir("knowledge")
    pkg = build_multi_scene_package(topic=topic, style=style, scenes=scenes, sec_per_scene=sec_per_scene)
    full_script = " ".join(str(s.get("voice_line", "")) for s in pkg.get("scenes", []))

    base_dir = os.path.dirname(os.path.abspath(__file__))
    voice_dir = os.path.join(base_dir, "renders_ultimate", "voice")
    os.makedirs(voice_dir, exist_ok=True)
    voice_path = os.path.join(voice_dir, f"{_slug(topic)}.mp3")

    voice_res = synthesize_voice_safe(full_script, voice_path, voice=voice)
    used_voice_file = str(voice_res["file"]) if voice_res.get("ok") else None

    video_res = render_4k_multi_scene_video(
        topic=topic,
        style=style,
        scenes=scenes,
        sec_per_scene=sec_per_scene,
        fps=fps,
        voice_audio_path=used_voice_file,
    )

    return {
        "ok": bool(video_res.get("ok")),
        "creator": CREATOR,
        "greeting": GREETING,
        "resolution": RES_4K,
        "knowledge_health": health,
        "voice_status": voice_res,
        "video_status": video_res,
    }


def run_math_or_science_check() -> Dict[str, object]:
    return {
        "eval": eval_expression("(45 + 15) / 3 + sin(90)"),
        "square_root": square_and_root(225),
        "trig": solve_trigonometry(perpendicular=6, base=8),
        "science": solve_science("ohm", i=3, r=4),
    }


if __name__ == "__main__":
    print("Math/Science:", run_math_or_science_check())
    print(
        "4K Studio Run:",
        produce_4k_video_with_voice(
            topic="KAILI AI Voice + 4K Engine",
            style="explainer",
            scenes=2,
            sec_per_scene=2,
            fps=24,
        ),
    )
