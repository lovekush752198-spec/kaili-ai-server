import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional

from kaili_app_builder import handle_app_command
from kaili_server_bridge import guard_request, normalize_math_text, route_smart_command
from kaili_ultimate_core import CREATOR, GREETING, self_heal_knowledge_dir
from kaili_web_builder import build_website_project


def _load_knowledge_entries(knowledge_dir: str = "knowledge") -> List[Dict[str, str]]:
    self_heal_knowledge_dir(knowledge_dir)
    entries: List[Dict[str, str]] = []
    if not os.path.isdir(knowledge_dir):
        return entries

    for fname in sorted(os.listdir(knowledge_dir)):
        if not fname.endswith(".json"):
            continue
        domain = fname[:-5]
        fpath = os.path.join(knowledge_dir, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        if isinstance(data, dict):
            for k, v in data.items():
                entries.append({"domain": domain, "q": str(k), "a": str(v)})
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    q = item.get("q") or item.get("question") or item.get("prompt") or item.get("input") or ""
                    a = item.get("a") or item.get("answer") or item.get("reply") or item.get("response") or ""
                    if q and a:
                        entries.append({"domain": domain, "q": str(q), "a": str(a)})
    return entries


def _search_knowledge(query: str, knowledge_dir: str = "knowledge") -> Optional[str]:
    q_clean = re.sub(r"[^\w\s\u0900-\u097f]+", " ", (query or "").lower()).strip()
    if not q_clean:
        return None
    q_tokens = {t for t in q_clean.split() if len(t) > 1}
    if not q_tokens:
        return None

    best_score = 0.0
    best_ans: Optional[str] = None

    for item in _load_knowledge_entries(knowledge_dir):
        k_clean = re.sub(r"[^\w\s\u0900-\u097f]+", " ", item["q"].lower()).strip()
        if not k_clean:
            continue
        if q_clean == k_clean:
            return item["a"]
        if k_clean in q_clean or q_clean in k_clean:
            score = 0.85
        else:
            k_tokens = {t for t in k_clean.split() if len(t) > 1}
            if not k_tokens:
                continue
            overlap = len(q_tokens & k_tokens)
            score = overlap / max(1, len(q_tokens | k_tokens))

        if score > best_score and score >= 0.45:
            best_score = score
            best_ans = item["a"]

    return best_ans


def _try_builder_command(text: str) -> Optional[str]:
    t = (text or "").strip()
    low = t.lower()

    app_res = handle_app_command(t)
    if app_res and app_res.get("ok"):
        files_txt = ", ".join(app_res.get("files", []))
        return (
            f"{GREETING}, Mini App '{app_res.get('app_name')}' taiyar hai!\n"
            f"Folder: {app_res.get('app_dir')}\n"
            f"Files: {files_txt}"
        )

    for prefix in ("website banao:", "create website:", "build website:", "वेबसाइट बनाओ:"):
        if low.startswith(prefix):
            topic = t[len(prefix):].strip() or "KAILI Web Showcase"
            web_res = build_website_project(topic=topic, brand_name="KAILI AI")
            if web_res.get("ok"):
                files_txt = ", ".join(web_res.get("files", []))
                return (
                    f"{GREETING}, Website '{web_res.get('topic')}' taiyar hai!\n"
                    f"Folder: {web_res.get('site_dir')}\n"
                    f"Files: {files_txt}"
                )

    return None


from kaili_unstoppable_voice import build_unstoppable_reply as _unstoppable_reply

def _smart_general_reply(raw_text: str) -> str:
    return str(_unstoppable_reply(raw_text).get('reply') or '')

def generate_smart_response(message: str, client_key: str = "boss", knowledge_dir: str = "knowledge") -> Dict[str, object]:
    raw = (message or "").strip()
    guard = guard_request(client_key, raw)
    if not guard.get("ok"):
        return {
            "ok": False,
            "mode": "security_guard",
            "reply": str(guard.get("reply")),
        }

    builder_out = _try_builder_command(raw)
    if builder_out:
        return {
            "ok": True,
            "mode": "kaili_app_web_builder",
            "reply": builder_out,
        }

    normalized = normalize_math_text(raw)
    routed = route_smart_command(normalized)
    if routed and routed.get("handled"):
        return {
            "ok": True,
            "mode": routed.get("engine", "smart_route"),
            "reply": str(routed.get("reply")),
        }

    kb_ans = _search_knowledge(raw, knowledge_dir=knowledge_dir)
    if kb_ans:
        return {
            "ok": True,
            "mode": "knowledge_base",
            "reply": f"{GREETING}, {kb_ans}" if not kb_ans.startswith(GREETING) else kb_ans,
        }

    return {
        "ok": True,
        "mode": "smart_conversational_brain",
        "reply": _smart_general_reply(raw),
    }


if __name__ == "__main__":
    r = generate_smart_response("app banao: Boss Calculator - Simple calculator app")
    print(r["reply"])
