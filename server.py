import json
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from flask import Flask, Response, jsonify, request, stream_with_context

app = Flask(__name__)

# ==============================================================================
# LAYER 7: RUNTIME & HEALTH LAYER (Config, Memory Limits, Health)
# ==============================================================================
SERVER_NAME = "KAILI AI Server"
SERVER_VERSION = "5.0-own-master"
CREATOR_NAME = os.getenv("CREATOR_NAME", "LAVKUSH KUMAR")
DEFAULT_GREETING = os.getenv("DEFAULT_GREETING", "Boss")
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "3600"))
MAX_HISTORY_TURNS = int(os.getenv("MAX_HISTORY_TURNS", "12"))
KNOWLEDGE_FILE = os.getenv("KAILI_KNOWLEDGE_FILE", "kaili_knowledge.json")

START_TIME = time.time()


def load_saved_knowledge() -> Dict[str, str]:
    if not os.path.exists(KNOWLEDGE_FILE):
        return {}
    try:
        with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return {
                    " ".join(str(k).strip().lower().split()): str(v).strip()
                    for k, v in data.items()
                    if str(k).strip() and str(v).strip()
                }
    except Exception:
        pass
    return {}


def save_knowledge_entry(question: str, answer: str) -> bool:
    key = " ".join(question.strip().lower().split())
    val = answer.strip()
    if not key or not val:
        return False
    data = load_saved_knowledge()
    data[key] = val
    try:
        with open(KNOWLEDGE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def get_runtime_health() -> Dict[str, Any]:
    saved = load_saved_knowledge()
    return {
        "ok": True,
        "service": SERVER_NAME,
        "version": SERVER_VERSION,
        "architecture": "7-layer-own",
        "external_ai": False,
        "creator": CREATOR_NAME,
        "greeting": DEFAULT_GREETING,
        "uptime_seconds": int(time.time() - START_TIME),
        "active_sessions": len(SESSIONS),
        "saved_knowledge_count": len(saved),
    }


# ==============================================================================
# LAYER 2: SESSION & IDENTITY LAYER (Session Memory & KAILI Identity)
# ==============================================================================
SESSIONS: Dict[str, Dict[str, Any]] = {}


def cleanup_sessions() -> None:
    now = time.time()
    expired = [
        sid for sid, info in SESSIONS.items()
        if now - info.get("updated_at", now) > SESSION_TTL_SECONDS
    ]
    for sid in expired:
        del SESSIONS[sid]


def get_or_create_session(session_id: str) -> Dict[str, Any]:
    cleanup_sessions()
    sid = (session_id or "default").strip() or "default"
    session = SESSIONS.setdefault(
        sid, {"created_at": time.time(), "updated_at": time.time(), "messages": []}
    )
    session["updated_at"] = time.time()
    return session


def append_message(session: Dict[str, Any], role: str, text: str) -> None:
    msgs: List[Dict[str, Any]] = session.setdefault("messages", [])
    msgs.append({"role": role, "text": text, "ts": time.time()})
    max_items = MAX_HISTORY_TURNS * 2
    if len(msgs) > max_items:
        session["messages"] = msgs[-max_items:]


def reset_session(session_id: str) -> None:
    sid = (session_id or "default").strip() or "default"
    if sid in SESSIONS:
        del SESSIONS[sid]


# ==============================================================================
# LAYER 3: OWN KNOWLEDGE & RULE ENGINE (Aapka Gyan, Aapke Niyam)
# ==============================================================================
OWN_RULES: List[Tuple[List[str], str]] = [
    (
        ["kaun ho", "tum kaun", "who are you", "apna parichay", "introduce yourself"],
        f"{DEFAULT_GREETING}, main KAILI AI hoon — {CREATOR_NAME} ka apna swatantra AI system. Main kisi bahari AI par nirbhar nahi hoon; mera gyan aur niyam aap khud banate aur sikhate hain.",
    ),
    (
        ["creator", "banaya", "kisne banaya", "owner", "malik kaun"],
        f"{DEFAULT_GREETING}, mere creator {CREATOR_NAME} hain, aur main aapke nirdesh par {DEFAULT_GREETING} ke roop mein kaam karta hoon.",
    ),
    (
        ["ready", "taiyar", "kya haal", "kaise ho", "status"],
        f"{DEFAULT_GREETING}, main bilkul ready hoon! Apna 7-layer KAILI AI engine aapke gyan aur command ke saath active hai.",
    ),
]


def _tokenize(text: str) -> List[str]:
    return [w for w in re.findall(r"[a-z0-9\u0900-\u097f]+", text.lower()) if len(w) >= 2]


def query_own_brain(prompt: str) -> Optional[Tuple[str, str]]:
    clean = " ".join(prompt.strip().split())
    lower = clean.lower()

    # 1. User dwara diya gaya exact ya substring saved gyan
    saved = load_saved_knowledge()
    if lower in saved:
        return saved[lower], "layer3-own-exact"

    for k, v in saved.items():
        if len(k) >= 3 and (k in lower or lower in k):
            return v, "layer3-own-match"

    # 2. Keyword/token overlap se saved gyan mein best match dhoondhna
    q_tokens = set(_tokenize(lower))
    if q_tokens:
        best_score = 0.0
        best_ans: Optional[str] = None
        for k, v in saved.items():
            k_tokens = set(_tokenize(k))
            if not k_tokens:
                continue
            overlap = len(q_tokens.intersection(k_tokens))
            if overlap > 0:
                score = overlap / max(len(q_tokens), len(k_tokens))
                if score > best_score and score >= 0.5:
                    best_score = score
                    best_ans = v
        if best_ans:
            return best_ans, "layer3-own-smart-match"

    # 3. Apne built-in rules
    for keywords, reply in OWN_RULES:
        for kw in keywords:
            if kw in lower:
                return reply, "layer3-own-rule"

    # 4. Apna math engine
    math_match = re.fullmatch(r"[\d\s\+\-\*\/\(\)\.]+", lower)
    if math_match and re.search(r"\d", lower):
        try:
            result = eval(lower, {"__builtins__": {}}, {})
            return f"{DEFAULT_GREETING}, iska uttar hai: {result}", "layer3-own-math"
        except Exception:
            pass

    return None


def parse_teach_command(prompt: str) -> Optional[Tuple[str, str]]:
    """
    Aap khud gyan daalne ke liye likh sakte hain:
    seekho: sawal = jawab
    ya
    gyan: sawal = jawab
    """
    m = re.match(
        r"^\s*(?:seekho|sikhayo|gyan|learn|yaad rakho)\s*:\s*(.+?)\s*=\s*(.+?)\s*$",
        prompt,
        re.IGNORECASE | re.DOTALL,
    )
    if not m:
        return None
    q = " ".join(m.group(1).strip().split())
    a = m.group(2).strip()
    if not q or not a:
        return None
    return q, a


# ==============================================================================
# LAYER 4 & 5: OWN ROUTER & SELF-ORGANIZING ENGINE (No External AI)
# ==============================================================================
def route_and_think(prompt: str, session: Dict[str, Any]) -> Tuple[str, str]:
    teach_pair = parse_teach_command(prompt)
    if teach_pair:
        q, a = teach_pair
        if save_knowledge_entry(q, a):
            return (
                f"{DEFAULT_GREETING}, maine aapka diya hua gyan apne paas surakshit kar liya hai:\n"
                f"• Vishay/Sawal: {q}\n"
                f"• Aapka Gyan/Jawab: {a}",
                "layer3-own-learned",
            )
        return f"{DEFAULT_GREETING}, gyan save karne mein samasya aayi.", "layer3-own-error"

    own = query_own_brain(prompt)
    if own:
        return own

    turns = len([m for m in session.get("messages", []) if m.get("role") == "user"])
    snippet = " ".join(prompt.strip().split())[:90]
    return (
        f"{DEFAULT_GREETING}, '{snippet}' par mere paas abhi aapka koi saved gyan ya rule darj nahi hai "
        f"(is session mein {turns} baatein ho chuki hain).\n"
        f"Aap mujhe apna gyan de sakte hain: `seekho: {snippet} = aapka jawab`",
        "layer4-own-awaiting-knowledge",
    )


# ==============================================================================
# LAYER 6: RESPONSE & MEMORY FORMATTER LAYER
# ==============================================================================
def format_chat_payload(session_id: str, reply: str, source: str) -> Dict[str, Any]:
    return {
        "ok": True,
        "architecture": "7-layer-own",
        "mode": "own-ai-master",
        "external_ai": False,
        "source": source,
        "creator": CREATOR_NAME,
        "greeting": DEFAULT_GREETING,
        "session_id": session_id,
        "reply": reply,
    }


# ==============================================================================
# LAYER 1: GATEWAY & REQUEST LAYER (Routes)
# ==============================================================================
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "service": SERVER_NAME,
        "status": "ok",
        "version": SERVER_VERSION,
        "architecture": "7-layer-own",
        "external_ai": False,
        "creator": CREATOR_NAME,
        "greeting": DEFAULT_GREETING,
        "endpoints": [
            "GET /",
            "GET /health",
            "POST /api/chat",
            "POST /api/stream",
            "POST /api/teach",
            "POST /api/reset",
        ],
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify(get_runtime_health())


@app.route("/api/teach", methods=["POST"])
def api_teach():
    data = request.get_json(silent=True) or {}
    question = str(data.get("question") or "").strip()
    answer = str(data.get("answer") or "").strip()
    if not question or not answer:
        return jsonify({"ok": False, "error": "Both 'question' and 'answer' are required"}), 400
    ok = save_knowledge_entry(question, answer)
    return jsonify({"ok": ok, "saved_question": question, "saved_answer": answer})


@app.route("/api/reset", methods=["POST"])
def api_reset():
    data = request.get_json(silent=True) or {}
    session_id = str(data.get("session_id") or "default").strip() or "default"
    reset_session(session_id)
    return jsonify({"ok": True, "session_id": session_id, "status": "reset"})


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json(silent=True) or {}
    prompt = str(data.get("message") or data.get("prompt") or "").strip()
    session_id = str(data.get("session_id") or "default").strip() or "default"

    if not prompt:
        return jsonify({"ok": False, "error": "Message or prompt is required"}), 400

    session = get_or_create_session(session_id)
    append_message(session, "user", prompt)

    reply, source = route_and_think(prompt, session)
    append_message(session, "assistant", reply)

    return jsonify(format_chat_payload(session_id, reply, source))


@app.route("/api/stream", methods=["POST"])
def api_stream():
    data = request.get_json(silent=True) or {}
    prompt = str(data.get("message") or data.get("prompt") or "").strip()
    session_id = str(data.get("session_id") or "default").strip() or "default"

    if not prompt:
        return jsonify({"ok": False, "error": "Message or prompt is required"}), 400

    session = get_or_create_session(session_id)
    append_message(session, "user", prompt)
    reply, source = route_and_think(prompt, session)
    append_message(session, "assistant", reply)

    def generate():
        words = reply.split(" ")
        for i, w in enumerate(words):
            chunk = w + (" " if i < len(words) - 1 else "")
            payload = json.dumps({"ok": True, "chunk": chunk, "source": source}, ensure_ascii=False)
            yield f"data: {payload}\n\n"
        yield f"data: {json.dumps({'ok': True, 'done': True, 'session_id': session_id, 'source': source}, ensure_ascii=False)}\n\n"

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
