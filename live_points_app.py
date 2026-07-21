# -*- coding: utf-8 -*-
import customtkinter as ctk

# Shared design system (same constants the main tab uses — one cohesive style).
from ui_theme import (
    COL_ACCENT, COL_ACCENT_HOVER, COL_DANGER, COL_DANGER_HOVER,
    COL_CARD, COL_CARD_BORDER, COL_INSET,
    COL_TEXT, COL_TEXT_MUTED, COL_TEXT_FAINT,
    FS_SECTION, FS_LABEL, FS_BODY, FS_SMALL,
    PAD_S, PAD_M, PAD_L,
)


class LiveDisplayWindow(ctk.CTkToplevel):
    """ Secondary borderless window to display the live main points. """
    def __init__(self, parent, monitor_offset_x=0):
        super().__init__(parent)
        self.title("Live Sermon Points")
        self.geometry(f"1280x720+{monitor_offset_x}+0")
        self.attributes("-fullscreen", True)
        self.configure(fg_color="#0d0d0d")
        self.bind("<Escape>", lambda e: self.destroy())
        self.content_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=48, weight="bold"),
            text_color="#e0e0e0",
            justify="left",
            anchor="nw",
            wraplength=1600
        )
        self.content_label.pack(fill="both", expand=True, padx=80, pady=80)
        self.bind("<Configure>", self._resize_wraplength)

    def _resize_wraplength(self, event):
        self.content_label.configure(wraplength=self.winfo_width() - 160)

    def update_text(self, new_text):
        self.content_label.configure(text=new_text)


class LivePointsController:
    """ Manages the UI and logic for the Live Points tab """
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self.display_win = None
        self._build_tab()

    def _build_tab(self):
        self.parent.grid_columnconfigure(0, weight=1)
        self.parent.grid_rowconfigure(4, weight=2)

        # ── Controls card ─────────────────────────────────────────────────────
        # Groups the primary action + its options into one calm block instead of
        # a flat row of mismatched widgets.
        controls = ctk.CTkFrame(self.parent, fg_color=COL_CARD, corner_radius=10,
                                border_width=1, border_color=COL_CARD_BORDER)
        controls.grid(row=0, column=0, padx=PAD_L, pady=(PAD_L, PAD_M), sticky="ew")

        control_row = ctk.CTkFrame(controls, fg_color="transparent")
        control_row.pack(fill="x", padx=PAD_M, pady=(PAD_M, PAD_S))

        self.btn_launch_display = ctk.CTkButton(
            control_row, text="🖥️  Launch Audience Display", width=210, height=36,
            fg_color=COL_ACCENT, hover_color=COL_ACCENT_HOVER,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._toggle_audience_display
        )
        self.btn_launch_display.pack(side="left", padx=(0, PAD_L))

        # Toggle: only run AI Live Outline when explicitly enabled (saves Groq tokens)
        self.live_llm_enabled = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            control_row,
            text="Enable AI Live Outline (tokens)",
            variable=self.live_llm_enabled,
            font=ctk.CTkFont(size=FS_BODY), text_color=COL_TEXT,
            checkbox_width=20, checkbox_height=20,
        ).pack(side="left", padx=(0, PAD_L))

        # Display Monitor selector
        ctk.CTkLabel(
            control_row, text="Monitor:",
            font=ctk.CTkFont(size=FS_LABEL), text_color=COL_TEXT
        ).pack(side="left", padx=(0, PAD_S))

        self.screen_var = ctk.StringVar(value="Display 2 (Right/Extended)")
        ctk.CTkOptionMenu(
            control_row,
            variable=self.screen_var,
            values=["Display 1 (Primary)", "Display 2 (Right/Extended)", "Windowed (Test Mode)"],
            width=210
        ).pack(side="left")

        ctk.CTkLabel(
            controls,
            text="Start the main Engine in the VerseView tab to begin transcribing.",
            text_color=COL_TEXT_FAINT, anchor="w",
            font=ctk.CTkFont(size=FS_SMALL, slant="italic")
        ).pack(fill="x", padx=PAD_M, pady=(0, PAD_M))

        # ── AI Prompt Configuration ───────────────────────────────────────────
        ctk.CTkLabel(
            self.parent, text="⚙️  AI Behavior Prompt (Instructions for Groq LLM)",
            anchor="w", font=ctk.CTkFont(size=FS_SECTION, weight="bold"),
            text_color=COL_TEXT_MUTED
        ).grid(row=1, column=0, padx=PAD_L, pady=(PAD_S, PAD_S), sticky="w")

        self.prompt_box = ctk.CTkTextbox(
            self.parent, height=120, font=("Segoe UI", 13), wrap="word",
            fg_color=COL_INSET, corner_radius=8,
            border_width=1, border_color=COL_CARD_BORDER,
        )
        self.prompt_box.grid(row=2, column=0, padx=PAD_L, pady=(0, PAD_M), sticky="ew")

        # ── Live Output Preview ───────────────────────────────────────────────
        ctk.CTkLabel(
            self.parent, text="👁️  Live Display Preview",
            anchor="w", font=ctk.CTkFont(size=FS_SECTION, weight="bold"),
            text_color=COL_TEXT_MUTED
        ).grid(row=3, column=0, padx=PAD_L, pady=(PAD_S, PAD_S), sticky="w")

        self.preview_box = ctk.CTkTextbox(
            self.parent,
            font=("Segoe UI", 16, "bold"),
            wrap="word",
            fg_color=COL_INSET,
            text_color=COL_TEXT,
            corner_radius=8,
            border_width=1, border_color=COL_CARD_BORDER,
        )
        self.preview_box.grid(row=4, column=0, padx=PAD_L, pady=(0, PAD_L), sticky="nsew")
        self.preview_box.insert(
            "1.0",
            "When the engine is running, the generated points will appear here and on the audience display..."
        )
        # preview_box is intentionally editable so operators can fix points in real time

    # ── Audience Display ──
    def _toggle_audience_display(self):
        if self.display_win is None or not self.display_win.winfo_exists():
            selection = self.screen_var.get()
            offset_x = 0
            if "Display 2" in selection:
                offset_x = 1920
            self.display_win = LiveDisplayWindow(
                self.parent.winfo_toplevel(), monitor_offset_x=offset_x
            )
            if "Windowed" in selection:
                self.display_win.attributes("-fullscreen", False)
                self.display_win.geometry("800x600")
            self.btn_launch_display.configure(
                text="🖥️  Close Audience Display",
                fg_color=COL_DANGER, hover_color=COL_DANGER_HOVER
            )
            self.update_live_points("")
            self.display_win.bind("<Destroy>", lambda e: self._reset_display_button())
        else:
            self.display_win.destroy()
            self._reset_display_button()

    def _reset_display_button(self):
        self.display_win = None
        self.btn_launch_display.configure(
            text="🖥️  Launch Audience Display",
            fg_color=COL_ACCENT, hover_color=COL_ACCENT_HOVER
        )

    # ── Live Points Update ──
    def update_live_points(self, text):
        def _update():
            self.preview_box.delete("1.0", "end")
            self.preview_box.insert("1.0", text)
            if self.display_win and self.display_win.winfo_exists():
                self.display_win.update_text(text)
        self.parent.after(0, _update)

    # ── Getters / Setters ──
    def get_prompt(self):
        return self.prompt_box.get("1.0", "end-1c")

    def set_prompt(self, text):
        self.prompt_box.delete("1.0", "end")
        self.prompt_box.insert("1.0", text)

    def get_screen(self):
        return self.screen_var.get()

    def set_screen(self, value):
        self.screen_var.set(value)

    def get_current_display(self):
        """Returns current preview box content including any manual edits."""
        return self.preview_box.get("1.0", "end-1c")

    def is_live_llm_enabled(self):
        """Whether the AI Live Outline LLM should run for this service."""
        return bool(self.live_llm_enabled.get())

    def get_live_llm_enabled(self):
        """Alias for is_live_llm_enabled() (used by _collect_settings)."""
        return self.is_live_llm_enabled()

    def set_live_llm_enabled(self, value: bool):
        self.live_llm_enabled.set(bool(value))
