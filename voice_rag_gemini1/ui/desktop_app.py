"""
ui/desktop_app.py
The main desktop GUI window — built with tkinter (no extra install needed).
Dark, futuristic aesthetic. Works on Windows, macOS, Linux.
"""
from __future__ import annotations
import os
import sys
import threading
import queue
import time
import math
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
from pathlib import Path
from typing import Optional


# ── colour palette ────────────────────────────────────────────────────────────
BG        = "#0a0d14"
BG2       = "#111520"
PANEL     = "#151b2e"
BORDER    = "#1e2d4a"
ACCENT    = "#00d4ff"
ACCENT2   = "#7b5ea7"
GREEN     = "#00ff88"
RED       = "#ff4466"
YELLOW    = "#ffd166"
TEXT      = "#d0e8ff"
TEXT_DIM  = "#4a6080"
FONT_MAIN = ("Consolas", 11)
FONT_BIG  = ("Consolas", 13, "bold")
FONT_SM   = ("Consolas", 9)


class PulseCanvas(tk.Canvas):
    """Animated pulse ring shown while listening / thinking."""

    def __init__(self, parent, size=120, **kw):
        super().__init__(parent, width=size, height=size,
                         bg=BG, highlightthickness=0, **kw)
        self.size = size
        self.cx = size // 2
        self.cy = size // 2
        self._state = "idle"   # idle | listening | thinking | speaking
        self._frame = 0
        self._running = True
        self._animate()

    def set_state(self, state: str):
        self._state = state
        self._frame = 0

    def _animate(self):
        if not self._running:
            return
        self.delete("all")
        f = self._frame
        cx, cy, r = self.cx, self.cy, self.size // 2 - 6

        if self._state == "idle":
            self._draw_idle(cx, cy, r)
        elif self._state == "listening":
            self._draw_listening(cx, cy, r, f)
        elif self._state == "thinking":
            self._draw_thinking(cx, cy, r, f)
        elif self._state == "speaking":
            self._draw_speaking(cx, cy, r, f)

        self._frame += 1
        self.after(40, self._animate)   # ~25 fps

    def _draw_idle(self, cx, cy, r):
        self.create_oval(cx-r, cy-r, cx+r, cy+r,
                         outline=BORDER, width=2)
        self.create_oval(cx-10, cy-10, cx+10, cy+10,
                         fill=BORDER, outline="")
        self.create_text(cx, cy+r+14, text="IDLE",
                         fill=TEXT_DIM, font=FONT_SM)

    def _draw_listening(self, cx, cy, r, f):
        # pulsing outer ring
        pulse = math.sin(f * 0.15) * 0.3 + 0.7
        pr = int(r * pulse)
        self.create_oval(cx-pr, cy-pr, cx+pr, cy+pr,
                         outline=GREEN, width=2)
        # inner mic dot
        self.create_oval(cx-14, cy-14, cx+14, cy+14,
                         fill=GREEN, outline="")
        # bars
        for i, h in enumerate([8, 14, 20, 14, 8]):
            hh = int(h * (0.5 + 0.5 * math.sin(f * 0.3 + i * 0.8)))
            x = cx - 20 + i * 10
            self.create_rectangle(x, cy - hh, x + 6, cy + hh,
                                  fill=GREEN, outline="")
        self.create_text(cx, cy+r+14, text="LISTENING",
                         fill=GREEN, font=FONT_SM)

    def _draw_thinking(self, cx, cy, r, f):
        # rotating arc
        start = (f * 6) % 360
        self.create_arc(cx-r, cy-r, cx+r, cy+r,
                        start=start, extent=270,
                        outline=ACCENT, width=3, style="arc")
        # inner dot spin
        angle = math.radians(f * 8)
        dx = int(math.cos(angle) * 20)
        dy = int(math.sin(angle) * 20)
        self.create_oval(cx+dx-5, cy+dy-5, cx+dx+5, cy+dy+5,
                         fill=ACCENT, outline="")
        self.create_text(cx, cy+r+14, text="THINKING",
                         fill=ACCENT, font=FONT_SM)

    def _draw_speaking(self, cx, cy, r, f):
        # sound wave rings
        for i in range(3):
            phase = (f * 0.2 + i * 1.0) % (2 * math.pi)
            alpha_r = int(r * (0.4 + 0.6 * ((i + 1) / 3)))
            fade = int(200 * abs(math.sin(phase)))
            col = f"#{fade:02x}88{fade:02x}"
            try:
                self.create_oval(cx-alpha_r, cy-alpha_r,
                                 cx+alpha_r, cy+alpha_r,
                                 outline=col, width=1)
            except Exception:
                pass
        self.create_oval(cx-12, cy-12, cx+12, cy+12,
                         fill=ACCENT2, outline="")
        self.create_text(cx, cy+r+14, text="SPEAKING",
                         fill=ACCENT2, font=FONT_SM)

    def destroy(self):
        self._running = False
        super().destroy()


class DesktopApp:
    """Main application window."""

    def __init__(self, agent, stt, tts):
        self.agent = agent
        self.stt   = stt
        self.tts   = tts

        self._ui_queue: queue.Queue = queue.Queue()
        self._busy = False

        self.root = tk.Tk()
        self.root.title("JARVIS  ·  Voice AI Agent  (Gemini)")
        self.root.geometry("960x700")
        self.root.minsize(760, 560)
        self.root.configure(bg=BG)
        self._build_ui()
        self._poll_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ─── UI Construction ──────────────────────────────────────────────────────

    def _build_ui(self):
        # ── top bar ──────────────────────────────────────────────────────────
        topbar = tk.Frame(self.root, bg=PANEL, height=52)
        topbar.pack(fill="x", side="top")
        topbar.pack_propagate(False)

        tk.Label(topbar, text="◈  JARVIS", fg=ACCENT, bg=PANEL,
                 font=("Consolas", 16, "bold")).pack(side="left", padx=20, pady=12)
        tk.Label(topbar, text="GEMINI  RAG  AGENT", fg=TEXT_DIM, bg=PANEL,
                 font=FONT_SM).pack(side="left", padx=0, pady=16)

        self._status_var = tk.StringVar(value="● READY")
        tk.Label(topbar, textvariable=self._status_var,
                 fg=GREEN, bg=PANEL, font=FONT_SM).pack(side="right", padx=20)

        # ── main body (left panel + right panel) ─────────────────────────────
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=12, pady=8)

        # LEFT — chat transcript
        left = tk.Frame(body, bg=BG)
        left.pack(side="left", fill="both", expand=True)

        tk.Label(left, text="CONVERSATION LOG", fg=TEXT_DIM,
                 bg=BG, font=FONT_SM).pack(anchor="w", pady=(0, 4))

        self.chat_box = scrolledtext.ScrolledText(
            left, bg=BG2, fg=TEXT, insertbackground=ACCENT,
            font=FONT_MAIN, relief="flat", bd=0,
            wrap="word", state="disabled",
            selectbackground=BORDER,
        )
        self.chat_box.pack(fill="both", expand=True)
        self._configure_chat_tags()

        # text input row
        input_frame = tk.Frame(left, bg=BG, pady=6)
        input_frame.pack(fill="x")
        self.text_input = tk.Entry(
            input_frame, bg=PANEL, fg=TEXT, insertbackground=ACCENT,
            font=FONT_MAIN, relief="flat", bd=0,
        )
        self.text_input.pack(side="left", fill="x", expand=True,
                             ipady=8, ipadx=10)
        self.text_input.bind("<Return>", lambda e: self._on_send_text())

        tk.Button(input_frame, text="SEND", command=self._on_send_text,
                  bg=ACCENT2, fg="white", font=FONT_SM,
                  relief="flat", padx=12, cursor="hand2").pack(side="left", padx=(6, 0))

        # RIGHT — controls
        right = tk.Frame(body, bg=BG, width=220)
        right.pack(side="right", fill="y", padx=(12, 0))
        right.pack_propagate(False)

        # pulse animation
        self.pulse = PulseCanvas(right, size=130)
        self.pulse.pack(pady=(8, 4))

        # big mic button
        self.mic_btn = tk.Button(
            right, text="🎙  SPEAK",
            command=self._on_mic_click,
            bg=GREEN, fg=BG, font=("Consolas", 12, "bold"),
            relief="flat", padx=10, pady=10, cursor="hand2",
            activebackground="#00cc77", activeforeground=BG,
        )
        self.mic_btn.pack(fill="x", padx=8, pady=4)

        tk.Button(right, text="⟳  NEW CHAT", command=self._on_reset,
                  bg=BORDER, fg=TEXT, font=FONT_SM,
                  relief="flat", pady=6, cursor="hand2").pack(fill="x", padx=8, pady=2)

        # separator
        tk.Frame(right, bg=BORDER, height=1).pack(fill="x", padx=8, pady=10)

        # Knowledge base section
        tk.Label(right, text="KNOWLEDGE BASE", fg=TEXT_DIM,
                 bg=BG, font=FONT_SM).pack(anchor="w", padx=8)

        tk.Button(right, text="+ Add Text File (.txt/.md)",
                  command=self._on_add_file,
                  bg=PANEL, fg=ACCENT, font=FONT_SM,
                  relief="flat", pady=5, cursor="hand2").pack(fill="x", padx=8, pady=2)

        tk.Button(right, text="+ Add PDF",
                  command=self._on_add_pdf,
                  bg=PANEL, fg=ACCENT, font=FONT_SM,
                  relief="flat", pady=5, cursor="hand2").pack(fill="x", padx=8, pady=2)

        tk.Button(right, text="+ Add Folder",
                  command=self._on_add_folder,
                  bg=PANEL, fg=ACCENT, font=FONT_SM,
                  relief="flat", pady=5, cursor="hand2").pack(fill="x", padx=8, pady=2)

        self._kb_count_var = tk.StringVar(value="0 chunks stored")
        tk.Label(right, textvariable=self._kb_count_var,
                 fg=TEXT_DIM, bg=BG, font=FONT_SM).pack(anchor="w", padx=8, pady=(2,0))

        # separator
        tk.Frame(right, bg=BORDER, height=1).pack(fill="x", padx=8, pady=10)

        # Tool activity log
        tk.Label(right, text="TOOL ACTIVITY", fg=TEXT_DIM,
                 bg=BG, font=FONT_SM).pack(anchor="w", padx=8)

        self.tool_box = tk.Text(
            right, bg=BG2, fg=YELLOW, font=FONT_SM,
            relief="flat", bd=0, height=10, wrap="word",
            state="disabled",
        )
        self.tool_box.pack(fill="both", expand=True, padx=8, pady=4)

        self._update_kb_count()

    def _configure_chat_tags(self):
        self.chat_box.tag_configure("user",   foreground=ACCENT,  font=("Consolas", 11, "bold"))
        self.chat_box.tag_configure("agent",  foreground=GREEN,   font=FONT_MAIN)
        self.chat_box.tag_configure("system", foreground=TEXT_DIM, font=FONT_SM)
        self.chat_box.tag_configure("error",  foreground=RED,     font=FONT_MAIN)

    # ─── Chat helpers ─────────────────────────────────────────────────────────

    def _append_chat(self, speaker: str, text: str, tag: str = "agent"):
        self.chat_box.configure(state="normal")
        ts = time.strftime("%H:%M")
        self.chat_box.insert("end", f"\n[{ts}] {speaker}\n", tag)
        self.chat_box.insert("end", f"{text}\n")
        self.chat_box.configure(state="disabled")
        self.chat_box.see("end")

    def _append_tool(self, name: str, info: str = ""):
        self.tool_box.configure(state="normal")
        ts = time.strftime("%H:%M:%S")
        self.tool_box.insert("end", f"[{ts}] {name}\n")
        if info:
            self.tool_box.insert("end", f"  {info[:60]}\n")
        self.tool_box.configure(state="disabled")
        self.tool_box.see("end")

    def _set_status(self, text: str, color: str = GREEN):
        self._status_var.set(text)
        # find the status label and recolour it
        for w in self.root.winfo_children()[0].winfo_children():
            if isinstance(w, tk.Label) and w.cget("textvariable") == str(self._status_var):
                w.configure(fg=color)

    def _update_kb_count(self):
        if self.agent.kb:
            n = self.agent.kb.collection.count()
            self._kb_count_var.set(f"{n} chunks stored")

    # ─── Event handlers ───────────────────────────────────────────────────────

    def _on_mic_click(self):
        if self._busy:
            return
        self._busy = True
        threading.Thread(target=self._voice_flow, daemon=True).start()

    def _voice_flow(self):
        """Full pipeline: record → STT → agent → TTS (runs in bg thread)."""
        self._ui_queue.put(("state", "listening"))

        # 1. Record + transcribe
        text = self.stt.record_and_transcribe(max_seconds=15)
        if not text:
            self._ui_queue.put(("state", "idle"))
            self._ui_queue.put(("chat", ("⚠", "Could not hear anything — try again.", "system")))
            self._busy = False
            return

        self._ui_queue.put(("chat", ("YOU", text, "user")))
        self._ui_queue.put(("state", "thinking"))
        self._ui_queue.put(("chat", ("JARVIS", "⏳ Thinking... (Gemini API)", "system")))

        # 2. Agent
        response = self.agent.chat(text)

        # 3. Speak
        self._ui_queue.put(("state", "speaking"))
        self._ui_queue.put(("chat", ("JARVIS", response, "agent")))
        self.tts.speak(response, blocking=False)   # non-blocking so GUI stays alive

        self._ui_queue.put(("state", "idle"))
        self._busy = False

    def _on_send_text(self):
        """Handle typed message."""
        text = self.text_input.get().strip()
        if not text or self._busy:
            return
        self.text_input.delete(0, "end")
        self._busy = True

        def _run():
            self._ui_queue.put(("chat", ("YOU", text, "user")))
            self._ui_queue.put(("state", "thinking"))
            self._ui_queue.put(("chat", ("JARVIS", "⏳ Thinking... (Gemini API)", "system")))
            response = self.agent.chat(text)
            self._ui_queue.put(("state", "speaking"))
            self._ui_queue.put(("chat", ("JARVIS", response, "agent")))
            self.tts.speak(response, blocking=False)   # non-blocking
            self._ui_queue.put(("state", "idle"))
            self._busy = False

        threading.Thread(target=_run, daemon=True).start()

    def _on_reset(self):
        self.agent.reset()
        self._append_chat("SYSTEM", "Conversation cleared.", "system")

    def _on_add_file(self):
        path = filedialog.askopenfilename(
            title="Select a text / markdown file",
            filetypes=[("Text files", "*.txt *.md"), ("All files", "*.*")]
        )
        if path and self.agent.kb:
            n = self.agent.kb.add_file(path)
            self._append_chat("SYSTEM", f"Added {Path(path).name} → {n} chunks", "system")
            self._update_kb_count()

    def _on_add_pdf(self):
        path = filedialog.askopenfilename(
            title="Select a PDF",
            filetypes=[("PDF files", "*.pdf")]
        )
        if path and self.agent.kb:
            n = self.agent.kb.add_file(path)
            self._append_chat("SYSTEM", f"Added {Path(path).name} → {n} chunks", "system")
            self._update_kb_count()

    def _on_add_folder(self):
        folder = filedialog.askdirectory(title="Select folder to ingest")
        if folder and self.agent.kb:
            n = self.agent.kb.add_folder(folder)
            self._append_chat("SYSTEM", f"Added folder → {n} total chunks", "system")
            self._update_kb_count()

    def _on_close(self):
        self.tts.stop()
        self.root.destroy()

    # ─── UI queue polling (thread-safe UI updates) ────────────────────────────

    def _poll_ui(self):
        try:
            while True:
                msg = self._ui_queue.get_nowait()
                kind = msg[0]

                if kind == "state":
                    state = msg[1]
                    self.pulse.set_state(state)
                    labels = {
                        "idle":      ("● READY",    GREEN),
                        "listening": ("◉ LISTENING", GREEN),
                        "thinking":  ("◌ THINKING",  ACCENT),
                        "speaking":  ("▶ SPEAKING",  ACCENT2),
                    }
                    if state in labels:
                        txt, col = labels[state]
                        self._status_var.set(txt)

                elif kind == "chat":
                    _, (speaker, text, tag) = msg
                    self._append_chat(speaker, text, tag)

                elif kind == "tool":
                    _, (name, info) = msg
                    self._append_tool(name, info)

        except queue.Empty:
            pass
        self.root.after(50, self._poll_ui)

    # ─── Public callbacks (called from agent thread) ───────────────────────────

    def on_tool_call(self, name: str, inputs: dict):
        import json
        info = json.dumps(inputs)[:80]
        self._ui_queue.put(("tool", (name, info)))

    def on_response(self, text: str):
        pass   # already handled in _voice_flow / _on_send_text

    # ─── Run ──────────────────────────────────────────────────────────────────

    def run(self):
        # Welcome message
        self._append_chat("SYSTEM",
            "JARVIS is online. Click 🎙 SPEAK or type below. "
            "You can also add documents to the knowledge base.", "system")
        self.root.mainloop()
