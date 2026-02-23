# -*- coding: utf-8 -*-
import customtkinter as ctk
import tkinter as tk
import threading
import asyncio
import logging
import pyaudio
import sys

import vv_streaming_master as engine

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class GUILogHandler(logging.Handler):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def emit(self, record):
        self.callback(self.format(record))


class VerseViewApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("VerseView Live")
        self.geometry("1000x640")
        self.minsize(800, 500)

        self._engine_thread = None
        self._running       = False

        self._build_ui()
        self._populate_mics()
        self._attach_log_handler()


    def _build_ui(self):
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)

        # ===== LEFT PANEL =====
        left = ctk.CTkFrame(self)
        left.grid(row=0, column=0, padx=(12, 6), pady=12, sticky="nsew")
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        # Top bar
        top = ctk.CTkFrame(left, fg_color="transparent")
        top.grid(row=0, column=0, padx=10, pady=(10, 6), sticky="ew")

        self.btn_start = ctk.CTkButton(
            top, text="▶  START", width=130,
            fg_color="#2a7a2a", hover_color="#1f5c1f",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._start
        )
        self.btn_start.pack(side="left", padx=(0, 8))

        self.btn_stop = ctk.CTkButton(
            top, text="⏹  STOP", width=130,
            fg_color="#7a2a2a", hover_color="#5c1f1f",
            font=ctk.CTkFont(size=13, weight="bold"),
            state="disabled",
            command=self._stop
        )
        self.btn_stop.pack(side="left", padx=(0, 16))

        self.lbl_status = ctk.CTkLabel(
            top, text="● Stopped",
            text_color="#666666",
            font=ctk.CTkFont(size=13)
        )
        self.lbl_status.pack(side="left")

        # Log output
        self.log_box = ctk.CTkTextbox(
            left, state="disabled",
            font=("Courier New", 11),
            wrap="word"
        )
        self.log_box.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")

        # Clear log button
        ctk.CTkButton(
            left, text="Clear Log", height=28,
            fg_color="transparent", border_width=1,
            text_color=("gray40", "gray60"),
            command=self._clear_log
        ).grid(row=2, column=0, padx=10, pady=(0, 8), sticky="e")

        # ===== RIGHT PANEL =====
        right = ctk.CTkScrollableFrame(self, label_text="⚙   Settings",
                                        label_font=ctk.CTkFont(size=14, weight="bold"))
        right.grid(row=0, column=1, padx=(6, 12), pady=12, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)

        def section_label(parent, text, row):
            ctk.CTkLabel(
                parent, text=text, anchor="w",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=("gray30", "gray70")
            ).grid(row=row, column=0, sticky="ew", padx=14, pady=(14, 2))

        def entry_row(parent, label, default, row):
            section_label(parent, label, row)
            e = ctk.CTkEntry(parent)
            e.insert(0, default)
            e.grid(row=row + 1, column=0, sticky="ew", padx=14, pady=(0, 4))
            return e

        # Language
        section_label(right, "Language", 0)
        self.lang_var  = ctk.StringVar(value="English (Nova-2)")
        self.lang_menu = ctk.CTkOptionMenu(
            right, variable=self.lang_var,
            values=[
                "English (Nova-2)",
                "Malayalam (Sarvam AI)",
                "Hindi (Nova-3)",
                "Multi (Nova-2)",
            ]
        )
        self.lang_menu.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 4))

        # Microphone
        section_label(right, "Microphone", 2)
        self.mic_var  = ctk.StringVar(value="Loading...")
        self.mic_menu = ctk.CTkOptionMenu(right, variable=self.mic_var, values=["Loading..."])
        self.mic_menu.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 4))

        # Refresh mic button
        ctk.CTkButton(
            right, text="↺  Refresh Mics", height=28,
            fg_color="transparent", border_width=1,
            text_color=("gray40", "gray60"),
            command=self._populate_mics
        ).grid(row=4, column=0, sticky="ew", padx=14, pady=(0, 8))

        # VerseView URL
        section_label(right, "VerseView URL", 5)
        self.url_entry = ctk.CTkEntry(right, placeholder_text="http://localhost:50010/control.html")
        self.url_entry.insert(0, "http://localhost:50010/control.html")
        self.url_entry.grid(row=6, column=0, sticky="ew", padx=14, pady=(0, 4))

        
        self._adv_open = False
        self.btn_adv   = ctk.CTkButton(
            right, text="▶   Advanced Settings",
            fg_color="transparent",
            text_color=("gray40", "gray60"),
            anchor="w", hover=False,
            command=self._toggle_advanced
        )
        self.btn_adv.grid(row=7, column=0, sticky="ew", padx=10, pady=(14, 2))

        
        self.adv_frame = ctk.CTkFrame(right)
        self.adv_frame.grid_columnconfigure(1, weight=1)
        self._build_advanced()

    def _build_advanced(self):
        fields = [
            ("Sample Rate",       "16000",  "rate_entry"),
            ("Chunk Size",        "4096",   "chunk_entry"),
            ("Cooldown (s)",      "3.0",    "cooldown_entry"),
            ("Dedup Window (s)",  "60",     "dedup_entry"),
        ]
        for i, (lbl, default, attr) in enumerate(fields):
            ctk.CTkLabel(self.adv_frame, text=lbl, anchor="w").grid(
                row=i, column=0, padx=10, pady=4, sticky="w"
            )
            e = ctk.CTkEntry(self.adv_frame, width=90)
            e.insert(0, default)
            e.grid(row=i, column=1, padx=10, pady=4, sticky="ew")
            setattr(self, attr, e)

        ctk.CTkLabel(self.adv_frame, text="LLM Fallback", anchor="w").grid(
            row=len(fields), column=0, padx=10, pady=4, sticky="w"
        )
        self.llm_var = ctk.StringVar(value="Enabled")
        ctk.CTkOptionMenu(
            self.adv_frame, variable=self.llm_var,
            values=["Enabled", "Disabled"], width=100
        ).grid(row=len(fields), column=1, padx=10, pady=4, sticky="ew")

    def _toggle_advanced(self):
        self._adv_open = not self._adv_open
        if self._adv_open:
            self.adv_frame.grid(row=8, column=0, sticky="ew", padx=14, pady=(0, 10))
            self.btn_adv.configure(text="▼   Advanced Settings")
        else:
            self.adv_frame.grid_forget()
            self.btn_adv.configure(text="▶   Advanced Settings")


    def _populate_mics(self):
        p    = pyaudio.PyAudio()
        mics = {}
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info.get("maxInputChannels", 0) > 0:
                mics[i] = f"[{i}]  {info['name']}"
        p.terminate()

        if mics:
            values       = list(mics.values())
            self.mic_map = {v: k for k, v in mics.items()}
            self.mic_menu.configure(values=values)
            self.mic_var.set(values[0])
        else:
            self.mic_map = {}
            self.mic_menu.configure(values=["No input devices found"])


    def _attach_log_handler(self):
        handler = GUILogHandler(self._append_log)
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s  %(message)s'))
        logging.getLogger().addHandler(handler)

    def _append_log(self, msg: str):
        def _do():
            self.log_box.configure(state="normal")
            self.log_box.insert("end", msg + "\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
        self.after(0, _do)

    def _clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")


    def _lang_code(self) -> str:
        return {
            "English (Nova-2)":       "en",
            "Malayalam (Sarvam AI)":  "ml",
            "Hindi (Nova-3)":         "hi",
            "Multi (Nova-2)":         "multi",
        }.get(self.lang_var.get(), "en")

    def _mic_index(self) -> int:
        return self.mic_map.get(self.mic_var.get(), 1)

    def _safe_int(self, entry, default):
        try:    return int(entry.get())
        except: return default

    def _safe_float(self, entry, default):
        try:    return float(entry.get())
        except: return default


    def _start(self):
        if self._running:
            return

        engine.configure(
            language     = self._lang_code(),
            mic_index    = self._mic_index(),
            rate         = self._safe_int(self.rate_entry, 16000),
            chunk        = self._safe_int(self.chunk_entry, 4096),
            remote_url   = self.url_entry.get() or "http://localhost:50010/control.html",
            dedup_window = self._safe_int(self.dedup_entry, 60),
            cooldown     = self._safe_float(self.cooldown_entry, 3.0),
            llm_enabled  = (self.llm_var.get() == "Enabled"),
        )

        self._running = True
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.lbl_status.configure(text="● Running", text_color="#2a7a2a")
        self.lang_menu.configure(state="disabled")
        self.mic_menu.configure(state="disabled")

        self._engine_thread = threading.Thread(target=self._engine_thread_fn, daemon=True)
        self._engine_thread.start()

    def _engine_thread_fn(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(engine.main())
        except Exception as e:
            self._append_log(f"ENGINE ERROR: {e}")
        finally:
            loop.close()
            self.after(0, self._on_stopped)

    def _stop(self):
        self.btn_stop.configure(state="disabled")
        self.lbl_status.configure(text="● Stopping...", text_color="#a07020")
        engine.request_stop()

    def _on_stopped(self):
        self._running = False
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.lbl_status.configure(text="● Stopped", text_color="#666666")
        self.lang_menu.configure(state="normal")
        self.mic_menu.configure(state="normal")

    def on_closing(self):
        if self._running:
            engine.request_stop()
        self.destroy()


if __name__ == "__main__":
    app = VerseViewApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
