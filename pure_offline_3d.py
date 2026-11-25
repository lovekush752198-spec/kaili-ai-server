import os
import re
import time

MEDIA_DIR = os.path.expanduser("~/kaili-api/media")
os.makedirs(MEDIA_DIR, exist_ok=True)


def _parse_3d_request(prompt_text):
    t = prompt_text.lower()

    if any(w in t for w in ("गोला", "बॉल", "ऑर्ब", "ग्रह", "sphere", "ball", "orb")):
        shape = "sphere"
    elif any(w in t for w in ("पिरामिड", "कोन", "pyramid", "cone")):
        shape = "pyramid"
    else:
        shape = "cube"

    color_map = {
        "नीला": "#00B7FF", "blue": "#00B7FF",
        "हरा": "#00FF88", "green": "#00FF88",
        "लाल": "#FF3B5C", "red": "#FF3B5C",
        "पीला": "#FFD43B", "yellow": "#FFD43B",
        "बैंगनी": "#9B5DE5", "purple": "#9B5DE5",
        "नारंगी": "#FF8C42", "orange": "#FF8C42",
    }
    accent = "#00B7FF"
    for k, hx in color_map.items():
        if k in t:
            accent = hx
            break

    dur_match = re.search(r"(\d+)\s*(?:सेकंड|sec|second|s)", t)
    duration = max(4, min(60, int(dur_match.group(1)))) if dur_match else 8

    excludes = []
    for m in re.findall(r"(?:बिना|नहीं\s+हो|नहीं\s+चाहिए|exclude|without)\s+([a-zA-Z\u0900-\u097F0-9_ -]{2,25})", prompt_text, flags=re.IGNORECASE):
        val = m.strip(" .,।")
        if val and val not in excludes:
            excludes.append(val)

    return shape, accent, duration, excludes


def generate_pure_offline_3d(prompt_text):
    clean_p = prompt_text.strip()
    shape, accent, duration, excludes = _parse_3d_request(clean_p)

    ex_text = f"बाहर रखा गया: {', '.join(excludes)}" if excludes else "बाहर रखा गया: कुछ नहीं"
    script_lines = [
        f"01 [शुरुआत]: '{clean_p}' का 3D स्पेस और कैमरा शुरू होता है।",
        f"02 [3D मोशन]: {shape.upper()} ऑब्जेक्ट ({accent}) 3D अक्षों पर घूमता है।",
        f"03 [नियम]: {ex_text}।",
        f"04 [समाप्ति]: {duration}s पर सीक्वेंस पूरा होकर अंतिम फ़्रेम रुकता है।",
    ]

    ts = int(time.time())
    html_file = os.path.join(MEDIA_DIR, f"pure3d_{ts}.html")
    safe_title = clean_p.replace("<", "").replace(">", "")[:55]
    li_items = "".join(f"<li>{line}</li>" for line in script_lines)

    page = f"""<!DOCTYPE html>
<html lang="hi">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>Kaili 3D - {safe_title}</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:#050811;color:#e2e8f0;font-family:sans-serif;display:flex;flex-direction:column;height:100vh}}
  canvas{{flex:1;width:100%;display:block}}
  .bar{{background:#0c1324;border-top:1px solid #1e293b;padding:10px 14px;font-size:12px;max-height:36vh;overflow:auto}}
  .bar b{{color:{accent};display:block;margin-bottom:4px}}
  ul{{padding-left:18px;line-height:1.45}}
</style>
</head>
<body>
<canvas id="c"></canvas>
<div class="bar">
  <b>3D स्क्रिप्ट ({duration}s) — {safe_title}</b>
  <ul>{li_items}</ul>
</div>
<script>
const canvas = document.getElementById('c');
const ctx = canvas.getContext('2d');
const shape = '{shape}';
const color = '{accent}';
const duration = {duration};

function resize() {{
  canvas.width = canvas.clientWidth || window.innerWidth;
  canvas.height = canvas.clientHeight || (window.innerHeight * 0.64);
}}
resize();
window.addEventListener('resize', resize);

function project(x, y, z, rx, ry, fov, cx, cy) {{
  let cosY = Math.cos(ry), sinY = Math.sin(ry);
  let x1 = x * cosY - z * sinY;
  let z1 = x * sinY + z * cosY;
  let cosX = Math.cos(rx), sinX = Math.sin(rx);
  let y2 = y * cosX - z1 * sinX;
  let z2 = y * sinX + z1 * cosX + 4.2;
  let scale = fov / Math.max(0.4, z2);
  return {{ px: cx + x1 * scale, py: cy + y2 * scale, s: scale }};
}}

const vertices = shape === 'pyramid'
  ? [[0,-1.1,0],[-1,1,-1],[1,1,-1],[1,1,1],[-1,1,1]]
  : [[-1,-1,-1],[1,-1,-1],[1,1,-1],[-1,1,-1],[-1,-1,1],[1,-1,1],[1,1,1],[-1,1,1]];

const edges = shape === 'pyramid'
  ? [[0,1],[0,2],[0,3],[0,4],[1,2],[2,3],[3,4],[4,1]]
  : [[0,1],[1,2],[2,3],[3,0],[4,5],[5,6],[6,7],[7,4],[0,4],[1,5],[2,6],[3,7]];

const t0 = performance.now();
function loop(now) {{
  const sec = ((now - t0) / 1000) % duration;
  const p = sec / duration;
  ctx.fillStyle = '#050811';
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  const cx = canvas.width / 2;
  const cy = canvas.height / 2;
  const fov = Math.min(canvas.width, canvas.height) * 0.55;
  const ry = p * Math.PI * 2;
  const rx = Math.sin(p * Math.PI * 2) * 0.6;

  ctx.strokeStyle = color;
  ctx.lineWidth = 2.5;

  if (shape === 'sphere') {{
    const r = Math.min(canvas.width, canvas.height) * 0.22 * (0.9 + 0.12 * Math.sin(p * Math.PI * 2));
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.stroke();
    for (let i = 1; i <= 3; i++) {{
      ctx.beginPath();
      ctx.ellipse(cx, cy, r * Math.abs(Math.cos(ry + i * 0.6)), r, 0, 0, Math.PI * 2);
      ctx.stroke();
    }}
  }} else {{
    const pts = vertices.map(v => project(v[0], v[1], v[2], rx, ry, fov, cx, cy));
    for (const [a, b] of edges) {{
      ctx.beginPath();
      ctx.moveTo(pts[a].px, pts[a].py);
      ctx.lineTo(pts[b].px, pts[b].py);
      ctx.stroke();
    }}
  }}

  ctx.fillStyle = '#94a3b8';
  ctx.font = '12px sans-serif';
  ctx.fillText(`Time: ${{sec.toFixed(1)}}s / ${{duration}}s | 3D Mode: ${{shape}}`, 14, 22);
  requestAnimationFrame(loop);
}}
requestAnimationFrame(loop);
</script>
</body>
</html>
"""
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(page)

    return {
        "reply": (
            f"ऑफलाइन 3D वीडियो जनरेट हो गया!\n"
            f"फ़ाइल: {html_file}\n"
            f"स्क्रिप्ट:\n" + "\n".join(script_lines)
        ),
        "status": "ok",
        "source": "pure_offline_3d",
        "media_file": html_file,
        "media_type": "3d_video",
    }
