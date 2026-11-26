import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional

from kaili_server_bridge import guard_request, normalize_math_text, route_smart_command
from kaili_ultimate_core import CREATOR, GREETING, self_heal_knowledge_dir


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


def _smart_general_reply(raw_text: str) -> str:
    text = (raw_text or "").strip()
    low = text.lower()

    # Greetings & identity
    if re.search(r"\b(hi|hello|hey|namaste|namaskar|ao|kya haal|kaise ho|kaisi ho)\b", low) or "नमस्ते" in text:
        return (
            f"{GREETING}, मैं KAILI AI हूँ—जिसे {CREATOR} ने तैयार किया है। "
            f"बताइए आज हम किस पर काम करें? गणित/विज्ञान हल करना हो, 4K/3D वीडियो प्लान बनाना हो, "
            f"कोडिंग करनी हो या कोई भी सवाल पूछना हो—बेझिझक बोलिए।"
        )

    if any(k in low for k in ["kaun ho", "tumhara naam", "who are you", "about you", "creator", "kisne banaya"]):
        return (
            f"{GREETING}, मेरा नाम KAILI AI है और मेरे क्रिएटर {CREATOR} हैं। "
            f"मैं गणित, त्रिकोणमिति, विज्ञान गणना, 4K/3D वीडियो डायरेक्शन, कोड सहायता और आपके ज्ञान भंडार के साथ काम करता हूँ।"
        )

    if any(k in low for k in ["time", "samay", "date", "aaj ki tarikh", "waqt"]):
        now = datetime.now().strftime("%d-%m-%Y %I:%M %p")
        return f"{GREETING}, अभी का समय और तारीख है: {now}।"

    # Help / capabilities
    if any(k in low for k in ["help", "madad", "kya kar sakte", "features", "commands"]):
        return (
            f"{GREETING}, मैं आपकी इन चीज़ों में मदद कर सकता हूँ:\n"
            f"1. गणित और विज्ञान: सीधे `2+2`, `√144`, `(18+12)/3`, `trig p=3 b=4`, या `sci force m=5 a=3` लिखें।\n"
            f"2. 4K और 3D वीडियो: `4k plan: ...`, `4k render: ...` या 3D सीन डायरेक्शन।\n"
            f"3. नया ज्ञान सिखाना: `seekho [chat]: सवाल = जवाब` लिखकर आप मुझे कोई भी कस्टम उत्तर सिखा सकते हैं।"
        )

    # Helpful reasoning fallback for open questions
    if len(text) >= 2:
        return (
            f"{GREETING}, आपने \"{text}\" पूछा है। "
            f"अगर यह गणित या विज्ञान से जुड़ा है तो आप समीकरण/मान स्पष्ट लिखें (जैसे `2+2`, `√144`, `trig p=3 b=4`, या `sci force m=4 a=3`), "
            f"और अगर आप चाहते हैं कि मैं इस विशेष वाक्य पर हमेशा एक तय जवाब दूँ, तो लिखें: "
            f"`seekho [chat]: {text} = आपका तय जवाब`।"
        )

    return f"{GREETING}, कृपया अपना सवाल या कमांड लिखें।"


def generate_smart_response(message: str, client_key: str = "boss", knowledge_dir: str = "knowledge") -> Dict[str, object]:
    raw = (message or "").strip()
    guard = guard_request(client_key, raw)
    if not guard.get("ok"):
        return {
            "ok": False,
            "mode": "security_guard",
            "reply": str(guard.get("reply")),
        }

    # 1. Direct math, trig, science, 4K studio routing
    normalized = normalize_math_text(raw)
    routed = route_smart_command(normalized)
    if routed and routed.get("handled"):
        return {
            "ok": True,
            "mode": routed.get("engine", "smart_route"),
            "reply": str(routed.get("reply")),
        }

    # 2. Knowledge base match
    kb_ans = _search_knowledge(raw, knowledge_dir=knowledge_dir)
    if kb_ans:
        return {
            "ok": True,
            "mode": "knowledge_base",
            "reply": f"{GREETING}, {kb_ans}" if not kb_ans.startswith(GREETING) else kb_ans,
        }

    # 3. Smart conversational response
    return {
        "ok": True,
        "mode": "smart_conversational_brain",
        "reply": _smart_general_reply(raw),
    }


if __name__ == "__main__":
    samples = ["2+2", "√144", "नमस्ते कैली", "tum kaun ho", "kya kar sakte ho"]
    for s in samples:
        out = generate_smart_response(s)
        print(f"Q: {s}\nA ({out['mode']}): {out['reply']}\n---")
