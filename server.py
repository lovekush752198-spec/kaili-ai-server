import glob
import shutil
import subprocess
import json
import os
import random
import re
import time
import urllib.error
import urllib.request
from flask import send_from_directory, Flask, jsonify, request

app = Flask(__name__)
# KAILI_CORS_READY
@app.after_request
def add_cors_headers(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return resp

@app.route("/", methods=["GET"])
def home_status():
    return jsonify({"status": "ok", "service": "KAILI AI Server", "version": "1.0"}), 200

MEMORY_FILE = os.path.expanduser("~/kaili-api/memory.json")
MEDIA_DIR = os.path.expanduser("~/kaili-api/media")
os.makedirs(MEDIA_DIR, exist_ok=True)

RIDDLES_AND_QUIZ = [
    {
        "q": ["बोलती नहीं पर सब कुछ बताती", "ऐसी कौन सी चीज़ है जो बोलती नहीं"],
        "a": "किताब या घड़ी—पहेली के हिसाब से 'किताब' (या 'घड़ी') सबसे सटीक उत्तर है।"
    },
    {
        "q": ["काला हूँ पर काग नहीं", "लंबा हूँ पर नाग नहीं"],
        "a": "बाल—काला हूँ पर काग नहीं, लंबा हूँ पर नाग नहीं!"
    },
    {
        "q": ["एक थाल मोती से भरा", "सबके सिर पर औंधा धरा"],
        "a": "आसमान और तारे।"
    },
    {
        "q": ["भारत का राष्ट्रीय पक्षी", "राष्ट्रीय पक्षी कौन"],
        "a": "मोर (Peacock) भारत का राष्ट्रीय पक्षी है।"
    },
    {
        "q": ["भारत का राष्ट्रीय पशु", "राष्ट्रीय पशु कौन"],
        "a": "बाघ (Bengal Tiger) भारत का राष्ट्रीय पशु है।"
    },
    {
        "q": ["पृथ्वी के सबसे करीब तारा", "सबसे करीब तारा"],
        "a": "सूर्य पृथ्वी के सबसे करीब का तारा है।"
    },
]

SHAYARI_LIST = [
    "ख़्वाबों को हक़ीक़त बनाने की ज़िद रखिए,\nअंधेरों में भी अपना रास्ता ख़ुद बनाइए।",
    "मंज़िलें उन्हीं को मिलती हैं जिनके सपनों में जान होती है,\nपंखों से कुछ नहीं होता, हौसलों से उड़ान होती है।",
    "जहाँ कोशिशें सच्ची और इरादे पक्के हों,\nवहाँ हर मुश्किल भी झुकने पर मजबूर होती है।",
]

SCHOOL_KNOWLEDGE = [
    # कक्षा 1
    {
        "classes": [1],
        "keys": ["वर्णमाला", "स्वर", "व्यंजन", "हिंदी वर्णमाला"],
        "a": "[कक्षा 1 - हिंदी] हिंदी वर्णमाला में मुख्य रूप से स्वर (अ, आ, इ, ई, उ, ऊ, ऋ, ए, ऐ, ओ, औ, अं, अः) और व्यंजन (क से ज्ञ तक) होते हैं।"
    },
    {
        "classes": [1],
        "keys": ["एक से दस", "गिनती", "1 से 10", "counting"],
        "a": "[कक्षा 1 - गणित] 1 से 10 तक गिनती: 1 (एक), 2 (दो), 3 (तीन), 4 (चार), 5 (पाँच), 6 (छह), 7 (सात), 8 (आठ), 9 (नौ), 10 (दस)।"
    },
    {
        "classes": [1],
        "keys": ["रंगों के नाम", "सात रंग", "इंद्रधनुष"],
        "a": "[कक्षा 1 - सामान्य ज्ञान] इंद्रधनुष में 7 रंग होते हैं: बैंगनी, जामुनी, नीला, हरा, पीला, नारंगी और लाल।"
    },
    # कक्षा 2
    {
        "classes": [2],
        "keys": ["सप्ताह के दिन", "दिनों के नाम", "7 दिन"],
        "a": "[कक्षा 2 - सामान्य ज्ञान/हिंदी] सप्ताह में 7 दिन होते हैं: सोमवार, मंगलवार, बुधवार, गुरुवार, शुक्रवार, शनिवार और रविवार।"
    },
    {
        "classes": [2],
        "keys": ["महीनों के नाम", "साल में महीने", "12 महीने"],
        "a": "[कक्षा 2 - सामान्य ज्ञान] एक वर्ष में 12 महीने होते हैं: जनवरी, फरवरी, मार्च, अप्रैल, मई, जून, जुलाई, अगस्त, सितंबर, अक्टूबर, नवंबर और दिसंबर।"
    },
    {
        "classes": [2],
        "keys": ["संज्ञा", "नाम वाले शब्द", "noun"],
        "a": "[कक्षा 2 - व्याकरण] किसी व्यक्ति, वस्तु, स्थान या भाव के नाम को संज्ञा कहते हैं। जैसे: राम, किताब, स्कूल, खुशी।"
    },
    # कक्षा 3
    {
        "classes": [3],
        "keys": ["सौरमंडल", "ग्रह", "सूर्य के कितने ग्रह", "planets"],
        "a": "[कक्षा 3 - पर्यावरण/विज्ञान] सूर्य के 8 ग्रह हैं: बुध, शुक्र, पृथ्वी, मंगल, बृहस्पति, शनि, अरुण और वरुण। पृथ्वी जीवन के लिए उपयुक्त ग्रह है।"
    },
    {
        "classes": [3],
        "keys": ["जल चक्र", "पानी का चक्र", "वाष्पीकरण", "वर्षा"],
        "a": "[कक्षा 3 - विज्ञान/पर्यावरण] जल चक्र में सूरज की गर्मी से पानी भाप बनकर ऊपर उठता है, बादल बनते हैं और वर्षा के रूप में वापस ज़मीन पर आता है।"
    },
    {
        "classes": [3],
        "keys": ["दिशाएं", "चार दिशा", "पूर्व पश्चिम उत्तर दक्षिण"],
        "a": "[कक्षा 3 - पर्यावरण] मुख्य 4 दिशाएँ होती हैं: पूर्व, पश्चिम, उत्तर और दक्षिण। सूरज सामान्यतः पूर्व दिशा से उगता दिखाई देता है।"
    },
    # कक्षा 8
    {
        "classes": [8],
        "keys": ["कोशिका", "cell", "जीवन की मूल इकाई"],
        "a": "[कक्षा 8 - विज्ञान] कोशिका जीवों की संरचनात्मक और कार्यात्मक (मूल) इकाई है। सभी सजीव कोशिकाओं से बने होते हैं।"
    },
    {
        "classes": [8],
        "keys": ["बल और दाब", "force", "pressure", "दाब का मात्रक"],
        "a": "[कक्षा 8 - विज्ञान] किसी वस्तु पर लगने वाले धक्के या खिंचाव को बल कहते हैं। एकांक क्षेत्रफल पर लगने वाले बल को दाब कहते हैं (दाब = बल / क्षेत्रफल)।"
    },
    {
        "classes": [8],
        "keys": ["धातु और अधातु", "metals and non metals", "सुचालक"],
        "a": "[कक्षा 8 - विज्ञान] धातुएँ सामान्यतः चमकीली, आघातवर्ध्य (पीटकर चादर बनाने योग्य), तन्य और ऊष्मा व विद्युत की सुचालक होती हैं; अधातुएँ प्रायः इसके विपरीत होती हैं।"
    },
    {
        "classes": [8],
        "keys": ["परिमेय संख्या", "rational number", "p/q"],
        "a": "[कक्षा 8 - गणित] वे संख्याएँ जिन्हें p/q के रूप में लिखा जा सके जहाँ p और q पूर्णांक हों तथा q ≠ 0 हो, परिमेय संख्याएँ कहलाती हैं।"
    },
    # कक्षा 9
    {
        "classes": [9],
        "keys": ["न्यूटन", "गति के नियम", "newton", "जड़त्व"],
        "a": "[कक्षा 9 - विज्ञान/भौतिकी] न्यूटन के गति के तीन नियम हैं: 1) जड़त्व का नियम, 2) संवेग परिवर्तन की दर बल के समानुपाती होती है (F = ma), 3) प्रत्येक क्रिया के बराबर व विपरीत प्रतिक्रिया होती है।"
    },
    {
        "classes": [9],
        "keys": ["माइटोकॉन्ड्रिया", "पावरहाउस", "powerhouse", "कोशिका का बिजलीघर"],
        "a": "[कक्षा 9 - विज्ञान/जीवविज्ञान] माइटोकॉन्ड्रिया को कोशिका का 'पावरहाउस' (बिजलीघर) कहा जाता है क्योंकि यह ATP के रूप में ऊर्जा उत्पन्न करता है।"
    },
    {
        "classes": [9],
        "keys": ["परमाणु", "अणु", "atom", "molecule", "डाल्टन"],
        "a": "[कक्षा 9 - विज्ञान/रसायन] परमाणु पदार्थ की सबसे छोटी इकाई है जो रासायनिक अभिक्रिया में भाग लेती है; दो या अधिक परमाणु मिलकर अणु बनाते हैं।"
    },
    {
        "classes": [9],
        "keys": ["बहुपद", "polynomial", "रैखिक बहुपद", "द्विघात बहुपद"],
        "a": "[कक्षा 9 - गणित] ऐसा बीजीय व्यंजक जिसमें चर की घात पूर्ण संख्या (0, 1, 2, ...) हो, बहुपद कहलाता है। घात के आधार पर रैखिक, द्विघात और त्रिघात बहुपद होते हैं।"
    },
    # कक्षा 12 - हिंदी
    {
        "classes": [12],
        "keys": ["रस", "श्रृंगार", "वीर रस", "करुण रस", "स्थायी भाव", "काव्य"],
        "a": "[कक्षा 12 - हिंदी] काव्य को पढ़ने, सुनने या देखने से जो आनंद प्राप्त होता है, उसे 'रस' कहते हैं। मुख्य रसों में श्रृंगार (रति), वीर (उत्साह), करुण (शोक), हास्य (हास) आदि आते हैं।"
    },
    {
        "classes": [12],
        "keys": ["अलंकार", "अनुप्रास", "यमक", "श्लेष", "उपमा", "रूपक"],
        "a": "[कक्षा 12 - हिंदी] काव्य की शोभा बढ़ाने वाले तत्वों को 'अलंकार' कहते हैं। प्रमुख अलंकार: अनुप्रास (वर्ण की आवृत्ति), यमक (एक शब्द के अलग-अलग अर्थ), श्लेष, उपमा और रूपक।"
    },
    # कक्षा 12 - इंग्लिश (English)
    {
        "classes": [12],
        "keys": ["direct indirect", "narration", "reported speech", "tense", "active passive"],
        "a": "[कक्षा 12 - इंग्लिश] Narration (Direct to Indirect) में reporting verb past tense में हो तो tense बदलता है (Present Simple -> Past Simple, Present Continuous -> Past Continuous) और pronouns नियम अनुसार बदलते हैं।"
    },
    {
        "classes": [12],
        "keys": ["figure of speech", "simile", "metaphor", "personification", "english grammar"],
        "a": "[कक्षा 12 - इंग्लिश] Key Figures of Speech: Simile uses 'as' or 'like' for comparison; Metaphor implies comparison without 'as'/'like'; Personification gives human traits to non-human things."
    },
    # कक्षा 12 - गणित (Maths)
    {
        "classes": [12],
        "keys": ["अवकलन", "derivative", "differentiation", "d/dx", "x^n"],
        "a": "[कक्षा 12 - गणित] अवकलन (Differentiation) किसी फलन के परिवर्तन की दर बताता है। मुख्य सूत्र: d/dx(x^n) = n*x^(n-1), d/dx(sin x) = cos x, d/dx(cos x) = -sin x, d/dx(e^x) = e^x।"
    },
    {
        "classes": [12],
        "keys": ["समाकलन", "integration", "integral", "antiderivative"],
        "a": "[कक्षा 12 - गणित] समाकलन (Integration) अवकलन की प्रतिलोम प्रक्रिया है। मुख्य सूत्र: ∫x^n dx = (x^(n+1))/(n+1) + C (n ≠ -1), ∫e^x dx = e^x + C, ∫cos x dx = sin x + C।"
    },
    {
        "classes": [12],
        "keys": ["आव्यूह", "सारणिक", "matrix", "determinant"],
        "a": "[कक्षा 12 - गणित] संख्याओं या फलनों का आयताकार विन्यास 'आव्यूह' (Matrix) कहलाता है। प्रत्येक वर्ग आव्यूह से संबद्ध एक विशिष्ट मान 'सारणिक' (Determinant) कहलाता है।"
    },
]


def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {"notes": []}
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get("notes"), list):
                return data
    except Exception:
        pass
    return {"notes": []}


def save_note(text):
    data = load_memory()
    clean = text.strip()
    if clean and clean not in data["notes"]:
        data["notes"].append(clean)
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    return len(data["notes"])


def search_memory(query):
    q = query.lower().strip()
    data = load_memory()
    for note in reversed(data["notes"]):
        if any(word in note.lower() for word in q.split() if len(word) > 2):
            return note
    return None


def clean_wake_prefix(text):
    msg = text.strip()
    lower = msg.lower()
    for prefix in ("hello kaili", "hey kaili", "hi kaili", "kaili"):
        if lower.startswith(prefix):
            msg = msg[len(prefix):].strip(" ,:-")
            break
    return msg


def solve_offline_smalltalk(text):
    t = text.strip().lower()

    # क्या नहीं करते हो
    if any(k in t for k in ("क्या नहीं करते", "क्या नही करते", "नहीं करते", "नही करते", "क्या नहीं कर सकते", "what dont you do", "what do you not do")):
        return (
            "मैं कोई भौतिक काम (जैसे सामान उठाना या बाहर जाना) नहीं कर सकता, न ही बिना आपकी अनुमति/कमांड के खुद से दुनिया बदलता हूँ। "
            "मैं केवल आपके निर्देशों और लोकल/कनेक्टेड सिस्टम के दायरे में नोट्स सेव करने, हिसाब/सीरीज़ हल करने, कक्षा 1-12 के सवालों, "
            "कोड/डिज़ाइन बनाने, फोटो/वीडियो प्रीव्यू जनरेट करने और बातचीत में मदद करता हूँ।"
        )

    # क्या करते हो
    if any(k in t for k in ("क्या करते हो", "क्या काम करते", "तुम्हारा काम क्या", "क्या कर सकते हो", "what do you do")):
        return (
            "मैं आपके लोकल एजेंट/असिस्टेंट के रूप में काम करता हूँ:\n"
            "1. 'याद रखो ...' से लोकल मेमोरी में बातें सेव और याद रखता हूँ।\n"
            "2. गणित व नंबर सीरीज़, पहेली/क्विज़ और शायरी के जवाब देता हूँ।\n"
            "3. कक्षा 1, 2, 3, 8, 9 और 12 (हिंदी, इंग्लिश, गणित व अन्य विषयों) के प्रश्न समझाता हूँ।\n"
            "4. आपके निर्देश अनुसार HTML/CSS, Unity C#, और C++ कोड/डिज़ाइन तैयार करता हूँ।\n"
            "5. फोटो और वीडियो प्रॉम्प्ट पर लोकल प्रीव्यू फ़ाइलें बनाता हूँ और ज़रूरत पड़ने पर ऑनलाइन/स्टैंडबाय मोड संभालता हूँ।"
        )

    # आप कौन हो / परिचय
    if any(k in t for k in ("आप कौन हो", "तुम कौन हो", "कौन हो", "अपना परिचय", "who are you", "who r u")):
        return (
            "मैं Kaili (केली) हूँ—आपका कस्टम लोकल/एजेंट असिस्टेंट। "
            "मैं आपके सर्वर पर चलकर ऑफलाइन/लोकल मेमोरी, टूल्स और निर्देशों के हिसाब से आपकी मदद करने के लिए बनाया गया हूँ।"
        )

    # आप कैसे हो / हालचाल
    if any(k in t for k in ("आप कैसे हो", "तुम कैसे हो", "कैसे हो", "कैसे हैं", "क्या हाल", "how are you", "how r u")):
        return (
            "मैं बिल्कुल ठीक और तैयार हूँ! सर्वर लोकल मोड में एक्टिव है। "
            "बताइए, आज मैं आपकी क्या मदद करूँ?"
        )

    # सामान्य नमस्ते / हाय / धन्यवाद
    if t in ("नमस्ते", "नमस्कार", "हेलो", "हैलो", "हाय", "hi", "hello", "hey"):
        return "नमस्ते! मैं केली हूँ—ऑफलाइन/लोकल एजेंट तैयार है। बताइए, क्या काम करना है?"

    if any(k in t for k in ("धन्यवाद", "शुक्रिया", "थैंक्स", "thanks", "thank you")):
        return "आपका स्वागत है! कोई और काम या सवाल हो तो बेझिझक बताइए।"

    return None


def detect_color(text, default_hex):
    t = text.lower()
    color_map = {
        "नीला": "#00B7FF", "blue": "#00B7FF",
        "हरा": "#00FF88", "green": "#00FF88",
        "लाल": "#FF3B5C", "red": "#FF3B5C",
        "पीला": "#FFD43B", "yellow": "#FFD43B",
        "सफेद": "#FFFFFF", "white": "#FFFFFF",
        "काला": "#0B1020", "डार्क": "#0B1020", "dark": "#0B1020",
        "नारंगी": "#FF8C42", "orange": "#FF8C42",
        "बैंगनी": "#9B5DE5", "purple": "#9B5DE5",
    }
    for k, hx in color_map.items():
        if k in t:
            return hx
    return default_hex


def generate_ai_image(prompt_text):
    accent = detect_color(prompt_text, "#00B7FF")
    secondary = "#00FF88" if accent != "#00FF88" else "#00B7FF"
    safe_title = (prompt_text.strip()[:56] or "AI Image").replace("<", "").replace(">", "").replace("&", "and")
    ts = int(time.time())
    svg_path = os.path.join(MEDIA_DIR, f"img_{ts}.svg")

    svg_content = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="800" height="450" viewBox="0 0 800 450">\n'
        f'  <defs>\n'
        f'    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">\n'
        f'      <stop offset="0%" stop-color="#070B14"/>\n'
        f'      <stop offset="100%" stop-color="#111C33"/>\n'
        f'    </linearGradient>\n'
        f'  </defs>\n'
        f'  <rect width="800" height="450" fill="url(#bg)"/>\n'
        f'  <circle cx="630" cy="140" r="95" fill="{accent}" fill-opacity="0.22"/>\n'
        f'  <circle cx="190" cy="330" r="120" fill="{secondary}" fill-opacity="0.18"/>\n'
        f'  <rect x="48" y="48" width="704" height="354" rx="18" fill="none" stroke="{accent}" stroke-width="2" stroke-opacity="0.65"/>\n'
        f'  <text x="80" y="120" fill="{secondary}" font-size="20" font-family="sans-serif">KAILI LOCAL IMAGE ENGINE</text>\n'
        f'  <text x="80" y="190" fill="#FFFFFF" font-size="30" font-weight="bold" font-family="sans-serif">{safe_title}</text>\n'
        f'  <text x="80" y="245" fill="#CBD5E1" font-size="18" font-family="sans-serif">Style: Custom Prompt Render | Accent: {accent}</text>\n'
        f'  <line x1="80" y1="285" x2="720" y2="285" stroke="#334155" stroke-width="1.5"/>\n'
        f'  <text x="80" y="335" fill="#94A3B8" font-size="16" font-family="sans-serif">Saved at: {svg_path}</text>\n'
        f'</svg>\n'
    )
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(svg_content)

    return {
        "file": svg_path,
        "text": (
            f"AI फोटो जनरेट हो गई है!\n"
            f"प्रॉम्प्ट: {prompt_text}\n"
            f"फ़ाइल सेव: {svg_path}\n"
            f"रंग/थीम: {accent}"
        ),
    }


def generate_ai_video(prompt_text):
    accent = detect_color(prompt_text, "#00B7FF")
    safe_title = (prompt_text.strip()[:56] or "AI Video").replace("<", "").replace(">", "").replace("&", "and")
    dur_match = re.search(r"(\d+)\s*(?:सेकंड|sec|second|s)", prompt_text.lower())
    duration_sec = int(dur_match.group(1)) if dur_match else 6
    duration_sec = max(3, min(30, duration_sec))

    ts = int(time.time())
    html_video_path = os.path.join(MEDIA_DIR, f"vid_{ts}.html")

    scenes = [
        f"Scene 1 (0s): ओपनिंग फ़्रेम — '{safe_title}'",
        f"Scene 2 ({duration_sec // 2}s): मोशन व लाइटिंग इफ़ेक्ट ({accent})",
        f"Scene 3 ({duration_sec}s): फ़ाइनल आउटपुट फ़्रेम",
    ]

    html_content = (
        f'<!DOCTYPE html>\n<html lang="hi">\n<head>\n<meta charset="UTF-8"/>\n'
        f'<meta name="viewport" content="width=device-width, initial-scale=1.0"/>\n'
        f'<title>KAILI AI Video - {safe_title}</title>\n'
        f'<style>\n'
        f'body{{margin:0;background:#060911;color:#fff;font-family:sans-serif;display:grid;place-items:center;min-height:100vh;}}\n'
        f'.stage{{position:relative;width:720px;max-width:94vw;height:405px;border-radius:16px;overflow:hidden;border:2px solid {accent};background:#0d1322;}}\n'
        f'.orb{{position:absolute;width:90px;height:90px;border-radius:50%;background:{accent};box-shadow:0 0 35px {accent};top:155px;left:40px;animation:moveOrb {duration_sec}s linear infinite alternate;}}\n'
        f'@keyframes moveOrb{{from{{left:40px;transform:scale(0.9);}}to{{left:calc(100% - 130px);transform:scale(1.15);}}}}\n'
        f'.hud{{position:relative;z-index:2;padding:20px;background:linear-gradient(to bottom,rgba(6,9,17,0.8),transparent);}}\n'
        f'</style>\n</head>\n<body>\n'
        f'<div class="stage">\n'
        f'  <div class="hud"><div>KAILI AI VIDEO PREVIEW ({duration_sec}s)</div><h3>{safe_title}</h3></div>\n'
        f'  <div class="orb"></div>\n'
        f'</div>\n</body>\n</html>\n'
    )
    with open(html_video_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    scenes_str = "\n".join(f"- {s}" for s in scenes)
    return {
        "file": html_video_path,
        "text": (
            f"AI वीडियो जनरेट हो गया है!\n"
            f"प्रॉम्प्ट: {prompt_text}\n"
            f"अवधि: {duration_sec}s | थीम रंग: {accent}\n"
            f"प्रीव्यू फ़ाइल: {html_video_path}\n"
            f"सीन प्लान:\n{scenes_str}"
        ),
    }


def handle_media_generation(text):
    t = text.lower()
    is_video = any(w in t for w in ("वीडियो", "video", "एनिमेशन", "animation", "रील", "reel"))
    is_image = any(w in t for w in ("फोटो", "फ़ोटो", "photo", "इमेज", "image", "चित्र", "picture", "draw"))
    is_gen_verb = any(w in t for w in ("बनाओ", "जनरेट", "generate", "तैयार करो", "create", "दिखाओ"))

    if is_video and (is_gen_verb or "प्रॉम्प्ट" in t or "prompt" in t):
        res = generate_ai_video(text)
        return {"reply": res["text"], "media_url": f"http://127.0.0.1:8000/media/{os.path.basename(media_file)}" if locals().get("media_file") else "",
            "media_file": res["file"], "media_type": "video"}

    if is_image and (is_gen_verb or "प्रॉम्प्ट" in t or "prompt" in t):
        res = generate_ai_image(text)
        return {"reply": res["text"], "media_file": res["file"], "media_type": "image"}

    return None


def solve_school_books(text):
    q_low = text.lower()
    class_match = re.search(r"(?:कक्षा|क्लास|class)\s*(12|[12389])", q_low)
    target_class = int(class_match.group(1)) if class_match else None

    subject_filter = None
    if any(w in q_low for w in ("हिंदी", "hindi", "व्याकरण", "रस", "अलंकार")):
        subject_filter = "हिंदी"
    elif any(w in q_low for w in ("इंग्लिश", "अंग्रेजी", "english", "narration", "tense", "grammar")):
        subject_filter = "इंग्लिश"
    elif any(w in q_low for w in ("गणित", "maths", "math", "अवकलन", "समाकलन", "आव्यूह", "सारणिक")):
        subject_filter = "गणित"

    best_item = None
    best_score = 0

    for item in SCHOOL_KNOWLEDGE:
        score = 0
        if target_class and target_class in item["classes"]:
            score += 3
        if subject_filter and subject_filter in item["a"]:
            score += 3
        for k in item["keys"]:
            if k.lower() in q_low:
                score += 4
        for tok in re.findall(r"[a-zA-Z\u0900-\u097F]+", q_low):
            if len(tok) >= 3 and tok in item["a"].lower():
                score += 1
        if score > best_score:
            best_score = score
            best_item = item

    if best_item and best_score >= 4:
        return best_item["a"]

    if target_class in (1, 2, 3, 8, 9, 12):
        candidates = [x for x in SCHOOL_KNOWLEDGE if target_class in x["classes"]]
        if subject_filter:
            sub_matches = [x for x in candidates if subject_filter in x["a"]]
            if sub_matches:
                candidates = sub_matches
        if candidates:
            sub_label = f" - {subject_filter}" if subject_filter else ""
            return (
                f"[कक्षा {target_class}{sub_label} गाइड] यहाँ मुख्य विषय है:\n"
                f"{candidates[0]['a']}\n"
                f"अधिक सटीक उत्तर के लिए टॉपिक का नाम लिखें या 'याद रखो ...' से नया प्रश्न-उत्तर सेव करें।"
            )
    return None


def solve_math_or_series(text):
    nums = [int(n) for n in re.findall(r"-?\d+", text)]

    expr_match = re.findall(r"[\d\s\+\-\*\/\(\)\.]+", text)
    for candidate in expr_match:
        cleaned = candidate.strip()
        if re.search(r"[\+\-\*\/]", cleaned) and len(re.findall(r"\d+", cleaned)) >= 2:
            if re.fullmatch(r"[\d\s\+\-\*\/\(\)\.]+", cleaned):
                try:
                    val = eval(cleaned, {"__builtins__": None}, {})
                    if isinstance(val, float) and val.is_integer():
                        val = int(val)
                    return f"गणित उत्तर: {cleaned} = {val}"
                except Exception:
                    pass

    if len(nums) >= 4:
        total = sum(nums)
        pairs = [nums[i] + nums[i + 1] for i in range(0, len(nums) - 1, 2)]
        lines = [f"संख्याएँ: {nums}", f"कुल योग: {total}"]
        if len(pairs) >= 2:
            lines.append(f"जोड़ों का योग: {pairs}")
            diffs = [pairs[i + 1] - pairs[i] for i in range(len(pairs) - 1)]
            if len(set(diffs)) == 1:
                next_pair_sum = pairs[-1] + diffs[0]
                lines.append(f"पैटर्न: हर अगले जोड़े का योग {diffs[0]:+d} बढ़ रहा है -> अगला जोड़ा योग {next_pair_sum}")
            elif len(nums) >= 6 and nums[0] + nums[1] == nums[2] and nums[3] + nums[4] == nums[5]:
                lines.append(
                    f"पैटर्न जांच: {nums[0]}+{nums[1]}={nums[2]} और {nums[3]}+{nums[4]}={nums[5]}। "
                    f"अगर अगला जोड़ा {nums[3]} और {nums[5]} लें तो योग {nums[3] + nums[5]} बनता है।"
                )
        return "\n".join(lines)

    return None


def solve_riddle_or_quiz(text):
    q_low = text.lower()
    if any(k in q_low for k in ("पहेली", "riddle", "क्विज़", "quiz")):
        for item in RIDDLES_AND_QUIZ:
            if any(clue.lower() in q_low for clue in item["q"]):
                return item["a"]
        pick = random.choice(RIDDLES_AND_QUIZ)
        return f"क्विज़ / पहेली: {pick['q'][0]}?\nउत्तर: {pick['a']}"

    for item in RIDDLES_AND_QUIZ:
        if any(clue.lower() in q_low for clue in item["q"]):
            return item["a"]
    return None


def get_shayari(text):
    t = text.lower()
    if any(k in t for k in ("शायरी", "shayari", "शेर", "poetry")):
        if any(w in t for w in ("मेहनत", "लक्ष्य", "सपना", "मंज़िल", "2030")):
            return SHAYARI_LIST[1]
        if any(w in t for w in ("हिम्मत", "अंधेरा", "कोशिश")):
            return SHAYARI_LIST[0]
        return random.choice(SHAYARI_LIST)
    return None


def generate_custom_code(text):
    t = text.lower()
    is_code_req = any(
        w in t for w in (
            "कोड", "code", "html", "css", "unity", "c#", "csharp", "c++", "cpp",
            "डिजाइन", "design", "बटन", "button", "स्क्रिप्ट", "script", "प्रोग्राम"
        )
    )
    if not is_code_req:
        return None

    if "c++" in t or "cpp" in t:
        nums = [int(x) for x in re.findall(r"-?\d+", text)]
        a_val = nums[0] if len(nums) >= 1 else 10
        b_val = nums[1] if len(nums) >= 2 else 20
        return (
            "```cpp\n"
            "#include <iostream>\n"
            "using namespace std;\n\n"
            "int main() {\n"
            f"    int a = {a_val}, b = {b_val};\n"
            "    int sum = a + b;\n"
            "    cout << \"A = \" << a << \", B = \" << b << endl;\n"
            "    cout << \"Sum = \" << sum << endl;\n"
            "    return 0;\n"
            "}\n"
            "```"
        )

    if "unity" in t or "c#" in t or "csharp" in t:
        speed_match = re.search(r"(?:स्पीड|speed)\s*[:=]?\s*(\d+(?:\.\d+)?)", t)
        speed_val = f"{speed_match.group(1)}f" if speed_match else "7f"
        hp_match = re.search(r"(?:हेल्थ|health|hp)\s*[:=]?\s*(\d+)", t)
        hp_val = hp_match.group(1) if hp_match else "100"
        class_name = "CustomHealthSystem" if ("हेल्थ" in t or "health" in t or "डैमेज" in t or "damage" in t) else "CustomPlayerController"

        if class_name == "CustomHealthSystem":
            return (
                "```csharp\n"
                "using UnityEngine;\n\n"
                f"public class {class_name} : MonoBehaviour\n"
                "{\n"
                f"    public int maxHealth = {hp_val};\n"
                "    public int currentHealth;\n\n"
                "    void Start()\n"
                "    {\n"
                "        currentHealth = maxHealth;\n"
                "    }\n\n"
                "    public void TakeDamage(int amount)\n"
                "    {\n"
                "        currentHealth = Mathf.Max(0, currentHealth - amount);\n"
                "        if (currentHealth == 0) Die();\n"
                "    }\n\n"
                "    void Die()\n"
                "    {\n"
                "        gameObject.SetActive(false);\n"
                "    }\n"
                "}\n"
                "```"
            )

        return (
            "```csharp\n"
            "using UnityEngine;\n\n"
            f"public class {class_name} : MonoBehaviour\n"
            "{\n"
            f"    public float moveSpeed = {speed_val};\n"
            "    public float jumpForce = 6f;\n"
            "    private Rigidbody rb;\n\n"
            "    void Start()\n"
            "    {\n"
            "        rb = GetComponent<Rigidbody>();\n"
            "    }\n\n"
            "    void Update()\n"
            "    {\n"
            "        float h = Input.GetAxisRaw(\"Horizontal\");\n"
            "        float v = Input.GetAxisRaw(\"Vertical\");\n"
            "        Vector3 move = new Vector3(h, 0f, v).normalized * moveSpeed;\n"
            "        if (rb != null)\n"
            "            rb.linearVelocity = new Vector3(move.x, rb.linearVelocity.y, move.z);\n"
            "        else\n"
            "            transform.Translate(move * Time.deltaTime, Space.World);\n\n"
            "        if (Input.GetKeyDown(KeyCode.Space) && rb != null)\n"
            "            rb.AddForce(Vector3.up * jumpForce, ForceMode.Impulse);\n"
            "    }\n"
            "}\n"
            "```"
        )

    bg_color = "#0B1020" if ("डार्क" in t or "dark" in t or "काला" in t) else "#111827"
    btn_color = detect_color(t, "#00B7FF")
    btn_label = "शुरू करें" if ("स्टार्ट" in t or "start" in t or "शुरू" in t) else "क्लिक करें"
    title_text = text.strip()[:48] or "कस्टम डिज़ाइन"

    return (
        "```html\n"
        "<!DOCTYPE html>\n"
        "<html lang=\"hi\">\n"
        "<head>\n"
        "  <meta charset=\"UTF-8\" />\n"
        "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />\n"
        f"  <title>{title_text}</title>\n"
        "  <style>\n"
        f"    body {{ margin:0; min-height:100vh; display:grid; place-items:center; background:{bg_color}; color:#fff; font-family:sans-serif; }}\n"
        "    .card { padding:24px; border-radius:14px; background:rgba(255,255,255,0.08); text-align:center; max-width:360px; width:90%; }\n"
        f"    .btn {{ margin-top:16px; padding:10px 20px; border:none; border-radius:8px; background:{btn_color}; color:#061018; font-weight:bold; cursor:pointer; }}\n"
        "  </style>\n"
        "</head>\n"
        "<body>\n"
        "  <div class=\"card\">\n"
        f"    <h2>{title_text}</h2>\n"
        f"    <button class=\"btn\" onclick=\"alert('एक्शन सक्रिय!')\">{btn_label}</button>\n"
        "  </div>\n"
        "</body>\n"
        "</html>\n"
        "```"
    )


def ask_gemini_fast(prompt, api_key):
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.0-flash:generateContent?key={api_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=8) as resp:
        body = json.loads(resp.read().decode("utf-8"))
        candidates = body.get("candidates") or []
        if candidates:
            parts = (candidates[0].get("content") or {}).get("parts") or []
            texts = [p.get("text", "") for p in parts if p.get("text")]
            if texts:
                return "\n".join(texts).strip(), "ok"
    return "जवाब खाली आया है, कृपया दोबारा प्रयास करें।", "fallback"


@app.route("/health", methods=["GET"])
def health():
    mem = load_memory()
    return jsonify({
        "status": "ok",
        "engine": "kaili-fast-agent-v6",
        "modules": [
            "offline_smalltalk", "local_memory", "media_image_video_gen",
            "school_books_1_2_3_8_9_12", "custom_coding_html_cs_unity_cpp",
            "math_series", "riddle_quiz", "shayari", "gemini_fallback"
        ],
        "notes_count": len(mem["notes"]),
        "has_gemini_key": bool(os.environ.get("GEMINI_API_KEY", "").strip()),
    })


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    raw_msg = str(data.get("message") or data.get("prompt") or "").strip()
    if not raw_msg:
        return jsonify({"reply": "कृपया कोई संदेश लिखें।", "status": "fallback"}), 200

    msg = clean_wake_prefix(raw_msg) or raw_msg
    try:
        from offline_3d_video import run_offline_3d_video_prompt
        anim_3d = run_offline_3d_video_prompt(msg)
        if anim_3d:
            return jsonify(anim_3d)
    except Exception:
        pass
    lower = msg.lower()

    # 0. ऑफलाइन सामान्य चैट / परिचय (ऑनलाइन सर्वर से पहले लोकल जवाब)
    smalltalk_ans = solve_offline_smalltalk(msg)
    if smalltalk_ans:
        return jsonify({"reply": smalltalk_ans, "status": "ok", "source": "offline_smalltalk"})

    # 1. लोकल मेमोरी में लिखने की कमांड
    for trigger in ("याद रखो", "मेमोरी में लिखो", "नोट करो", "save "):
        if lower.startswith(trigger):
            note_text = msg[len(trigger):].strip(" :-")
            if note_text:
                total = save_note(note_text)
                return jsonify({
                    "reply": f"सेव हो गया (कुल नोट्स: {total}): {note_text}",
                    "status": "ok",
                    "source": "local_memory",
                })

    media_ans = handle_media_generation(msg)
    if media_ans:
        return jsonify({
            "reply": media_ans["reply"],
            "media_file": media_ans["media_file"],
            "media_type": media_ans["media_type"],
            "status": "ok",
            "source": f"local_{media_ans['media_type']}_gen",
        })

    shayari_ans = get_shayari(msg)
    if shayari_ans:
        return jsonify({"reply": shayari_ans, "status": "ok", "source": "shayari"})

    riddle_ans = solve_riddle_or_quiz(msg)
    if riddle_ans:
        return jsonify({"reply": riddle_ans, "status": "ok", "source": "riddle_quiz"})

    math_ans = solve_math_or_series(msg)
    if math_ans:
        return jsonify({"reply": math_ans, "status": "ok", "source": "math_series"})

    school_ans = solve_school_books(msg)
    if school_ans:
        return jsonify({"reply": school_ans, "status": "ok", "source": "school_books"})

    mem_hit = search_memory(msg)
    if mem_hit and ("याद" in lower or "मेमोरी" in lower or "नोट" in lower or "मेरा" in lower):
        return jsonify({
            "reply": f"लोकल मेमोरी से: {mem_hit}",
            "status": "ok",
            "source": "local_memory",
        })

    code_ans = generate_custom_code(msg)
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if api_key:
        try:
            prompt_to_send = (
                f"निर्देश के अनुसार साफ, सटीक और तैयार कोड/डिज़ाइन दो: {msg}"
                if code_ans is not None else msg
            )
            reply, status = ask_gemini_fast(prompt_to_send, api_key)
            return jsonify({
                "reply": reply,
                "status": status,
                "source": "gemini",
            })
        except urllib.error.HTTPError as e:
            if e.code == 429:
                if code_ans:
                    return jsonify({"reply": code_ans, "status": "fallback", "source": "custom_coding_standby"})
                fallback_msg = (
                    f"कोटा सीमा (429) पूरी हो गई है। लोकल मेमोरी: {mem_hit}"
                    if mem_hit
                    else "अभी Gemini कोटा सीमा (429) पूरी हो गई है। स्टैंडबाय मोड सक्रिय है।"
                )
                return jsonify({"reply": fallback_msg, "status": "fallback", "source": "standby_429"})
        except Exception:
            pass

    if code_ans:
        return jsonify({"reply": code_ans, "status": "fallback", "source": "custom_coding"})

    if mem_hit:
        return jsonify({
            "reply": f"स्टैंडबाय मेमोरी: {mem_hit}",
            "status": "fallback",
            "source": "local_memory",
        })

    msg_low = (msg or "").lower()
    if any(k in msg_low for k in ["shayari", "sayre", "शायरी", "शायरी सुनाओ", "sayre sunao"]):
        return jsonify({
            "reply": "ख़्वाबों की दुनिया में जब हम उतर जाते हैं,\nहर मुश्किल को हँसकर पार कर जाते हैं,\nमंज़िलें चाहे कितनी भी दूर क्यों न हों,\nहम अपनी मेहनत से रास्ता बना ही जाते हैं।",
            "status": "ok",
            "source": "local_shayari"
        })

    return jsonify({
        "reply": f"स्टैंडबाय एजेंट सक्रिय है। आपका संदेश मिला: '{msg}'। आप कैसे हो/कौन हो/क्या करते हो, फोटो/वीडियो प्रॉम्प्ट, कक्षा 1-12 के प्रश्न, HTML/Unity/C#/C++ कोड, गणित/सीरीज़, पहेली, शायरी या 'याद रखो ...' आज़मा सकते हैं।",
        "status": "fallback",
        "source": "standby",
    })



MEDIA_DIR = "/data/data/com.termux/files/home/kaili-api/media"

@app.route("/media/<path:filename>")
def serve_kaili_media(filename):
    safe_name = os.path.basename(filename)
    return send_from_directory(MEDIA_DIR, safe_name, mimetype="video/mp4") if safe_name.lower().endswith(".mp4") else send_from_directory(MEDIA_DIR, safe_name)


@app.route("/data/data/com.termux/files/home/kaili-api/media/<path:filename>", methods=["GET"])
def kaili_serve_fullpath_media(filename):
    return send_from_directory(MEDIA_DIR, os.path.basename(filename))

@app.route("/media", methods=["GET", "POST"])
def kaili_media_endpoint():
    os.makedirs(MEDIA_DIR, exist_ok=True)
    files = sorted(os.listdir(MEDIA_DIR))
    latest = files[-1] if files else ""
    return jsonify({
        "status": "ok",
        "media_dir": MEDIA_DIR,
        "latest_file": latest,
        "media_url": f"http://127.0.0.1:8000/media/{latest}" if latest else ""
    })


MEDIA_DIR = "/data/data/com.termux/files/home/kaili-api/media"
os.makedirs(MEDIA_DIR, exist_ok=True)

def kaili_make_real_mp4(prompt_text="KAILI AI Reel", seconds=6):
    ts = int(time.time())
    fname = f"kaili_vid_{ts}.mp4"
    fpath = os.path.join(MEDIA_DIR, fname)
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=0x060b19:s=720x1280:d={seconds}:r=24",
        "-vf", (
            "drawbox=x='(iw-w)/2+140*sin(t*2.2)':y='(ih-h)/2+140*cos(t*2.2)':"
            "w=160:h=160:color=0x00f0ff@0.85:t=fill,"
            "drawbox=x='(iw-w)/2-110*cos(t*1.7)':y='(ih-h)/2+90*sin(t*1.7)':"
            "w=90:h=90:color=0xff3b5c@0.85:t=fill"
        ),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        fpath
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    return fpath, f"http://127.0.0.1:8000/media/{fname}"

@app.route("/make-mp4", methods=["GET", "POST"])
def kaili_make_mp4_route():
    data = request.get_json(silent=True) or {}
    p = data.get("prompt") or data.get("message") or request.args.get("prompt") or "KAILI AI Reel"
    fpath, murl = kaili_make_real_mp4(p, seconds=6)
    exists = os.path.exists(fpath) and os.path.getsize(fpath) > 0
    return jsonify({
        "status": "ok" if exists else "error",
        "reply": f"MP4 वीडियो तैयार: {murl}" if exists else "MP4 नहीं बन पाया, ffmpeg जाँचें।",
        "media_file": fpath,
        "media_url": murl
    })


def kaili_build_render_command(prompt_text):
    p = (prompt_text or "").strip()
    lower = p.lower()

    if "cyber" in lower or "neon" in lower:
        preset = "cyber_neon_arena"
        accent = "#00F0FF"
    elif "space" in lower or "planet" in lower or "mars" in lower:
        preset = "deep_space_orbit"
        accent = "#FF3B5C"
    else:
        preset = "cinematic_stage"
        accent = "#00E5FF"

    camera_mode = "orbit_slow" if "orbit" in lower or "pan" in lower else "dolly_in"

    return {
        "engine": "unreal_hdr",
        "command_driven": True,
        "auto_evolve": False,
        "preset": preset,
        "camera": {
            "mode": camera_mode,
            "fps": 60,
            "hdr": True
        },
        "lighting": {
            "accent_color": accent,
            "exposure_mode": "manual_hdr"
        },
        "duration_sec": 12,
        "prompt": p or "KAILI AI 3D Scene"
    }

@app.route("/unreal-plan", methods=["GET", "POST"])
def kaili_unreal_plan_route():
    data = request.get_json(silent=True) or {}
    p = data.get("prompt") or data.get("message") or request.args.get("prompt") or ""
    plan = kaili_build_render_command(p)
    return jsonify({
        "status": "ok",
        "reply": json.dumps(plan, ensure_ascii=False, indent=2),
        "render_command": plan
    })


def kaili_build_video_blueprint(prompt_text, duration_sec=12, aspect_ratio="9:16"):
    p = (prompt_text or "").strip()
    lower = p.lower()

    if "space" in lower or "planet" in lower or "mars" in lower:
        preset = "deep_space_orbit"
        accent = "#FF3B5C"
        style = "space_hdr"
    elif "cyber" in lower or "neon" in lower or "ai" in lower:
        preset = "cyber_neon_arena"
        accent = "#00F0FF"
        style = "cyber_hdr"
    else:
        preset = "cinematic_stage"
        accent = "#00E5FF"
        style = "cinematic_hdr"

    is_landscape = ("16:9" in lower) or ("youtube" in lower) or (aspect_ratio == "16:9")
    ratio = "16:9" if is_landscape else "9:16"
    resolution = "1920x1080" if is_landscape else "1080x1920"
    v_type = "youtube_video" if is_landscape else "short_reel"

    try:
        dur = max(6, min(120, int(duration_sec)))
    except Exception:
        dur = 12

    s1_end = max(2, round(dur * 0.25))
    s2_end = max(s1_end + 2, round(dur * 0.70))
    if s2_end >= dur:
        s2_end = max(s1_end + 1, dur - 1)

    blueprint = {
        "project_name": "kaili_video_project",
        "command_driven": True,
        "auto_evolve": False,
        "self_modifying": {
            "enabled": True,
            "mode": "safe_module_append",
            "require_backup": True,
            "target_scope": "presets_and_editing_rules"
        },
        "meta": {
            "video_type": v_type,
            "aspect_ratio": ratio,
            "resolution": resolution,
            "fps": 60,
            "total_duration_sec": dur,
            "style": style,
            "source_prompt": p or "KAILI AI Custom Video"
        },
        "scenes": [
            {
                "scene_id": 1,
                "start_sec": 0,
                "end_sec": s1_end,
                "role": "hook",
                "visual_desc": f"Opening hook for: {p or 'scene'}",
                "unreal_command": {
                    "preset": preset,
                    "camera_mode": "dolly_in",
                    "accent_color": accent,
                    "hdr": True
                },
                "overlay_text": "KAILI AI"
            },
            {
                "scene_id": 2,
                "start_sec": s1_end,
                "end_sec": s2_end,
                "role": "main_action",
                "visual_desc": "Core visual sequence and camera motion",
                "unreal_command": {
                    "preset": preset,
                    "camera_mode": "orbit_slow",
                    "accent_color": accent,
                    "hdr": True
                },
                "overlay_text": "SCENE FLOW"
            },
            {
                "scene_id": 3,
                "start_sec": s2_end,
                "end_sec": dur,
                "role": "climax_outro",
                "visual_desc": "Final framing, polish, and ending beat",
                "unreal_command": {
                    "preset": "cinematic_stage",
                    "camera_mode": "static_hero",
                    "accent_color": accent,
                    "hdr": True
                },
                "overlay_text": "READY"
            }
        ],
        "edit_timeline": {
            "cuts": [
                {"at_sec": s1_end, "type": "hard_cut"},
                {"at_sec": s2_end, "type": "cross_dissolve", "duration_sec": 0.4}
            ],
            "audio": {
                "voiceover": {"enabled": True, "script_sync": True},
                "bgm": {"enabled": True, "duck_under_voice": True},
                "sfx": [f"transition_{s1_end}s", f"beat_{s2_end}s"]
            },
            "captions": {"enabled": True, "style": "clean_bold"}
        },
        "export": {
            "format": "mp4",
            "codec": "h264",
            "output_dir": "renders/"
        }
    }
    return blueprint

@app.route("/video-blueprint", methods=["GET", "POST"])
def kaili_video_blueprint_route():
    data = request.get_json(silent=True) or {}
    p = data.get("prompt") or data.get("message") or request.args.get("prompt") or ""
    dur = data.get("duration_sec") or request.args.get("duration_sec") or 12
    ratio = data.get("aspect_ratio") or request.args.get("aspect_ratio") or "9:16"
    bp = kaili_build_video_blueprint(p, duration_sec=dur, aspect_ratio=ratio)
    return jsonify({
        "status": "ok",
        "reply": json.dumps(bp, ensure_ascii=False, indent=2),
        "blueprint": bp
    })


RULES_FILE = "/data/data/com.termux/files/home/kaili-api/video_rules.json"
BACKUP_DIR = "/data/data/com.termux/files/home/kaili-api/backups"

def kaili_safe_modify_rule(section, key, value):
    if section not in ("presets", "editing_rules"):
        return False, "केवल presets या editing_rules में बदलाव की अनुमति है।"
    if not key or not isinstance(key, str):
        return False, "सही key नाम दें।"
    if not isinstance(value, dict):
        return False, "value एक JSON ऑब्जेक्ट (dict) होना चाहिए।"

    os.makedirs(BACKUP_DIR, exist_ok=True)
    if os.path.exists(RULES_FILE):
        shutil.copy2(RULES_FILE, os.path.join(BACKUP_DIR, f"video_rules_{int(time.time())}.json"))
        with open(RULES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {"presets": {}, "editing_rules": {}}

    data.setdefault(section, {})
    data[section][key.strip()] = value

    with open(RULES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return True, f"{section}.{key} सुरक्षित रूप से अपडेट हो गया (बैकअप सेव है)।"

@app.route("/self-modify-rule", methods=["POST"])
def kaili_self_modify_rule_route():
    req = request.get_json(silent=True) or {}
    ok, msg = kaili_safe_modify_rule(req.get("section"), req.get("key"), req.get("value"))
    return jsonify({"status": "ok" if ok else "error", "message": msg})


PACKAGES_DIR = "/data/data/com.termux/files/home/kaili-api/packages"

def kaili_build_render_edit_package(prompt_text, duration_sec=12, aspect_ratio="9:16"):
    if "kaili_build_video_blueprint" in globals():
        bp = kaili_build_video_blueprint(prompt_text, duration_sec=duration_sec, aspect_ratio=aspect_ratio)
    else:
        bp = {
            "project_name": "kaili_video_project",
            "command_driven": True,
            "auto_evolve": False,
            "meta": {"total_duration_sec": int(duration_sec or 12), "aspect_ratio": aspect_ratio or "9:16"},
            "scenes": [],
            "edit_timeline": {},
            "export": {"format": "mp4", "codec": "h264", "output_dir": "renders/"}
        }

    os.makedirs(PACKAGES_DIR, exist_ok=True)
    ts = int(time.time())
    pkg_id = f"kaili_pkg_{ts}"

    unreal_queue = []
    for sc in bp.get("scenes", []):
        uc = sc.get("unreal_command", {})
        unreal_queue.append({
            "shot_id": sc.get("scene_id"),
            "start_sec": sc.get("start_sec"),
            "end_sec": sc.get("end_sec"),
            "preset": uc.get("preset", "cinematic_stage"),
            "camera_mode": uc.get("camera_mode", "orbit_slow"),
            "accent_color": uc.get("accent_color", "#00E5FF"),
            "hdr": bool(uc.get("hdr", True)),
            "overlay_text": sc.get("overlay_text", "")
        })

    package = {
        "package_id": pkg_id,
        "command_driven": True,
        "auto_evolve": False,
        "meta": bp.get("meta", {}),
        "unreal_render_queue": unreal_queue,
        "edit_timeline": bp.get("edit_timeline", {}),
        "export": bp.get("export", {"format": "mp4", "codec": "h264", "output_dir": "renders/"})
    }

    pkg_path = os.path.join(PACKAGES_DIR, f"{pkg_id}.json")
    with open(pkg_path, "w", encoding="utf-8") as f:
        json.dump(package, f, ensure_ascii=False, indent=2)

    return package, pkg_path

@app.route("/build-package", methods=["GET", "POST"])
def kaili_build_package_route():
    data = request.get_json(silent=True) or {}
    p = data.get("prompt") or data.get("message") or request.args.get("prompt") or ""
    dur = data.get("duration_sec") or request.args.get("duration_sec") or 12
    ratio = data.get("aspect_ratio") or request.args.get("aspect_ratio") or "9:16"
    pkg, pkg_path = kaili_build_render_edit_package(p, duration_sec=dur, aspect_ratio=ratio)
    return jsonify({
        "status": "ok",
        "package_id": pkg["package_id"],
        "saved_path": pkg_path,
        "package": pkg
    })


PACKAGES_DIR = "/data/data/com.termux/files/home/kaili-api/packages"
JOBS_DIR = "/data/data/com.termux/files/home/kaili-api/jobs"

def kaili_use_latest_package():
    base_dir = "/data/data/com.termux/files/home/kaili-api"
    os.makedirs(JOBS_DIR, exist_ok=True)
    files = sorted(
        glob.glob(os.path.join(PACKAGES_DIR, "kaili_pkg_*.json")),
        key=os.path.getmtime,
        reverse=True
    )
    if not files:
        return False, "कोई kaili_pkg_*.json फ़ाइल नहीं मिली। पहले /build-package चलाएं।", None

    latest_pkg_path = files[0]
    with open(latest_pkg_path, "r", encoding="utf-8") as f:
        pkg = json.load(f)

    meta = pkg.get("meta", {})
    queue = pkg.get("unreal_render_queue", [])
    timeline = pkg.get("edit_timeline", {})
    export_cfg = pkg.get("export", {})

    res = meta.get("resolution", "1080x1920")
    try:
        w, h = res.lower().split("x")
        w, h = int(w), int(h)
    except Exception:
        w, h = 1080, 1920

    fps = int(meta.get("fps", 60) or 60)
    out_dir = export_cfg.get("output_dir", "renders/")
    out_file = os.path.join(base_dir, out_dir.lstrip("./"), f"{pkg.get('package_id', 'kaili_out')}.mp4")
    os.makedirs(os.path.dirname(out_file), exist_ok=True)

    shot_steps = []
    for s in queue:
        start_s = s.get("start_sec", 0)
        end_s = s.get("end_sec", 4)
        dur_s = max(0.5, float(end_s) - float(start_s))
        shot_steps.append({
            "shot_id": s.get("shot_id"),
            "window": f"{start_s}s-{end_s}s",
            "duration_sec": dur_s,
            "preset": s.get("preset"),
            "camera_mode": s.get("camera_mode"),
            "accent_color": s.get("accent_color"),
            "overlay_text": s.get("overlay_text", "")
        })

    dur_total = meta.get("total_duration_sec", 12)
    filters = []
    for s in shot_steps:
        txt = str(s.get("overlay_text", "") or "").replace(":", "\\:").replace("'", "")
        if not txt:
            continue
        win = str(s.get("window", "0s-4s"))
        try:
            a, b = win.replace("s", "").split("-")
            t0, t1 = float(a), float(b)
        except Exception:
            t0, t1 = 0.0, 4.0
        col = str(s.get("accent_color", "#00F0FF")).replace("#", "0x")
        if len(col) == 8:
            col = col + "FF"
        filters.append(
            f"drawtext=text='{txt}':fontcolor={col}:fontsize=72:x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,{t0},{t1})'"
        )

    vf_chain = ",".join(filters)
    if vf_chain:
        ffmpeg_preview_cmd = (
            f'ffmpeg -y -f lavfi -i color=c=black:s={w}x{h}:r={fps} '
            f'-vf "{vf_chain}" -t {dur_total} -c:v libx264 -pix_fmt yuv420p "{out_file}"'
        )
    else:
        ffmpeg_preview_cmd = (
            f'ffmpeg -y -f lavfi -i color=c=black:s={w}x{h}:r={fps} '
            f'-t {dur_total} -c:v libx264 -pix_fmt yuv420p "{out_file}"'
        )

    job = {
        "job_id": f"job_{int(time.time())}",
        "source_package": latest_pkg_path,
        "command_driven": bool(pkg.get("command_driven", True)),
        "auto_evolve": bool(pkg.get("auto_evolve", False)),
        "shot_steps": shot_steps,
        "cuts_count": len(timeline.get("cuts", [])),
        "audio_config": timeline.get("audio", {}),
        "captions_config": timeline.get("captions", {}),
        "target_output": out_file,
        "android_ffmpeg_base_cmd": ffmpeg_preview_cmd
    }

    job_path = os.path.join(JOBS_DIR, f"{job['job_id']}.json")
    with open(job_path, "w", encoding="utf-8") as f:
        json.dump(job, f, ensure_ascii=False, indent=2)

    return True, f"पैकेज इस्तेमाल हो गया: {os.path.basename(latest_pkg_path)} -> {job['job_id']}", {"job": job, "job_path": job_path}

@app.route("/use-latest-package", methods=["GET", "POST"])
def kaili_use_latest_package_route():
    ok, msg, payload = kaili_use_latest_package()
    return jsonify({
        "status": "ok" if ok else "error",
        "message": msg,
        **(payload or {})
    })

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=False)
