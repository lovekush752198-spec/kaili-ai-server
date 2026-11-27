import json
import os
import re
import tempfile
from typing import Dict, List, Optional, Tuple
from flask import Flask, Response, jsonify, request, stream_with_context


# --- KAILI MATH SOLVER (SQRT, CBRT, CUBE, SQUARE) ---
def kaili_fmt_num(val: float) -> str:
    if math.isnan(val) or math.isinf(val):
        return "undefined"
    nearest = round(val)
    if abs(val - nearest) < 1e-9:
        return str(int(nearest))
    return f"{val:.6f}".rstrip("0").rstrip(".")

def kaili_solve_math(text: str):
    if not text or not isinstance(text, str):
        return None
    q = text.strip().lower()

    # Cube root: ∛1728, cbrt(1728), cube root of 1728, 1728 ka ghanmul
    for pat in [
        r"∛\s*(-?\d+(?:\.\d+)?)",
        r"cbrt\s*\(\s*(-?\d+(?:\.\d+)?)\s*\)",
        r"cube\s*root\s*(?:of\s*)?(-?\d+(?:\.\d+)?)",
        r"(-?\d+(?:\.\d+)?)\s*(?:ka|ki|ke)?\s*ghanmul",
        r"ghanmul\s*(?:of\s*)?(-?\d+(?:\.\d+)?)",
    ]:
        m = re.search(pat, q)
        if m:
            n = float(m.group(1))
            ans = math.copysign(abs(n) ** (1.0 / 3.0), n)
            return f"Boss, {kaili_fmt_num(ans)} hota hai."

    # Square root: √144, sqrt(144), square root of 144, 144 ka vargmul
    for pat in [
        r"√\s*(\d+(?:\.\d+)?)",
        r"sqrt\s*\(\s*(\d+(?:\.\d+)?)\s*\)",
        r"square\s*root\s*(?:of\s*)?(\d+(?:\.\d+)?)",
        r"(\d+(?:\.\d+)?)\s*(?:ka|ki|ke)?\s*vargmul",
        r"vargmul\s*(?:of\s*)?(\d+(?:\.\d+)?)",
    ]:
        m = re.search(pat, q)
        if m:
            n = float(m.group(1))
            if n < 0:
                return "Boss, negative number ka real square root nahi hota."
            ans = math.sqrt(n)
            return f"Boss, {kaili_fmt_num(ans)} hota hai."

    # Cube: 12^3, 12 ka cube, cube of 12, 12 ka ghan
    for pat in [
        r"(-?\d+(?:\.\d+)?)\s*(?:\^|\*\*)\s*3(?:\b|[^0-9])",
        r"(-?\d+(?:\.\d+)?)\s*(?:ka|ki|ke)?\s*(?:cube|ghan)",
        r"(?:cube|ghan)\s*(?:of\s*)?(-?\d+(?:\.\d+)?)",
    ]:
        m = re.search(pat, q)
        if m:
            n = float(m.group(1))
            return f"Boss, {kaili_fmt_num(n ** 3)} hota hai."

    # Square: 12^2, 12 ka square, square of 12, 12 ka varg
    for pat in [
        r"(-?\d+(?:\.\d+)?)\s*(?:\^|\*\*)\s*2(?:\b|[^0-9])",
        r"(-?\d+(?:\.\d+)?)\s*(?:ka|ki|ke)?\s*(?:square|varg)",
        r"(?:square|varg)\s*(?:of\s*)?(-?\d+(?:\.\d+)?)",
    ]:
        m = re.search(pat, q)
        if m:
            n = float(m.group(1))
            return f"Boss, {kaili_fmt_num(n ** 2)} hota hai."

    return None
# --- END KAILI MATH SOLVER ---

app = Flask(__name__)


# === KAILI_CORS_SUPPORT ===
@app.after_request
def _kaili_add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-API-Key"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    return response

CREATOR = "LAVKUSH KUMAR"
DEFAULT_GREETING = "Boss"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KNOWLEDGE_DIR = os.path.join(BASE_DIR, "knowledge")

DOMAIN_FILES: Dict[str, str] = {
    "chat": os.path.join(KNOWLEDGE_DIR, "chat.json"),
    "study": os.path.join(KNOWLEDGE_DIR, "study.json"),
    "coding": os.path.join(KNOWLEDGE_DIR, "coding.json"),
}

SESSIONS: Dict[str, List[Dict[str, str]]] = {}


def ensure_storage() -> None:
    os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
    for _, path in DOMAIN_FILES.items():
        if not os.path.exists(path):
            save_json_atomic(path, {})


def save_json_atomic(path: str, data: Dict[str, str]) -> None:
    parent = os.path.dirname(path)
    os.makedirs(parent, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".kaili_", suffix=".tmp", dir=parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
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


def load_domain_knowledge(domain: str) -> Dict[str, str]:
    ensure_storage()
    path = DOMAIN_FILES.get(domain, DOMAIN_FILES["chat"])
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return {str(k).strip().lower(): str(v) for k, v in data.items() if str(k).strip()}
    except Exception:
        return {}
    return {}


def save_domain_knowledge(domain: str, data: Dict[str, str]) -> None:
    ensure_storage()
    path = DOMAIN_FILES.get(domain, DOMAIN_FILES["chat"])
    save_json_atomic(path, data)


def _tokenize(text: str) -> set:
    return set(re.findall(r"[a-z0-9\u0900-\u097f]+", text.lower()))


# Layer 3: Topic Classifier
def classify_topic(message: str) -> str:
    tokens = _tokenize(message)
    coding_tokens = {
        "code", "cod", "coding", "python", "c", "csharp", "html", "css",
        "javascript", "js", "flask", "api", "git", "unreal", "ue5", "3d",
        "sequencer", "ffmpeg", "render", "voice", "audio", "function", "bug",
        "video", "prompt", "pov", "workflow", "script", "server", "apk",
    }
    study_tokens = {
        "formula", "formule", "farmula", "math", "ganit", "trikonmiti",
        "rikormiti", "sin", "cos", "tan", "pythagoras", "varg", "vargmul",
        "jod", "ghatana", "guna", "bhag", "science", "saince", "vigyan",
        "physics", "chemistry", "newton", "ohm", "padhai", "study", "niyam",
        "equation", "samikaran",
    }

    c_score = len(tokens.intersection(coding_tokens))
    s_score = len(tokens.intersection(study_tokens))

    if c_score > s_score and c_score > 0:
        return "coding"
    if s_score > c_score and s_score > 0:
        return "study"
    if c_score > 0:
        return "coding"
    if s_score > 0:
        return "study"
    return "chat"


def _search_in_domain(domain: str, q: str, q_tokens: set) -> Tuple[Optional[str], str]:
    kb = load_domain_knowledge(domain)
    if q in kb:
        return kb[q], f"layer5->layer4-{domain}-exact"

    if not q_tokens:
        return None, "layer5-no-entry-yet"

    best_score = 0
    best_ans: Optional[str] = None
    for k, v in kb.items():
        k_tokens = _tokenize(k)
        if not k_tokens:
            continue
        overlap = len(q_tokens.intersection(k_tokens))
        if overlap > best_score:
            best_score = overlap
            best_ans = v

    if best_ans and best_score >= 2:
        return best_ans, f"layer5->layer4-{domain}-matched"
    return None, "layer5-no-entry-yet"


# Layer 4 & 5: Domain Knowledge Lookup + Reasoning/Composition
def find_best_knowledge(domain: str, query: str) -> Tuple[Optional[str], str, str]:
    q = " ".join(query.strip().lower().split())
    q_tokens = _tokenize(q)

    ans, src = _search_in_domain(domain, q, q_tokens)
    if ans:
        return ans, src, domain

    for other in ["coding", "study", "chat"]:
        if other == domain:
            continue
        ans, src = _search_in_domain(other, q, q_tokens)
        if ans:
            return ans, f"{src}-cross", other

    return None, "layer5-no-entry-yet", domain


def parse_seekho_command(message: str) -> Optional[Tuple[str, str, str]]:
    m = re.match(
        r"^\s*seekho\s*\[(chat|study|coding)\]\s*:\s*(.+?)\s*=\s*(.+)$",
        message,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not m:
        return None
    domain = m.group(1).lower()
    question = " ".join(m.group(2).strip().lower().split())
    answer = m.group(3).strip()
    if not question or not answer:
        return None
    return domain, question, answer


def process_message(session_id: str, message: str) -> Dict[str, object]:
    turns = SESSIONS.setdefault(session_id, [])
    turns.append({"role": "user", "text": message})

    seekho = parse_seekho_command(message)
    if seekho:
        domain, question, answer = seekho
        kb = load_domain_knowledge(domain)
        kb[question] = answer
        save_domain_knowledge(domain, kb)
        reply = (
            f"{DEFAULT_GREETING}, maine [{domain}] gyan mein yeh darj kar liya hai:\n"
            f"Sawal: {question}\nJawab: {answer}"
        )
        turns.append({"role": "assistant", "text": reply})
        return {
            "ok": True,
            "architecture": "7-layer-domains-hardened",
            "creator": CREATOR,
            "greeting": DEFAULT_GREETING,
            "session_id": session_id,
            "domain": domain,
            "knowledge_file": f"knowledge/{domain}.json",
            "saved_question": question,
            "reply": reply,
            "source": f"layer5->teach-{domain}",
        }

    classified = classify_topic(message)
    found, source, resolved_domain = find_best_knowledge(classified, message)

    if found:
        reply = found if found.lower().startswith(DEFAULT_GREETING.lower()) else f"{DEFAULT_GREETING}, {found}"
    else:
        reply = (
            f"{DEFAULT_GREETING}, `{message}` ka gyan abhi `knowledge/{resolved_domain}.json` mein darj nahi hai "
            f"(session turns: {len(turns)}).\n"
            f"Aap likh kar sikha sakte hain: `seekho [{resolved_domain}]: {message} = aapka jawab`"
        )

    turns.append({"role": "assistant", "text": reply})
    return {
        "ok": True,
        "architecture": "7-layer-domains-hardened",
        "creator": CREATOR,
        "greeting": DEFAULT_GREETING,
        "session_id": session_id,
        "domain": resolved_domain,
        "knowledge_file": f"knowledge/{resolved_domain}.json",
        "reply": reply,
        "source": source,
    }


@app.get("/")
def home():
    ensure_storage()
    counts = {d: len(load_domain_knowledge(d)) for d in DOMAIN_FILES}
    return jsonify({
        "ok": True,
        "service": "KAILI AI Server",
        "creator": CREATOR,
        "greeting": DEFAULT_GREETING,
        "architecture": "7-layer-domains-hardened",
        "knowledge_counts": counts,
    })


@app.get("/health")
def health():
    ensure_storage()
    return jsonify({"ok": True, "status": "healthy", "creator": CREATOR})


@app.post("/api/teach")
def api_teach():
    body = request.get_json(silent=True) or {}
    domain = str(body.get("domain", "chat")).strip().lower()
    if domain not in DOMAIN_FILES:
        domain = "chat"
    question = " ".join(str(body.get("question", "")).strip().lower().split())
    answer = str(body.get("answer", "")).strip()
    if not question or not answer:
        return jsonify({"ok": False, "error": "question and answer are required"}), 400

    kb = load_domain_knowledge(domain)
    kb[question] = answer
    save_domain_knowledge(domain, kb)
    return jsonify({
        "ok": True,
        "domain": domain,
        "knowledge_file": f"knowledge/{domain}.json",
        "saved_question": question,
        "total_entries": len(kb),
    })


@app.post("/api/chat")
def api_chat():
    body = request.get_json(silent=True) or {}
    session_id = str(body.get("session_id", "default")).strip() or "default"
    message = str(body.get("message", "")).strip()
    if not message:
        return jsonify({"ok": False, "error": "message is required"}), 400
    return jsonify(process_message(session_id, message))


@app.post("/api/stream")
def api_stream():
    body = request.get_json(silent=True) or {}
    session_id = str(body.get("session_id", "default")).strip() or "default"
    message = str(body.get("message", "")).strip()
    if not message:
        return jsonify({"ok": False, "error": "message is required"}), 400

    payload = process_message(session_id, message)
    text = str(payload.get("reply", ""))

    @stream_with_context
    def event_stream():
        for chunk in text.split(" "):
            yield f"data: {json.dumps({'token': chunk + ' '}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'done': True, 'meta': payload}, ensure_ascii=False)}\n\n"

    return Response(event_stream(), mimetype="text/event-stream")


@app.post("/api/reset")
def api_reset():
    body = request.get_json(silent=True) or {}
    session_id = str(body.get("session_id", "default")).strip() or "default"
    SESSIONS.pop(session_id, None)
    return jsonify({"ok": True, "session_id": session_id, "reset": True})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port, debug=False)

# === KAILI_ENGINE_BRIDGE_HOOK ===
import re as _re_bridge
from kaili_server_bridge import guard_request as _guard_req, route_smart_command as _route_cmd

def handle_message_with_engines(client_key: str, message: str):
    guard = _guard_req(client_key, message)
    if not guard.get("ok"):
        return guard["reply"]
    normalized = _re_bridge.sub(r"√\s*(\d+(?:\.\d+)?)", r"sqrt(\1)", (message or "").strip())
    routed = _route_cmd(normalized)
    if routed and routed.get("handled"):
        return routed["reply"]
    return None

# === KAILI_ENGINE_BRIDGE_HOOK_V2 ===
from kaili_server_bridge import guard_request as _guard_v2, route_smart_command as _route_v2

def kaili_smart_answer(client_key: str, message: str):
    g = _guard_v2(client_key, message)
    if not g.get("ok"):
        return g["reply"]
    r = _route_v2(message)
    if r and r.get("handled"):
        return r["reply"]
    return None


# --- KAILI MP4 VIDEO RENDERER (/render-video) ---
import subprocess as _kaili_subprocess
import uuid as _kaili_uuid

_KAILI_VIDEO_DIR = "/tmp/kaili_renders"
os.makedirs(_KAILI_VIDEO_DIR, exist_ok=True)

def render_kaili_mp4(prompt_text: str, duration: int = 5) -> str:
    safe_text = (prompt_text or "KAILI AI - BOSS").replace("'", "").replace(":", " ").replace("\\", " ")[:60]
    dur = max(1, min(int(duration or 5), 30))
    out_path = os.path.join(_KAILI_VIDEO_DIR, f"kaili_{_kaili_uuid.uuid4().hex[:8]}.mp4")
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=#06101a:s=1280x720:d={dur}",
        "-vf", f"drawtext=text='{safe_text}':fontcolor=white:fontsize=40:x=(w-text_w)/2:y=(h-text_h)/2",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        out_path
    ]
    _kaili_subprocess.run(cmd, check=True, stdout=_kaili_subprocess.DEVNULL, stderr=_kaili_subprocess.DEVNULL)
    return out_path

if "app" in globals() and "/render-video" not in src:
    @app.route("/render-video", methods=["POST"])
    def api_render_video():
        data = request.get_json(silent=True) or {}
        prompt = data.get("prompt") or data.get("text") or "KAILI AI - BOSS"
        duration = data.get("duration") or 5
        try:
            mp4_path = render_kaili_mp4(prompt, duration=int(duration))
            filename = os.path.basename(mp4_path)
            return jsonify({
                "ok": True,
                "status": "rendered",
                "file": filename,
                "path": mp4_path,
                "message": f"Boss, {filename} ready hai."
            })
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500
# --- END KAILI MP4 VIDEO RENDERER ---

