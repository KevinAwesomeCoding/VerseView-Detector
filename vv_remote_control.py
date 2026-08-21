# -*- coding: utf-8 -*-
"""
vv_remote_control.py — Version-aware VerseVIEW 10 / 11 remote control layer.

Provides a single facade (`VVRemoteControl`) that the rest of the app calls to
drive the VerseVIEW presentation software via its control.html Selenium session.
Internally it detects the VerseVIEW version from the page title and delegates to
version-specific adapters for elements that differ between V10 and V11, while
sharing a common implementation for the many elements that are identical.

Architecture
~~~~~~~~~~~~
    VVRemoteControl (facade)
        ├── VersionDetector      — reads <title>, returns version tag
        ├── VVSharedActions      — Bible tab, songs search/lyrics, presentation bar
        ├── VerseView10Adapter   — V10-only: schedule, bookmark, two-line checkboxes
        └── VerseView11Adapter   — V11-only: events, custom tab, song-to-event, theme

Design rules
~~~~~~~~~~~~
* ID-based selectors only (no CSS-class or positional selectors).
* Unsupported actions log a clear message and return safely — never raise.
* If version is 'unknown', *all* DOM operations are refused.
* Every V10 code path remains intact when V10 is detected.
"""

import re
import logging

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Version constants
# ──────────────────────────────────────────────────────────────────────────────
VERSION_V10     = "verseview10"
VERSION_V11     = "verseview11"
VERSION_UNKNOWN = "unknown"

_TITLE_PATTERN = re.compile(r"VerseVIEW Remote (\d+)\.\d+\.\d+")


# ══════════════════════════════════════════════════════════════════════════════
#  VERSION DETECTOR
# ══════════════════════════════════════════════════════════════════════════════

class VersionDetector:
    """Detect the VerseVIEW version from the browser page title.

    Primary signal:  ``<title>VerseVIEW Remote X.Y.Z</title>``
    Secondary check: presence of ``#themeToggle`` (V11 only).
    """

    @staticmethod
    def detect(driver) -> str:
        """Return VERSION_V10, VERSION_V11, or VERSION_UNKNOWN.

        Parameters
        ----------
        driver : selenium.webdriver.Chrome
            A live Selenium driver that has already loaded the control page.
        """
        title = ""
        try:
            title = driver.title or ""
        except Exception as exc:
            logger.error(f"[VersionDetector] Could not read page title: {exc}")
            return VERSION_UNKNOWN

        match = _TITLE_PATTERN.search(title)
        if not match:
            logger.warning(
                f"[VersionDetector] Title does not match expected pattern. "
                f"Title was: \"{title}\""
            )
            return VERSION_UNKNOWN

        major = int(match.group(1))

        if major == 10:
            version = VERSION_V10
        elif major == 11:
            version = VERSION_V11
        else:
            logger.warning(
                f"[VersionDetector] Unrecognised major version {major} "
                f"(title: \"{title}\"). Treating as unknown."
            )
            return VERSION_UNKNOWN

        # Secondary confirmation: #themeToggle exists only in V11
        try:
            from selenium.webdriver.common.by import By
            has_theme_toggle = bool(driver.find_elements(By.ID, "themeToggle"))
        except Exception:
            has_theme_toggle = False

        if version == VERSION_V11 and not has_theme_toggle:
            logger.warning(
                "[VersionDetector] Title says V11 but #themeToggle not found. "
                "Proceeding as V11 anyway (title is authoritative)."
            )
        elif version == VERSION_V10 and has_theme_toggle:
            logger.warning(
                "[VersionDetector] Title says V10 but #themeToggle IS present. "
                "Proceeding as V10 anyway (title is authoritative)."
            )

        logger.info(f"✅ [VersionDetector] Detected VerseVIEW version: {version} (title: \"{title}\")")
        return version


# ══════════════════════════════════════════════════════════════════════════════
#  SHARED ACTIONS (identical in V10 and V11)
# ══════════════════════════════════════════════════════════════════════════════

class VVSharedActions:
    """Operations on elements whose IDs and onclick handlers are the same in
    both VerseVIEW 10 and VerseVIEW 11.

    All methods accept a live Selenium ``driver`` and work exclusively through
    ID-based selectors.
    """

    # ── Bible Tab ─────────────────────────────────────────────────────────────

    @staticmethod
    def set_reference(driver, ref: str) -> bool:
        """Set the value of the Bible reference input (#remotebibleRefID)."""
        try:
            from selenium.webdriver.common.by import By
            box = driver.find_element(By.ID, "remotebibleRefID")
            driver.execute_script("arguments[0].value = arguments[1];", box, ref)
            return True
        except Exception as exc:
            logger.error(f"[Shared] set_reference failed: {exc}")
            return False

    @staticmethod
    def get_verses(driver) -> bool:
        """Click the 'Get Chapter' button (#remotebibleget → getVerses)."""
        try:
            from selenium.webdriver.common.by import By
            btn = driver.find_element(By.ID, "remotebibleget")
            driver.execute_script("arguments[0].click();", btn)
            logger.debug("[Shared] get_verses clicked")
            return True
        except Exception as exc:
            logger.error(f"[Shared] get_verses failed: {exc}")
            return False

    @staticmethod
    def present_verse(driver) -> bool:
        """Click the PRESENT button (#remotebiblepresent → getBibleRef)."""
        try:
            from selenium.webdriver.common.by import By
            btn = driver.find_element(By.ID, "remotebiblepresent")
            driver.execute_script("arguments[0].click();", btn)
            logger.debug("[Shared] present_verse clicked")
            return True
        except Exception as exc:
            logger.error(f"[Shared] present_verse failed: {exc}")
            return False

    @staticmethod
    def show_verse(driver, ref: str) -> bool:
        """Set reference + click PRESENT in one call."""
        if not VVSharedActions.set_reference(driver, ref):
            return False
        return VVSharedActions.present_verse(driver)

    # ── Presentation Control Bar ──────────────────────────────────────────────

    @staticmethod
    def blank_presentation(driver) -> bool:
        """Click the blank button (#iconBlank → blankPresentWindow)."""
        return _click_by_id(driver, "iconBlank", "blank_presentation")

    @staticmethod
    def logo_presentation(driver) -> bool:
        """Click the logo button (#iconLogo → logoPresentWindow)."""
        return _click_by_id(driver, "iconLogo", "logo_presentation")

    @staticmethod
    def close_presentation(driver) -> bool:
        """Click the close button (#iconClose → closePresentWindow)."""
        return _click_by_id(driver, "iconClose", "close_presentation")

    @staticmethod
    def prev_slide(driver) -> bool:
        """Click the previous button (#iconPrev → getPrevBibleRef)."""
        return _click_by_id(driver, "iconPrev", "prev_slide")

    @staticmethod
    def next_slide(driver) -> bool:
        """Click the next button (#iconNext → getNextBibleRef)."""
        return _click_by_id(driver, "iconNext", "next_slide")

    # ── Songs Tab (shared part) ───────────────────────────────────────────────

    @staticmethod
    def search_songs(driver, query: str) -> bool:
        """Set the song search input (#remotesongSearchID) and click search
        (#remotesongsearch → getSongList)."""
        try:
            from selenium.webdriver.common.by import By
            inp = driver.find_element(By.ID, "remotesongSearchID")
            driver.execute_script("arguments[0].value = arguments[1];", inp, query)
            btn = driver.find_element(By.ID, "remotesongsearch")
            driver.execute_script("arguments[0].click();", btn)
            logger.debug(f"[Shared] search_songs: \"{query}\"")
            return True
        except Exception as exc:
            logger.error(f"[Shared] search_songs failed: {exc}")
            return False

    @staticmethod
    def get_song_lyrics(driver) -> bool:
        """Click the get-lyrics button (#remotesongget → getSongContent)."""
        return _click_by_id(driver, "remotesongget", "get_song_lyrics")

    @staticmethod
    def get_selected_song(driver) -> str:
        """Read the current value from #songID select."""
        try:
            from selenium.webdriver.common.by import By
            sel = driver.find_element(By.ID, "songID")
            return driver.execute_script("return arguments[0].value;", sel) or ""
        except Exception as exc:
            logger.error(f"[Shared] get_selected_song failed: {exc}")
            return ""

    @staticmethod
    def set_selected_song(driver, value: str) -> bool:
        """Set the value of #songID select."""
        try:
            from selenium.webdriver.common.by import By
            sel = driver.find_element(By.ID, "songID")
            driver.execute_script("arguments[0].value = arguments[1];", sel, value)
            return True
        except Exception as exc:
            logger.error(f"[Shared] set_selected_song failed: {exc}")
            return False

    # ── Tab switching ─────────────────────────────────────────────────────────

    @staticmethod
    def switch_to_bible_tab(driver) -> bool:
        return _click_by_id(driver, "bible-tab", "switch_to_bible_tab")

    @staticmethod
    def switch_to_songs_tab(driver) -> bool:
        return _click_by_id(driver, "songs-tab", "switch_to_songs_tab")

    @staticmethod
    def switch_to_schedule_tab(driver) -> bool:
        """Works for both V10 (Schedule) and V11 (Events) — same tab ID."""
        return _click_by_id(driver, "schedule-tab", "switch_to_schedule_tab")


# ══════════════════════════════════════════════════════════════════════════════
#  VERSEVIEW 10 ADAPTER (V10-only elements)
# ══════════════════════════════════════════════════════════════════════════════

class VerseView10Adapter:
    """Handles elements that exist ONLY in VerseVIEW 10.

    Must not be called when the detected version is V11 — those IDs will not
    exist in the DOM.
    """

    # ── Schedule Tab (V10) ────────────────────────────────────────────────────

    @staticmethod
    def get_schedule_items(driver) -> bool:
        """Click the schedule-get button (#remoteschget → getSch)."""
        return _click_by_id(driver, "remoteschget", "get_schedule_items [V10]")

    @staticmethod
    def present_schedule_item(driver) -> bool:
        """Click the schedule-present button (#remoteschpresent → getSchContent)."""
        return _click_by_id(driver, "remoteschpresent", "present_schedule_item [V10]")

    @staticmethod
    def get_selected_schedule(driver) -> str:
        """Read the current value of the schedule dropdown (#schID)."""
        try:
            from selenium.webdriver.common.by import By
            sel = driver.find_element(By.ID, "schID")
            return driver.execute_script("return arguments[0].value;", sel) or ""
        except Exception as exc:
            logger.error(f"[V10] get_selected_schedule failed: {exc}")
            return ""

    @staticmethod
    def set_selected_schedule(driver, value: str) -> bool:
        """Set the value of the schedule dropdown (#schID)."""
        try:
            from selenium.webdriver.common.by import By
            sel = driver.find_element(By.ID, "schID")
            driver.execute_script("arguments[0].value = arguments[1];", sel, value)
            return True
        except Exception as exc:
            logger.error(f"[V10] set_selected_schedule failed: {exc}")
            return False

    # ── Song Bookmark (V10 only) ──────────────────────────────────────────────

    @staticmethod
    def set_song_bookmark(driver) -> bool:
        """Click the bookmark button (#remotesongbookmark → setSongBookmark)."""
        return _click_by_id(driver, "remotesongbookmark", "set_song_bookmark [V10]")

    # ── Two-Line Presentation Checkboxes (V10 only) ───────────────────────────

    @staticmethod
    def get_two_line_present(driver) -> bool:
        """Read the checked state of #twoLinePresent."""
        try:
            from selenium.webdriver.common.by import By
            cb = driver.find_element(By.ID, "twoLinePresent")
            return driver.execute_script("return arguments[0].checked;", cb) or False
        except Exception as exc:
            logger.error(f"[V10] get_two_line_present failed: {exc}")
            return False

    @staticmethod
    def set_two_line_present(driver, checked: bool) -> bool:
        """Set the checked state of #twoLinePresent."""
        try:
            from selenium.webdriver.common.by import By
            cb = driver.find_element(By.ID, "twoLinePresent")
            driver.execute_script("arguments[0].checked = arguments[1];", cb, checked)
            return True
        except Exception as exc:
            logger.error(f"[V10] set_two_line_present failed: {exc}")
            return False

    @staticmethod
    def get_two_line_present2(driver) -> bool:
        """Read the checked state of #twoLinePresent2."""
        try:
            from selenium.webdriver.common.by import By
            cb = driver.find_element(By.ID, "twoLinePresent2")
            return driver.execute_script("return arguments[0].checked;", cb) or False
        except Exception as exc:
            logger.error(f"[V10] get_two_line_present2 failed: {exc}")
            return False

    @staticmethod
    def set_two_line_present2(driver, checked: bool) -> bool:
        """Set the checked state of #twoLinePresent2."""
        try:
            from selenium.webdriver.common.by import By
            cb = driver.find_element(By.ID, "twoLinePresent2")
            driver.execute_script("arguments[0].checked = arguments[1];", cb, checked)
            return True
        except Exception as exc:
            logger.error(f"[V10] set_two_line_present2 failed: {exc}")
            return False


# ══════════════════════════════════════════════════════════════════════════════
#  VERSEVIEW 11 ADAPTER (V11-only elements)
# ══════════════════════════════════════════════════════════════════════════════

class VerseView11Adapter:
    """Handles elements that exist ONLY in VerseVIEW 11.

    Must not be called when the detected version is V10 — those IDs will not
    exist in the DOM.
    """

    # ── Events Tab (V11 — replaces V10 Schedule Tab) ──────────────────────────

    @staticmethod
    def refresh_events_list(driver) -> bool:
        """Click the events-refresh button (#remoteschrefresh → getSchEventsList)."""
        return _click_by_id(driver, "remoteschrefresh", "refresh_events_list [V11]")

    @staticmethod
    def get_selected_event(driver) -> str:
        """Read the current value of the events dropdown (#schEventSelID)."""
        try:
            from selenium.webdriver.common.by import By
            sel = driver.find_element(By.ID, "schEventSelID")
            return driver.execute_script("return arguments[0].value;", sel) or ""
        except Exception as exc:
            logger.error(f"[V11] get_selected_event failed: {exc}")
            return ""

    @staticmethod
    def set_selected_event(driver, value: str) -> bool:
        """Set the value of the events dropdown (#schEventSelID) and trigger
        the onchange handler (loadSchEvent)."""
        try:
            from selenium.webdriver.common.by import By
            sel = driver.find_element(By.ID, "schEventSelID")
            driver.execute_script(
                "arguments[0].value = arguments[1]; "
                "if (typeof loadSchEvent === 'function') loadSchEvent();",
                sel, value
            )
            logger.debug(f"[V11] set_selected_event: {value}")
            return True
        except Exception as exc:
            logger.error(f"[V11] set_selected_event failed: {exc}")
            return False

    @staticmethod
    def get_event_items_html(driver) -> str:
        """Read the innerHTML of the event-items container (#schItemsID)."""
        try:
            from selenium.webdriver.common.by import By
            container = driver.find_element(By.ID, "schItemsID")
            return driver.execute_script("return arguments[0].innerHTML;", container) or ""
        except Exception as exc:
            logger.error(f"[V11] get_event_items_html failed: {exc}")
            return ""

    # ── Custom Tab (V11 only) ─────────────────────────────────────────────────

    @staticmethod
    def switch_to_custom_tab(driver) -> bool:
        """Switch to the Custom tab (#custom-tab) — V11 only."""
        return _click_by_id(driver, "custom-tab", "switch_to_custom_tab [V11]")

    @staticmethod
    def set_custom_title(driver, title: str) -> bool:
        """Set the custom title input (#customTitleID)."""
        try:
            from selenium.webdriver.common.by import By
            inp = driver.find_element(By.ID, "customTitleID")
            driver.execute_script("arguments[0].value = arguments[1];", inp, title)
            return True
        except Exception as exc:
            logger.error(f"[V11] set_custom_title failed: {exc}")
            return False

    @staticmethod
    def set_custom_text(driver, text: str) -> bool:
        """Set the custom text input (#customTextID)."""
        try:
            from selenium.webdriver.common.by import By
            inp = driver.find_element(By.ID, "customTextID")
            driver.execute_script("arguments[0].value = arguments[1];", inp, text)
            return True
        except Exception as exc:
            logger.error(f"[V11] set_custom_text failed: {exc}")
            return False

    @staticmethod
    def refresh_custom_events(driver) -> bool:
        """Click the custom-events refresh button (#remotecustomrefresh)."""
        return _click_by_id(driver, "remotecustomrefresh", "refresh_custom_events [V11]")

    @staticmethod
    def get_selected_custom_event(driver) -> str:
        """Read the current value of #customEventSelID."""
        try:
            from selenium.webdriver.common.by import By
            sel = driver.find_element(By.ID, "customEventSelID")
            return driver.execute_script("return arguments[0].value;", sel) or ""
        except Exception as exc:
            logger.error(f"[V11] get_selected_custom_event failed: {exc}")
            return ""

    @staticmethod
    def set_selected_custom_event(driver, value: str) -> bool:
        """Set the value of #customEventSelID."""
        try:
            from selenium.webdriver.common.by import By
            sel = driver.find_element(By.ID, "customEventSelID")
            driver.execute_script("arguments[0].value = arguments[1];", sel, value)
            return True
        except Exception as exc:
            logger.error(f"[V11] set_selected_custom_event failed: {exc}")
            return False

    @staticmethod
    def add_custom_to_schedule(driver) -> bool:
        """Click the add-custom button (#remotecustomadd → addCustomToSchedule)."""
        return _click_by_id(driver, "remotecustomadd", "add_custom_to_schedule [V11]")

    # ── Song-to-Event Scheduling (V11 only) ───────────────────────────────────

    @staticmethod
    def refresh_song_events(driver) -> bool:
        """Click the song-events refresh button (#remoteeventrefresh → getEventsList)."""
        return _click_by_id(driver, "remoteeventrefresh", "refresh_song_events [V11]")

    @staticmethod
    def get_selected_song_event(driver) -> str:
        """Read the current value of #eventSelID."""
        try:
            from selenium.webdriver.common.by import By
            sel = driver.find_element(By.ID, "eventSelID")
            return driver.execute_script("return arguments[0].value;", sel) or ""
        except Exception as exc:
            logger.error(f"[V11] get_selected_song_event failed: {exc}")
            return ""

    @staticmethod
    def set_selected_song_event(driver, value: str) -> bool:
        """Set the value of #eventSelID."""
        try:
            from selenium.webdriver.common.by import By
            sel = driver.find_element(By.ID, "eventSelID")
            driver.execute_script("arguments[0].value = arguments[1];", sel, value)
            return True
        except Exception as exc:
            logger.error(f"[V11] set_selected_song_event failed: {exc}")
            return False

    @staticmethod
    def schedule_song_to_event(driver) -> bool:
        """Click the song-to-event button (#remotesongtoevent → scheduleSongToEvent)."""
        return _click_by_id(driver, "remotesongtoevent", "schedule_song_to_event [V11]")

    # ── Theme Toggle (V11 only) ───────────────────────────────────────────────

    @staticmethod
    def toggle_theme(driver) -> bool:
        """Click the theme toggle (#themeToggle → toggleTheme)."""
        return _click_by_id(driver, "themeToggle", "toggle_theme [V11]")

    @staticmethod
    def get_current_theme(driver) -> str:
        """Read the current theme from <html data-theme='…'>."""
        try:
            return driver.execute_script(
                "return document.documentElement.getAttribute('data-theme') || '';"
            ) or ""
        except Exception as exc:
            logger.error(f"[V11] get_current_theme failed: {exc}")
            return ""


# ══════════════════════════════════════════════════════════════════════════════
#  FACADE — Single dispatcher for the rest of the app
# ══════════════════════════════════════════════════════════════════════════════

class VVRemoteControl:
    """Unified remote-control facade.

    Instantiate once with a Selenium driver after the page loads, call
    ``detect_version()`` to determine V10/V11/unknown, then use the public
    methods to drive the VerseVIEW UI.  Version-specific actions are routed
    to the correct adapter automatically; calling an action that doesn't exist
    for the detected version logs a warning and returns safely.

    Usage::

        rc = VVRemoteControl(driver)
        rc.detect_version()
        rc.show_verse("John 3:16")
        rc.next_slide()
        rc.get_schedule_or_events()  # auto-selects V10 or V11 path
    """

    def __init__(self, driver):
        self.driver = driver
        self.version: str = VERSION_UNKNOWN
        self._v10 = VerseView10Adapter()
        self._v11 = VerseView11Adapter()

    # ── Version Detection ─────────────────────────────────────────────────────

    def detect_version(self) -> str:
        """Run version detection and store the result.  Returns the version tag."""
        self.version = VersionDetector.detect(self.driver)
        return self.version

    @property
    def is_v10(self) -> bool:
        return self.version == VERSION_V10

    @property
    def is_v11(self) -> bool:
        return self.version == VERSION_V11

    @property
    def is_known(self) -> bool:
        return self.version in (VERSION_V10, VERSION_V11)

    # ── Guard ─────────────────────────────────────────────────────────────────

    def _guard(self, action: str) -> bool:
        """Return True if it's safe to proceed, False if version is unknown."""
        if not self.is_known:
            logger.warning(
                f"[VVRemoteControl] {action}: refused — version is '{self.version}'. "
                f"No DOM interaction will be attempted."
            )
            return False
        return True

    def _guard_v10(self, action: str) -> bool:
        """Return True if current version is V10."""
        if not self._guard(action):
            return False
        if not self.is_v10:
            logger.info(f"[VVRemoteControl] {action}: not supported on {self.version} — no-op")
            return False
        return True

    def _guard_v11(self, action: str) -> bool:
        """Return True if current version is V11."""
        if not self._guard(action):
            return False
        if not self.is_v11:
            logger.info(f"[VVRemoteControl] {action}: not supported on {self.version} — no-op")
            return False
        return True

    # ── Shared: Bible ─────────────────────────────────────────────────────────

    def show_verse(self, ref: str) -> bool:
        if not self._guard("show_verse"):
            return False
        return VVSharedActions.show_verse(self.driver, ref)

    def get_verses(self, ref: str) -> bool:
        """Set the reference and click Get Chapter."""
        if not self._guard("get_verses"):
            return False
        if not VVSharedActions.set_reference(self.driver, ref):
            return False
        return VVSharedActions.get_verses(self.driver)

    def set_reference(self, ref: str) -> bool:
        if not self._guard("set_reference"):
            return False
        return VVSharedActions.set_reference(self.driver, ref)

    def present_verse(self) -> bool:
        if not self._guard("present_verse"):
            return False
        return VVSharedActions.present_verse(self.driver)

    # ── Shared: Presentation Control ──────────────────────────────────────────

    def clear_presentation(self) -> bool:
        """Alias for close_presentation (consistent naming)."""
        return self.close_presentation()

    def blank_presentation(self) -> bool:
        if not self._guard("blank_presentation"):
            return False
        return VVSharedActions.blank_presentation(self.driver)

    def logo_presentation(self) -> bool:
        if not self._guard("logo_presentation"):
            return False
        return VVSharedActions.logo_presentation(self.driver)

    def close_presentation(self) -> bool:
        if not self._guard("close_presentation"):
            return False
        return VVSharedActions.close_presentation(self.driver)

    def next_slide(self) -> bool:
        if not self._guard("next_slide"):
            return False
        return VVSharedActions.next_slide(self.driver)

    def prev_slide(self) -> bool:
        if not self._guard("prev_slide"):
            return False
        return VVSharedActions.prev_slide(self.driver)

    # ── Shared: Songs ─────────────────────────────────────────────────────────

    def search_songs(self, query: str) -> bool:
        if not self._guard("search_songs"):
            return False
        return VVSharedActions.search_songs(self.driver, query)

    def get_song_lyrics(self) -> bool:
        if not self._guard("get_song_lyrics"):
            return False
        return VVSharedActions.get_song_lyrics(self.driver)

    # ── Shared: Tab Switching ─────────────────────────────────────────────────

    def switch_to_bible_tab(self) -> bool:
        if not self._guard("switch_to_bible_tab"):
            return False
        return VVSharedActions.switch_to_bible_tab(self.driver)

    def switch_to_songs_tab(self) -> bool:
        if not self._guard("switch_to_songs_tab"):
            return False
        return VVSharedActions.switch_to_songs_tab(self.driver)

    def switch_to_schedule_tab(self) -> bool:
        """Switch to Schedule (V10) or Events (V11) tab — same underlying ID."""
        if not self._guard("switch_to_schedule_tab"):
            return False
        return VVSharedActions.switch_to_schedule_tab(self.driver)

    def switch_to_custom_tab(self) -> bool:
        """V11 only — switch to the Custom tab."""
        if not self._guard_v11("switch_to_custom_tab"):
            return False
        return self._v11.switch_to_custom_tab(self.driver)

    # ── Version-Specific: Schedule / Events ───────────────────────────────────

    def get_schedule_or_events(self) -> bool:
        """Load schedule (V10) or refresh events list (V11)."""
        if not self._guard("get_schedule_or_events"):
            return False
        if self.is_v10:
            return self._v10.get_schedule_items(self.driver)
        else:
            return self._v11.refresh_events_list(self.driver)

    def present_schedule_item(self) -> bool:
        """V10 only — present the selected schedule item."""
        if not self._guard_v10("present_schedule_item"):
            return False
        return self._v10.present_schedule_item(self.driver)

    def set_selected_event(self, value: str) -> bool:
        """V11 only — select an event and trigger loadSchEvent."""
        if not self._guard_v11("set_selected_event"):
            return False
        return self._v11.set_selected_event(self.driver, value)

    # ── Version-Specific: V10 Song Bookmark ───────────────────────────────────

    def set_song_bookmark(self) -> bool:
        """V10 only — set the current song as a bookmark."""
        if not self._guard_v10("set_song_bookmark"):
            return False
        return self._v10.set_song_bookmark(self.driver)

    # ── Version-Specific: V10 Two-Line Presentation ───────────────────────────

    def get_two_line_present(self) -> bool:
        if not self._guard_v10("get_two_line_present"):
            return False
        return self._v10.get_two_line_present(self.driver)

    def set_two_line_present(self, checked: bool) -> bool:
        if not self._guard_v10("set_two_line_present"):
            return False
        return self._v10.set_two_line_present(self.driver, checked)

    def get_two_line_present2(self) -> bool:
        if not self._guard_v10("get_two_line_present2"):
            return False
        return self._v10.get_two_line_present2(self.driver)

    def set_two_line_present2(self, checked: bool) -> bool:
        if not self._guard_v10("set_two_line_present2"):
            return False
        return self._v10.set_two_line_present2(self.driver, checked)

    # ── Version-Specific: V11 Custom Tab ──────────────────────────────────────

    def add_custom_to_schedule(self, title: str = "", text: str = "") -> bool:
        """V11 only — set custom title/text and click add."""
        if not self._guard_v11("add_custom_to_schedule"):
            return False
        if title:
            self._v11.set_custom_title(self.driver, title)
        if text:
            self._v11.set_custom_text(self.driver, text)
        return self._v11.add_custom_to_schedule(self.driver)

    # ── Version-Specific: V11 Song-to-Event Scheduling ────────────────────────

    def schedule_song_to_event(self) -> bool:
        """V11 only — schedule the selected song to the selected event."""
        if not self._guard_v11("schedule_song_to_event"):
            return False
        return self._v11.schedule_song_to_event(self.driver)

    # ── Version-Specific: V11 Theme Toggle ────────────────────────────────────

    def toggle_theme(self) -> bool:
        """V11 only — toggle the dark/light theme."""
        if not self._guard_v11("toggle_theme"):
            return False
        return self._v11.toggle_theme(self.driver)


# ══════════════════════════════════════════════════════════════════════════════
#  INTERNAL HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _click_by_id(driver, element_id: str, label: str) -> bool:
    """Find an element by ID and click it via JavaScript.  Returns True on
    success, False on failure (logs the error)."""
    try:
        from selenium.webdriver.common.by import By
        el = driver.find_element(By.ID, element_id)
        driver.execute_script("arguments[0].click();", el)
        logger.debug(f"[{label}] clicked #{element_id}")
        return True
    except Exception as exc:
        logger.error(f"[{label}] click #{element_id} failed: {exc}")
        return False
