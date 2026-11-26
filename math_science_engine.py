import math
import re
from typing import Dict, List, Optional, Tuple

CREATOR = "LAVKUSH KUMAR"
GREETING = "Boss"


# 1. Safe Math Evaluator (+, -, *, /, //, %, **, sqrt, sin, cos, tan, rad, deg)
def eval_expression(expr: str) -> Dict[str, object]:
    raw = expr.strip()
    cleaned = (
        raw.lower()
        .replace("^", "**")
        .replace("×", "*")
        .replace("x", "*")
        .replace("÷", "/")
        .replace("√", "sqrt")
    )
    cleaned = re.sub(r"[^0-9a-zA-Z_+\-*/().%,\s]", "", cleaned)

    allowed_names = {
        "sqrt": math.sqrt,
        "sin": lambda deg: round(math.sin(math.radians(deg)), 8),
        "cos": lambda deg: round(math.cos(math.radians(deg)), 8),
        "tan": lambda deg: None if abs(math.cos(math.radians(deg))) < 1e-12 else round(math.tan(math.radians(deg)), 8),
        "pi": math.pi,
        "abs": abs,
        "round": round,
    }

    try:
        compiled = compile(cleaned, "<expr>", "eval")
        for node_name in compiled.co_names:
            if node_name not in allowed_names:
                return {"ok": False, "error": f"Disallowed identifier: {node_name}"}
        val = eval(compiled, {"__builtins__": {}}, allowed_names)
        return {
            "ok": True,
            "creator": CREATOR,
            "greeting": GREETING,
            "expression": raw,
            "normalized": cleaned,
            "result": val,
        }
    except ZeroDivisionError:
        return {"ok": False, "error": "Zero se bhag (division by zero) sambhav nahi hai."}
    except Exception as exc:
        return {"ok": False, "error": f"Expression evaluate nahi ho paya: {exc}"}


# 2. Square, Square Root & Prime Factorization
def square_and_root(n: float) -> Dict[str, object]:
    sq = n * n
    root = math.sqrt(n) if n >= 0 else None
    steps = [
        f"1. Varg (Square): ({n})^2 = {sq}",
    ]
    if root is not None:
        steps.append(f"2. Vargmul (Square Root): sqrt({n}) = {round(root, 8)}")
    else:
        steps.append("2. Negative sankhya ka real vargmul nahi hota.")
    return {"ok": True, "input": n, "square": sq, "sqrt": root, "steps": steps}


# 3. Trigonometry (Right Triangle: given any 2 of perpendicular, base, hypotenuse + angle)
def solve_trigonometry(
    perpendicular: Optional[float] = None,
    base: Optional[float] = None,
    hypotenuse: Optional[float] = None,
) -> Dict[str, object]:
    steps: List[str] = []
    p, b, h = perpendicular, base, hypotenuse

    if p is not None and b is not None and h is None:
        h = math.hypot(p, b)
        steps.append(f"Pythagoras: Karn (h) = sqrt({p}^2 + {b}^2) = {round(h, 6)}")
    elif p is not None and h is not None and b is None:
        if h <= p:
            return {"ok": False, "error": "Karn (hypotenuse), Lamb (perpendicular) se bada hona chahiye."}
        b = math.sqrt(h * h - p * p)
        steps.append(f"Pythagoras: Aadhar (b) = sqrt({h}^2 - {p}^2) = {round(b, 6)}")
    elif b is not None and h is not None and p is None:
        if h <= b:
            return {"ok": False, "error": "Karn (hypotenuse), Aadhar (base) se bada hona chahiye."}
        p = math.sqrt(h * h - b * b)
        steps.append(f"Pythagoras: Lamb (p) = sqrt({h}^2 - {b}^2) = {round(p, 6)}")

    if not (p and b and h):
        return {"ok": False, "error": "Kam se kam 2 bhujayein (perpendicular, base, hypotenuse) dein."}

    sin_val = p / h
    cos_val = b / h
    tan_val = p / b if b != 0 else None
    angle_deg = math.degrees(math.atan2(p, b))

    return {
        "ok": True,
        "perpendicular_lamb": round(p, 6),
        "base_aadhar": round(b, 6),
        "hypotenuse_karn": round(h, 6),
        "angle_theta_deg": round(angle_deg, 4),
        "ratios": {
            "sin_theta": round(sin_val, 6),
            "cos_theta": round(cos_val, 6),
            "tan_theta": round(tan_val, 6) if tan_val is not None else "undefined",
        },
        "steps": steps,
    }


# 4. Science Formula Solver (Speed, Force, Work, Ohm's Law, Motion v = u + at)
def solve_science(formula: str, **kwargs: float) -> Dict[str, object]:
    key = formula.strip().lower()
    if key in {"speed", "chal"}:
        d, t = kwargs.get("d"), kwargs.get("t")
        if d is not None and t and t != 0:
            v = d / t
            return {"ok": True, "formula": "v = d / t", "result": v, "unit": "m/s", "step": f"{d} / {t} = {v} m/s"}
        return {"ok": False, "error": "d aur t (non-zero) dein."}

    if key in {"force", "bal"}:
        m, a = kwargs.get("m"), kwargs.get("a")
        if m is not None and a is not None:
            f = m * a
            return {"ok": True, "formula": "F = m * a", "result": f, "unit": "N", "step": f"{m} * {a} = {f} N"}
        return {"ok": False, "error": "m aur a dein."}

    if key in {"work", "karya"}:
        f, d = kwargs.get("f"), kwargs.get("d")
        theta = kwargs.get("theta", 0.0)
        if f is not None and d is not None:
            w = f * d * math.cos(math.radians(theta))
            return {
                "ok": True,
                "formula": "W = F * d * cos(theta)",
                "result": round(w, 6),
                "unit": "J",
                "step": f"{f} * {d} * cos({theta}°) = {round(w, 6)} J",
            }
        return {"ok": False, "error": "f aur d dein."}

    if key in {"ohm", "voltage"}:
        i, r = kwargs.get("i"), kwargs.get("r")
        if i is not None and r is not None:
            v = i * r
            return {"ok": True, "formula": "V = I * R", "result": v, "unit": "V", "step": f"{i} * {r} = {v} V"}
        return {"ok": False, "error": "i aur r dein."}

    if key in {"motion_v", "gati"}:
        u, a, t = kwargs.get("u"), kwargs.get("a"), kwargs.get("t")
        if u is not None and a is not None and t is not None:
            v = u + a * t
            return {"ok": True, "formula": "v = u + a*t", "result": v, "unit": "m/s", "step": f"{u} + ({a} * {t}) = {v} m/s"}
        return {"ok": False, "error": "u, a aur t dein."}

    return {"ok": False, "error": "Supported formulas: speed, force, work, ohm, motion_v"}


if __name__ == "__main__":
    print("BODMAS/Math:", eval_expression("(25 + 15) * 2 - 10 / 2 + sin(30)"))
    print("Square/Root:", square_and_root(144))
    print("Trigonometry:", solve_trigonometry(perpendicular=3, base=4))
    print("Science Force:", solve_science("force", m=5, a=2))
    print("Science Work:", solve_science("work", f=10, d=4, theta=60))
