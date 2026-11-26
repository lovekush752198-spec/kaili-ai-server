import re
from typing import Dict, Optional

from kaili_security_shield import RateLimiter, inspect_input_safety, scan_for_leaked_secrets
from kaili_studio_engine import produce_4k_video_with_voice
from kaili_ultimate_core import CREATOR, GREETING, build_multi_scene_package, self_heal_knowledge_dir
from math_science_engine import eval_expression, solve_science, solve_trigonometry, square_and_root

_BRIDGE_LIMITER = RateLimiter(max_requests=60, window_seconds=60)


def normalize_math_text(text: str) -> str:
    s = (text or "").strip()
    # Convert unicode root symbols like √144 or √(144) to sqrt(...)
    s = re.sub(r"√\s*\(\s*([^)]+)\s*\)", r"sqrt(\1)", s)
    s = re.sub(r"√\s*(\d+(?:\.\d+)?)", r"sqrt(\1)", s)
    return s


def _looks_like_math_expr(expr: str) -> bool:
    e = expr.strip().lower()
    if not e or len(e) > 120:
        return False
    # Allow numbers, basic operators, trig/sqrt functions, spaces, parentheses, dots
    allowed_tokens = re.sub(r"\b(sin|cos|tan|sqrt|log|pi|e)\b", "", e)
    if not re.fullmatch(r"[0-9+\-*/().^%\s]+", allowed_tokens):
        return False
    return bool(re.search(r"[0-9]", e) and re.search(r"[+\-*/^%]|\b(sin|cos|tan|sqrt)\b", e))


def guard_request(client_key: str, text: str) -> Dict[str, object]:
    allowed, limit_info = _BRIDGE_LIMITER.allow(client_key or "default_client")
    if not allowed:
        return {
            "ok": False,
            "blocked_by": "rate_limiter",
            "reply": f"{GREETING}, thoda rukkar ({limit_info['retry_after_sec']}s baad) try karein.",
        }

    safety = inspect_input_safety(text)
    if not safety.get("safe"):
        return {
            "ok": False,
            "blocked_by": "input_guard",
            "reasons": safety.get("reasons", []),
            "reply": f"{GREETING}, security shield ne unsafe request block kar di hai.",
        }

    return {"ok": True, "risk_level": safety.get("risk_level", "LOW")}


def route_smart_command(message: str) -> Optional[Dict[str, object]]:
    """Handle math (including 2+2 and √144), trig, science, or 4K studio commands."""
    raw = normalize_math_text(message or "")
    low = raw.lower().strip()

    # 1. Explicit calc:/math: OR any clean arithmetic/sqrt/trig expression like '2+2' or 'sqrt(144)'
    if low.startswith("calc:") or low.startswith("math:"):
        expr = raw.split(":", 1)[1].strip()
        res = eval_expression(expr)
        if res.get("ok"):
            return {
                "handled": True,
                "engine": "math_science_engine.eval_expression",
                "reply": f"{GREETING}, Result ({res.get('expression')}): {res.get('result')}",
                "data": res,
            }
        return {"handled": True, "engine": "math_science_engine", "reply": f"{GREETING}, {res.get('error')}", "data": res}

    if _looks_like_math_expr(raw):
        res = eval_expression(raw)
        if res.get("ok"):
            return {
                "handled": True,
                "engine": "math_science_engine.eval_expression",
                "reply": f"{GREETING}, {res.get('expression')} = {res.get('result')}",
                "data": res,
            }

    # 2. Square & square root words
    m_sq = re.match(r"^(?:varg|square|sqrt|vargmul)\s+(-?\d+(?:\.\d+)?)$", low)
    if m_sq:
        num = float(m_sq.group(1))
        res = square_and_root(num)
        steps_txt = " | ".join(str(s) for s in res.get("steps", []))
        return {
            "handled": True,
            "engine": "math_science_engine.square_and_root",
            "reply": f"{GREETING}, {steps_txt}",
            "data": res,
        }

    # 3. Trigonometry / Pythagoras
    if low.startswith("trig ") or low.startswith("trikonmiti "):
        nums = {k.lower(): float(v) for k, v in re.findall(r"\b([pbh])\s*=\s*(-?\d+(?:\.\d+)?)", low)}
        res = solve_trigonometry(
            perpendicular=nums.get("p"),
            base=nums.get("b"),
            hypotenuse=nums.get("h"),
        )
        if res.get("ok"):
            return {
                "handled": True,
                "engine": "math_science_engine.solve_trigonometry",
                "reply": (
                    f"{GREETING}, Lamb={res.get('perpendicular_lamb')}, Aadhar={res.get('base_aadhar')}, "
                    f"Karn={res.get('hypotenuse_karn')}, Angle={res.get('angle_theta_deg')} deg"
                ),
                "data": res,
            }
        return {"handled": True, "engine": "math_science_engine", "reply": f"{GREETING}, {res.get('error')}", "data": res}

    # 4. Science formula
    if low.startswith("sci ") or low.startswith("science "):
        parts = low.split()
        if len(parts) >= 2:
            formula_name = parts[1]
            params = {k.lower(): float(v) for k, v in re.findall(r"\b([a-zA-Z_]+)\s*=\s*(-?\d+(?:\.\d+)?)", raw)}
            res = solve_science(formula_name, **params)
            if res.get("ok"):
                return {
                    "handled": True,
                    "engine": "math_science_engine.solve_science",
                    "reply": f"{GREETING}, {res.get('formula')} -> {res.get('step')}",
                    "data": res,
                }
            return {"handled": True, "engine": "math_science_engine", "reply": f"{GREETING}, {res.get('error')}", "data": res}

    # 5. 4K Scene Plan / Render
    if low.startswith("4k plan:") or low.startswith("4k video:"):
        topic = raw.split(":", 1)[1].strip() or "KAILI 4K Vision"
        pkg = build_multi_scene_package(topic=topic, style="pov", scenes=3, sec_per_scene=3)
        scene_lines = [f"Scene {s['scene']}: {s['video_prompt']}" for s in pkg.get("scenes", [])]
        return {
            "handled": True,
            "engine": "kaili_ultimate_core.build_multi_scene_package",
            "reply": f"{GREETING}, 4K Plan ({pkg.get('resolution')}) taiyar hai:\n" + "\n".join(scene_lines),
            "data": pkg,
        }

    if low.startswith("4k render:"):
        topic = raw.split(":", 1)[1].strip() or "KAILI 4K Render"
        out = produce_4k_video_with_voice(topic=topic, style="pov", scenes=2, sec_per_scene=2, fps=24)
        return {
            "handled": True,
            "engine": "kaili_studio_engine.produce_4k_video_with_voice",
            "reply": f"{GREETING}, 4K Render status: ok={out.get('ok')}, resolution={out.get('resolution')}",
            "data": out,
        }

    return None


def bridge_health_check() -> Dict[str, object]:
    heal = self_heal_knowledge_dir("knowledge")
    return {
        "ok": True,
        "creator": CREATOR,
        "greeting": GREETING,
        "knowledge": heal.get("domains", {}),
        "secret_scan_sample_ok": not scan_for_leaked_secrets("clean_health_check").get("has_secrets"),
    }


if __name__ == "__main__":
    print("2+2:", route_smart_command("2+2")["reply"])
    print("√144:", route_smart_command("√144")["reply"])
