from pure_offline_3d import generate_pure_offline_3d

def run_offline_3d_video_prompt(prompt: str):
    if not prompt:
        return None
    t = prompt.lower()
    triggers = ["3d", "3-d", "एनिमेशन", "animation", "वीडियो", "video", "गोला", "sphere", "अंतरिक्ष", "space"]
    if not any(k in t for k in triggers):
        return None
    return generate_pure_offline_3d(prompt)
