import json
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from flask import Flask, Response, jsonify, request, stream_with_context

app = Flask(__name__)

# ==============================================================================
# LAYER 7: RUNTIME & PERSISTENCE LAYER
# ==============================================================================
SERVER_NAME = "KAILI AI Server"
SERVER_VERSION = "6.0-7layer-domains"
CREATOR_NAME = os.getenv("CREATOR_NAME", "LAVKUSH KUMAR")
DEFAULT_GREETING = os.getenv("DEFAULT_GREETING", "Boss")
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "3600"))
MAX_HISTORY_TURNS = int(os.getenv("MAX_HISTORY_TURNS", "12"))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KNOWLEDGE_DIR = os.path.join(BASE_DIR, os.getenv("KAILI_KNOWLEDGE_DIR", "knowledge"))

DOMAIN_FILES: Dict[str, str] = {
    "chat": os.path.join(KNOWLEDGE_DIR, "chat.json"),
    "study": os.path.join(KNOWLEDGE_DIR, "study.json"),
    "coding": os.path.join(KNOWLEDGE_DIR, "coding.json"),
}

START_TIME = time.time()


def ensure_knowledge_files() -> None:
    os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
    for domain, path in DOMAIN_FILES.items():
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False, indent=2)


def get_runtime_health() -> Dict[str, Any]:
    ensure_knowledge_files()
    counts: Dict[str, int] = {}
    for domain, path in DOMAIN_FILES.items():
        counts[domain] = len(load_domain_knowledge(domain))
    return {
        "ok": True,
        "service": SERVER_NAME,
        "version": SERVER_VERSION,
        "architecture": "7-layer-domains",
        "creator": CREATOR_NAME,
        "greeting": DEFAULT_GREETING,
        "uptime_seconds": int(time.time() - START_TIME),
        "active_sessions": len(SESSIONS),
        "domain_knowledge_counts": counts,
        "total_saved_entries": sum(counts.values()),
    }


# ==============================================================================
# LAYER 2: SESSION & IDENTITY LAYER
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
# LAYER 3: TOPIC CLASSIFIER LAYER (chat / study / coding)
# ==============================================================================
CODING_KEYWORDS = {
    "code", "coding", "python", "c#", "csharp", "html", "css", "javascript", "js",
    "flask", "gunicorn", "api", "json", "git", "github", "termux", "unity",
    "error", "bug", "function", "def ", "class ", "server", "endpoint", "curl"
}

STUDY_KEYWORDS = {
    "padhai", "study", "chapter", "lesson", "formula", "theorem", "exam",
    "question", "answer", "definition", "paribhasha", "science", "history",
    "math", "maths", "physics", "chemistry", "biology", "note", "notes", "samjhao"
}


def classify_topic(text: str) -> str:
    lower = text.lower()
    coding_hits = sum(1 for kw in CODING_KEYWORDS if kw in lower)
    study_hits = sum(1 for kw in STUDY_KEYWORDS if kw in lower)

    if coding_hits > study_hits and coding_hits >= 1:
        return "coding"
    if study_hits > coding_hits and study_hits >= 1:
        return "study"
    return "chat"


# ==============================================================================
# LAYER 4: DOMAIN KNOWLEDGE ENGINE (Separate Files per Topic)
# ==============================================================================
BUILTIN_DOMAIN_RULES: Dict[str, List[Tuple[List[str], str]]] = {
    "chat": [
        (
            ["kaun ho", "tum kaun", "who are you", "apna parichay"],
            f"{DEFAULT_GREETING}, main KAILI AI hoon — {CREATOR_NAME} ka apna 7-layer AI system. Mera gyan chat, study aur coding ki alag-alag files mein rakha jata hai.",
        ),
        (
            ["creator", "kisne banaya", "owner", "malik"],
            f"{DEFAULT_GREETING}, mere creator {CREATOR_NAME} hain, aur main aapko {DEFAULT_GREETING} keh kar sambodhit karta hoon.",
        ),
        (
            ["ready", "taiyar", "kya haal", "kaise ho"],
            f"{DEFAULT_GREETING}, main bilkul ready hoon! Chat, study aur coding teeno domain active hain.",
        ),
    ],
    "study": [
        (
            ["padhai", "study", "notes"],
            f"{DEFAULT_GREETING}, padhai ka gyan `knowledge/study.json` mein save hota hai. Aap `seekho: <topic> = <samajh/notes>` se naya study gyan jod sakte hain.",
        ),
    ],
    "coding": [
        (
            ["server", "flask", "gunicorn"],
            f"{DEFAULT_GREETING}, coding ka gyan `knowledge/coding.json` mein save hota hai. Aap `seekho: <concept/command> = <solution>` se naya coding gyan jod sakte hain.",
        ),
    ],
}


def normalize_domain(domain: Optional[str]) -> str:
    d = (domain or "").strip().lower()
    return d if d in DOMAIN_FILES else "chat"


def load_domain_knowledge(domain: str) -> Dict[str, str]:
    ensure_knowledge_files()
    d = normalize_domain(domain)
    path = DOMAIN_FILES[d]
    try:
        with open(path, "r", encoding="utf-8") as f:
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


def save_domain_knowledge(domain: str, question: str, answer: str) -> bool:
    ensure_knowledge_files()
    d = normalize_domain(domain)
    key = " ".join(question.strip().lower().split())
    val = answer.strip()
    if not key or not val:
        return False
    data = load_domain_knowledge(d)
    data[key] = val
    try:
        with open(DOMAIN_FILES[d], "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def _tokens(text: str) -> List[str]:
    return [w for w in re.findall(r"[a-z0-9\u0900-\u097f\+\#]+", text.lower()) if len(w) >= 2]


def search_in_domain(domain: str, prompt: str) -> Optional[Tuple[str, str]]:
    clean = " ".join(prompt.strip().split())
    lower = clean.lower()
    data = load_domain_knowledge(domain)

    if lower in data:
        return data[lower], f"layer4-{domain}-exact"

    for k, v in data.items():
        if len(k) >= 3 and (k in lower or lower in k):
            return v, f"layer4-{domain}-substring"

    q_toks = set(_tokens(lower))
    if q_toks:
        best_score = 0.0
        best_val: Optional[str] = None
        for k, v in data.items():
            k_toks = set(_tokens(k))
            if not k_toks:
                continue
            overlap = len(q_toks.intersection(k_toks))
            if overlap > 0:
                score = overlap / max(len(q_toks), len(k_toks))
                if score > best_score and score >= 0.5:
                    best_score = score
                    best_val = v
        if best_val:
            return best_val, f"layer4-{domain}-token-match"

    for keywords, reply in BUILTIN_DOMAIN_RULES.get(domain, []):
        for kw in keywords:
            if kw in lower:
                return reply, f"layer4-{domain}-rule"

    return None


def parse_teach_command(prompt: str) -> Optional[Tuple[str, str, str]]:
    """
    Formats:
    seekho: sawal = jawab
    seekho [coding]: sawal = jawab
    seekho [study]: sawal = jawab
    """
    m = re.match(
        r"^\s*(?:seekho|sikhayo|gyan|learn)\s*(?:\[\s*(chat|study|coding)\s*\])?\s*:\s*(.+?)\s*=\s*(.+?)\s*$",
        prompt,
        re.IGNORECASE | re.DOTALL,
    )
    if not m:
        return None
    explicit_domain = m.group(1)
    q = " ".join(m.group(2).strip().split())
    a = m.group(3).strip()
    if not q or not a:
        return None
    domain = normalize_domain(explicit_domain) if explicit_domain else classify_topic(f"{q} {a}")
    return domain, q, a


# ==============================================================================
# LAYER 5: REASONING & COMPOSITION LAYER
# ==============================================================================
def compose_reply(prompt: str, session: Dict[str, Any]) -> Tuple[str, str, str]:
    teach = parse_teach_command(prompt)
    if teach:
        domain, q, a = teach
        if save_domain_knowledge(domain, q, a):
            rel_file = f"knowledge/{domain}.json"
            return (
                f"{DEFAULT_GREETING}, maine yeh gyan `{rel_file}` mein save kar liya hai:\n"
                f"• Domain: {domain}\n"
                f"• Sawal/Topic: {q}\n"
                f"• Jawab: {a}",
                "layer5-saved-domain-knowledge",
                domain,
            )
        return f"{DEFAULT_GREETING}, gyan save karne mein dikqat aayi.", "layer5-save-error", domain

    primary_domain = classify_topic(prompt)

    # Pehle primary domain file mein dekhein
    found = search_in_domain(primary_domain, prompt)
    if found:
        reply, src = found
        return reply, f"layer5->{src}", primary_domain

    # Agar primary domain mein nahi mila, toh baaki 2 domain files mein check karein
    for other_domain in ("chat", "study", "coding"):
        if other_domain == primary_domain:
            continue
        found_other = search_in_domain(other_domain, prompt)
        if found_other:
            reply, src = found_other
            return reply, f"layer5->{src}", other_domain

    # Math support
    lower = prompt.strip().lower()
    if re.fullmatch(r"[\d\s\+\-\*\/\(\)\.]+", lower) and re.search(r"\d", lower):
        try:
            ans = eval(lower, {"__builtins__": {}}, {})
            return f"{DEFAULT_GREETING}, iska parinaam hai: {ans}", "layer5-math-engine", "study"
        except Exception:
            pass

    turns = len([m for m in session.get("messages", []) if m.get("role") == "user"])
    snippet = " ".join(prompt.strip().split())[:80]
    return (
        f"{DEFAULT_GREETING}, `{snippet}` ka gyan abhi `knowledge/{primary_domain}.json` mein darj nahi hai "
        f"(session turns: {turns}).\n"
        f"Aap likh kar sikha sakte hain: `seekho [{primary_domain}]: {snippet} = aapka jawab`",
        "layer5-no-entry-yet",
        primary_domain,
    )


# ==============================================================================
# LAYER 6: RESPONSE & STREAM FORMATTER LAYER
# ==============================================================================
def format_chat_payload(session_id: str, domain: str, reply: str, source: str) -> Dict[str, Any]:
    return {
        "ok": True,
        "architecture": "7-layer-domains",
        "domain": domain,
        "knowledge_file": f"knowledge/{domain}.json",
        "source": source,
        "creator": CREATOR_NAME,
        "greeting": DEFAULT_GREETING,
        "session_id": session_id,
        "reply": reply,
    }


# ==============================================================================
# LAYER 1: GATEWAY & REQUEST LAYER
# ==============================================================================
@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "service": SERVER_NAME,
        "status": "ok",
        "version": SERVER_VERSION,
        "architecture": "7-layer-domains",
        "creator": CREATOR_NAME,
        "greeting": DEFAULT_GREETING,
        "domains": ["chat", "study", "coding"],
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
    domain_raw = data.get("domain")
    if not question or not answer:
        return jsonify({"ok": False, "error": "Both 'question' and 'answer' are required"}), 400
    domain = normalize_domain(domain_raw) if domain_raw else classify_topic(f"{question} {answer}")
    ok = save_domain_knowledge(domain, question, answer)
    return jsonify({
        "ok": ok,
        "domain": domain,
        "knowledge_file": f"knowledge/{domain}.json",
        "saved_question": question,
        "saved_answer": answer,
    })


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

    reply, source, domain = compose_reply(prompt, session)
    append_message(session, "assistant", reply)

    return jsonify(format_chat_payload(session_id, domain, reply, source))


@app.route("/api/stream", methods=["POST"])
def api_stream():
    data = request.get_json(silent=True) or {}
    prompt = str(data.get("message") or data.get("prompt") or "").strip()
    session_id = str(data.get("session_id") or "default").strip() or "default"

    if not prompt:
        return jsonify({"ok": False, "error": "Message or prompt is required"}), 400

    session = get_or_create_session(session_id)
    append_message(session, "user", prompt)
    reply, source, domain = compose_reply(prompt, session)
    append_message(session, "assistant", reply)

    def generate():
        words = reply.split(" ")
        for i, w in enumerate(words):
            chunk = w + (" " if i < len(words) - 1 else "")
            payload = json.dumps(
                {"ok": True, "chunk": chunk, "domain": domain, "source": source},
                ensure_ascii=False,
            )
            yield f"data: {payload}\n\n"
        yield (
            f"data: {json.dumps({'ok': True, 'done': True, 'session_id': session_id, 'domain': domain, 'source': source}, ensure_ascii=False)}\n\n"
        )

    return Response(stream_with_context(generate()), mimetype="text/event-stream")


if __name__ == "__main__":
    ensure_knowledge_files()
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
