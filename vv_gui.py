# ════════════════════════════════════════════════════════════════════════════
#  vv_gui.py  —  CHANGED METHODS ONLY (session persistence feature)
#  Add  `import session_state`  to the top-level imports block.
#  Add  `import datetime`       if not already present (it already is).
# ════════════════════════════════════════════════════════════════════════════


# ── 1.  Add this import alongside the other top-level imports ─────────────────
#
#     import session_state
#
# ─────────────────────────────────────────────────────────────────────────────


# ── 2.  __init__  (replace only the two `self.after(...)` lines at the bottom
#        of the existing __init__ with the block below, and add the new ones) ──

    def __init__(self):
        super().__init__()
        self.title(f"VerseView Detector  v{APP_VERSION}  [{BUILD_VERSION}]")
        self.geometry("1060x700")
        self.minsize(800, 500)

        self._s                   = cfg.load()
        self._running             = False
        self._closing             = False
        self._engine_thread       = None
        self._notes_saved         = False
        self._notes_generated     = False
        self._worship_mode_active = False
        self._restore_dialog_shown = False   # NEW: prevent double-fire

        self._build_ui()
        self._populate_mics()
        self._attach_log_handler()
        self._load_into_ui()
        self.bind("<Shift-Escape>", lambda e: self._panic_shortcut())
        self.after(500,   self._check_auto_start)
        self._last_history_len = 0
        self.after(1000,  self._update_history_loop)
        self.after(1500,  self._update_chapter_browser_loop)
        self.after(15000, self._check_for_update_bg)
        self.after(3000,  self._sync_settings_on_launch)
        # Session restore check — fires after the window is fully drawn
        self.after(800,   self._check_restore_session)   # NEW


# ── 3.  NEW METHOD: _check_restore_session ────────────────────────────────────

    def _check_restore_session(self):
        """Called once 800 ms after launch. Shows a restore dialog if a saved
        session exists. The flag prevents it from firing more than once."""
        if self._restore_dialog_shown:
            return
        self._restore_dialog_shown = True

        if not session_state.session_exists():
            return

        data = session_state.load_session()
        if not data:
            return

        # ── Format the saved_at timestamp nicely ──
        saved_at_raw = data.get("saved_at", "")
        try:
            dt = datetime.datetime.fromisoformat(saved_at_raw)
            saved_at_nice = dt.strftime("%A %B %d at %I:%M %p").replace(" 0", " ")
        except Exception:
            saved_at_nice = saved_at_raw or "unknown time"

        n_verses    = len(data.get("verse_history", []))
        n_chars     = len(data.get("full_sermon_transcript", ""))

        # ── Build a dark-themed CTkToplevel dialog ──
        dialog = ctk.CTkToplevel(self)
        dialog.title("Restore Previous Session?")
        dialog.geometry("440x240")
        dialog.resizable(False, False)
        dialog.attributes("-topmost", True)
        self.after(200, lambda: dialog.attributes("-topmost", False))

        ctk.CTkLabel(
            dialog,
            text="Restore Previous Session?",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(pady=(18, 6))

        ctk.CTkLabel(
            dialog,
            text=f"VerseView found a saved session from {saved_at_nice}.\n"
                 f"It contains {n_verses} verse(s) and {n_chars:,} chars of transcript.",
            font=ctk.CTkFont(size=12),
            text_color=("gray30", "gray75"),
            wraplength=400,
            justify="center",
        ).pack(pady=(0, 16))

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack()

        def _do_restore():
            dialog.destroy()
            self._restore_session_data(data)

        def _do_discard():
            session_state.clear_session()
            dialog.destroy()

        ctk.CTkButton(
            btn_frame, text="Restore",
            fg_color="#2a7a2a", hover_color="#1f5c1f",
            font=ctk.CTkFont(size=13, weight="bold"),
            width=120,
            command=_do_restore,
        ).pack(side="left", padx=(0, 12))

        ctk.CTkButton(
            btn_frame, text="Discard",
            fg_color="#7a2a2a", hover_color="#5c1f1f",
            font=ctk.CTkFont(size=13, weight="bold"),
            width=120,
            command=_do_discard,
        ).pack(side="left")


# ── 4.  NEW METHOD: _restore_session_data ────────────────────────────────────

    def _restore_session_data(self, data: dict):
        """Apply a loaded session dict: restore engine globals, repopulate the
        history panel, update context fields, and set note flags."""
        try:
            # 1. Push all globals back into the engine
            engine.restore_session(data)

            # 2. Repopulate verse history scroll frame
            for w in self.history_scroll_frame.winfo_children():
                w.destroy()
            for item in engine.get_verse_history():
                ref = item["ref"]
                lbl = f"[{item['time']}] {ref}"
                btn = ctk.CTkButton(
                    self.history_scroll_frame,
                    text=lbl,
                    anchor="w",
                    fg_color="transparent",
                    hover_color=("gray80", "gray25"),
                    text_color=("gray20", "gray85"),
                    font=ctk.CTkFont(size=10),
                    height=22,
                    command=lambda r=ref: self._open_verse_popup(r),
                )
                btn.pack(fill="x", padx=2, pady=1)
            self._last_history_len = len(engine.get_verse_history())

            # 3. Restore context display fields
            book    = data.get("current_book")    or ""
            chapter = data.get("current_chapter") or ""
            verse   = data.get("current_verse")   or ""
            self.ctx_book.configure(placeholder_text=book or "e.g. John")
            self.ctx_chapter.configure(placeholder_text=chapter or "e.g. 3")
            self.ctx_verse.configure(placeholder_text=verse or "e.g. 16")

            # 4. Restore note flags
            self._notes_saved     = bool(data.get("notes_saved",     False))
            self._notes_generated = bool(data.get("notes_generated", False))

            n_verses = len(engine.get_verse_history())
            n_chars  = len(engine.full_sermon_transcript)
            self._append_log(
                f"✅ Session restored: {n_verses} verse(s), {n_chars:,} chars of transcript"
            )

            # 5. Session is now live in memory — clear the file.
            #    The periodic auto-save will recreate it within 60 s.
            session_state.clear_session()

        except Exception as e:
            self._append_log(f"⚠️ Session restore error: {e}")


# ── 5.  NEW METHOD: _build_session_data ──────────────────────────────────────
#  Helper used by both _periodic_session_save and _finish_close.

    def _build_session_data(self) -> dict:
        """Collect the current in-memory state into a session dict.
        Never includes API keys.
        """
        import datetime as _dt
        return {
            "saved_at":                  _dt.datetime.now().isoformat(),
            "full_sermon_transcript":    engine.full_sermon_transcript or "",
            "verses_cited":              list(engine.verses_cited) if hasattr(engine, "verses_cited") else [],
            "verse_history":             engine.get_verse_history(),
            "current_book":              engine.current_book,
            "current_chapter":           engine.current_chapter,
            "current_verse":             engine.current_verse,
            "session_verse_high_water":  dict(engine._session_verse_high_water)
                                         if hasattr(engine, "_session_verse_high_water") else {},
            "advance_transcript_offset": getattr(engine, "_advance_transcript_offset", 0),
            # Saved as 0.0 so it doesn't expire on next launch
            "last_explicit_ref_time":    0.0,
            "notes_saved":               self._notes_saved,
            "notes_generated":           self._notes_generated,
        }


# ── 6.  NEW METHOD: _start_session_autosave ──────────────────────────────────
#  Call this from _start() after self._running = True.

    def _start_session_autosave(self):
        """Start the 60-second background auto-save daemon thread."""
        self._session_save_stop = threading.Event()

        def _loop():
            while not self._session_save_stop.wait(60):
                if not self._running:
                    break
                try:
                    session_state.save_session(self._build_session_data())
                except Exception as e:
                    logging.warning(f"⚠️ Periodic session save failed: {e}")

        t = threading.Thread(target=_loop, daemon=True, name="vv-session-autosave")
        t.start()


# ── 7.  CHANGED METHOD: _start  (add two lines near the end) ─────────────────
#  Find the block that sets self._running = True and starts the engine thread,
#  and insert the two marked lines:

    def _start(self):
        try:
            if self._running:
                return

            s = self._collect_settings()
            cfg.save(s)

            missing = []
            _engine    = s.get("stt_engine", "deepgram")
            _lang_code = self._lang_code()
            _sec_engine = s.get("secondary_stt_engine", "deepgram")
            _sec_lang   = s.get("secondary_language")

            if _engine == "deepgram" and _lang_code != "ml":
                if not s["deepgram_api_key"]:
                    missing.append("Deepgram API Key")
            if _engine == "sarvam":
                if not s["sarvam_api_key"]:
                    missing.append("Sarvam API Key")
            if _engine in ("assemblyai", "assemblyai_pro", "assemblyai_multilingual"):
                if not s.get("assemblyai_api_key"):
                    missing.append("AssemblyAI API Key")

            if s.get("dual_stt_enabled") and _sec_lang:
                if _sec_engine == "deepgram" and not s["deepgram_api_key"]:
                    missing.append("Deepgram API Key (required for secondary stream)")
                if _sec_engine == "sarvam" and not s["sarvam_api_key"]:
                    missing.append("Sarvam API Key (required for secondary Malayalam stream)")
                if _sec_engine in ("assemblyai", "assemblyai_pro", "assemblyai_multilingual") and not s.get("assemblyai_api_key"):
                    missing.append("AssemblyAI API Key (required for secondary stream)")

            if missing:
                mb.showwarning("Missing Keys", f"Please enter in Advanced Settings:\n\n{chr(10).join(missing)}")
                self._append_log(f"⚠️ Missing keys: {', '.join(missing)}")
                return

            engine.configure(
                language                  = self._lang_code(),
                mic_index                 = self._mic_index(),
                rate                      = s["rate"],
                chunk                     = s["chunk"],
                remote_url                = s["remote_url"],
                dedup_window              = s["dedup_window"],
                cooldown                  = s["cooldown"],
                llm_enabled               = s["llm_enabled"],
                bible_translation         = s["bible_translation"],
                deepgram_api_key          = s["deepgram_api_key"],
                groq_api_key              = s["groq_api_key"],
                gemini_api_key            = s["gemini_api_key"],
                cerebras_api_key          = s["cerebras_api_key"],
                mistral_api_key           = s["mistral_api_key"],
                sarvam_api_key            = s["sarvam_api_key"],
                discord_webhook_url       = s["discord_webhook_url"],
                discord_log_webhook_url   = s["discord_log_webhook_url"],
                discord_notes_webhook_url = s["discord_notes_webhook_url"],
                confidence                = s["confidence"],
                manual_confirm            = s["manual_confirm"],
                confirm_callback          = self._user_confirm_callback,
                verify                    = s["verify"],
                verse_interrupt           = s["verse_interrupt"],
                spoken_numeral_mode       = s.get("spoken_numeral_mode", False),
                smart_amen                = s["smart_amen"],
                panic_key                 = s["panic_key"],
                live_points_prompt         = s["live_points_prompt"],
                live_points_callback       = self.live_app.update_live_points,
                live_points_get_current_cb = self.live_app.get_current_display,
                live_points_enabled        = self.live_app.is_live_llm_enabled(),
                silence_timeout            = s.get("silence_timeout", 60),
                atem_enabled               = s.get("atem_enabled", False),
                atem_ip                    = s.get("atem_ip", ""),
                atem_key_duration          = s.get("atem_key_duration", 5.0),
                gui_app                    = self,
                bridge_ready_callback      = self._on_bridge_ready,
                dual_stt_enabled           = s.get("dual_stt_enabled", False),
                secondary_language         = _sec_lang,
                secondary_stt_engine       = _sec_engine,
                stt_engine                 = _engine,
                assemblyai_api_key         = s.get("assemblyai_api_key", ""),
                aai_turn_cutoff            = s.get("aai_turn_cutoff", 5),
                malayalam_transliteration  = s.get("malayalam_transliteration", False),
            )

            self._running = True
            self._notes_saved     = False
            self._notes_generated = False
            self.btn_stop.configure(state="normal")
            self.lbl_status.configure(text="● Running", text_color="#2a7a2a")
            self.lang_menu.configure(state="disabled")
            self.mic_menu.configure(state="disabled")

            self._start_session_autosave()   # NEW — start 60-s periodic save

            self._engine_thread = threading.Thread(target=self._run_engine, daemon=True)
            self._engine_thread.start()
            self.after(2000, self._refresh_context)

        except Exception as e:
            mb.showerror("Start Error", f"Failed to start:\n\n{e}")
            self._append_log(f"❌ Start failed: {e}")


# ── 8.  CHANGED METHOD: _on_stopped  (stop auto-save thread) ─────────────────

    def _on_stopped(self):
        self._running = False
        # Stop the periodic session-save thread cleanly
        if hasattr(self, "_session_save_stop"):
            self._session_save_stop.set()   # NEW
        # Stop the Discord bot — the bridge is dead, bot would be useless
        if self._bot_process and self._bot_process.poll() is None:
            self._bot_process.terminate()
        self.bot_start_btn.configure(state="disabled")
        self.bot_stop_btn.configure(state="disabled")
        self.bot_status_lbl.configure(text="⏸ Waiting for engine…", text_color="#888888")
        self.btn_stop.configure(state="disabled")
        self.lbl_status.configure(text="● Stopped", text_color="#666666")
        self.lang_menu.configure(state="normal")
        self.mic_menu.configure(state="normal")
        if getattr(self, "_closing", False):
            self.after(200, self._finish_close)
            return
        self.btn_start.configure(state="normal")


# ── 9.  CHANGED METHOD: _finish_close  (save session before destroy) ─────────

    def _finish_close(self):
        """Called after the engine has fully stopped (or was already stopped)."""
        # Save session so it can be restored on next launch
        try:
            data = self._build_session_data()
            if data.get("full_sermon_transcript", "").strip() or data.get("verse_history"):
                session_state.save_session(data)
                self._append_log("💾 Session saved for next launch.")
        except Exception as e:
            logging.warning(f"⚠️ Session save on close failed: {e}")

        # Auto-save summary if needed
        if (
            self.auto_save_var.get()
            and not self._notes_saved
            and not self._notes_generated
            and engine.full_sermon_transcript
            and len(engine.full_sermon_transcript.strip()) > 100
        ):
            self.lbl_status.configure(text="● Auto-Saving Notes...", text_color="#a07020")
            self.update()
            try:
                self._append_log("⚠️ Auto-generating summary before close...")
                content = engine.generate_sermon_summary()

                default_title = "Unsaved_Sermon"
                first_line = content.split("\n")[0]
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

        self.destroy()


# ── 10. CHANGED METHOD: _clear_sermon_memory  (also clears the session) ──────

    def _clear_sermon_memory(self):
        if mb.askyesno(
            "Clear Memory",
            "Are you sure you want to delete the current recorded sermon?\n\nThis cannot be undone!"
        ):
            engine.clear_sermon_buffer()
            session_state.clear_session()   # NEW — don't offer a stale restore
            self._notes_saved     = False
            self._notes_generated = False
            self._append_log("🗑️ Sermon memory wiped clean for the next service.")
