# -*- coding: utf-8 -*-
# ══════════════════════════════════════════════════════════════════════════════
#  DESIGN SYSTEM  —  single source of truth, shared across every tab/window
#
#  Established in Part 1 (was inline at the top of vv_gui.py); lifted into this
#  tiny dependency-free module in Part 2 so the Live Points tab
#  (live_points_app.py) and the main app (vv_gui.py) reference the EXACT same
#  constants instead of maintaining a second parallel style. There is no logic
#  here — only values — so importing it can never create a cycle.
#
#  Dark-mode-first: this app runs in dim sanctuary/control rooms. Color tuples
#  are (light, dark); the DARK value is the one that matters. The system is
#  intentionally small so the UI reads as one calm, purpose-built tool:
#    • ONE accent  → primary actions only (Start / Start Bot / Launch Display, Save)
#    • ONE danger  → destructive / stop actions (Stop, Emergency Quit, Clear)
#    • warn / toggle → attention + active-mode states
#    • neutral grays → everything else
# ══════════════════════════════════════════════════════════════════════════════

# ── Semantic action colors ──
COL_ACCENT        = "#3a72d8"   # PRIMARY actions only
COL_ACCENT_HOVER  = "#2c5aad"
COL_DANGER        = "#c9483d"   # DESTRUCTIVE / stop actions
COL_DANGER_HOVER  = "#a5382f"
COL_DANGER_TINT   = ("#f3d9d6", "#3a1e1c")   # faint hover wash for guarded/outlined danger
COL_WARN          = "#c6891e"   # ATTENTION (update available, generate notes, "ready")
COL_WARN_HOVER    = "#a06f13"
COL_TOGGLE        = "#7358c4"   # ACTIVE mode toggles (Worship, Pin, Set Context)
COL_TOGGLE_HOVER  = "#5a439c"
COL_OK            = "#3aa76d"   # running / healthy status

# ── Neutral surfaces & text (dark-primary) ──
COL_CARD          = ("#ececee", "#242429")   # grouped-section / cluster card bg
COL_CARD_BORDER   = ("#dadadf", "#34343d")
COL_INSET         = ("#e6e6e9", "#1b1b20")   # sunken areas (log/transcript panes, editors)
COL_DIVIDER       = ("#c6c6cd", "#3a3a44")
COL_TEXT          = ("gray10", "gray92")     # primary text
COL_TEXT_MUTED    = ("gray38", "gray62")     # labels / section headers
COL_TEXT_FAINT    = ("gray50", "gray52")     # hints / captions
COL_BTN_BORDER    = ("gray70", "gray38")     # neutral outlined button
COL_BTN_TEXT      = ("gray25", "gray78")
COL_BTN_HOVER     = ("gray85", "gray28")

# ── Typography tiers (point sizes; weight passed to CTkFont) ──
FS_TITLE   = 15   # tab / panel titles
FS_SECTION = 12   # section headers within a panel
FS_LABEL   = 12   # field labels
FS_BODY    = 12   # checkbox / body text
FS_SMALL   = 11   # status / helper text
FS_TINY    = 10   # captions / badges / version

# ── Spacing rhythm (px) — use these instead of ad-hoc padx/pady ──
PAD_XS = 2
PAD_S  = 4    # tight   — within a row / between checkbox lines
PAD_M  = 8    # normal  — inside a card, between controls
PAD_L  = 14   # loose   — between grouped sections
PAD_XL = 20

__all__ = [
    "COL_ACCENT", "COL_ACCENT_HOVER", "COL_DANGER", "COL_DANGER_HOVER", "COL_DANGER_TINT",
    "COL_WARN", "COL_WARN_HOVER", "COL_TOGGLE", "COL_TOGGLE_HOVER", "COL_OK",
    "COL_CARD", "COL_CARD_BORDER", "COL_INSET", "COL_DIVIDER",
    "COL_TEXT", "COL_TEXT_MUTED", "COL_TEXT_FAINT",
    "COL_BTN_BORDER", "COL_BTN_TEXT", "COL_BTN_HOVER",
    "FS_TITLE", "FS_SECTION", "FS_LABEL", "FS_BODY", "FS_SMALL", "FS_TINY",
    "PAD_XS", "PAD_S", "PAD_M", "PAD_L", "PAD_XL",
]
