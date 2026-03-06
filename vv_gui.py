# -*- coding: utf-8 -*-
import customtkinter as ctk
import tkinter.messagebox as mb
import threading
import asyncio
import logging
import pyaudio
from pynput import keyboard as pynput_kb
import datetime
import re
import os
import sys

import settings as cfg
import vv_streaming_master as engine

APP_VERSION = "1.0.0"

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
        self.title(f"VerseView Detector  v{APP_VERSION}")
        self.geometry("1060x700")
        self.minsize(800, 500)

        self._s             = cfg.load()
        self._running       = False
        self._engine_thread = None
        self._notes_saved   = False

        self._build_ui()
        self._populate_mics()
        self._attach_log_handler()
        self._load_into_ui()

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
            font=("Segoe UI", 12), wrap="word"
        )
        self.log_box.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")

        # ── ACTION BUTTONS ROW ──
        action_frame = ctk.CTkFrame(left, fg_color="transparent")
        action_frame.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="ew")
        action_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            action_frame, text="Clear Log", height=28, width=70,
            fg_color="transparent", border_width=1,
            text_color=("gray40", "gray60"),
            command=self._clear_log
        ).grid(row=0, column=0, padx=(0, 5), sticky="w")

        self.btn_summary = ctk.CTkButton(
            action_frame, text="📝 Generate Sermon Notes", height=32,
            fg_color="#a07020", hover_color="#805010",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._generate_summary
        )
        self.btn_summary.grid(row=0, column=1, padx=5, sticky="ew")

        self.btn_clear_sermon = ctk.CTkButton(
            action_frame, text="🗑️ Clear Memory", height=28, width=70,
            fg_color="transparent", border_width=1,
            text_color=("#b53b3b", "#e05a5a"), 
            command=self._clear_sermon_memory
        )
        self.btn_clear_sermon.grid(row=0, column=2, padx=(5, 0), sticky="e")

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
            lbl = ctk.CTkLabel(
                right, text=text, anchor="w",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=("gray30", "gray70")
            )
            lbl.grid(row=row, column=0, sticky="ew", padx=14, pady=(14, 2))
            row += 1
            return lbl

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

        # Bible Translation
        sep_label("Bible Translation")
        self.bible_var, self.bible_menu = add_option([
            "KJV", "WEB", "ASV", "NET", "NLT",
            "NIV", "ESV", "NASB", "NKJV", "AMP",
            "CSB", "MSG", "OEB", "WEBBE",
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

        # ── Current Context ──
        sep_label("📌  Current Context")

        ctx_frame = ctk.CTkFrame(right, fg_color="transparent")
        ctx_frame.grid(row=row, column=0, sticky="ew", padx=14, pady=(0, 4))
        ctx_frame.grid_columnconfigure((0, 1, 2), weight=1)
        row += 1

        ctk.CTkLabel(ctx_frame, text="Book",    anchor="center", font=ctk.CTkFont(size=11)).grid(row=0, column=0, padx=2)
        ctk.CTkLabel(ctx_frame, text="Chapter", anchor="center", font=ctk.CTkFont(size=11)).grid(row=0, column=1, padx=2)
        ctk.CTkLabel(ctx_frame, text="Verse",   anchor="center", font=ctk.CTkFont(size=11)).grid(row=0, column=2, padx=2)

        self.ctx_book    = ctk.CTkEntry(ctx_frame, placeholder_text="e.g. John", width=80)
        self.ctx_chapter = ctk.CTkEntry(ctx_frame, placeholder_text="e.g. 3",    width=50)
        self.ctx_verse   = ctk.CTkEntry(ctx_frame, placeholder_text="e.g. 16",   width=50)

        self.ctx_book.grid(row=1,    column=0, padx=2, pady=2)
        self.ctx_chapter.grid(row=1, column=1, padx=2, pady=2)
        self.ctx_verse.grid(row=1,   column=2, padx=2, pady=2)

        ctk.CTkButton(
            right, text="📌  Set Context", height=28,
            fg_color="#5a3a8a", hover_color="#3f2060",
            command=self._set_context
        ).grid(row=row, column=0, sticky="ew", padx=14, pady=(0, 8))
        row += 1

        # ── Verification & Confidence ──
        self.conf_val_label = sep_label("Confidence Threshold: 75%")
        
        self.conf_var = ctk.DoubleVar(value=0.75)
        
        def update_conf_label(val):
            self.conf_val_label.configure(text=f"Confidence Threshold: {int(float(val)*100)}%")

        self.conf_slider = ctk.CTkSlider(right, from_=0.5, to=1.0, variable=self.conf_var, command=update_conf_label)
        self.conf_slider.grid(row=row, column=0, sticky="ew", padx=14, pady=(0, 4))
        row += 1

        self.manual_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(right, text="Require Manual Confirmation (Ask Y/N if low)", variable=self.manual_var).grid(row=row, column=0, sticky="w", padx=14, pady=(10, 4))
        row += 1

        # ── PANIC KEYBIND RECORDER ──
        sep_label("Panic Keybind")
        self.panic_var = ctk.StringVar(value="esc")
        
        self.panic_btn = ctk.CTkButton(
            right, text="Panic Key: esc",
            fg_color="#4a4a4a", hover_color="#333333",
            command=self._record_panic_key
        )
        self.panic_btn.grid(row=row, column=0, sticky="ew", padx=14, pady=(0, 4))
        row += 1

        self.verify_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(right, text="Require Verification (Hear verse twice)", variable=self.verify_var).grid(row=row, column=0, sticky="w", padx=14, pady=(10, 4))
        row += 1

        # ── SMART AMEN TOGGLE ──
        self.smart_amen_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(right, text="Smart Amen (Auto-Clear on 'Let us pray')", variable=self.smart_amen_var).grid(row=row, column=0, sticky="w", padx=14, pady=(10, 4))
        row += 1

        # ── AUTO-SAVE TOGGLE ──
        self.auto_save_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(right, text="Auto-Save Sermon Notes on App Close", variable=self.auto_save_var).grid(row=row, column=0, sticky="w", padx=14, pady=(10, 4))
        row += 1

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

        self.adv_frame = ctk.CTkFrame(right)
        self.adv_frame.grid_columnconfigure(1, weight=1)
        self._build_advanced()

        ctk.CTkButton(
            right, text="💾  Save Settings",
            fg_color="#1a5a8a", hover_color="#144a72",
            command=self._save_settings
        ).grid(row=row + 10, column=0, sticky="ew", padx=14, pady=(16, 4))

        ctk.CTkButton(
            right, text="📤  Export Settings",
            fg_color="#4a4a4a", hover_color="#333333",
            command=self._export_settings
        ).grid(row=row + 11, column=0, sticky="ew", padx=14, pady=(0, 4))

        ctk.CTkButton(
            right, text="📥  Import Settings",
            fg_color="#4a4a4a", hover_color="#333333",
            command=self._import_settings
        ).grid(row=row + 12, column=0, sticky="ew", padx=14, pady=(0, 8))

        # Version label
        ctk.CTkLabel(
            self, text=f"v{APP_VERSION}",
            text_color=("gray50", "gray50"),
            font=ctk.CTkFont(size=10)
        ).grid(row=1, column=0, columnspan=2, pady=(0, 4), sticky="e", padx=12)

        self.after(2000, self._refresh_context)

    def _build_advanced(self):
        fields = [
            ("Sample Rate",      "16000", "rate_entry"),
            ("Chunk Size",       "4096",  "chunk_entry"),
            ("Cooldown (s)",     "3.0",   "cooldown_entry"),
            ("Dedup Window (s)", "60",    "dedup_entry"),
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

        ctk.CTkLabel(
            self.adv_frame, text="─── API Keys ───", anchor="w",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("gray30", "gray70")
        ).grid(row=n+1, column=0, columnspan=2, padx=10, pady=(14, 2), sticky="ew")

        key_fields = [
            ("Deepgram Key",        "dg_key_entry"),
            ("Groq API Key",      "or_key_entry"),
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
    # PANIC RECORDING LOGIC
    # ─────────────────────────────────────────────────
    def _record_panic_key(self):
        """ Allows the user to press a key combo to record it safely without typing """
        self.panic_btn.configure(text="Listening... Press a key now!", fg_color="#a07020", state="disabled")

        def on_press(key):
            try:
                key_name = key.char
            except AttributeError:
                key_name = key.name
            
            if key_name:
                self.after(0, lambda: self._on_panic_recorded(key_name))
            
            return False 

        def recorder():
            try:
                with pynput_kb.Listener(on_press=on_press) as listener:
                    listener.join()
            except Exception as e:
                self._append_log(f"⚠️ Key recording error: {e}")
                self.after(0, lambda: self._on_panic_recorded(self.panic_var.get()))

        threading.Thread(target=recorder, daemon=True).start()

    def _on_panic_recorded(self, combo):
        if combo:
            self.panic_var.set(combo)
            self.panic_btn.configure(text=f"Panic Key: {combo}", fg_color=["#3B8ED0", "#1F6AA5"], state="normal")
            self._append_log(f"⌨️ Panic key updated to: {combo}")
        else:
            self.panic_btn.configure(text=f"Panic Key: {self.panic_var.get()}", fg_color=["#3B8ED0", "#1F6AA5"], state="normal")


    # ─────────────────────────────────────────────────
    # SETTINGS PERSISTENCE
    # ─────────────────────────────────────────────────
    def _load_into_ui(self):
        s = self._s
        self.lang_var.set(s.get("language", "English (Nova-2)"))
        self.bible_var.set(s.get("bible_translation", "WEB").upper())
        self.url_entry.delete(0, "end")
        self.url_entry.insert(0, s.get("remote_url", "http://localhost:50010/control.html"))
        
        # Load Verification / Confidence settings
        saved_conf = s.get("confidence", 0.75)
        self.conf_var.set(saved_conf)
        self.conf_val_label.configure(text=f"Confidence Threshold: {int(saved_conf * 100)}%")
        
        self.manual_var.set(s.get("manual_confirm", True))
        self.verify_var.set(s.get("verify", True))
        self.smart_amen_var.set(s.get("smart_amen", True))
        self.auto_save_var.set(s.get("auto_save_notes", True))
        
        saved_panic = s.get("panic_key", "esc")
        self.panic_var.set(saved_panic)
        self.panic_btn.configure(text=f"Panic Key: {saved_panic}")

        self.rate_entry.delete(0, "end");     self.rate_entry.insert(0,     str(s.get("rate",        16000)))
        self.chunk_entry.delete(0, "end");    self.chunk_entry.insert(0,    str(s.get("chunk",        4096)))
        self.cooldown_entry.delete(0, "end"); self.cooldown_entry.insert(0, str(s.get("cooldown",     3.0)))
        self.dedup_entry.delete(0, "end");    self.dedup_entry.insert(0,    str(s.get("dedup_window", 60)))
        self.llm_var.set("Enabled" if s.get("llm_enabled", True) else "Disabled")

        for attr, key in [
            ("dg_key_entry", "deepgram_api_key"),
            ("or_key_entry", "groq_api_key"),
            ("sv_key_entry", "sarvam_api_key"),
            ("dc_key_entry", "discord_webhook_url"),
        ]:
            e = getattr(self, attr)
            e.delete(0, "end")
            e.insert(0, s.get(key, ""))

    def _collect_settings(self) -> dict:
        return {
            "language":            self.lang_var.get(),
            "bible_translation":   self.bible_var.get().lower(),
            "remote_url":          self.url_entry.get(),
            "confidence":          self.conf_var.get(),
            "manual_confirm":      self.manual_var.get(),
            "verify":              self.verify_var.get(),
            "smart_amen":          self.smart_amen_var.get(),
            "auto_save_notes":     self.auto_save_var.get(),
            "panic_key":           self.panic_var.get(),
            "rate":                self._safe_int(self.rate_entry,       16000),
            "chunk":               self._safe_int(self.chunk_entry,      4096),
            "cooldown":            self._safe_float(self.cooldown_entry,  3.0),
            "dedup_window":        self._safe_int(self.dedup_entry,      60),
            "llm_enabled":         self.llm_var.get() == "Enabled",
            "deepgram_api_key":    self.dg_key_entry.get(),
            "groq_api_key":        self.or_key_entry.get(),
            "sarvam_api_key":      self.sv_key_entry.get(),
            "discord_webhook_url": self.dc_key_entry.get(),
            "mic_index":           self._mic_index(),
        }

    def _save_settings(self):
        self._s = self._collect_settings()
        cfg.save(self._s)
        self._append_log("✅ Settings saved.")

    def _export_settings(self):
        data = self._collect_settings()
        if cfg.export_settings(data):
            self._append_log("📤 Settings exported successfully.")
        else:
            self._append_log("⚠️ Export cancelled.")

    def _import_settings(self):
        data = cfg.import_settings()
        if data:
            self._s = data
            cfg.save(data)
            self._load_into_ui()
            self._append_log("📥 Settings imported successfully.")
        else:
            self._append_log("⚠️ Import cancelled.")

    # ─────────────────────────────────────────────────
    # CONTEXT & LOGGING
    # ─────────────────────────────────────────────────
    def _set_context(self):
        typed_book = self.ctx_book.get().strip()
        typed_chapter = self.ctx_chapter.get().strip()
        typed_verse = self.ctx_verse.get().strip()

        final_book = typed_book if typed_book else engine.current_book
        final_chapter = typed_chapter if typed_chapter else engine.current_chapter
        final_verse = typed_verse if typed_verse else engine.current_verse

        final_book = final_book or ""
        final_chapter = final_chapter or ""
        final_verse = final_verse or ""

        engine.set_context(final_book, final_chapter, final_verse)

        self.ctx_book.delete(0, "end")
        self.ctx_chapter.delete(0, "end")
        self.ctx_verse.delete(0, "end")

        self._append_log(f"📌 Context updated: {final_book} {final_chapter}:{final_verse}")

    def _refresh_context(self):
        focused = self.focus_get()

        def is_inside(widget):
            try:
                f = str(focused)
                return str(widget) in f or f.startswith(str(widget))
            except:
                return False

        if not (is_inside(self.ctx_book) or is_inside(self.ctx_chapter) or is_inside(self.ctx_verse)):
            self.ctx_book.configure(placeholder_text=engine.current_book or "e.g. John")
            self.ctx_chapter.configure(placeholder_text=engine.current_chapter or "e.g. 3")
            self.ctx_verse.configure(placeholder_text=engine.current_verse or "e.g. 16")

        self.after(2000, self._refresh_context)

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
    # ENGINE CONTROL & CALLBACKS
    # ─────────────────────────────────────────────────
    def _user_confirm_callback(self, ref: str, confidence: float) -> bool:
        """ Thread-safe popup to ask the user if they want to send a low-confidence verse. """
        result = [False]
        ev = threading.Event()
        
        def _ask():
            ans = mb.askyesno(
                title="Low Confidence Verse", 
                message=f"The AI is only {int(confidence * 100)}% sure.\n\nDetected: {ref}\n\nDo you want to send this to VerseView?"
            )
            result[0] = ans
            ev.set()

        self.after(0, _ask)
        ev.wait() 
        return result[0]

    def _start(self):
        try:
            if self._running:
                return

            s = self._collect_settings()
            cfg.save(s)

            missing = []
            if not s["deepgram_api_key"] and self._lang_code() != "ml":
                missing.append("Deepgram API Key")
            if not s["sarvam_api_key"] and self._lang_code() == "ml":
                missing.append("Sarvam API Key")
            if missing:
                mb.showwarning("Missing Keys", f"Please enter in Advanced Settings:\n\n{chr(10).join(missing)}")
                self._append_log(f"⚠️ Missing keys: {', '.join(missing)}")
                return

            # Pass new args down to engine
            engine.configure(
                language            = self._lang_code(),
                mic_index           = self._mic_index(),
                rate                = s["rate"],
                chunk               = s["chunk"],
                remote_url          = s["remote_url"],
                dedup_window        = s["dedup_window"],
                cooldown            = s["cooldown"],
                llm_enabled         = s["llm_enabled"],
                bible_translation   = s["bible_translation"],
                deepgram_api_key    = s["deepgram_api_key"],
                groq_api_key        = s["groq_api_key"],
                sarvam_api_key      = s["sarvam_api_key"],
                discord_webhook_url = s["discord_webhook_url"],
                confidence          = s["confidence"],
                manual_confirm      = s["manual_confirm"],
                confirm_callback    = self._user_confirm_callback,
                verify              = s["verify"],
                smart_amen          = s["smart_amen"],
                panic_key           = s["panic_key"],
            )

            self._running = True
            self.btn_start.configure(state="disabled")
            self.btn_stop.configure(state="normal")
            self.lbl_status.configure(text="● Running", text_color="#2a7a2a")
            self.lang_menu.configure(state="disabled")
            self.mic_menu.configure(state="disabled")

            self._engine_thread = threading.Thread(target=self._run_engine, daemon=True)
            self._engine_thread.start()
            self.after(2000, self._refresh_context)

        except Exception as e:
            mb.showerror("Start Error", f"Failed to start:\n\n{e}")
            self._append_log(f"❌ Start failed: {e}")

    def _run_engine(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(engine.main())
        except Exception as e:
            self._append_log(f"ENGINE ERROR: {e}")
            self.after(0, lambda: mb.showerror("Engine Error", str(e)))
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

    # ── FOLDER MANAGER ──
    def _get_sermon_notes_dir(self):
        if getattr(sys, 'frozen', False):
            app_dir = os.path.dirname(sys.executable)
        else:
            app_dir = os.path.dirname(os.path.abspath(__file__))
            
        parent_dir = os.path.dirname(app_dir)
        
        notes_dir = os.path.join(parent_dir, "Sermon Notes")
        os.makedirs(notes_dir, exist_ok=True)
        
        return notes_dir

    # ── SERMON CLIFF NOTES ──
    def _generate_summary(self):
        def _task():
            self._append_log("⏳ Asking AI to summarize the sermon... (Please wait)")
            summary = engine.generate_sermon_summary()
            self.after(0, lambda: self._show_summary_window(summary))
            
        threading.Thread(target=_task, daemon=True).start()

    def _show_summary_window(self, content):
        win = ctk.CTkToplevel(self)
        win.title("Sermon Cliff Notes")
        win.geometry("600x700")
        
        # Bring window to front
        win.attributes("-topmost", True)
        self.after(100, lambda: win.attributes("-topmost", False))
        
        textbox = ctk.CTkTextbox(win, font=("Segoe UI", 14), wrap="word")
        textbox.pack(fill="both", expand=True, padx=15, pady=15)
        textbox.insert("1.0", content)
        textbox.configure(state="disabled")
        
        def _save():
            default_title = "Sermon_Notes"
            first_line = content.split('\n')[0]
            if first_line.startswith("TITLE:"):
                raw_title = first_line.replace("TITLE:", "").strip()
                default_title = re.sub(r'[\\/*?:"<>|]', "", raw_title)
            
            date_str = datetime.date.today().strftime("%B %d %Y")
            suggested_filename = f"{default_title} {date_str}.txt"

            notes_folder = self._get_sermon_notes_dir()

            import tkinter.filedialog as fd
            path = fd.asksaveasfilename(
                initialdir=notes_folder, 
                defaultextension=".txt", 
                filetypes=[("Text Files", "*.txt")],
                initialfile=suggested_filename
            )
            if path:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                self._append_log(f"💾 Saved Sermon Notes to {path}")
                self._notes_saved = True # <--- Note is safely saved!
                win.destroy()
                
        btn_save = ctk.CTkButton(
            win, text="💾 Save to File", 
            font=ctk.CTkFont(size=14, weight="bold"), 
            command=_save
        )
        btn_save.pack(pady=(0, 15))

    def _clear_sermon_memory(self):
        if mb.askyesno("Clear Memory", "Are you sure you want to delete the current recorded sermon?\n\nThis cannot be undone!"):
            engine.clear_sermon_buffer()
            self._notes_saved = False 
            self._append_log("🗑️ Sermon memory wiped clean for the next service.")

    def on_closing(self):
        if self.auto_save_var.get() and not self._notes_saved and engine.full_sermon_transcript and len(engine.full_sermon_transcript.strip()) > 100:
            self.lbl_status.configure(text="● Auto-Saving Notes...", text_color="#a07020")
            self.update()
            try:
                self._append_log("⚠️ App closed without saving! Auto-generating summary...")
                content = engine.generate_sermon_summary()
                
                default_title = "Unsaved_Sermon"
                first_line = content.split('\n')[0]
                if first_line.startswith("TITLE:"):
                    raw_title = first_line.replace("TITLE:", "").strip()
                    default_title = re.sub(r'[\\/*?:"<>|]', "", raw_title)
                
                date_str = datetime.date.today().strftime("%B %d %Y")
                filename = f"{default_title} {date_str}.txt"
                
                notes_folder = self._get_sermon_notes_dir()
                filepath = os.path.join(notes_folder, filename)
                
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"Emergency Auto-Save triggered: {filepath}")
            except Exception as e:
                print(f"Emergency Auto-Save Failed: {e}")

        # Shut down normally
        cfg.save(self._collect_settings())
        if self._running:
            engine.request_stop()
        self.destroy()


if __name__ == "__main__":
    app = VerseViewApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
