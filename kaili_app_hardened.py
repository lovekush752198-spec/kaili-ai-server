import threading
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from kivy.app import App
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.textinput import TextInput

from kaili_security_shield import RateLimiter, inspect_input_safety
from kaili_ultimate_core import CREATOR, GREETING, build_multi_scene_package
from math_science_engine import eval_expression

LIVE_SERVER_URL = "https://kaili-ai-server-1.onrender.com"
SESSION_ID = "kaili_live_boss"


def build_resilient_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=2,
        backoff_factor=0.6,
        status_forcelist=[502, 503, 504],
        allowed_methods=["POST", "GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


class TricolorBanner(BoxLayout):
    """Bigger Tiranga (Indian Flag) bar with Saffron, White, Green bands."""

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", size_hint=(None, None), size=(156, 86), **kwargs)
        with self.canvas.before:
            Color(1.0, 0.42, 0.05, 1)
            self._r_saffron = Rectangle(pos=self.pos, size=(self.width, self.height / 3))

            Color(1.0, 1.0, 1.0, 1)
            self._r_white = Rectangle(pos=(self.x, self.y + self.height / 3), size=(self.width, self.height / 3))

            Color(0.07, 0.53, 0.03, 1)
            self._r_green = Rectangle(pos=(self.x, self.y + 2 * self.height / 3), size=(self.width, self.height / 3))

        self.bind(pos=self._sync_rects, size=self._sync_rects)

    def _sync_rects(self, *_):
        third = self.height / 3.0
        self._r_saffron.pos = (self.x, self.y + 2 * third)
        self._r_saffron.size = (self.width, third)

        self._r_white.pos = (self.x, self.y + third)
        self._r_white.size = (self.width, third)

        self._r_green.pos = (self.x, self.y)
        self._r_green.size = (self.width, third)


class SplashScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(name="splash", **kwargs)
        root = BoxLayout(orientation="vertical", padding=18, spacing=14)

        top_bar = BoxLayout(orientation="horizontal", size_hint_y=None, height=100)
        top_bar.add_widget(Label(text=""))
        flag_box = BoxLayout(orientation="vertical", size_hint=(None, None), size=(162, 100), spacing=2)
        flag_box.add_widget(TricolorBanner())
        flag_box.add_widget(Label(text="INDIA", size_hint_y=None, height=16, font_size="12sp"))
        top_bar.add_widget(flag_box)
        root.add_widget(top_bar)

        root.add_widget(Label(text=""))
        root.add_widget(Label(text="KAILI AI", font_size="34sp", bold=True, size_hint_y=None, height=56))
        root.add_widget(
            Label(
                text=f'CREATOR "{CREATOR}"  |  {GREETING}',
                font_size="15sp",
                size_hint_y=None,
                height=34,
            )
        )

        enter_btn = Button(text="Enter Live KAILI AI", size_hint_y=None, height=52)
        enter_btn.bind(on_press=lambda _: setattr(self.manager, "current", "core"))
        root.add_widget(enter_btn)
        root.add_widget(Label(text=""))
        self.add_widget(root)


class CoreScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(name="core", **kwargs)
        self.limiter = RateLimiter(max_requests=30, window_seconds=60)
        self.http = build_resilient_session()
        self.voice_enabled = False
        self._lock = threading.Lock()
        self._busy = False

        root = BoxLayout(orientation="vertical", padding=12, spacing=8)

        top = BoxLayout(size_hint_y=None, height=44, spacing=8)
        top.add_widget(Label(text=f"KAILI AI  |  {GREETING}", bold=True))
        self.voice_btn = Button(text="Voice: OFF", size_hint_x=None, width=115)
        self.voice_btn.bind(on_press=self.toggle_voice_stable)
        top.add_widget(self.voice_btn)
        root.add_widget(top)

        self.status_lbl = Label(
            text=f"{GREETING}, Hardened Live Mode ready",
            size_hint_y=None,
            height=28,
            font_size="12sp",
        )
        root.add_widget(self.status_lbl)

        self.scroll = ScrollView(size_hint=(1, 1))
        self.log_lbl = Label(
            text=f"{GREETING}, KAILI Hardened Live taiyar hai.\n\n",
            size_hint_y=None,
            valign="top",
        )
        self.log_lbl.bind(width=lambda inst, w: setattr(inst, "text_size", (w, None)))
        self.log_lbl.bind(texture_size=self.log_lbl.setter("size"))
        self.scroll.add_widget(self.log_lbl)
        root.add_widget(self.scroll)

        self.input_box = TextInput(
            hint_text="Message, math, '4k ...', या 'comment: ...' likhein",
            multiline=False,
            size_hint_y=None,
            height=46,
        )
        self.input_box.bind(on_text_validate=lambda _: self.run_live_task())
        root.add_widget(self.input_box)

        action_row = BoxLayout(size_hint_y=None, height=46, spacing=8)
        send_btn = Button(text="Run Live")
        send_btn.bind(on_press=lambda _: self.run_live_task())
        studio_btn = Button(text="4K Studio")
        studio_btn.bind(on_press=lambda _: setattr(self.manager, "current", "studio"))
        clear_btn = Button(text="Clear")
        clear_btn.bind(on_press=lambda _: setattr(self.log_lbl, "text", f"{GREETING}, log clear ho gaya.\n\n"))
        action_row.add_widget(send_btn)
        action_row.add_widget(studio_btn)
        action_row.add_widget(clear_btn)
        root.add_widget(action_row)

        self.add_widget(root)

    def toggle_voice_stable(self, _btn) -> None:
        self.voice_enabled = not self.voice_enabled
        self.voice_btn.text = "Voice: ON" if self.voice_enabled else "Voice: OFF"
        self.status_lbl.text = f"{GREETING}, Voice mode -> {'ON (Stable)' if self.voice_enabled else 'OFF'}"

    def _append(self, text: str) -> None:
        self.log_lbl.text += text + "\n\n"
        Clock.schedule_once(lambda dt: setattr(self.scroll, "scroll_y", 0), 0.05)

    def _auto_task_executor(self, msg: str) -> str:
        low = msg.strip().lower()
        if low.startswith("comment:") or "comment likh" in low or "kament likh" in low:
            custom = msg.split(":", 1)[1].strip() if ":" in msg else ""
            return (
                f"{GREETING}, yeh raha aapke liye taiyar comment:\n"
                f"\"{custom or 'Bahut shaandar kaam hai Boss, aise hi aage badhte rahiye!'}\""
            )

        if low.startswith("4k ") or "4k video" in low or "pov " in low:
            pack = build_multi_scene_package(topic=msg, style="pov", scenes=3, sec_per_scene=3)
            lines = [f"{GREETING}, 4K Multi-Scene Pack ({pack['total_duration_sec']}s):"]
            for sc in pack["scenes"]:
                lines.append(f"- Scene {sc['scene']}: {sc['video_prompt']}")
            return "\n".join(lines)

        if any(op in low for op in ["+", "-", "*", "/", "^", "sin(", "cos(", "tan(", "sqrt("]):
            calc = eval_expression(msg)
            if calc.get("ok"):
                return f"{GREETING}, Calculation Result ({calc.get('expression')}): {calc.get('result')}"

        return ""

    def run_live_task(self) -> None:
        with self._lock:
            if self._busy:
                return
            msg = self.input_box.text.strip()
            if not msg:
                return
            self.input_box.text = ""

            allowed, info = self.limiter.allow(SESSION_ID)
            if not allowed:
                self._append(f"{GREETING}, rate limit active ({info['retry_after_sec']}s baad try karein).")
                return

            safety = inspect_input_safety(msg)
            if not safety.get("safe"):
                self._append(f"{GREETING}, unsafe input block kiya gaya: {safety.get('reasons')}")
                return

            self._busy = True

        self._append(f"You: {msg}")
        local_auto = self._auto_task_executor(msg)
        if local_auto:
            with self._lock:
                self._busy = False
            self._append(f"KAILI (Auto): {local_auto}")
            return

        self.status_lbl.text = f"{GREETING}, Live Server se jawab la raha hoon..."
        threading.Thread(target=self._call_live_server, args=(msg,), daemon=True).start()

    def _call_live_server(self, msg: str) -> None:
        started = time.time()
        reply_text = ""
        try:
            resp = self.http.post(
                f"{LIVE_SERVER_URL}/api/chat",
                json={"session_id": SESSION_ID, "message": msg},
                timeout=(6, 22),
            )
            resp.raise_for_status()
            data = resp.json()
            reply_text = str(data.get("reply") or "").strip()
        except Exception as exc:
            reply_text = f"{GREETING}, server response me dikkat aayi: {exc}"

        if not reply_text:
            reply_text = f"{GREETING}, server se khali jawab aaya."

        elapsed = round(time.time() - started, 2)
        Clock.schedule_once(lambda dt, r=reply_text, t=elapsed: self._finish_live_call(r, t), 0)

    def _finish_live_call(self, reply_text: str, elapsed: float) -> None:
        with self._lock:
            self._busy = False
        self.status_lbl.text = f"{GREETING}, Live Server ready ({elapsed}s)"
        self._append(f"KAILI (Live): {reply_text}")


class StudioScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(name="studio", **kwargs)
        root = BoxLayout(orientation="vertical", padding=14, spacing=12)
        root.add_widget(Label(text=f"KAILI STUDIO  |  {GREETING}", font_size="20sp", bold=True, size_hint_y=None, height=40))
        self.topic_input = TextInput(hint_text="4K Studio topic likhein...", multiline=False, size_hint_y=None, height=46)
        root.add_widget(self.topic_input)

        self.out_lbl = Label(text="", size_hint=(1, 1), valign="top")
        self.out_lbl.bind(width=lambda inst, w: setattr(inst, "text_size", (w, None)))
        root.add_widget(self.out_lbl)

        gen_btn = Button(text="Generate 4K Scene Plan", size_hint_y=None, height=48)
        gen_btn.bind(on_press=self.build_plan)
        back_btn = Button(text="Back to Core", size_hint_y=None, height=48)
        back_btn.bind(on_press=lambda _: setattr(self.manager, "current", "core"))
        root.add_widget(gen_btn)
        root.add_widget(back_btn)
        self.add_widget(root)

    def build_plan(self, _btn) -> None:
        topic = self.topic_input.text.strip() or "KAILI AI Live Showcase"
        pack = build_multi_scene_package(topic=topic, style="explainer", scenes=3, sec_per_scene=3)
        lines = [f"{GREETING}, {pack['topic']} ({pack['resolution']}):"]
        for sc in pack["scenes"]:
            lines.append(f"Scene {sc['scene']}: {sc['voice_line']}")
        self.out_lbl.text = "\n".join(lines)


class KailiHardenedApp(App):
    def build(self):
        self.title = "KAILI AI"
        sm = ScreenManager()
        sm.add_widget(SplashScreen())
        sm.add_widget(CoreScreen())
        sm.add_widget(StudioScreen())
        sm.current = "splash"
        return sm


if __name__ == "__main__":
    KailiHardenedApp().run()
