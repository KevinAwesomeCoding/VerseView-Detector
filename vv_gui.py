# -*- coding: utf-8 -*-
import customtkinter as ctk
import threading
import asyncio
import logging
import pyaudio

import settings as cfg
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
        self.geometry("1060x660")
        self.minsize(800, 500)

        self._s        = cfg.load()   # load saved settings
        self._running  = False
        self._engine_thread = None

        self._build_ui()
        self._populate_mics()
        self._attach_log_handler()
        self._load_into_ui()           # fill fields from saved settings

    # ─────────────────────────────────────────────────
    # UI BUILD
    # ─────────────────────────────────────────────────
    def _build_ui(self):
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)

        # ── LEFT PANEL ──
        left = ctk.CTkFrame(self)
        left.grid(row=0, column=0, padx=(12, 6), pady=12, sticky="nsew")
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

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
            state="disabled", command=self._stop
        )
        self.btn_stop.pack(side="left", padx=(0, 16))

        self.lbl_status = ctk.CTkLabel(
            top, text="● Stopped",
            text_color="#666666",
            font=ctk.CTkFont(size=13)
        )
        self.lbl_status.pack(side="left")

        self.log_box = ctk.CTkTextbox(
            left, state="disabled",
            font=("Courier New", 11), wrap="word"
        )
        self.log_box.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")

        ctk.CTkButton(
            left, text="Clear Log", height=28,
            fg_color="transparent", border_width=1,
            text_color=("gray40", "gray60"),
            command=self._clear_log
        ).grid(row=2, column=0, padx=10, pady=(0, 8), sticky="e")

        # ── RIGHT PANEL ──
        right = ctk.CTkScrollableFrame(
            self, label_text="⚙   Settings",
            label_font=ctk.CTkFont(size=14, weight="bold")
        )
        right.grid(row=0, column=1, padx=(6, 12), pady=12, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)

        row = 0

        def sep_label(text):
            nonlocal row
            ctk.CTkLabel(
                right, text=text, anchor="w",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=("gray30", "gray70")
            ).grid(row=row, column=0, sticky="ew", padx=14, pady=(14, 2))
            row += 1

        def add_entry(placeholder="", show=""):
            nonlocal row
            e = ctk.CTkEntry(right, placeholder_text=placeholder, show=show)
            e.grid(row=row, column=0, sticky="ew", padx=14, pady=(0, 4))
            row += 1
            return e

        def add_option(values):
            nonlocal row
            var = ctk.StringVar(value=values[0])
            m   = ctk.CTkOptionMenu(right, variable=var, values=values)
            m.grid(row=row, column=0, sticky="ew", padx=14, pady=(0, 4))
            row += 1
            return var, m

        # Language
        sep_label("Language")
        self.lang_var, self.lang_menu = add_option([
            "English (Nova-2)",
            "Malayalam (Sarvam AI)",
            "Hindi (Nova-3)",
            "Multi (Nova-2)",
        ])

        # Microphone
        sep_label("Microphone")
        self.mic_var  = ctk.StringVar(value="Loading...")
        self.mic_menu = ctk.CTkOptionMenu(right, variable=self.mic_var, values=["Loading..."])
        self.mic_menu.grid(row=row, column=0, sticky="ew", padx=14, pady=(0, 4))
        row += 1
        ctk.CTkButton(
            right, text="↺  Refresh Mics", height=28,
            fg_color="transparent", border_width=1,
            text_color=("gray40", "gray60"),
            command=self._populate_mics
        ).grid(row=row, column=0, sticky="ew", padx=14, pady=(0, 8))
        row += 1

        # VerseView URL
        sep_label("VerseView URL")
        self.url_entry = add_entry("http://localhost:50010/control.html")

        # ── Advanced toggle ──
        self._adv_open = False
        self.btn_adv = ctk.CTkButton(
            right, text="▶   Advanced Settings",
            fg_color="transparent",
            text_color=("gray40", "gray60"),
            anchor="w", hover=False,
            command=self._toggle_advanced
        )
        self.btn_adv.grid(row=row, column=0, sticky="ew", padx=10, pady=(14, 2))
        self._adv_row = row
        row += 1

        # Advanced frame
        self.adv_frame = ctk.CTkFrame(right)
        self.adv_frame.grid_columnconfigure(1, weight=1)
        self._build_advanced()

        # Save button at bottom
        ctk.CTkButton(
            right, text="💾  Save Settings",
            fg_color="#1a5a8a", hover_color="#144a72",
            command=self._save_settings
        ).grid(row=row + 10, column=0, sticky="ew", padx=14, pady=(16, 8))

    def _build_advanced(self):
        fields = [
            ("Sample Rate",      "16000",  "rate_entry"),
            ("Chunk Size",       "4096",   "chunk_entry"),
            ("Cooldown (s)",     "3.0",    "cooldown_entry"),
            ("Dedup Window (s)", "60",     "dedup_entry"),
        ]
        for i, (lbl, default, attr) in enumerate(fields):
            ctk.CTkLabel(self.adv_frame, text=lbl, anchor="w").grid(
                row=i, column=0, padx=10, pady=4, sticky="w"
            )
            e = ctk.CTkEntry(self.adv_frame, width=90)
            e.insert(0, default)
            e.grid(row=i, column=1, padx=10, pady=4, sticky="ew")
            setattr(self, attr, e)

        n = len(fields)

        ctk.CTkLabel(self.adv_frame, text="LLM Fallback", anchor="w").grid(
            row=n, column=0, padx=10, pady=4, sticky="w"
        )
        self.llm_var = ctk.StringVar(value="Enabled")
        ctk.CTkOptionMenu(
            self.adv_frame, variable=self.llm_var,
            values=["Enabled", "Disabled"], width=100
        ).grid(row=n, column=1, padx=10, pady=4, sticky="ew")

        # ── API Keys section ──
        ctk.CTkLabel(
            self.adv_frame,
            text="─── API Keys ───",
            anchor="w",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("gray30", "gray70")
        ).grid(row=n+1, column=0, columnspan=2, padx=10, pady=(14, 2), sticky="ew")

        key_fields = [
            ("Deepgram Key",        "dg_key_entry"),
            ("OpenRouter Key",      "or_key_entry"),
            ("Sarvam Key",          "sv_key_entry"),
            ("Discord Webhook URL", "dc_key_entry"),
        ]
        for j, (lbl, attr) in enumerate(key_fields):
            ctk.CTkLabel(self.adv_frame, text=lbl, anchor="w").grid(
                row=n+2+j, column=0, padx=10, pady=4, sticky="w"
            )
            e = ctk.CTkEntry(self.adv_frame, show="•", width=200,
                             placeholder_text="Paste key here")
            e.grid(row=n+2+j, column=1, padx=10, pady=4, sticky="ew")
            setattr(self, attr, e)

    def _toggle_advanced(self):
        self._adv_open = not self._adv_open
        if self._adv_open:
            self.adv_frame.grid(
                row=self._adv_row + 1, column=0,
                sticky="ew", padx=14, pady=(0, 10)
            )
            self.btn_adv.configure(text="▼   Advanced Settings")
        else:
            self.adv_frame.grid_forget()
            self.btn_adv.configure(text="▶   Advanced Settings")

    # ─────────────────────────────────────────────────
    # SETTINGS PERSISTENCE
    # ─────────────────────────────────────────────────
    def _load_into_ui(self):
        s = self._s
        self.lang_var.set(s.get("language", "English (Nova-2)"))
        self.url_entry.delete(0, "end")
        self.url_entry.insert(0, s.get("remote_url", "http://localhost:50010/control.html"))

        self.rate_entry.delete(0, "end");     self.rate_entry.insert(0,     str(s.get("rate",         16000)))
        self.chunk_entry.delete(0, "end");    self.chunk_entry.insert(0,    str(s.get("chunk",         4096)))
        self.cooldown_entry.delete(0, "end"); self.cooldown_entry.insert(0, str(s.get("cooldown",      3.0)))
        self.dedup_entry.delete(0, "end");    self.dedup_entry.insert(0,    str(s.get("dedup_window",  60)))
        self.llm_var.set("Enabled" if s.get("llm_enabled", True) else "Disabled")

        for attr, key in [
            ("dg_key_entry", "deepgram_api_key"),
            ("or_key_entry", "openrouter_api_key"),
            ("sv_key_entry", "sarvam_api_key"),
            ("dc_key_entry", "discord_webhook_url"),
        ]:
            e = getattr(self, attr)
            e.delete(0, "end")
            e.insert(0, s.get(key, ""))

    def _collect_settings(self) -> dict:
        return {
            "language":            self.lang_var.get(),
            "remote_url":          self.url_entry.get(),
            "rate":                self._safe_int(self.rate_entry,     16000),
            "chunk":               self._safe_int(self.chunk_entry,    4096),
            "cooldown":            self._safe_float(self.cooldown_entry, 3.0),
            "dedup_window":        self._safe_int(self.dedup_entry,    60),
            "llm_enabled":         self.llm_var.get() == "Enabled",
            "deepgram_api_key":    self.dg_key_entry.get(),
            "openrouter_api_key":  self.or_key_entry.get(),
            "sarvam_api_key":      self.sv_key_entry.get(),
            "discord_webhook_url": self.dc_key_entry.get(),
            "mic_index":           self._mic_index(),
        }

    def _save_settings(self):
        self._s = self._collect_settings()
        cfg.save(self._s)
        self._append_log("✅ Settings saved.")

    # ─────────────────────────────────────────────────
    # MIC ENUMERATION
    # ─────────────────────────────────────────────────
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
            saved_idx    = self._s.get("mic_index", 0)
            match        = next((v for v in values if f"[{saved_idx}]" in v), values[0])
            self.mic_var.set(match)
        else:
            self.mic_map = {}
            self.mic_menu.configure(values=["No input devices found"])

    # ─────────────────────────────────────────────────
    # LOGGING
    # ─────────────────────────────────────────────────
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

    # ─────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────
    def _lang_code(self) -> str:
        return {
            "English (Nova-2)":      "en",
            "Malayalam (Sarvam AI)": "ml",
            "Hindi (Nova-3)":        "hi",
            "Multi (Nova-2)":        "multi",
        }.get(self.lang_var.get(), "en")

    def _mic_index(self) -> int:
        return self.mic_map.get(self.mic_var.get(), 0)

    def _safe_int(self, e, d):
        try:    return int(e.get())
        except: return d

    def _safe_float(self, e, d):
        try:    return float(e.get())
        except: return d

    # ─────────────────────────────────────────────────
    # ENGINE CONTROL
    # ─────────────────────────────────────────────────
    def _start(self):
        if self._running:
            return

        s = self._collect_settings()
        cfg.save(s)   # auto-save on start

        missing = []
        if not s["deepgram_api_key"] and self._lang_code() != "ml":
            missing.append("Deepgram API Key")
        if not s["sarvam_api_key"] and self._lang_code() == "ml":
            missing.append("Sarvam API Key")
        if missing:
            self._append_log(f"⚠️  Missing keys in Advanced Settings: {', '.join(missing)}")
            return

        engine.configure(
            language            = self._lang_code(),
            mic_index           = self._mic_index(),
            rate                = s["rate"],
            chunk               = s["chunk"],
            remote_url          = s["remote_url"],
            dedup_window        = s["dedup_window"],
            cooldown            = s["cooldown"],
            llm_enabled         = s["llm_enabled"],
            deepgram_api_key    = s["deepgram_api_key"],
            openrouter_api_key  = s["openrouter_api_key"],
            sarvam_api_key      = s["sarvam_api_key"],
            discord_webhook_url = s["discord_webhook_url"],
        )

        self._running = True
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.lbl_status.configure(text="● Running", text_color="#2a7a2a")
        self.lang_menu.configure(state="disabled")
        self.mic_menu.configure(state="disabled")

        self._engine_thread = threading.Thread(target=self._run_engine, daemon=True)
        self._engine_thread.start()

    def _run_engine(self):
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
        cfg.save(self._collect_settings())   # save on exit too
        if self._running:
            engine.request_stop()
        self.destroy()


if __name__ == "__main__":
    app = VerseViewApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
