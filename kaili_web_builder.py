import os
import re
from typing import Dict

from kaili_ultimate_core import CREATOR, GREETING


def _safe_folder_name(title: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", (title or "").strip()).strip("_").lower()
    return slug[:40] or "kaili_website"


def build_website_project(
    topic: str,
    brand_name: str = "KAILI WEB",
    output_root: str = "generated_sites",
) -> Dict[str, object]:
    """Generate a clean HTML + CSS + JS website project for any given topic."""
    clean_topic = " ".join((topic or "").strip().split()) or "Modern Web Showcase"
    clean_brand = " ".join((brand_name or "").strip().split()) or "KAILI WEB"
    folder_name = _safe_folder_name(f"{clean_brand}_{clean_topic}")

    base_dir = os.path.dirname(os.path.abspath(__file__))
    site_dir = os.path.join(base_dir, output_root, folder_name)
    os.makedirs(site_dir, exist_ok=True)

    html_path = os.path.join(site_dir, "index.html")
    css_path = os.path.join(site_dir, "style.css")
    js_path = os.path.join(site_dir, "script.js")

    html_content = f"""<!DOCTYPE html>
<html lang="hi">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{clean_brand} — {clean_topic}</title>
  <link rel="stylesheet" href="style.css" />
</head>
<body>
  <header class="navbar">
    <div class="logo">{clean_brand}</div>
    <nav>
      <a href="#features">Features</a>
      <a href="#about">About</a>
      <a href="#contact">Action</a>
    </nav>
  </header>

  <section class="hero">
    <p class="tag">{GREETING} • Built by {CREATOR}</p>
    <h1>{clean_topic}</h1>
    <p class="subtitle">
      Fast, clean, and mobile-ready web experience generated for <strong>{clean_topic}</strong>.
    </p>
    <button id="demoBtn" class="btn">Explore Live Action</button>
    <p id="statusText" class="status"></p>
  </section>

  <section id="features" class="grid">
    <div class="card">
      <h3>Fast Structure</h3>
      <p>Clean semantic HTML5 layout with instant loading on mobile and desktop.</p>
    </div>
    <div class="card">
      <h3>Responsive UI</h3>
      <p>Adapts smoothly to phone screens, tablets, and wide monitors.</p>
    </div>
    <div class="card">
      <h3>Interactive JS</h3>
      <p>Ready for custom buttons, live state updates, and API integration.</p>
    </div>
  </section>

  <section id="about" class="about">
    <h2>About This Project</h2>
    <p>
      Created under <strong>{clean_brand}</strong> ({CREATOR}) focusing on <strong>{clean_topic}</strong>.
    </p>
  </section>

  <footer id="contact" class="footer">
    <p>{clean_brand} • Creator: {CREATOR}</p>
  </footer>

  <script src="script.js"></script>
</body>
</html>
"""

    css_content = """* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
  font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
}

body {
  background: #070b14;
  color: #f1f5f9;
  line-height: 1.6;
}

.navbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 6%;
  background: rgba(15, 23, 42, 0.9);
  border-bottom: 1px solid rgba(148, 163, 184, 0.15);
  position: sticky;
  top: 0;
}

.logo {
  font-weight: 700;
  font-size: 1.15rem;
  color: #38bdf8;
}

nav a {
  color: #cbd5e1;
  text-decoration: none;
  margin-left: 18px;
  font-size: 0.95rem;
}

nav a:hover {
  color: #38bdf8;
}

.hero {
  text-align: center;
  padding: 72px 6%;
  background: radial-gradient(circle at top, rgba(14, 165, 233, 0.18), transparent 65%);
}

.tag {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 999px;
  background: rgba(56, 189, 248, 0.14);
  color: #7dd3fc;
  font-size: 0.85rem;
  margin-bottom: 14px;
}

.hero h1 {
  font-size: clamp(1.9rem, 4vw, 3rem);
  margin-bottom: 12px;
}

.subtitle {
  max-width: 640px;
  margin: 0 auto 24px;
  color: #94a3b8;
}

.btn {
  background: #0284c7;
  color: #fff;
  border: none;
  padding: 12px 22px;
  border-radius: 10px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
}

.btn:hover {
  background: #0369a1;
}

.status {
  margin-top: 14px;
  color: #38bdf8;
  min-height: 24px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 18px;
  padding: 24px 6% 56px;
}

.card {
  background: #0f172a;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 14px;
  padding: 22px;
}

.card h3 {
  margin-bottom: 8px;
  color: #7dd3fc;
}

.about {
  padding: 36px 6% 56px;
  background: #0b1220;
  border-top: 1px solid rgba(148, 163, 184, 0.12);
}

.about h2 {
  margin-bottom: 10px;
}

.footer {
  text-align: center;
  padding: 24px 6%;
  color: #64748b;
  font-size: 0.9rem;
}
"""

    js_content = """document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("demoBtn");
  const status = document.getElementById("statusText");
  let clicks = 0;

  if (btn && status) {
    btn.addEventListener("click", () => {
      clicks += 1;
      status.textContent = `Interactive preview active (Clicks: ${clicks})`;
    });
  }
});
"""

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    with open(css_path, "w", encoding="utf-8") as f:
        f.write(css_content)
    with open(js_path, "w", encoding="utf-8") as f:
        f.write(js_content)

    return {
        "ok": True,
        "creator": CREATOR,
        "greeting": GREETING,
        "topic": clean_topic,
        "site_dir": site_dir,
        "files": [html_path, css_path, js_path],
    }


if __name__ == "__main__":
    out = build_website_project(
        topic="KAILI AI Studio & Game Showcase",
        brand_name="KAILI AI",
    )
    print("Website built:", out)
