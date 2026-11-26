import os
import re
from typing import Dict, Optional

from kaili_ultimate_core import CREATOR, GREETING


def _safe_slug(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", (name or "").strip()).strip("_").lower()
    return slug[:40] or "kaili_mini_app"


def build_mini_web_app(
    app_name: str = "KAILI Quick Notes",
    purpose: str = "Fast notes & tasks mini app",
    output_root: str = "generated_apps",
) -> Dict[str, object]:
    clean_name = " ".join((app_name or "").strip().split()) or "KAILI Mini App"
    clean_purpose = " ".join((purpose or "").strip().split()) or "Interactive utility app"
    folder = _safe_slug(clean_name)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    app_dir = os.path.join(base_dir, output_root, folder)
    os.makedirs(app_dir, exist_ok=True)

    html_path = os.path.join(app_dir, "index.html")
    css_path = os.path.join(app_dir, "style.css")
    js_path = os.path.join(app_dir, "app.js")

    html_code = f"""<!DOCTYPE html>
<html lang="hi">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{clean_name}</title>
  <link rel="stylesheet" href="style.css" />
</head>
<body>
  <main class="app-box">
    <p class="badge">{GREETING} • {CREATOR}</p>
    <h1>{clean_name}</h1>
    <p class="desc">{clean_purpose}</p>

    <div class="input-row">
      <input id="itemInput" type="text" placeholder="Naya note ya task likhein..." />
      <button id="addBtn">Add</button>
    </div>

    <ul id="itemList" class="list"></ul>
  </main>
  <script src="app.js"></script>
</body>
</html>
"""

    css_code = """* {
  box-sizing: border-box;
  font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
}

body {
  margin: 0;
  padding: 24px;
  background: #070b14;
  color: #f8fafc;
  display: flex;
  justify-content: center;
}

.app-box {
  width: 100%;
  max-width: 480px;
  background: #0f172a;
  border: 1px solid rgba(56, 189, 248, 0.25);
  border-radius: 16px;
  padding: 22px;
}

.badge {
  display: inline-block;
  font-size: 0.8rem;
  color: #7dd3fc;
  background: rgba(56, 189, 248, 0.14);
  padding: 4px 10px;
  border-radius: 999px;
  margin: 0 0 10px;
}

h1 {
  margin: 0 0 6px;
  font-size: 1.5rem;
}

.desc {
  margin: 0 0 18px;
  color: #94a3b8;
  font-size: 0.92rem;
}

.input-row {
  display: flex;
  gap: 8px;
}

input {
  flex: 1;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid #334155;
  background: #020617;
  color: #fff;
}

button {
  padding: 10px 16px;
  border: none;
  border-radius: 10px;
  background: #0284c7;
  color: #fff;
  font-weight: 600;
  cursor: pointer;
}

.list {
  list-style: none;
  padding: 0;
  margin: 18px 0 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #1e293b;
  padding: 10px 12px;
  border-radius: 10px;
}

.del-btn {
  background: #dc2626;
  padding: 6px 10px;
  font-size: 0.8rem;
}
"""

    js_code = """const STORAGE_KEY = "kaili_mini_app_items_v1";

function loadItems() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
  } catch {
    return [];
  }
}

function saveItems(items) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
}

function render() {
  const list = document.getElementById("itemList");
  const items = loadItems();
  list.innerHTML = "";

  items.forEach((text, idx) => {
    const li = document.createElement("li");
    li.className = "item";

    const span = document.createElement("span");
    span.textContent = text;

    const del = document.createElement("button");
    del.className = "del-btn";
    del.textContent = "Delete";
    del.onclick = () => {
      const next = loadItems().filter((_, i) => i !== idx);
      saveItems(next);
      render();
    };

    li.appendChild(span);
    li.appendChild(del);
    list.appendChild(li);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("itemInput");
  const addBtn = document.getElementById("addBtn");

  const addCurrent = () => {
    const val = (input.value || "").trim();
    if (!val) return;
    const next = loadItems();
    next.unshift(val);
    saveItems(next);
    input.value = "";
    render();
  };

  addBtn.addEventListener("click", addCurrent);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") addCurrent();
  });

  render();
});
"""

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_code)
    with open(css_path, "w", encoding="utf-8") as f:
        f.write(css_code)
    with open(js_path, "w", encoding="utf-8") as f:
        f.write(js_code)

    return {
        "ok": True,
        "creator": CREATOR,
        "greeting": GREETING,
        "app_name": clean_name,
        "app_dir": app_dir,
        "files": [html_path, css_path, js_path],
    }


def handle_app_command(message: str) -> Optional[Dict[str, object]]:
    text = (message or "").strip()
    low = text.lower()
    triggers = ("app banao:", "create app:", "mini app:", "build app:", "ऐप बनाओ:")
    for trig in triggers:
        if low.startswith(trig):
            raw_spec = text[len(trig):].strip()
            parts = [p.strip() for p in re.split(r"\||-|\bfor\b", raw_spec, maxsplit=1)]
            app_name = parts[0] if parts and parts[0] else "KAILI Mini App"
            purpose = parts[1] if len(parts) > 1 and parts[1] else f"Interactive mini app for {app_name}"
            return build_mini_web_app(app_name=app_name, purpose=purpose)
    return None


if __name__ == "__main__":
    print("App test result:", handle_app_command("app banao: Boss Quick Notes - Fast notes app"))
