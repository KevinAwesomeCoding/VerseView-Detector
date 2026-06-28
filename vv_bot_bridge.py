# -*- coding: utf-8 -*-
"""
vv_bot_bridge.py — Lightweight HTTP bridge server for the Discord bot.

Listens on http://127.0.0.1:50011 (separate from VerseView's own port 50010).
The Discord bot (vv_discord_bot.py) calls these endpoints, and the bridge
executes the corresponding action on the host: either an engine remote-control
helper or a direct Selenium navigation click on the already-running driver.

Usage:
    from vv_bot_bridge import start_bot_bridge
    start_bot_bridge(gui_app=app)            # at app startup (engine NOT required)
    start_bot_bridge(controller, gui_app=app)# again when the engine connects (idempotent)

Endpoints (all GET):
    /start               — start the VerseView engine on the host (remote power-on)
    /stop                — stop the engine
    /goto?ref=John+1:5   — present a verse directly (bypasses STT detection)
    /clear               — clear the verse off the screen (panic/blank)
    /present             — re-click the PRESENT button
    /next                — click the forward/next button
    /prev                — click the backward/prev button
    /close               — click the close (iconClose) button
    /status              — JSON-ish text: engine running / connected / current verse

Design notes:
  • Runs in a daemon thread — never blocks the main app.
  • Uses only Python stdlib (http.server) — zero extra dependencies.
  • DECOUPLED FROM THE ENGINE: the live VerseController is looked up from the
    engine module on every request, so the bridge keeps working across engine
    stop/start cycles WITHOUT being restarted. This is what lets a remote
    operator power the engine back on with /start after a /stop.
  • Engine power (start/stop) is marshalled onto the tkinter GUI thread via
    gui_app.after(), so it is thread-safe.
  • All HTTP request logs are suppressed (log_message is a no-op).
  • Self-contained: remove the import + start_bot_bridge() call to disable
    entirely without touching any other code.
"""

import logging
import threading
import urllib.parse
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer

logger = logging.getLogger(__name__)

# Module-level references. _controller is only a *fallback*; the live controller
# is read from the engine module each request (see _get_controller) so engine
# restarts never leave the bridge pointing at a dead driver.
_controller = None
_gui_app    = None
_server: "HTTPServer | None" = None   # kept so we never try to bind twice


# ── Live lookups ───────────────────────────────────────────────────────────────

def _get_controller():
    """Return the engine's current VerseController, or None.

    Prefers the live `_controller` global inside vv_streaming_master (the single
    source of truth, recreated on every engine start) and falls back to whatever
    was injected via start_bot_bridge(). This is the key to surviving engine
    restarts without rebinding the bridge.
    """
    try:
        import vv_streaming_master as _engine
        live = getattr(_engine, "_controller", None)
        if live is not None:
            return live
    except Exception:
        pass
    return _controller


def _engine_running() -> bool:
    """True if the GUI says the engine session is active."""
    if _gui_app is None:
        return False
    return bool(getattr(_gui_app, "_running", False))


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
            "/start":   self._handle_start,
            "/stop":    self._handle_stop,
            "/goto":    self._handle_goto,
            "/clear":   self._handle_clear,
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

    # ── Engine power (remote start/stop) ──────────────────────────────────────

    def _handle_start(self, params):
        """Start the VerseView engine on the host machine (remote power-on).

        Works even when the engine is stopped because the bridge runs for the
        whole app lifetime, independent of the engine.
        """
        if _gui_app is None:
            self._send(503, "GUI not available — cannot start the engine remotely")
            return
        if _engine_running():
            self._send(200, "Engine is already running")
            return
        try:
            # _start touches tkinter widgets — must run on the GUI thread.
            _gui_app.after(0, _gui_app._start)
            logger.info("[bridge] /start → engine start scheduled")
            self._send(200, "Starting VerseView engine… (give it a few seconds to connect)")
        except Exception as exc:
            logger.error(f"[bridge] /start failed: {exc}")
            self._send(500, f"Could not start engine: {exc}")

    def _handle_stop(self, params):
        """Stop the VerseView engine on the host machine."""
        if _gui_app is None:
            self._send(503, "GUI not available — cannot stop the engine remotely")
            return
        if not _engine_running():
            self._send(200, "Engine is already stopped")
            return
        try:
            _gui_app.after(0, _gui_app._stop)
            logger.info("[bridge] /stop → engine stop scheduled")
            self._send(200, "Stopping VerseView engine…")
        except Exception as exc:
            logger.error(f"[bridge] /stop failed: {exc}")
            self._send(500, f"Could not stop engine: {exc}")

    # ── Verse override + clear (routed through the engine helpers) ─────────────

    def _handle_goto(self, params):
        """Present a verse directly, bypassing STT detection."""
        ref = (params.get("ref") or [""])[0].strip()
        if not ref:
            self._send(400, "Missing ?ref= parameter")
            return
        try:
            import vv_streaming_master as _engine
            ok, msg = _engine.remote_present_verse(ref)
        except Exception as exc:
            logger.error(f"[bridge] /goto failed: {exc}")
            traceback.print_exc()
            self._send(500, f"Selenium error: {exc}")
            return

        if ok:
            logger.info(f"[bridge] /goto → {ref}")
            # No GUI nudge needed: remote_present_verse() already updated the
            # engine context, and the GUI's own 2s poll (_refresh_context) picks
            # that up automatically. Calling it here would spawn a second loop.
            self._send(200, msg)
        else:
            # "not connected" → 503 so the bot tells the user to start the engine.
            self._send(503 if "not connected" in msg.lower() else 500, msg)

    def _handle_clear(self, params):
        """Clear the currently displayed verse (panic / blank screen)."""
        try:
            import vv_streaming_master as _engine
            ok, msg = _engine.remote_clear()
        except Exception as exc:
            logger.error(f"[bridge] /clear failed: {exc}")
            self._send(500, f"Clear error: {exc}")
            return
        if ok:
            logger.info("[bridge] /clear → screen cleared")
            self._send(200, msg)
        else:
            self._send(503 if "not connected" in msg.lower() else 500, msg)

    # ── Navigation (direct Selenium on the live driver) ───────────────────────

    def _handle_present(self, params):
        driver = self._driver_or_503()
        if driver is None:
            return
        try:
            from selenium.webdriver.common.by import By
            btn = driver.find_element(By.ID, "remote_bible_present")
            driver.execute_script("arguments[0].click();", btn)
            logger.info("[bridge] /present clicked")
            self._send(200, "Re-presented current verse")
        except Exception as exc:
            logger.error(f"[bridge] /present failed: {exc}")
            self._send(500, f"Selenium error: {exc}")

    def _handle_next(self, params):
        """Click the forward/next navigation button on control.html."""
        driver = self._driver_or_503()
        if driver is None:
            return
        try:
            from selenium.webdriver.common.by import By
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
            self._send(200, "Next verse")
        except Exception as exc:
            logger.error(f"[bridge] /next failed: {exc}")
            self._send(500, f"Selenium error: {exc}")

    def _handle_prev(self, params):
        """Click the backward/prev navigation button on control.html."""
        driver = self._driver_or_503()
        if driver is None:
            return
        try:
            from selenium.webdriver.common.by import By
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
            self._send(200, "Previous verse")
        except Exception as exc:
            logger.error(f"[bridge] /prev failed: {exc}")
            self._send(500, f"Selenium error: {exc}")

    def _handle_close(self, params):
        driver = self._driver_or_503()
        if driver is None:
            return
        try:
            from selenium.webdriver.common.by import By
            close_btn = driver.find_element(By.ID, "iconClose")
            driver.execute_script("arguments[0].click();", close_btn)
            logger.info("[bridge] /close clicked")
            self._send(200, "Closed presentation")
        except Exception as exc:
            logger.error(f"[bridge] /close failed: {exc}")
            self._send(500, f"Selenium error: {exc}")

    def _handle_status(self, params):
        """Report engine running + connection + current verse as one line.

        Always 200 so /status is a pure info query (the bot formats the body).
        """
        running   = _engine_running()
        connected = False
        context   = ""
        try:
            import vv_streaming_master as _engine
            snap = _engine.remote_status()
            connected = bool(snap.get("connected"))
            book, chap, vs = snap.get("book"), snap.get("chapter"), snap.get("verse")
            if book and chap:
                context = f"{book} {chap}" + (f":{vs}" if vs else "")
        except Exception as exc:
            logger.warning(f"[bridge] /status snapshot failed: {exc}")

        if running and connected:
            state = "🟢 Engine running and connected to VerseView"
        elif running and not connected:
            state = "🟡 Engine running — connecting to VerseView…"
        else:
            state = "🔴 Engine stopped (use /start to power it on)"
        if context:
            state += f"  ·  last verse: {context}"
        self._send(200, state)

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _driver_or_503(self):
        """Return the live Selenium driver, or send a 503 and return None."""
        ctrl = _get_controller()
        if ctrl is None or getattr(ctrl, "driver", None) is None:
            self._send(503, "VerseView not connected — start the engine first")
            return None
        return ctrl.driver

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
        for by, sel in selectors:
            try:
                return driver.find_element(by, sel)
            except Exception:
                continue
        return None


# ── Public API ─────────────────────────────────────────────────────────────────

def start_bot_bridge(controller=None, port: int = 50011, gui_app=None):
    """
    Start (or refresh) the HTTP bridge server in a background daemon thread.

    Safe to call multiple times. The socket is bound only once; subsequent calls
    just refresh the injected references. Call it once at app startup with only
    `gui_app` (so remote /start works before the engine ever runs), and again
    from the engine when it connects (so the controller fallback is current).

    Parameters
    ----------
    controller : VerseController | None
        Optional fallback controller. The live controller is normally read from
        the engine module on each request, so this may be None.
    port : int
        Port to listen on (default 50011). Must differ from VerseView's port 50010.
    gui_app : VerseViewApp | None
        The tkinter GUI app — required for remote /start and /stop, and for
        thread-safe context-field refreshes.
    """
    global _controller, _gui_app, _server

    if controller is not None:
        _controller = controller
    if gui_app is not None:
        _gui_app = gui_app

    if _server is not None:
        # Bridge already bound — references refreshed above, nothing else to do.
        logger.info("[bridge] Bot bridge already running — references refreshed")
        return _server

    try:
        _server = HTTPServer(("127.0.0.1", port), _BridgeHandler)
    except OSError as exc:
        # Most likely the port is already held by a previous run in this process.
        logger.error(f"[bridge] Could not bind port {port}: {exc}")
        raise

    def _serve():
        logger.info(f"[bridge] Bot bridge listening on http://127.0.0.1:{port}")
        try:
            _server.serve_forever()
        except Exception as exc:
            logger.error(f"[bridge] Server stopped unexpectedly: {exc}")

    thread = threading.Thread(target=_serve, name="vv-bot-bridge", daemon=True)
    thread.start()
    return _server
