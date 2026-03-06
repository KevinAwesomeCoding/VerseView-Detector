# -*- coding: utf-8 -*-
import customtkinter as ctk

class LiveDisplayWindow(ctk.CTkToplevel):
    """ Secondary borderless window to display the live main points. """
    def __init__(self, parent, monitor_offset_x=0):
        super().__init__(parent)
        self.title("Live Sermon Points")
        
        # Move to selected monitor and fullscreen
        self.geometry(f"1280x720+{monitor_offset_x}+0")
        self.attributes("-fullscreen", True)
        self.configure(fg_color="#0d0d0d")  # Deep black background

        # Press Escape to exit fullscreen/close
        self.bind("<Escape>", lambda e: self.destroy())

        # Main text display
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

        # Top Controls
        top_bar = ctk.CTkFrame(self.parent, fg_color="transparent")
        top_bar.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.btn_launch_display = ctk.CTkButton(
            top_bar, text="🖥️ Launch Audience Display", width=200, height=36,
            fg_color="#1a5a8a", hover_color="#144a72",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._toggle_audience_display
        )
        self.btn_launch_display.pack(side="left", padx=(0, 10))
        
        ctk.CTkLabel(
            top_bar, text="Note: Start the main Engine in VerseView tab to begin transcribing.",
            text_color="gray50", font=ctk.CTkFont(size=12, slant="italic")
        ).pack(side="left", padx=10)

        # ── Display Monitor selector (moved here from Settings panel) ──
        ctk.CTkLabel(
            top_bar, text="Monitor:",
            font=ctk.CTkFont(size=13)
        ).pack(side="left", padx=(20, 4))

        self.screen_var = ctk.StringVar(value="Display 2 (Right/Extended)")
        ctk.CTkOptionMenu(
            top_bar,
            variable=self.screen_var,
            values=["Display 1 (Primary)", "Display 2 (Right/Extended)", "Windowed (Test Mode)"],
            width=220
        ).pack(side="left", padx=(0, 10))

        # AI Prompt Configuration
        ctk.CTkLabel(
            self.parent, text="⚙️ AI Behavior Prompt (Instructions for Groq LLM)", 
            anchor="w", font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=1, column=0, padx=10, pady=(10, 0), sticky="w")

        self.prompt_box = ctk.CTkTextbox(self.parent, height=120, font=("Segoe UI", 13), wrap="word")
        self.prompt_box.grid(row=2, column=0, padx=10, pady=(5, 15), sticky="ew")

        # Live Output Preview
        ctk.CTkLabel(
            self.parent, text="👁️ Live Display Preview", 
            anchor="w", font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=3, column=0, padx=10, pady=(5, 0), sticky="w")

        self.preview_box = ctk.CTkTextbox(self.parent, font=("Segoe UI", 16, "bold"), wrap="word", fg_color="#1c1c1c", text_color="#d0d0d0")
        self.preview_box.grid(row=4, column=0, padx=10, pady=(5, 10), sticky="nsew")
        self.preview_box.insert("1.0", "When the engine is running, the generated points will appear here and on the audience display...")

    def _toggle_audience_display(self):
        if self.display_win is None or not self.display_win.winfo_exists():
            selection = self.screen_var.get()
            
            offset_x = 0
            if "Display 2" in selection:
                offset_x = 1920 

            self.display_win = LiveDisplayWindow(self.parent.winfo_toplevel(), monitor_offset_x=offset_x)
            
            if "Windowed" in selection:
                self.display_win.attributes("-fullscreen", False)
                self.display_win.geometry("800x600")

            self.btn_launch_display.configure(text="🖥️ Close Audience Display", fg_color="#a02020", hover_color="#801010")
            self.update_live_points("")
            
            self.display_win.bind("<Destroy>", lambda e: self._reset_display_button())
        else:
            self.display_win.destroy()
            self._reset_display_button()

    def _reset_display_button(self):
        self.display_win = None
        self.btn_launch_display.configure(text="🖥️ Launch Audience Display", fg_color="#1a5a8a", hover_color="#144a72")

    def update_live_points(self, text):
        def _update():
            self.preview_box.delete("1.0", "end")
            self.preview_box.insert("1.0", text)
            
            if self.display_win and self.display_win.winfo_exists():
                self.display_win.update_text(text)
                
        self.parent.after(0, _update)

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