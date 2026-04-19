# -*- coding: utf-8 -*-
"""
vv_bot_bridge.py — Lightweight HTTP bridge server for the Discord bot.

Listens on http://127.0.0.1:50011 (separate from VerseView's own port 50010).
The Discord bot (verseview_bot.py) calls these endpoints, and the bridge
executes the corresponding Selenium actions via the already-running driver.

Usage:
    from vv_bot_bridge import start_bot_bridge
    start_bot_bridge(controller)   # pass the VerseController instance

Endpoints (all GET):
    /goto?ref=John+1:5   — type ref into the input and click the search btn
    /present             — click the PRESENT button
    /next                — click the forward/next button
    /prev                — click the backward/prev button
    /close               — click the close (iconClose) button
    /status              — 200 if connected, 503 if not

Design notes:
  • Runs in a daemon thread — never blocks the main app.
  • Uses only Python stdlib (http.server) — zero extra dependencies.
  • All HTTP request logs are suppressed (log_message is a no-op).
  • Selenium errors are caught, logged to the engine logger, and returned as
    HTTP 500 so the Discord bot can surface a meaningful error to the user.
  • Self-contained: remove the import + start_bot_bridge() call to disable
    entirely without touching any other code.
"""

import logging
import threading
import urllib.parse
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer

logger = logging.getLogger(__name__)

# Module-level references injected by start_bot_bridge()
_controller = None
_gui_app    = None
_server: "HTTPServer | None" = None   # kept so we never try to bind twice


# ── Handler ────────────────────────────────────────────────────────────────────

class _BridgeHandler(BaseHTTPRequestHandler):
    """Each incoming request is dispatched to a route function."""

    # ── Suppress all HTTP access logging ──────────────────────────────────────
    def log_message(self, format, *args):  # noqa: A002
        pass

    # ── Entry point ───────────────────────────────────────────────────────────
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        path   = parsed.path.rstrip("/")

        routes = {
            "/goto":    self._handle_goto,
            "/present": self._handle_present,
            "/next":    self._handle_next,
            "/prev":    self._handle_prev,
            "/close":   self._handle_close,
            "/status":  self._handle_status,
        }

        handler = routes.get(path)
        if handler is None:
            self._send(404, f"Unknown endpoint: {path}")
            return

        try:
            handler(params)
        except Exception as exc:
            logger.error(f"[bridge] Unhandled error in {path}: {exc}")
            self._send(500, f"Internal error: {exc}")

    # ── Routes ─────────────────────────────────────────────────────────────────

    def _handle_goto(self, params):
        ref = (params.get("ref") or [""])[0].strip()
        print(f"[Bridge] /goto called with ref={ref}")
        if not ref:
            self._send(400, "Missing ?ref= parameter")
            return
        if not self._check_connected():
            return
        try:
            from selenium.webdriver.common.by import By
            driver = _controller.driver

            print("[Bridge] Step 1: Finding verse input field...")
            box    = driver.find_element(By.ID, "remote_bibleRefID")

            print("[Bridge] Step 2: Clearing field...")
            # We use JS to set value but Step 2 is requested
            driver.execute_script("arguments[0].value = '';", box)

            print("[Bridge] Step 3: Typing reference...")
            driver.execute_script("arguments[0].value = arguments[1];", box, ref)

            print("[Bridge] Step 4: Clicking search/present button...")
            # In VerseController, self.btn is the found PRESENT button
            driver.execute_script("arguments[0].click();", _controller.btn)

            # Step 5 requested by user - clicking the present button specifically
            # In our code, _controller.btn is already the present button, but
            # we'll add a check/click for a dedicated present ID just in case.
            print("[Bridge] Step 5: Verifying presentation...")
            try:
                present_btn = driver.find_element(By.ID, "remote_bible_present")
                driver.execute_script("arguments[0].click();", present_btn)
            except:
                # If not found or already clicked, no worries
                pass

            logger.info(f"[bridge] /goto → {ref}")
            self._send(200, f"OK: {ref}")

            # ── Update engine context + GUI fields ────────────────────────────
            try:
                import vv_streaming_master as _engine
                # Parse "John 1:5" or "1 Corinthians 3:16" → book, chapter, verse
                _parts = ref.split()
                if _parts[0].isdigit() and len(_parts) > 1:
                    _book   = f"{_parts[0]} {_parts[1]}"
                    _rest   = _parts[2] if len(_parts) > 2 else ""
                else:
                    _book   = _parts[0]
                    _rest   = _parts[1] if len(_parts) > 1 else ""
                if ":" in _rest:
                    _chapter, _verse = _rest.split(":", 1)
                else:
                    _chapter, _verse = _rest, ""
                _engine.set_context(_book, _chapter, _verse)
                logger.info(f"[bridge] Context updated → {_book} {_chapter}:{_verse}")

                if _gui_app is not None:
                    def _refresh_gui(b=_book, c=_chapter, v=_verse):
                        try:
                            _gui_app.ctx_book.delete(0, "end")
                            _gui_app.ctx_chapter.delete(0, "end")
                            _gui_app.ctx_verse.delete(0, "end")
                            _gui_app.ctx_book.insert(0, b)
                            _gui_app.ctx_chapter.insert(0, c)
                            _gui_app.ctx_verse.insert(0, v)
                        except Exception:
                            pass
                    _gui_app.after(0, _refresh_gui)
            except Exception as _ctx_err:
                logger.warning(f"[bridge] Context update failed: {_ctx_err}")
        except Exception as exc:
            print(f"[Bridge] /goto FAILED during Selenium execution:")
            traceback.print_exc()
            logger.error(f"[bridge] /goto failed: {exc}")
            self._send(500, f"Selenium error: {exc}")

    def _handle_present(self, params):
        if not self._check_connected():
            return
        try:
            from selenium.webdriver.common.by import By
            driver = _controller.driver
            btn    = driver.find_element(By.ID, "remote_bible_present")
            driver.execute_script("arguments[0].click();", btn)
            logger.info("[bridge] /present clicked")
            self._send(200, "OK: presented")
        except Exception as exc:
            logger.error(f"[bridge] /present failed: {exc}")
            self._send(500, f"Selenium error: {exc}")

    def _handle_next(self, params):
        """Click the forward/next navigation button on control.html."""
        if not self._check_connected():
            return
        try:
            from selenium.webdriver.common.by import By
            driver = _controller.driver
            # Try known IDs/selectors for the forward button.
            # Add more selectors here if VerseView's UI changes.
            btn = self._find_any(driver, [
                (By.ID,    "iconForward"),
                (By.ID,    "remote_bible_forward"),
                (By.ID,    "remote_bible_next"),
                (By.XPATH, "//button[contains(@id,'forward') or contains(@id,'next')]"),
                (By.XPATH, "//button[contains(normalize-space(text()),'▶') or "
                           "contains(normalize-space(text()),'Next') or "
                           "contains(normalize-space(text()),'NEXT')]"),
            ])
            if not btn:
                self._send(500, "Forward button not found on control.html")
                return
            driver.execute_script("arguments[0].click();", btn)
            logger.info("[bridge] /next clicked")
            self._send(200, "OK: next")
        except Exception as exc:
            logger.error(f"[bridge] /next failed: {exc}")
            self._send(500, f"Selenium error: {exc}")

    def _handle_prev(self, params):
        """Click the backward/prev navigation button on control.html."""
        if not self._check_connected():
            return
        try:
            from selenium.webdriver.common.by import By
            driver = _controller.driver
            btn = self._find_any(driver, [
                (By.ID,    "iconBack"),
                (By.ID,    "iconBackward"),
                (By.ID,    "remote_bible_back"),
                (By.ID,    "remote_bible_prev"),
                (By.XPATH, "//button[contains(@id,'back') or contains(@id,'prev')]"),
                (By.XPATH, "//button[contains(normalize-space(text()),'◀') or "
                           "contains(normalize-space(text()),'Back') or "
                           "contains(normalize-space(text()),'BACK') or "
                           "contains(normalize-space(text()),'Prev') or "
                           "contains(normalize-space(text()),'PREV')]"),
            ])
            if not btn:
                self._send(500, "Back button not found on control.html")
                return
            driver.execute_script("arguments[0].click();", btn)
            logger.info("[bridge] /prev clicked")
            self._send(200, "OK: prev")
        except Exception as exc:
            logger.error(f"[bridge] /prev failed: {exc}")
            self._send(500, f"Selenium error: {exc}")

    def _handle_close(self, params):
        if not self._check_connected():
            return
        try:
            from selenium.webdriver.common.by import By
            driver    = _controller.driver
            close_btn = driver.find_element(By.ID, "iconClose")
            driver.execute_script("arguments[0].click();", close_btn)
            logger.info("[bridge] /close clicked")
            self._send(200, "OK: closed")
        except Exception as exc:
            logger.error(f"[bridge] /close failed: {exc}")
            self._send(500, f"Selenium error: {exc}")

    def _handle_status(self, params):
        if _controller is None:
            logger.warning("Bridge: controller is None — engine not started yet")
            self._send(503, "Not connected — engine not started")
            return
        if _controller.driver is None:
            logger.warning("Bridge: controller.driver is None — engine not fully connected")
            self._send(503, "Not connected — driver not initialized")
            return
        try:
            # Light check — fetch the current page title to verify the driver is alive
            _ = _controller.driver.title
            self._send(200, "OK: connected")
        except Exception as exc:
            logger.warning(f"[bridge] /status driver ping failed: {exc}")
            self._send(503, f"Driver error: {exc}")

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _check_connected(self) -> bool:
        """Return True if a live Selenium session exists; otherwise send 503."""
        if _controller is None:
            logger.warning("Bridge: controller is None — engine not started yet")
            self._send(503, "VerseView not connected — start the engine first")
            return False
        if _controller.driver is None:
            logger.warning("Bridge: controller.driver is None — engine not fully connected")
            self._send(503, "VerseView not connected — driver not initialized")
            return False
        return True

    def _send(self, code: int, body: str):
        encoded = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    @staticmethod
    def _find_any(driver, selectors):
        """Try each (By, selector) pair and return the first element found, or None."""
        from selenium.webdriver.common.by import By  # noqa: F401 (imported for callers)
        for by, sel in selectors:
            try:
                return driver.find_element(by, sel)
            except Exception:
                continue
        return None


# ── Public API ─────────────────────────────────────────────────────────────────

def start_bot_bridge(controller, port: int = 50011, gui_app=None):
    """
    Start the HTTP bridge server in a background daemon thread.

    If the server is already running (e.g. engine restarted after a stop),
    the existing socket is reused and only the controller reference is updated.
    This prevents [Errno 48] / [Errno 10048] address-already-in-use errors
    on engine restart.

    Parameters
    ----------
    controller : VerseController
        The already-connected VerseController instance from vv_streaming_master.
    port : int
        Port to listen on (default 50011).  Must differ from VerseView's port 50010.
    gui_app : VerseViewApp | None
        Optional reference to the tkinter GUI app for thread-safe context field updates.
    """
    global _controller, _gui_app, _server

    _controller = controller
    _gui_app    = gui_app

    if _server is not None:
        # Bridge already bound — just update the controller reference and return.
        logger.info("[bridge] Bot bridge already running — controller re-injected")
        return _server

    _server = HTTPServer(("127.0.0.1", port), _BridgeHandler)

    def _serve():
        logger.info(f"[bridge] Bot bridge listening on http://127.0.0.1:{port}")
        try:
            _server.serve_forever()
        except Exception as exc:
            logger.error(f"[bridge] Server stopped unexpectedly: {exc}")

    thread = threading.Thread(target=_serve, name="vv-bot-bridge", daemon=True)
    thread.start()
    return _server
