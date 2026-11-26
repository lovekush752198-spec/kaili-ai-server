import os
import time
from flask import Flask, request, jsonify, Response, stream_with_context
from google import genai
from google.genai import types

app = Flask(__name__)

CREATOR_NAME = "LAVKUSH KUMAR"
DEFAULT_GREETING = "Boss"
DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash").strip()

SESSIONS = {}
MAX_HISTORY_TURNS = 16
SESSION_TTL_SECONDS = 3600

KAILI_SYSTEM_PROMPT = (
    "Tum KAILI AI ho - ek tez, samajhdar, grounded aur madadgar AI assistant, "
    "jise LAVKUSH KUMAR (Bijli Creations) ne banaya hai. "
    "User ko seedha, saaf aur kaam ka jawab do. "
    "Agar user Hindi ya Hinglish mein baat kare to natural Hindi/Hinglish mein jawab do, "
    "aur English mein puche to English mein jawab do. "
    "Pichli baatcheet ka context yaad rakho aur zaroorat padne par Boss ya Malik keh kar sambodhit karo."
)

MULTI_FILE_RULES = (
    "Jab user multiple files ya project maange, to har file ko alag se likho:\n"
    "FILE: path/to/filename.ext\n"
    "--- START FILE ---\n"
    "code yahan\n"
    "--- END FILE ---\n"
    "Har file ka naam, path aur imports aapas mein consistent rakho."
)


def get_api_key():
    return os.environ.get("GEMINI_API_KEY", "").strip()


def get_client():
    api_key = get_api_key()
    if not api_key:
        return None
    return genai.Client(api_key=api_key)


def cleanup_sessions():
    now = time.time()
    expired = [
        sid for sid, data in SESSIONS.items()
        if now - data["updated_at"] > SESSION_TTL_SECONDS
    ]
    for sid in expired:
        del SESSIONS[sid]


def build_contents(session_id: str, new_prompt: str):
    cleanup_sessions()
    session = SESSIONS.setdefault(
        session_id,
        {"updated_at": time.time(), "messages": []},
    )
    session["updated_at"] = time.time()

    contents = []
    for item in session["messages"][-(MAX_HISTORY_TURNS * 2):]:
        contents.append(
            types.Content(
                role=item["role"],
                parts=[types.Part.from_text(text=item["text"])],
            )
        )

    contents.append(
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=new_prompt)],
        )
    )
    return contents, session


def save_turn(session: dict, user_text: str, assistant_text: str):
    session["messages"].append({"role": "user", "text": user_text})
    session["messages"].append({"role": "model", "text": assistant_text})
    if len(session["messages"]) > MAX_HISTORY_TURNS * 2:
        session["messages"] = session["messages"][-(MAX_HISTORY_TURNS * 2):]
    session["updated_at"] = time.time()


def fallback_response(prompt: str, reason: str = "") -> str:
    clean = prompt.strip()
    note = f" ({reason})" if reason else ""
    if not clean:
        return f"{DEFAULT_GREETING}, kripya apna sawal ya command likhein.{note}"
    return (
        f"{DEFAULT_GREETING}, abhi live Gemini model se jawab nahi mil paaya{note}. "
        f"Aapka message mil gaya hai: {clean}. "
        f"API key aur GEMINI_MODEL check karein."
    )


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "service": "KAILI AI Server",
        "status": "ok",
        "version": "2.3",
        "creator": CREATOR_NAME,
        "greeting": DEFAULT_GREETING,
        "default_model": DEFAULT_MODEL,
        "endpoints": [
            "GET /",
            "GET /health",
            "POST /api/chat",
            "POST /api/stream",
            "POST /api/reset",
        ],
    })


@app.route("/health", methods=["GET"])
def health():
    has_key = bool(get_api_key())
    return jsonify({
        "status": "healthy",
        "gemini_configured": has_key,
        "model": DEFAULT_MODEL,
        "active_sessions": len(SESSIONS),
    })


@app.route("/api/reset", methods=["POST"])
def reset_session():
    data = request.get_json(silent=True) or {}
    session_id = str(data.get("session_id") or "default").strip()
    if session_id in SESSIONS:
        del SESSIONS[session_id]
    return jsonify({
        "ok": True,
        "session_id": session_id,
        "message": f"{DEFAULT_GREETING}, session history clear kar di gayi hai.",
    })


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    prompt = (data.get("prompt") or data.get("message") or "").strip()
    session_id = str(data.get("session_id") or "default").strip()
    model_name = (data.get("model") or DEFAULT_MODEL).strip()
    system_override = (data.get("system_instruction") or "").strip()
    mode_type = str(data.get("mode") or "chat").strip().lower()

    if not prompt:
        return jsonify({
            "ok": False,
            "error": "Prompt or message is required",
        }), 400

    client = get_client()
    if client is None:
        return jsonify({
            "ok": True,
            "mode": "fallback",
            "session_id": session_id,
            "reply": fallback_response(prompt, "API key missing"),
        })

    contents, session = build_contents(session_id, prompt)
    sys_instruction = system_override if system_override else KAILI_SYSTEM_PROMPT
    if mode_type == "files":
        sys_instruction = f"{sys_instruction}\n\n{MULTI_FILE_RULES}"

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=sys_instruction,
                temperature=0.7,
            ),
        )
        reply_text = (response.text or "").strip()
        if not reply_text:
            reply_text = fallback_response(prompt, "Empty model response")
        else:
            save_turn(session, prompt, reply_text)

        return jsonify({
            "ok": True,
            "mode": "gemini",
            "model": model_name,
            "session_id": session_id,
            "reply": reply_text,
        })
    except Exception as exc:
        return jsonify({
            "ok": True,
            "mode": "fallback",
            "model": model_name,
            "session_id": session_id,
            "warning": str(exc),
            "reply": fallback_response(prompt, str(exc)),
        })


@app.route("/api/stream", methods=["POST"])
def stream_chat():
    data = request.get_json(silent=True) or {}
    prompt = (data.get("prompt") or data.get("message") or "").strip()
    session_id = str(data.get("session_id") or "default").strip()
    model_name = (data.get("model") or DEFAULT_MODEL).strip()
    system_override = (data.get("system_instruction") or "").strip()

    if not prompt:
        return jsonify({
            "ok": False,
            "error": "Prompt or message is required",
        }), 400

    client = get_client()
    if client is None:
        msg = fallback_response(prompt, "API key missing")
        return Response(msg, mimetype="text/plain; charset=utf-8")

    contents, session = build_contents(session_id, prompt)
    sys_instruction = system_override if system_override else KAILI_SYSTEM_PROMPT

    def generate():
        full_chunks = []
        try:
            for chunk in client.models.generate_content_stream(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=sys_instruction,
                    temperature=0.7,
                ),
            ):
                piece = getattr(chunk, "text", None) or ""
                if piece:
                    full_chunks.append(piece)
                    yield piece
            combined = "".join(full_chunks).strip()
            if combined:
                save_turn(session, prompt, combined)
        except Exception as exc:
            yield f"\n[Error: {exc}]"

    return Response(stream_with_context(generate()), mimetype="text/plain; charset=utf-8")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
