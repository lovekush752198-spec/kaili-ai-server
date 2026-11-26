import argparse
import json
import os
from typing import Dict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KNOWLEDGE_DIR = os.path.join(BASE_DIR, "knowledge")


def build_chat_knowledge(target_count: int = 2000) -> Dict[str, str]:
    data: Dict[str, str] = {}

    # 1. Core conversational codes (greetings, tone, follow-ups, closing)
    core_chat = {
        "namaste": "Namaste Boss! KAILI AI aapki seva mein hazir hai. Aaj kis vishay par baat karni hai?",
        "hello": "Hello Boss! Bataiye, aaj kya plan hai—baat karni hai, padhna hai, ya koi project aage badhana hai?",
        "hi": "Hi Boss! Main taiyar hoon. Apna sawal ya command dijiye.",
        "kaise ho": "Boss, main bilkul mast aur active hoon! Aap bataiye, aapka din kaisa chal raha hai?",
        "kya chal raha hai": "Boss, main aapke nirdesh par ready hoon. Aap jo kahein, usi hisab se aage badhte hain.",
        "thank you": "Koi baat nahi Boss! Zaroorat pade to bas bol dijiye, main madad ke liye hazir hoon.",
        "dhanyawad": "Aapka swagat hai Boss! Kuch aur jaanna ya banwana ho to bejhijhak poochiye.",
        "bye": "Theek hai Boss, phir milte hain! Apna khayal rakhiye.",
        "alvida": "Alvida Boss! Jab bhi zaroorat ho, KAILI AI yahin milega.",
        "samajh nahi aaya": "Koi baat nahi Boss, main ise aur aasan shabdon mein samjha deta hoon. Aap kis hisse ko dobara samajhna chahte hain?",
        "aage kya karein": "Boss, abhi hamare paas do ache vikಲ್ಪ hain: pehla, jo banaya hai use test karein; doosra, naya feature jodein. Aap kaun sa chunenge?",
    }
    data.update(core_chat)

    # 2. Conversational variations & dialogue flows
    openers = ["boss", "kaili", "suno", "batao", "ek baat bolo"]
    moods = ["achha", "theek", "mast", "busy", "shant"]
    actions = ["baat karna", "seekhna", "plan banana", "aage badhna", "test karna"]

    for op in openers:
        for md in moods:
            key = f"{op} main {md} hoon"
            if len(data) < target_count:
                data[key] = (
                    f"Bahut achha Boss! Agar aap {md} feel kar rahe hain, toh {op} ke saath aage chalte hain. "
                    f"Kya hum abhi {actions[len(data) % len(actions)]} shuru karein?"
                )

    for act in actions:
        for i in range(1, 400):
            if len(data) >= target_count:
                break
            q = f"{act} ke baare mein baat #{i}"
            a = (
                f"Boss, '{act}' ko lekar hum step-by-step chal sakte hain. "
                f"Pehle mukhya baat saaf karein, phir uska practical kaam karein. Kya main ismein koi madad karoon?"
            )
            data[q] = a

    return data


def build_study_knowledge(target_count: int = 2000) -> Dict[str, str]:
    data: Dict[str, str] = {}

    core_study = {
        "prakash sanshleshan kya hai": "Boss, prakash sanshleshan (photosynthesis) woh prakriya hai jisse paudhe surya ke prakash, pani aur carbon dioxide ki madad se apna bhojan banate hain.",
        "gurutvakarshan kya hai": "Boss, gurutvakarshan (gravity) woh aakarshan bal hai jisse do vastuon ke beech khinchav hota hai, jaise dharti ka har cheez ko apni taraf kheench na.",
        "newton ka doosra niyam": "Boss, newton ke doosre niyam ke anusaar kisi vastu par lagne wala bal (F) uske dravyaman (m) aur tvaran (a) ke gunanfal ke barabar hota hai: F = m * a.",
        "paani ka rasayanik sutra": "Boss, paani ka rasayanik sutra H2O hota hai, jisme hydrogen ke 2 aur oxygen ka 1 parmanu hota hai.",
        "bharat ki rajdhani kya hai": "Boss, bharat ki rajdhani nai dilli (New Delhi) hai.",
        "saur mandal mein kitne grah hain": "Boss, hamare saur mandal mein kul 8 grah hain: budh, shukra, prithvi, mangal, brihaspati, shani, arun aur varun.",
        "atom kya hota hai": "Boss, atom (parmanu) padarth ki woh sabse chhoti ikai hai jisme us tatva ke gun maujood rehte hain.",
        "energy conservation law": "Boss, urja sanrakshan ke niyam ke anusaar urja ko na toh banaya ja sakta hai aur na hi nasht, balki ek roop se doosre roop mein badla ja sakta hai.",
    }
    data.update(core_study)

    subjects = [
        ("vigyan", "Vigyan prakriya aur prayog se niyam samajhne ka madhyam hai."),
        ("bhugol", "Bhugol prithvi ki satah, jalvayu, nadiyon aur sthanon ka adhyayan hai."),
        ("itihas", "Itihas beete hue samay aur ghatnaon ko samajhne ka zariya hai."),
        ("ganit", "Ganit sankhyaon, tark aur samasya samadhan ki bhasha hai."),
        ("nagrik shastra", "Nagrik shastra samvidhan, adhikar aur kartavyon ko samjhata hai."),
    ]

    for subj, base_line in subjects:
        for num in range(1, 450):
            if len(data) >= target_count:
                break
            q = f"{subj} avdharna {num}"
            a = (
                f"Boss, {subj} mein avdharna #{num} ka saransh yeh hai: {base_line} "
                f"Agar aap is topic ka koi khass prashn chahte hain toh pooch sakte hain."
            )
            data[q] = a

    return data


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate chat and study knowledge JSON files for KAILI AI.")
    parser.add_argument("--count", type=int, default=2000, help="Target entries per domain file (default: 2000)")
    args = parser.parse_args()

    os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
    chat_data = build_chat_knowledge(args.count)
    study_data = build_study_knowledge(args.count)

    chat_path = os.path.join(KNOWLEDGE_DIR, "chat.json")
    study_path = os.path.join(KNOWLEDGE_DIR, "study.json")

    with open(chat_path, "w", encoding="utf-8") as f:
        json.dump(chat_data, f, ensure_ascii=False, indent=2)

    with open(study_path, "w", encoding="utf-8") as f:
        json.dump(study_data, f, ensure_ascii=False, indent=2)

    print(f"Generated {len(chat_data)} entries in {chat_path}")
    print(f"Generated {len(study_data)} entries in {study_path}")


if __name__ == "__main__":
    main()
