# -*- coding: utf-8 -*-
import customtkinter as ctk  # type: ignore
import tkinter.messagebox as mb
import threading
import asyncio
import logging
# pyaudio imported lazily inside _populate_mics
# pynput imported lazily inside _record_panic_key
import datetime
import re
import os
import sys

import settings as cfg  # type: ignore
import vv_streaming_master as engine  # type: ignore
from live_points_app import LivePointsController  # type: ignore
try:
    import updater as _updater  # type: ignore
except ImportError:
    _updater = None

APP_VERSION = "1.2.0"

def _read_build_version() -> str:
    """Read the build tag from version.txt bundled by CI, or fall back to APP_VERSION."""
    try:
        import sys, os
        base = sys._MEIPASS if hasattr(sys, "_MEIPASS") else os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base, "version.txt")
        with open(path, encoding="utf-8") as f:
            v = f.read().strip()
        return v if v and v != "dev" else APP_VERSION
    except Exception:
        return APP_VERSION

BUILD_VERSION = _read_build_version()

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
        self.title(f"VerseView Detector  v{APP_VERSION}  [{BUILD_VERSION}]")
        self.geometry("1060x700")
        self.minsize(800, 500)


        self._s                   = cfg.load()
        self._running             = False
        self._closing             = False
        self._engine_thread       = None
        self._notes_saved         = False
        self._worship_mode_active = False


        self._build_ui()
        self._populate_mics()
        self._attach_log_handler()
        self._load_into_ui()
        # Shift+Escape panic binding — no pynput, no permissions needed
        self.bind("<Shift-Escape>", lambda e: self._panic_shortcut())
        # Trigger auto-start / smart schedule after window is ready
        self.after(500, self._check_auto_start)
        self._last_history_len = 0
        self.after(1000, self._update_history_loop)
        self.after(1500, self._update_chapter_browser_loop)
        # Silent update check — runs 15s after startup so it never delays launch
        self.after(15000, self._check_for_update_bg)
        # Settings sync — runs 3s after launch so UI is fully ready
        self.after(3000, self._sync_settings_on_launch)


    # ─────────────────────────────────────────────────
    # UI BUILD
    # ─────────────────────────────────────────────────
    def _build_ui(self):
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=(0, 10))


        # Add the two tabs
        self.tab_vv   = self.tabview.add("VerseView Detector")
        self.tab_live = self.tabview.add("Live Points")


        self.tab_vv.grid_columnconfigure(0, weight=3)
        self.tab_vv.grid_columnconfigure(1, weight=2)
        self.tab_vv.grid_rowconfigure(0, weight=1)


        # ── LEFT PANEL ──
        left = ctk.CTkFrame(self.tab_vv)
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

        self.btn_worship = ctk.CTkButton(
            top, text="🎵 Worship Mode", width=130,
            fg_color="transparent", border_color="#5a3a8a", border_width=2,
            text_color=("gray20", "gray90"), hover_color="#3f2060",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._toggle_worship_mode
        )
        self.btn_worship.pack(side="right", padx=(16, 0))

        # Update / check-for-update button — always visible
        self._update_info = None
        self.btn_update = ctk.CTkButton(
            top, text="⟳ Check for Update", width=160,
            fg_color="transparent", border_color=("gray60", "gray40"), border_width=1,
            text_color=("gray40", "gray70"), hover_color=("gray85", "gray25"),
            font=ctk.CTkFont(size=12),
            command=self._manual_check_update
        )
        self.btn_update.pack(side="right", padx=(8, 0))


        # ── SPLIT FRAME FOR LOGS AND HISTORY ──
        split_frame = ctk.CTkFrame(left, fg_color="transparent")
        split_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        split_frame.grid_rowconfigure(1, weight=1)
        split_frame.grid_columnconfigure(0, weight=1) 
        split_frame.grid_columnconfigure(1, weight=0) # lock sidebar width

        self.log_box = ctk.CTkTextbox(
            split_frame, state="disabled",
            font=("Segoe UI", 12), wrap="word"
        )
        self.log_box.grid(row=1, column=0, padx=(0, 2), sticky="nsew")

        # Read the actual rendered bg color from log_box so scroll frames match exactly
        _log_fg = ("gray86", "gray17")

        history_right = ctk.CTkFrame(split_frame, fg_color="transparent", width=240)
        history_right.grid(row=1, column=1, padx=(2, 0), sticky="nsew")
        history_right.grid_rowconfigure(1, weight=1)   # verse history — grows
        history_right.grid_rowconfigure(3, weight=1)   # chapter browser — grows equally
        history_right.grid_rowconfigure(2, weight=0)   # divider label — fixed
        history_right.grid_rowconfigure(4, weight=0)   # manual entry — fixed
        history_right.grid_columnconfigure(0, weight=1)
        history_right.grid_propagate(False)

        self.btn_clear_history = ctk.CTkButton(
            history_right, text="Clear", height=20, width=50,
            fg_color="transparent", border_width=1,
            text_color=("gray40", "gray60"),
            font=ctk.CTkFont(size=11),
            command=self._clear_verse_history
        )
        self.btn_clear_history.grid(row=0, column=0, pady=(0, 2), sticky="ew")

        # Rounded wrapper gives visible corners; scroll frame fills it flush
        _hist_wrapper = ctk.CTkFrame(
            history_right, fg_color=_log_fg, corner_radius=10
        )
        _hist_wrapper.grid(row=1, column=0, sticky="nsew")
        _hist_wrapper.grid_rowconfigure(0, weight=1)
        _hist_wrapper.grid_columnconfigure(0, weight=1)

        self.history_scroll_frame = ctk.CTkScrollableFrame(
            _hist_wrapper, width=228, label_text="📜 Verse History",
            label_font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=_log_fg,
            corner_radius=10,
            scrollbar_button_color=("gray70", "gray30"),
            scrollbar_button_hover_color=("gray60", "gray40"),
        )
        self.history_scroll_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.history_scroll_frame.grid_columnconfigure(0, weight=1)
        self.after(200, lambda: self._sync_scrollframe_bg(
            self.history_scroll_frame, _log_fg))

        # ── thin separator instead of label ──
        _sep = ctk.CTkFrame(history_right, height=1, fg_color=("gray70", "gray35"))
        _sep.grid(row=2, column=0, sticky="ew", padx=4, pady=(3, 3))

        # store reference for the chapter header text update
        # (Header now integrated into ScrollableFrame label)

        _chap_wrapper = ctk.CTkFrame(
            history_right, fg_color=_log_fg, corner_radius=10
        )
        _chap_wrapper.grid(row=3, column=0, sticky="nsew")
        _chap_wrapper.grid_rowconfigure(0, weight=1)
        _chap_wrapper.grid_columnconfigure(0, weight=1)

        self.chapter_browser_frame = ctk.CTkScrollableFrame(
            _chap_wrapper, width=228, label_text="📖 Chapter Verses",
            label_font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=_log_fg,
            corner_radius=10,
            scrollbar_button_color=("gray70", "gray30"),
            scrollbar_button_hover_color=("gray60", "gray40"),
        )
        self.chapter_browser_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.chapter_browser_frame.grid_columnconfigure(0, weight=1)
        self.after(200, lambda: self._sync_scrollframe_bg(
            self.chapter_browser_frame, _log_fg))

        self._chapter_browser_loaded = ""  # "Genesis 1" — skip reload if same
        self._chapter_browser_loading = False

        # ── MANUAL VERSE ENTRY ──
        self.manual_verse_entry = ctk.CTkEntry(
            history_right,
            placeholder_text="e.g. gen 3 2  or  john 3:16",
            font=ctk.CTkFont(size=10),
            height=26,
        )
        self.manual_verse_entry.grid(row=4, column=0, sticky="ew", pady=(4, 2))
        self.manual_verse_entry.bind("<Return>", lambda e: self._send_manual_verse())


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
            self.tab_vv, label_text="⚙   Settings",
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
            row += 1  # type: ignore
            return lbl


        def add_entry(placeholder="", show=""):
            nonlocal row
            e = ctk.CTkEntry(right, placeholder_text=placeholder, show=show)
            e.grid(row=row, column=0, sticky="ew", padx=14, pady=(0, 4))
            row += 1  # type: ignore
            return e


        def add_option(values):
            nonlocal row
            var = ctk.StringVar(value=values[0])
            m   = ctk.CTkOptionMenu(right, variable=var, values=values)
            m.grid(row=row, column=0, sticky="ew", padx=14, pady=(0, 4))
            row += 1  # type: ignore
            return var, m


        # Language
        sep_label("Language")
        self.lang_var, self.lang_menu = add_option([
            "English (Nova-2)",
            "Malayalam (Sarvam AI)",
            "Hindi (Nova-3)",
            "Multi (Nova-2)",
        ])

        def _on_ml_raw_toggle():
            engine.show_malayalam_raw = self.ml_raw_var.get()

        self.ml_raw_var = ctk.BooleanVar(value=False)
        self.ml_raw_cb = ctk.CTkCheckBox(
            right, text="Show Malayalam 🇮🇳",
            variable=self.ml_raw_var,
            command=_on_ml_raw_toggle
        )
        self.ml_raw_cb.grid(row=row, column=0, sticky="w", padx=14, pady=(2, 4))
        row += 1

        def _on_lang_changed(val):
            if "Malayalam" in val:
                self.ml_raw_cb.configure(state="normal")
            else:
                self.ml_raw_cb.configure(state="disabled")
        
        self.lang_menu.configure(command=_on_lang_changed)


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


        # ── Options toggle (checkboxes + confidence + panic) ──
        self._opts_open = False
        self.btn_opts = ctk.CTkButton(
            right, text="▶   Options",
            fg_color="transparent",
            text_color=("gray40", "gray60"),
            anchor="w", hover=False,
            command=self._toggle_options
        )
        self.btn_opts.grid(row=row, column=0, sticky="ew", padx=10, pady=(14, 2))
        self._opts_row = row
        row += 2  # row N+1 is reserved for opts_frame when expanded

        self.opts_frame = ctk.CTkFrame(right)
        self.opts_frame.grid_columnconfigure(0, weight=1)
        self._build_options()

        # ── Advanced toggle ──
        self._adv_open = False
        self.btn_adv = ctk.CTkButton(
            right, text="▶   Advanced Settings",
            fg_color="transparent",
            text_color=("gray40", "gray60"),
            anchor="w", hover=False,
            command=self._toggle_advanced
        )
        self.btn_adv.grid(row=row, column=0, sticky="ew", padx=10, pady=(4, 2))
        self._adv_row = row
        row += 2  # row N+1 is reserved for adv_frame when expanded

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
            self.tab_vv, text=f"v{APP_VERSION}  •  build: {BUILD_VERSION}",
            text_color=("gray50", "gray50"),
            font=ctk.CTkFont(size=10)
        ).grid(row=1, column=0, columnspan=2, pady=(0, 4), sticky="e", padx=12)


        # ── Initialize the Live Points Controller ──
        self.live_app = LivePointsController(self.tab_live)


        self.after(2000, self._refresh_context)


    def _build_options(self):
        f = self.opts_frame
        r = 0

        def o_sep(text):
            nonlocal r
            lbl = ctk.CTkLabel(
                f, text=text, anchor="w",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=("gray30", "gray70")
            )
            lbl.grid(row=r, column=0, sticky="ew", padx=10, pady=(12, 2))
            r += 1  # type: ignore
            return lbl

        # ── Confidence ──
        self.conf_val_label = o_sep("Confidence Threshold: 75%")
        self.conf_var = ctk.DoubleVar(value=0.75)

        def _update_conf(val):
            self.conf_val_label.configure(text=f"Confidence Threshold: {int(float(val)*100)}%")

        self.conf_slider = ctk.CTkSlider(f, from_=0.5, to=1.0, variable=self.conf_var, command=_update_conf)
        self.conf_slider.grid(row=r, column=0, sticky="ew", padx=10, pady=(0, 4))
        r += 1

        # ── Checkboxes ──
        self.manual_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(f, text="Require Manual Confirmation (Ask Y/N for low-confidence verses)",
                        variable=self.manual_var).grid(row=r, column=0, sticky="w", padx=10, pady=(8, 3))
        r += 1

        self.verify_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(f, text="Require Verification (Hear verse twice before displaying)",
                        variable=self.verify_var).grid(row=r, column=0, sticky="w", padx=10, pady=(0, 3))
        r += 1

        self.verse_interrupt_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(f, text="Verse Interrupt (wait for speaker to say verse; 60s timeout; new ref cancels)",
                        variable=self.verse_interrupt_var).grid(row=r, column=0, sticky="w", padx=10, pady=(0, 3))
        r += 1

        self.spoken_numeral_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(f, text="Spoken Numeral Mode ('John three sixteen' → John 3:16, no 'verse' keyword needed)",
                        variable=self.spoken_numeral_var).grid(row=r, column=0, sticky="w", padx=10, pady=(0, 3))
        r += 1

        self.smart_amen_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(f, text="Smart Amen (auto-clear screen on 'Let us pray')",
                        variable=self.smart_amen_var).grid(row=r, column=0, sticky="w", padx=10, pady=(0, 3))
        r += 1

        self.auto_save_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(f, text="Auto-Save Sermon Notes on App Close",
                        variable=self.auto_save_var).grid(row=r, column=0, sticky="w", padx=10, pady=(0, 3))
        r += 1

        self.auto_start_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(f, text="Auto-Start on Launch (starts engine automatically)",
                        variable=self.auto_start_var).grid(row=r, column=0, sticky="w", padx=10, pady=(0, 3))
        r += 1

        self.smart_schedule_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(f, text="Smart Schedule (auto-set language by day & time)",
                        variable=self.smart_schedule_var).grid(row=r, column=0, sticky="w", padx=10, pady=(0, 2))
        r += 1
        ctk.CTkLabel(f, text="  Sat→Malayalam  |  Sun 9:10 AM→English  |  10:40 AM→English  |  4:40 PM→Hindi",
                     text_color=["#666666", "#888888"],
                     font=ctk.CTkFont(size=11)).grid(row=r, column=0, sticky="w", padx=10, pady=(0, 6))
        r += 1

        # ── ATEM Chroma Key Overlay ──
        o_sep("🎬 ATEM Chroma Key Overlay")

        self.atem_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(f, text="Enable ATEM Keyer on Verse Display",
                        variable=self.atem_var).grid(
            row=r, column=0, sticky="w", padx=10, pady=(0, 4))
        r += 1

        atem_sub = ctk.CTkFrame(f, fg_color="transparent")
        atem_sub.grid(row=r, column=0, sticky="ew", padx=10, pady=(0, 6))
        atem_sub.grid_columnconfigure(1, weight=1)
        r += 1

        ctk.CTkLabel(atem_sub, text="ATEM IP", anchor="w", width=70).grid(
            row=0, column=0, padx=(0, 6), pady=2, sticky="w")
        self.atem_ip_entry = ctk.CTkEntry(atem_sub, placeholder_text="Auto (or enter IP)", width=110)
        self.atem_ip_entry.grid(row=0, column=1, sticky="ew", pady=2)
        self.atem_scan_btn = ctk.CTkButton(
            atem_sub, text="🔍", width=28,
            fg_color="#4a4a4a", hover_color="#666666",
            command=self._scan_atem_ip
        )
        self.atem_scan_btn.grid(row=0, column=2, sticky="w", padx=(4, 0), pady=2)

        ctk.CTkLabel(atem_sub, text="Key On (s)", anchor="w", width=70).grid(
            row=1, column=0, padx=(0, 6), pady=2, sticky="w")
        self.atem_dur_entry = ctk.CTkEntry(atem_sub, placeholder_text="5.0", width=60)
        self.atem_dur_entry.grid(row=1, column=1, sticky="w", pady=2)

        # ATEM manual test toggle
        self._atem_sw       = None
        self._atem_keyer_on = False
        self.atem_test_btn  = ctk.CTkButton(
            atem_sub,
            text="◼  Keyer: OFF",
            width=140,
            fg_color="#4a4a4a",
            hover_color="#555555",
            command=self._toggle_atem_keyer_manual
        )
        self.atem_test_btn.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(6, 2))

        # ── Panic keybind ──
        o_sep("Panic Keybind")
        self.panic_var = ctk.StringVar(value="esc")
        if sys.platform.startswith("win"):
            self.panic_btn = ctk.CTkButton(
                f, text="Panic Key: esc",
                fg_color="#4a4a4a", hover_color="#333333",
                command=self._record_panic_key
            )
            self.panic_btn.grid(row=r, column=0, sticky="ew", padx=10, pady=(0, 8))
        else:
            self.panic_btn = None
            ctk.CTkLabel(
                f, text="⌨️  Panic Key: Shift + Escape (fixed on macOS)",
                text_color=["#666666", "#888888"],
                font=ctk.CTkFont(size=12)
            ).grid(row=r, column=0, sticky="ew", padx=10, pady=(0, 8))
        r += 1


    def _toggle_options(self):
        self._opts_open = not self._opts_open
        if self._opts_open:
            self.opts_frame.grid(
                row=self._opts_row + 1, column=0,
                sticky="ew", padx=14, pady=(0, 10)
            )
            self.btn_opts.configure(text="▼   Options")
        else:
            self.opts_frame.grid_forget()
            self.btn_opts.configure(text="▶   Options")


    def _build_advanced(self):

        fields = [
            ("Sample Rate",          "16000", "rate_entry"),
            ("Chunk Size",           "4096",  "chunk_entry"),
            ("Cooldown (s)",         "3.0",   "cooldown_entry"),
            ("Dedup Window (s)",     "60",    "dedup_entry"),
            ("Silence Timeout (s)", "60",    "silence_entry"),
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
            ("Deepgram Key",              "dg_key_entry"),
            ("Cerebras API Key",          "cb_key_entry"),
            ("Mistral API Key",           "ms_key_entry"),
            ("Groq API Key",              "or_key_entry"),
            ("Gemini API Key",            "gm_key_entry"),
            ("Sarvam Key",                "sv_key_entry"),
            ("Discord Webhook URL",       "dc_key_entry"),
            ("Discord Log Webhook URL",   "dc_log_key_entry"),
            ("Discord Notes Webhook URL", "dc_notes_key_entry"),
        ]
        for j, (lbl, attr) in enumerate(key_fields):
            ctk.CTkLabel(self.adv_frame, text=lbl, anchor="w").grid(
                row=n+2+j, column=0, padx=10, pady=4, sticky="w"
            )
            e = ctk.CTkEntry(self.adv_frame, show="•", width=200,
                             placeholder_text="Paste key here")
            e.grid(row=n+2+j, column=1, padx=10, pady=4, sticky="ew")
            setattr(self, attr, e)

        # ── Settings Sync ──
        sync_row = n + 2 + len(key_fields)
        ctk.CTkLabel(
            self.adv_frame, text="─── Settings Sync ───", anchor="w",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("gray30", "gray70")
        ).grid(row=sync_row, column=0, columnspan=2, padx=10, pady=(14, 2), sticky="ew")

        ctk.CTkLabel(self.adv_frame, text="Sync URL", anchor="w").grid(
            row=sync_row+1, column=0, padx=10, pady=4, sticky="w"
        )
        self.sync_url_entry = ctk.CTkEntry(
            self.adv_frame, width=200,
            placeholder_text="Direct download URL (Google Drive, etc.)"
        )
        self.sync_url_entry.grid(row=sync_row+1, column=1, padx=10, pady=4, sticky="ew")

        self.btn_sync_now = ctk.CTkButton(
            self.adv_frame, text="⬇  Pull Now", height=28,
            fg_color="#1a5a8a", hover_color="#144a72",
            command=self._sync_settings_now
        )
        self.btn_sync_now.grid(row=sync_row+2, column=0, columnspan=2,
                               padx=10, pady=(0, 8), sticky="ew")


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
        if not sys.platform.startswith("win"):
            return  # no-op on macOS
        """ Allows the user to press a key combo to record it safely without typing """
        if self.panic_btn:
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
                from pynput import keyboard as pynput_kb  # type: ignore
                with pynput_kb.Listener(on_press=on_press) as listener:
                    listener.join()
            except Exception as e:
                self._append_log(f"⚠️ Key recording error: {e}")
                self.after(0, lambda: self._on_panic_recorded(self.panic_var.get()))


        threading.Thread(target=recorder, daemon=True).start()


    def _panic_shortcut(self):
        """Shift+Escape clears the screen — uses tkinter binding, no pynput."""
        if self._running:
            engine.trigger_panic()
            self._append_log("\U0001f6a8 Panic! Screen cleared via Shift+Escape")


    def _on_panic_recorded(self, combo):
        if combo:
            self.panic_var.set(combo)
            if self.panic_btn:
                self.panic_btn.configure(text=f"Panic Key: {combo}", fg_color=["#3B8ED0", "#1F6AA5"], state="normal")
            self._append_log(f"⌨️ Panic key updated to: {combo}")
        else:
            if self.panic_btn:
                self.panic_btn.configure(text=f"Panic Key: {self.panic_var.get()}", fg_color=["#3B8ED0", "#1F6AA5"], state="normal")


    # ─────────────────────────────────────────────────
    # SETTINGS PERSISTENCE
    # ─────────────────────────────────────────────────
    def _load_into_ui(self):
        s = self._s
        self.lang_var.set(s.get("language", "English (Nova-2)"))
        self.bible_var.set(s.get("bible_translation", "WEB").upper())
        self.live_app.set_screen(s.get("display_screen", "Display 2 (Right/Extended)"))
        self.url_entry.delete(0, "end")
        self.url_entry.insert(0, s.get("remote_url", "http://localhost:50010/control.html"))

        saved_conf = s.get("confidence", 0.75)
        self.conf_var.set(saved_conf)
        self.conf_val_label.configure(text=f"Confidence Threshold: {int(saved_conf * 100)}%")

        # Reset Worship Mode button visually if it was active
        if self._worship_mode_active:
            self.btn_worship.configure(fg_color="transparent", text_color=("gray20", "gray90"))
        self._worship_mode_active = False

        self.manual_var.set(s.get("manual_confirm", True))
        self.verify_var.set(s.get("verify", True))
        # verse_text_confirm kept for backward compat when loading old settings
        self.verse_interrupt_var.set(s.get("verse_interrupt", s.get("verse_text_confirm", False)))
        self.spoken_numeral_var.set(s.get("spoken_numeral_mode", False))
        self.smart_amen_var.set(s.get("smart_amen", True))
        self.auto_save_var.set(s.get("auto_save_notes", True))
        self.auto_start_var.set(s.get("auto_start", False))
        self.smart_schedule_var.set(s.get("smart_schedule", False))

        saved_ml_raw = s.get("show_malayalam_raw", False)
        self.ml_raw_var.set(saved_ml_raw)
        engine.show_malayalam_raw = saved_ml_raw
        if "Malayalam" in self.lang_var.get():
            self.ml_raw_cb.configure(state="normal")
        else:
            self.ml_raw_cb.configure(state="disabled")

        saved_panic = s.get("panic_key", "esc")
        self.panic_var.set(saved_panic)
        if self.panic_btn:
            self.panic_btn.configure(text=f"Panic Key: {saved_panic}")


        default_prompt = (
            "You are a real-time sermon outliner.\n\n"
            "STRICT RULES:\n"
            "1. ONLY extract explicitly stated points from the transcript.\n"
            "2. DO NOT hallucinate, guess, or add information not present in the text.\n"
            "3. If the speaker has only mentioned a title or intro, ONLY output the Title.\n"
            "4. DO NOT output 'Listening...', 'Waiting...', or any status messages.\n"
            "5. Keep points as brief, single-line bullet points.\n\n"
            "Output Format:\n"
            "[TITLE IN ALL CAPS]\n"
            "• Point 1\n"
            "• Point 2"
        )

        self.live_app.set_prompt(s.get("live_points_prompt", default_prompt))
        self.live_app.set_live_llm_enabled(s.get("live_points_llm_enabled", False))


        self.rate_entry.delete(0, "end");     self.rate_entry.insert(0,     str(s.get("rate",            16000)))
        self.chunk_entry.delete(0, "end");    self.chunk_entry.insert(0,    str(s.get("chunk",            4096)))
        self.cooldown_entry.delete(0, "end"); self.cooldown_entry.insert(0, str(s.get("cooldown",         3.0)))
        self.dedup_entry.delete(0, "end");    self.dedup_entry.insert(0,    str(s.get("dedup_window",     60)))
        self.silence_entry.delete(0, "end");  self.silence_entry.insert(0,  str(s.get("silence_timeout",  60)))
        self.llm_var.set("Enabled" if s.get("llm_enabled", True) else "Disabled")

        self.atem_var.set(s.get("atem_enabled", False))
        self.atem_ip_entry.delete(0, "end");  self.atem_ip_entry.insert(0,  s.get("atem_ip", ""))
        self.atem_dur_entry.delete(0, "end"); self.atem_dur_entry.insert(0, str(s.get("atem_key_duration", 5.0)))

        # ── load all 3 Discord webhook URLs ──
        for attr, key in [
            ("dg_key_entry",       "deepgram_api_key"),
            ("cb_key_entry",       "cerebras_api_key"),
            ("ms_key_entry",       "mistral_api_key"),
            ("or_key_entry",       "groq_api_key"),
            ("gm_key_entry",       "gemini_api_key"),
            ("sv_key_entry",       "sarvam_api_key"),
            ("dc_key_entry",       "discord_webhook_url"),
            ("dc_log_key_entry",   "discord_log_webhook_url"),
            ("dc_notes_key_entry", "discord_notes_webhook_url"),
        ]:
            e = getattr(self, attr)
            e.delete(0, "end")
            e.insert(0, s.get(key, ""))

        self.sync_url_entry.delete(0, "end")
        self.sync_url_entry.insert(0, s.get("settings_sync_url", ""))


    def _collect_settings(self) -> dict:
        return {
            "language":                   self.lang_var.get(),
            "bible_translation":          self.bible_var.get().lower(),
            "display_screen":             self.live_app.get_screen(),
            "remote_url":                 self.url_entry.get(),
            "confidence":                 self.conf_var.get(),
            "manual_confirm":             self.manual_var.get(),
            "verify":                     self.verify_var.get(),
            "verse_interrupt":            self.verse_interrupt_var.get(),
            "spoken_numeral_mode":        self.spoken_numeral_var.get(),
            "smart_amen":                 self.smart_amen_var.get(),
            "auto_save_notes":            self.auto_save_var.get(),
            "auto_start":                 self.auto_start_var.get(),
            "smart_schedule":             self.smart_schedule_var.get(),
            "show_malayalam_raw":         self.ml_raw_var.get(),
            "panic_key":                  self.panic_var.get(),
            "live_points_prompt":         self.live_app.get_prompt(),
            "live_points_llm_enabled":    self.live_app.get_live_llm_enabled() if hasattr(self.live_app, "get_live_llm_enabled") else False,
            "rate":                       self._safe_int(self.rate_entry,      16000),
            "chunk":                      self._safe_int(self.chunk_entry,     4096),
            "cooldown":                   self._safe_float(self.cooldown_entry, 3.0),
            "dedup_window":               self._safe_int(self.dedup_entry,     60),
            "silence_timeout":            self._safe_int(self.silence_entry,   60),
            "llm_enabled":                self.llm_var.get() == "Enabled",
            "deepgram_api_key":           self.dg_key_entry.get(),
            "groq_api_key":               self.or_key_entry.get(),
            "gemini_api_key":             self.gm_key_entry.get(),
            "cerebras_api_key":           self.cb_key_entry.get(),
            "mistral_api_key":            self.ms_key_entry.get(),
            "sarvam_api_key":             self.sv_key_entry.get(),
            # ── all 3 Discord webhook URLs ──
            "discord_webhook_url":        self.dc_key_entry.get(),
            "discord_log_webhook_url":    self.dc_log_key_entry.get(),
            "discord_notes_webhook_url":  self.dc_notes_key_entry.get(),
            "mic_index":                  self._mic_index(),
            "atem_enabled":               self.atem_var.get(),
            "atem_ip":                    self.atem_ip_entry.get().strip(),
            "atem_key_duration":          self._safe_float(self.atem_dur_entry, 5.0),
            "settings_sync_url":          self.sync_url_entry.get().strip(),
        }


    # ─────────────────────────────────────────────────
    # SETTINGS SYNC
    # ─────────────────────────────────────────────────
    # Keys that sync is allowed to update. Settings (language, mics, etc.)
    # are intentionally excluded — only credentials and webhooks are synced.
    _SYNC_ALLOWED_KEYS = {
        "deepgram_api_key", "groq_api_key", "gemini_api_key",
        "cerebras_api_key", "mistral_api_key", "sarvam_api_key",
        "discord_webhook_url", "discord_log_webhook_url", "discord_notes_webhook_url",
    }

    def _sync_settings_on_launch(self):
        """Silent sync on launch — only runs if a URL is configured."""
        url = self._s.get("settings_sync_url", "").strip()
        if url:
            threading.Thread(
                target=self._do_settings_sync, args=(url, False), daemon=True
            ).start()

    def _sync_settings_now(self):
        """Manual pull triggered by the Pull Now button."""
        url = self.sync_url_entry.get().strip()
        if not url:
            mb.showwarning("No URL", "Paste a direct-download URL in the Sync URL field first.")
            return
        # Save the URL immediately so it persists
        self._s = self._collect_settings()
        cfg.save(self._s)
        self.btn_sync_now.configure(state="disabled", text="Pulling...")
        threading.Thread(
            target=self._do_settings_sync, args=(url, True), daemon=True
        ).start()

    def _do_settings_sync(self, url: str, manual: bool):
        """Download JSON from url, merge allowed keys into local settings."""
        try:
            import requests as _req, certifi as _cert, json as _json
            r = _req.get(url, timeout=10, verify=_cert.where())
            r.raise_for_status()
            remote = _json.loads(r.text)

            if not isinstance(remote, dict):
                raise ValueError("Downloaded file is not a JSON object.")

            # Only merge the allowed keys — never touch settings keys
            merged = dict(self._s)
            updated = []
            for k in self._SYNC_ALLOWED_KEYS:
                if k in remote and remote[k] != merged.get(k, ""):
                    merged[k] = remote[k]
                    updated.append(k)

            if updated:
                cfg.save(merged)
                self._s = merged
                self.after(0, self._load_into_ui)
                msg = f"✅ Settings synced — {len(updated)} key(s) updated."
            else:
                msg = "✅ Settings sync — already up to date."

            self._append_log(f"🔄 {msg}")
            if manual:
                self.after(0, lambda: mb.showinfo("Sync Complete", msg))

        except Exception as e:
            err = f"Settings sync failed: {e}"
            self._append_log(f"⚠️ {err}")
            if manual:
                self.after(0, lambda: mb.showerror("Sync Failed", err))
        finally:
            if manual:
                self.after(0, lambda: self.btn_sync_now.configure(
                    state="normal", text="⬇  Pull Now"))

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
        typed_book    = self.ctx_book.get().strip()
        typed_chapter = self.ctx_chapter.get().strip()
        typed_verse   = self.ctx_verse.get().strip()


        final_book    = typed_book    if typed_book    else engine.current_book
        final_chapter = typed_chapter if typed_chapter else engine.current_chapter
        final_verse   = typed_verse   if typed_verse   else engine.current_verse


        final_book    = final_book    or ""
        final_chapter = final_chapter or ""
        final_verse   = final_verse   or ""


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
        import pyaudio  # type: ignore
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
            at_bottom = self.log_box.yview()[1] >= 0.99
            self.log_box.configure(state="normal")
            self.log_box.insert("end", msg + "\n")
            if at_bottom:
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


    # ──────────────────────────────────────────────────────────
    # SMART SCHEDULE + AUTO-START
    # ──────────────────────────────────────────────────────────
    def _get_scheduled_language(self):
        """Return the language string that matches the current day/time, or None."""
        now = datetime.datetime.now()
        wd  = now.weekday()  # 0=Mon … 5=Sat, 6=Sun
        t   = now.time()


        if wd == 5:  # Saturday → Malayalam
            return "Malayalam (Sarvam AI)"


        if wd == 6:  # Sunday — pick the LATEST threshold that has passed
            if t >= datetime.time(16, 40):
                return "Hindi (Nova-3)"
            if t >= datetime.time(10, 40):
                return "English (Nova-2)"
            if t >= datetime.time(9, 10):
                return "English (Nova-2)"


        return None  # weekday or too early — no auto-language


    def _check_auto_start(self):
        """Called once after the window opens. Applies smart schedule then auto-starts if enabled."""
        if self.smart_schedule_var.get():
            lang = self._get_scheduled_language()
            if lang:
                self.lang_var.set(lang)
                self._append_log(f"📅 Smart Schedule: language set to {lang}")
            else:
                self._append_log("📅 Smart Schedule: no service detected for current day/time")


        if self.auto_start_var.get():
            self._append_log("⚡ Auto-Start: starting engine in 3 seconds...")
            self.after(3000, self._start)


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


            # ── pass all 3 Discord webhook URLs to the engine ──
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
            )


            self._running = True
            self.btn_start.configure(state="disabled")
            self.btn_stop.configure(state="normal")
            self.lbl_status.configure(text="● Running", text_color="#2a7a2a")
            self.lang_menu.configure(state="disabled")
            self.mic_menu.configure(state="disabled")


            self._engine_thread = threading.Thread(target=self._run_engine, daemon=True)  # type: ignore
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
        self.btn_stop.configure(state="disabled")
        self.lbl_status.configure(text="● Stopped", text_color="#666666")
        self.lang_menu.configure(state="normal")
        self.mic_menu.configure(state="normal")
        if getattr(self, "_closing", False):
            # Window X was clicked while engine was running — finish the close now
            self.after(200, self._finish_close)
            return
        self.btn_start.configure(state="normal")


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
                self._notes_saved = True
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


    # ── AUTO-UPDATE ───────────────────────────────────────────────────────────

    def _check_for_update_bg(self):
        """Silent background update check 15s after startup."""
        if _updater is None:
            return
        def _run():
            info = _updater.check_for_update()
            if info:
                self._update_info = info
                self.after(0, self._show_update_badge)
        threading.Thread(target=_run, daemon=True).start()

    def _manual_check_update(self):
        """Triggered by the always-visible check button."""
        if self._update_info:
            # Already found an update — go straight to dialog
            self._show_update_dialog()
            return
        if _updater is None:
            mb.showinfo("Updater", "Updater module not available in this build.")
            return
        self.btn_update.configure(text="⟳ Checking...", state="disabled")
        def _run():
            info = _updater.check_for_update()
            if info:
                self._update_info = info
                self.after(0, self._show_update_badge)
                self.after(0, self._show_update_dialog)
            else:
                self.after(0, lambda: self.btn_update.configure(
                    text="✅ Up to date", state="normal"))
                # Reset label after 4s
                self.after(4000, lambda: self.btn_update.configure(
                    text="⟳ Check for Update"))
        threading.Thread(target=_run, daemon=True).start()

    def _show_update_badge(self):
        """Highlight the update button to show an update is available."""
        self.btn_update.configure(
            text="🔄 Update Available",
            fg_color="#7a5a00", hover_color="#5c4400",
            border_width=0,
            text_color="white",
            state="normal",
            command=self._show_update_dialog
        )

    def _show_update_dialog(self):
        """Show update details and let the user apply or skip."""
        info = self._update_info
        if not info:
            return

        win = ctk.CTkToplevel(self)
        win.title("Update Available")
        win.geometry("420x260")
        win.resizable(False, False)
        win.attributes("-topmost", True)
        self.after(200, lambda: win.attributes("-topmost", False))

        ctk.CTkLabel(
            win, text="🔄  VerseView Update Available",
            font=ctk.CTkFont(size=15, weight="bold")
        ).pack(pady=(20, 6))

        ctk.CTkLabel(
            win, text=f"New version: {info['tag_name']}",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray70")
        ).pack(pady=(0, 4))

        if info.get("is_windows"):
            desc = "Windows: your browser will open the\nrelease page to download manually."
        elif info.get("is_mac_intel"):
            desc = "Full update: all _internal/ files will be\nreplaced. A restart is required."
        else:
            desc = "Updated Python files will be installed\nautomatically. A restart is required."
        ctk.CTkLabel(
            win, text=desc,
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray70")
        ).pack(pady=(0, 12))

        self._upd_progress = ctk.CTkProgressBar(win, width=340)
        self._upd_progress.pack(pady=(0, 8))
        self._upd_progress.set(0)

        self._upd_status = ctk.CTkLabel(win, text="", font=ctk.CTkFont(size=11))
        self._upd_status.pack()

        btn_frame = ctk.CTkFrame(win, fg_color="transparent")
        btn_frame.pack(pady=12)

        apply_btn = ctk.CTkButton(
            btn_frame, text="Install Update",
            fg_color="#7a5a00", hover_color="#5c4400",
            command=lambda: self._apply_update(win, apply_btn, info)
        )
        apply_btn.pack(side="left", padx=8)

        ctk.CTkButton(
            btn_frame, text="Later",
            fg_color="#4a4a4a", hover_color="#333333",
            command=win.destroy
        ).pack(side="left", padx=8)

    def _apply_update(self, win, apply_btn, info):
        if _updater is None or not info.get("download_url"):
            import webbrowser
            webbrowser.open(info.get("release_url", ""))
            win.destroy()
            return

        apply_btn.configure(state="disabled", text="Downloading...")

        def on_progress(pct):
            self.after(0, lambda: self._upd_progress.set(pct / 100))
            self.after(0, lambda: self._upd_status.configure(text=f"Downloading... {pct}%"))

        def on_done():
            self.after(0, lambda: self._upd_status.configure(text="✅ Done — restarting..."))
            self.after(0, lambda: self._upd_progress.set(1.0))
            self.after(1500, _updater.restart_app)

        def on_error(msg):
            self.after(0, lambda: self._upd_status.configure(
                text=f"❌ {msg[:80]}", text_color="#cc4444"))
            self.after(0, lambda: apply_btn.configure(state="normal", text="Retry"))

        _updater.download_and_apply(
            info["download_url"],
            on_progress=on_progress,
            on_done=on_done,
            on_error=on_error,
        )

    def _scan_atem_ip(self):
        """Run ATEM auto-discovery in the background and fill the IP field if found."""
        self.atem_scan_btn.configure(text="⏳", state="disabled")
        self._append_log("🔍 Scanning for ATEM on network (port 9910)...")
        engine._atem_resolved_ip = None  # flush cache

        def _run():
            ip = engine._discover_atem_ip()
            if ip:
                self.after(0, lambda: self.atem_ip_entry.delete(0, "end"))
                self.after(0, lambda: self.atem_ip_entry.insert(0, ip))
                self._append_log(f"✅ ATEM found: {ip} — IP filled in automatically")
            else:
                self._append_log("⚠️ ATEM not found — make sure the switcher is on and on the same network")
            self.after(0, lambda: self.atem_scan_btn.configure(text="🔍", state="normal"))

        import threading
        threading.Thread(target=_run, daemon=True).start()

    def _toggle_atem_keyer_manual(self):
        """Manual ON/OFF toggle for the ATEM upstream keyer — for testing without a verse."""
        # Always read the entry field live and flush the discovery cache so we never
        # reuse a stale IP from a previous session or a saved-but-wrong static value.
        ip_field = self.atem_ip_entry.get().strip()
        engine.ATEM_IP = ip_field
        engine._atem_resolved_ip = None  # force fresh discovery on every toggle

        if not self._atem_keyer_on:
            # Turn ON
            def _connect_and_fire():
                try:
                    import PyATEMMax  # type: ignore
                    ip = engine._resolve_atem_ip()
                    if not ip:
                        self.after(0, lambda: self.atem_test_btn.configure(
                            text="◼  Keyer: OFF", fg_color="#4a4a4a"))
                        self._append_log("⚠️ ATEM: could not find switcher — leave IP blank for auto-discovery or enter it manually")
                        return
                    sw = PyATEMMax.ATEMMax()
                    sw.connect(ip)
                    import time as _t
                    _t.sleep(2)
                    sw.setKeyerOnAirEnabled(0, 0, True)
                    self._atem_sw = sw
                    self._atem_keyer_on = True
                    self.after(0, lambda: self.atem_test_btn.configure(
                        text="🟢  Keyer: ON", fg_color="#2a7a2a", hover_color="#226622"))
                    self._append_log(f"🎬 ATEM manual: keyer ON ({ip})")
                except ImportError:
                    self.after(0, lambda: self.atem_test_btn.configure(
                        text="◼  Keyer: OFF", fg_color="#4a4a4a"))
                    self._append_log("⚠️ PyATEMMax not installed — pip install PyATEMMax")
                except Exception as e:
                    self._atem_keyer_on = False
                    self.after(0, lambda: self.atem_test_btn.configure(
                        text="◼  Keyer: OFF", fg_color="#4a4a4a"))
                    self._append_log(f"⚠️ ATEM error: {e}")
            import threading
            threading.Thread(target=_connect_and_fire, daemon=True).start()
        else:
            # Turn OFF — try the stored connection first; if dead, re-discover and reconnect to turn off
            def _turn_off():
                import time as _t
                turned_off = False
                # Attempt 1: use the stored open connection
                if self._atem_sw:
                    try:
                        self._atem_sw.setKeyerOnAirEnabled(0, 0, False)
                        _t.sleep(0.3)
                        self._atem_sw.disconnect()
                        turned_off = True
                    except Exception:
                        pass
                # Attempt 2: re-discover and reconnect if the stored connection is dead
                if not turned_off:
                    try:
                        import PyATEMMax  # type: ignore
                        engine._atem_resolved_ip = None
                        ip = engine._resolve_atem_ip()
                        if ip:
                            sw2 = PyATEMMax.ATEMMax()
                            sw2.connect(ip)
                            _t.sleep(2)
                            sw2.setKeyerOnAirEnabled(0, 0, False)
                            _t.sleep(0.3)
                            sw2.disconnect()
                            turned_off = True
                    except Exception as e:
                        self._append_log(f"⚠️ ATEM OFF error: {e}")
                self._atem_sw = None
                self._atem_keyer_on = False
                self.after(0, lambda: self.atem_test_btn.configure(
                    text="◼  Keyer: OFF", fg_color="#4a4a4a", hover_color="#555555"))
                self._append_log("🎬 ATEM manual: keyer OFF" if turned_off else "⚠️ ATEM manual: keyer OFF (could not confirm — switcher unreachable)")
            import threading
            threading.Thread(target=_turn_off, daemon=True).start()

    def _toggle_worship_mode(self):
        self._worship_mode_active = not self._worship_mode_active
        engine.WORSHIP_MODE = self._worship_mode_active
        if self._worship_mode_active:
            self.btn_worship.configure(fg_color="#5a3a8a", text_color="white")
            self._append_log("🎵 Worship Mode ON — verse detection suspended")
        else:
            self.btn_worship.configure(fg_color="transparent", text_color=("gray20", "gray90"))
            self._append_log("🎵 Worship Mode OFF — verse detection resumed")


    def _sync_scrollframe_bg(self, frame, color_pair):
        """Patch the inner tkinter Canvas of a CTkScrollableFrame to match log_box exactly."""
        try:
            # Read the real rendered bg color straight from log_box's tkinter Text widget
            actual_bg = self.log_box._textbox.cget("background")
            # Walk every child of the scrollable frame looking for Canvas widgets
            def _patch(widget):
                try:
                    if widget.winfo_class() == "Canvas":
                        widget.configure(bg=actual_bg)
                except Exception:
                    pass
                for child in widget.winfo_children():
                    _patch(child)
            _patch(frame)
            # Also patch via the CTk internal attribute if it exists
            canvas = getattr(frame, "_parent_canvas", None)
            if canvas:
                try:
                    canvas.configure(bg=actual_bg)
                except Exception:
                    pass
        except Exception:
            pass

    def _clear_verse_history(self):
        engine.clear_verse_history()
        self._last_history_len = 0
        for w in self.history_scroll_frame.winfo_children():
            w.destroy()

    # ── FUZZY BOOK RESOLVER ──────────────────────────────────────────────────
    # Canonical list of all 66 Bible books (lowercase, with numbered variants)
    _ALL_BOOKS = [
        "genesis", "exodus", "leviticus", "numbers", "deuteronomy",
        "joshua", "judges", "ruth",
        "1 samuel", "2 samuel", "1 kings", "2 kings",
        "1 chronicles", "2 chronicles",
        "ezra", "nehemiah", "esther", "job", "psalms", "proverbs",
        "ecclesiastes", "song of solomon",
        "isaiah", "jeremiah", "lamentations", "ezekiel", "daniel",
        "hosea", "joel", "amos", "obadiah", "jonah", "micah",
        "nahum", "habakkuk", "zephaniah", "haggai", "zechariah", "malachi",
        "matthew", "mark", "luke", "john", "acts", "romans",
        "1 corinthians", "2 corinthians", "galatians", "ephesians",
        "philippians", "colossians",
        "1 thessalonians", "2 thessalonians",
        "1 timothy", "2 timothy", "titus", "philemon", "hebrews",
        "james", "1 peter", "2 peter",
        "1 john", "2 john", "3 john",
        "jude", "revelation",
    ]

    @classmethod
    def _resolve_book(cls, token: str) -> str | None:
        """Return the canonical book name for a prefix token, or None if ambiguous/unknown.

        Rules:
        - Numbered books: token "1pe" matches "1 peter" — strip the space for prefix matching.
        - A prefix matches if exactly ONE canonical book starts with it (case-insensitive).
        - Exact match always wins even if it is also a prefix of something longer.
        """
        t = token.lower().replace(" ", "")
        matches = []
        for book in cls._ALL_BOOKS:
            b = book.replace(" ", "")
            if b == t:
                # Exact match — return immediately
                return book
            if b.startswith(t):
                matches.append(book)
        if len(matches) == 1:
            return matches[0]
        return None  # 0 = unknown, 2+ = ambiguous

    def _send_manual_verse(self):
        """Parse the typed string (e.g. 'gen 3 2', 'josh 5:3', '1pe 3 8'),
        resolve the book via unique-prefix matching, update engine context,
        then send via Selenium."""
        raw = self.manual_verse_entry.get().strip()
        if not raw:
            return

        # ── 1. Normalise separators: colon → space, commas → space ──
        text = re.sub(r'[:\-,]', ' ', raw).lower()
        tokens = text.split()
        if not tokens:
            return

        # ── 2. Extract book token (may be "1 peter" style — consume leading digit) ──
        book_token = tokens[0]
        rest       = tokens[1:]
        if book_token.isdigit() and rest:
            # e.g. "1 pe 3 8" → book_token = "1pe", rest = ["3", "8"]
            book_token = book_token + rest[0]
            rest       = rest[1:]

        book = self._resolve_book(book_token)
        if not book:
            mb.showerror(
                "Unknown Book",
                f'"{book_token}" is ambiguous or not recognised.\n'
                f'Try a longer prefix, e.g. "jos" for Joshua, "joh" for John.'
            )
            return

        # Title-case the canonical name for display / Selenium
        book_display = book.title()

        # ── 3. Parse chapter and optional verse from remaining tokens ──
        nums = [t for t in rest if t.isdigit()]
        if not nums:
            mb.showerror("Missing Chapter", f"Please include a chapter number.\nExample: {book_display} 3")
            return

        chapter = nums[0]
        verse   = nums[1] if len(nums) >= 2 else None

        ref = f"{book_display} {chapter}" + (f":{verse}" if verse else "")

        # ── 4. Update engine context ──
        try:
            engine.set_context(book_display, chapter, verse or "")
        except Exception:
            pass

        # ── 5. Force chapter browser to reload ──
        self._chapter_browser_loaded = ""

        # ── 6. Send via Selenium ──
        ctrl = getattr(engine, "_controller", None)
        if not ctrl or not ctrl.driver:
            mb.showerror("Not Connected", "VerseView is not connected.\nStart the engine first.")
            return
        if not ctrl.box or not ctrl.btn:
            mb.showerror("Not Connected",
                         "Could not find the VerseView input or PRESENT button.\n"
                         "Check your VerseView URL.")
            return
        try:
            ctrl.driver.execute_script("arguments[0].value = arguments[1];", ctrl.box, ref)
            ctrl.driver.execute_script("arguments[0].click();", ctrl.btn)
            self._append_log(f"✏️ Manual verse sent: {ref}")
            self.manual_verse_entry.delete(0, "end")
        except Exception as e:
            mb.showerror("Send Error", f"Failed to send verse:\n{e}")

    def _update_chapter_browser_loop(self):
        """Poll engine context every 2s. When book+chapter changes, reload the panel."""
        try:
            book    = engine.current_book
            chapter = engine.current_chapter
            if book and chapter:
                key = f"{book} {chapter}"
                if key != self._chapter_browser_loaded:
                    self._chapter_browser_loaded = key
                    self.chapter_browser_frame.configure(
                        label_text=f"📖 {book} {chapter} Verses"
                    )
                    # Clear old buttons
                    for w in self.chapter_browser_frame.winfo_children():
                        w.destroy()
                    # Loading placeholder
                    ctk.CTkLabel(
                        self.chapter_browser_frame,
                        text="Loading...",
                        text_color=("gray50", "gray50"),
                        font=ctk.CTkFont(size=10),
                    ).pack(padx=4, pady=4)
                    # Fetch in background thread
                    def _load(b=book, c=chapter):
                        verses = engine.fetch_chapter_verses(b, c)
                        self.after(0, lambda: self._populate_chapter_browser(b, c, verses))
                    threading.Thread(target=_load, daemon=True).start()
        except Exception:
            pass
        finally:
            self.after(2000, self._update_chapter_browser_loop)

    def _populate_chapter_browser(self, book: str, chapter: str, verses: list):
        """Fill the chapter browser panel with one clickable ref per verse."""
        # Clear loading placeholder
        for w in self.chapter_browser_frame.winfo_children():
            w.destroy()
        if not verses:
            ctk.CTkLabel(
                self.chapter_browser_frame,
                text="No verses loaded.\nCheck translation.",
                text_color=("gray50", "gray50"),
                font=ctk.CTkFont(size=10),
            ).pack(padx=4, pady=4)
            return
        for v in verses:
            ref = f"{book} {chapter}:{v['num']}"
            btn = ctk.CTkButton(
                self.chapter_browser_frame,
                text=ref,
                anchor="w",
                fg_color="transparent",
                hover_color=("gray80", "gray25"),
                text_color=("gray10", "gray90"),
                font=ctk.CTkFont(size=10),
                height=22,
                command=lambda r=ref: self._send_chapter_verse(r),
            )
            btn.pack(fill="x", padx=2, pady=1)

    def _send_chapter_verse(self, ref: str):
        ctrl = getattr(engine, "_controller", None)
        if not ctrl or not ctrl.driver or not ctrl.box or not ctrl.btn:
            mb.showerror("Not Connected", "VerseView is not connected.")
            return
        try:
            ctrl.driver.execute_script("arguments[0].value = arguments[1];", ctrl.box, ref)
            ctrl.driver.execute_script("arguments[0].click();", ctrl.btn)
            self._append_log(f"📖 Chapter browser sent: {ref}")
            # Update engine context so the rest of detection stays in sync
            parts = ref.split()
            if len(parts) >= 2 and ":" in parts[-1]:
                book_ctx    = " ".join(parts[:-1])
                chap_ctx, v = parts[-1].split(":")
                try:
                    engine.set_context(book_ctx, chap_ctx, v)
                except Exception:
                    pass
        except Exception as e:
            mb.showerror("Send Error", f"Failed to send verse:\n{e}")

    def _open_verse_popup(self, ref: str):
        """Open a large popup showing the verse text for a history entry."""
        win = ctk.CTkToplevel(self)
        win.title(ref)
        win.geometry("520x340")
        win.resizable(True, True)
        win.attributes("-topmost", True)
        self.after(150, lambda: win.attributes("-topmost", False))

        textbox = ctk.CTkTextbox(win, font=("Segoe UI", 18), wrap="word")
        textbox.pack(fill="both", expand=True, padx=14, pady=(14, 6))
        textbox.insert("1.0", f"📖  {ref}\n\n(Loading verse text...)")
        textbox.configure(state="disabled")

        def _load_verse():
            text = engine.fetch_verse_text(ref)
            def _update():
                textbox.configure(state="normal")
                textbox.delete("1.0", "end")
                if text:
                    textbox.insert("1.0", f"📖  {ref}\n\n{text}")
                else:
                    textbox.insert("1.0", f"📖  {ref}\n\n(Verse text unavailable — check Bible translation setting)")
                textbox.configure(state="disabled")
            self.after(0, _update)

        threading.Thread(target=_load_verse, daemon=True).start()

        def _resend():
            ctrl = getattr(engine, "_controller", None)
            if ctrl:
                engine.deliver_verse(ref, ctrl, bypass_cooldown=True)
                self._append_log(f"🔁 Re-sent from history: {ref}")
            else:
                self._append_log(f"⚠️ Engine not running — cannot re-send {ref}")

        ctk.CTkButton(
            win, text="🔁 Send Again",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#2a7a2a", hover_color="#1f5c1f",
            command=_resend
        ).pack(pady=(0, 12))

    def _update_history_loop(self):
        try:
            hist = engine.get_verse_history()
            if len(hist) != self._last_history_len:
                if len(hist) == 0:
                    for w in self.history_scroll_frame.winfo_children():
                        w.destroy()
                    self._last_history_len = 0
                else:
                    new_items = hist[self._last_history_len:]
                    for item in new_items:
                        ref  = item["ref"]
                        lbl  = f"[{item['time']}] {ref}"
                        btn  = ctk.CTkButton(
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
                    self._last_history_len = len(hist)
        except Exception:
            pass
        finally:
            self.after(1000, self._update_history_loop)

    def on_closing(self):
        cfg.save(self._collect_settings())

        if self._running:
            # Engine is still live — stop it first, then finish closing once it settles
            engine._discord_live_log.set_close_message(
                "⚠️ App closed without Stop — auto-generated summary and log attached"
            )
            self._append_log("⚠️ App closed without Stop — stopping engine before closing...")
            self.lbl_status.configure(text="● Stopping...", text_color="#a07020")
            self.btn_stop.configure(state="disabled")
            self.btn_start.configure(state="disabled")
            self._closing = True   # flag so _on_stopped knows to finish the close
            engine.request_stop()
            # _on_stopped() will call _finish_close() once the engine thread ends
        else:
            self._finish_close()

    def _finish_close(self):
        """Called after the engine has fully stopped (or was already stopped)."""
        # Auto-save summary if needed
        if self.auto_save_var.get() and not self._notes_saved and engine.full_sermon_transcript and len(engine.full_sermon_transcript.strip()) > 100:
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


if __name__ == "__main__":
    app = VerseViewApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
