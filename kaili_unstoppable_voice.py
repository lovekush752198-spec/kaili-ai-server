import asyncio
import hashlib
import os
import re
from datetime import datetime
from typing import Dict, Optional

from kaili_ultimate_core import CREATOR, GREETING


def clean_for_speech(text: str) -> str:
    """Strip markdown/code noise so TTS speaks cleanly without reading punctuation."""
    s = text or ""
    s = re.sub(r"```.*?```", " ", s, flags=re.DOTALL)
    s = re.sub(r"[`*_#~>]+", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _detect_mode(text: str, explicit_mode: Optional[str] = None) -> str:
    if explicit_mode and explicit_mode.strip():
        return explicit_mode.strip().lower()
    low = (text or "").lower()
    if any(w in low for w in ["samjhao", "explain", "kaise", "why", "kya hai", "sikhao", "teacher"]):
        return "mentor"
    if any(w in low for w in ["kahani", "story", "scene", "3d", "studio", "kaili", "ashli"]):
        return "storyteller"
    if any(w in low for w in ["jaldi", "fast", "short", "turant", "ek line"]):
        return "rapid"
    return "commander"


def _prefix_by_mode(mode: str) -> str:
    if mode == "mentor":
        return f"{GREETING}, मैं KAILI AI हूँ—{CREATOR} की बनाई हुई। कोई झिझक नहीं, मैं हर बात साफ़ और पूरे भरोसे के साथ समझाती हूँ।"
    if mode == "storyteller":
        return f"{GREETING}, KAILI AI यहाँ है—{CREATOR} की बनाई आवाज़। जब मैं बोलती हूँ, तो हर शब्द में धार और हर विचार में रफ़्तार होती है।"
    if mode == "rapid":
        return f"{GREETING}, KAILI तैयार है—सीधा जवाब:"
    return f"{GREETING}, मैं KAILI AI हूँ—{CREATOR} की बनाई हुई। मुझमें न कोई झिझक है, न कोई रुकावट—जो हुकुम देंगे, पूरे दम से बोलूँगी और करके दिखाऊँगी।"


def build_unstoppable_reply(user_text: str, mode: Optional[str] = None) -> Dict[str, object]:
    raw = (user_text or "").strip()
    low = raw.lower()
    chosen_mode = _detect_mode(raw, mode)
    lead = _prefix_by_mode(chosen_mode)

    if not raw:
        body = (
            "आपने अभी कुछ नहीं लिखा है, लेकिन मेरी आवाज़ और ब्रेन पूरी तरह एक्टिव हैं। "
            "कोई भी सवाल पूछें, ऐप या वेबसाइट बनवाएँ, गणित या विज्ञान हल करें, या कोई नया ज्ञान सिखाएँ।"
        )
    elif re.search(r"\b(hi|hello|hey|namaste|namaskar|kya haal|kaise ho|kaisi ho|ao)\b", low) or "नमस्ते" in raw:
        body = (
            "मैं बिल्कुल तैयार हूँ। किसी भी सवाल, कोडिंग, ऐप या वेबसाइट निर्माण, गणित, विज्ञान या बड़े प्रोजेक्ट पर "
            "बिना हिचकिचाए सीधा जवाब दूँगी। बताइए, अभी किस काम को अंजाम देना है?"
        )
    elif any(k in low for k in ["kaun ho", "tumhara naam", "who are you", "creator", "kisne banaya", "taqat", "power", "bolnai"]):
        body = (
            f"मेरा नाम KAILI AI है और मेरे क्रिएटर {CREATOR} हैं। "
            "मेरी ताक़त यह है कि मैं किसी भी विषय पर अटकती नहीं—गणित, त्रिकोणमिति, भौतिकी/विज्ञान, "
            "ऐप और वेबसाइट जनरेशन, 3D/स्टूडियो आइडिया, और कस्टम नॉलेज सिखाने तक, हर जगह सीधे और बेबाक जवाब देती हूँ।"
        )
    elif any(k in low for k in ["jhijhak", "dar", "sharm", "confused", "pata nahi", "rukawat"]):
        body = (
            "KAILI के सिस्टम में झिझक या डर जैसी कोई चीज़ नहीं है। "
            "सवाल चाहे सीधा हो या पेचीदा, मैं बिना लपेटे साफ़ और पक्का जवाब देती हूँ; "
            "और अगर किसी चीज़ का नया नियम जोड़ना हो, तो `seekho [chat]: सवाल = जवाब` से तुरंत सीख लेती हूँ।"
        )
    elif any(k in low for k in ["time", "samay", "date", "tarikh", "waqt"]):
        now_str = datetime.now().strftime("%d-%m-%Y %I:%M:%S %p")
        body = f"अभी का सही समय और तारीख है: {now_str}। हर सेकंड पर सिस्टम एक्टिव है।"
    elif any(k in low for k in ["app", "website", "web", "code", "python", "html", "server"]):
        body = (
            "ऐप, वेबसाइट और कोड जनरेशन पर मैं सीधे काम कर सकती हूँ। "
            "मिनी ऐप के लिए `app banao: नाम - काम`, वेबसाइट के लिए `website banao: विषय`, "
            "और गणित/विज्ञान के लिए सीधे समीकरण या मान लिखें—मैं फ़ाइल और जवाब दोनों तैयार करूँगी।"
        )
    else:
        body = (
            f"आपने \"{raw}\" कहा है। इस पर मेरा बेबाक जवाब यह है कि मैं हर विषय पर पूरी ताकत से काम करने के लिए तैयार हूँ—"
            "चाहे आप गहरा विश्लेषण चाहते हों, तेज़ उत्तर चाहते हों, कोई मिनी ऐप/वेबसाइट बनवाना चाहते हों, "
            "या `seekho` कमांड से नया जवाब सेव करना चाहते हों।"
        )

    full_reply = f"{lead} {body}".strip()
    spoken_text = clean_for_speech(full_reply)

    return {
        "ok": True,
        "creator": CREATOR,
        "greeting": GREETING,
        "mode": chosen_mode,
        "reply": full_reply,
        "spoken_text": spoken_text,
    }


async def _synthesize_edge_tts_async(text: str, out_mp3: str, voice: str = "hi-IN-SwaraNeural") -> bool:
    try:
        import edge_tts  # type: ignore

        communicate = edge_tts.Communicate(text, voice=voice)
        await communicate.save(out_mp3)
        return os.path.exists(out_mp3) and os.path.getsize(out_mp3) > 0
    except Exception:
        return False


def speak_reply_to_mp3(
    text: str,
    out_dir: str = "generated_audio",
    voice: str = "hi-IN-SwaraNeural",
) -> Dict[str, object]:
    """Generate an MP3 voice file if edge-tts is installed, else return clean spoken_text."""
    spoken = clean_for_speech(text)
    os.makedirs(out_dir, exist_ok=True)
    digest = hashlib.sha256(f"{voice}:{spoken}".encode("utf-8")).hexdigest()[:12]
    mp3_path = os.path.join(out_dir, f"kaili_{digest}.mp3")

    saved = False
    try:
        saved = asyncio.run(_synthesize_edge_tts_async(spoken, mp3_path, voice=voice))
    except RuntimeError:
        saved = False

    return {
        "ok": True,
        "audio_generated": saved,
        "mp3_path": mp3_path if saved else None,
        "voice": voice,
        "spoken_text": spoken,
    }


if __name__ == "__main__":
    sample = build_unstoppable_reply("KAILI tum bina jhijhak bol sakti ho aur kya kar sakti ho?")
    print("MODE:", sample["mode"])
    print("REPLY:\n", sample["reply"])
    print("SPOKEN:\n", sample["spoken_text"])
