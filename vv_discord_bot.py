# -*- coding: utf-8 -*-
"""
vv_discord_bot.py — Standalone Discord slash-command bot for VerseView Detector.

This script is launched as a subprocess by the main VerseView app when the user
clicks "Start Bot". It has NO GUI, NO selenium, and NO engine — it only speaks
to the vv_bot_bridge HTTP server (default port 50011) running inside the main
app, which performs the real actions.

Because the bridge now runs for the WHOLE app lifetime (not just while the engine
is running), this bot can be online and useful even when the engine is stopped —
that is what makes remote power-on (/start) possible from a phone or another PC.

Environment variables (set by the parent process):
    VV_BOT_TOKEN   — Discord bot token (required)
    VV_HOST        — Bridge host, default 127.0.0.1
    VV_PORT        — Bridge port, default 50011
    VV_GUILD_ID    — (optional) Discord server ID for instant slash-command sync

Slash commands:
    /start         — Power on the VerseView engine on the host machine
    /stop          — Power off the engine
    /verse <ref>   — Present a Bible reference and post a control panel
    /clear         — Clear the verse off the screen (panic / blank)
    /present       — Re-present the current verse
    /next          — Navigate to the next verse
    /prev          — Navigate to the previous verse
    /close         — Close the current presentation
    /status        — Show engine / connection state
"""

import os
import sys
import asyncio
import logging
import urllib.error
import urllib.parse
import urllib.request

# Force UTF-8 on Windows BEFORE logging is configured.
# cp1252 (Windows default pipe encoding) cannot encode emoji and will crash.
for _stream_name in ("stdout", "stderr"):
    _stream = getattr(sys, _stream_name, None)
    if _stream and hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

import discord
from discord import app_commands
from typing import Optional, Tuple

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [discord-bot] %(levelname)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# ── Config from env ───────────────────────────────────────────────────────────
TOKEN    = os.environ.get("VV_BOT_TOKEN", "").strip()
HOST     = os.environ.get("VV_HOST", "127.0.0.1").strip()
PORT     = int(os.environ.get("VV_PORT", "50011"))
# VV_GUILD_ID: set this to your Discord Server ID for INSTANT slash command sync.
# Without it, commands use global sync which can take up to 1 hour to appear.
# Get your server ID: Discord → Server Settings → enable Developer Mode → right-click server → Copy ID
GUILD_ID = os.environ.get("VV_GUILD_ID", "").strip()

if not TOKEN:
    logger.error("VV_BOT_TOKEN is not set — cannot start Discord bot.")
    sys.exit(1)

BRIDGE_BASE = f"http://{HOST}:{PORT}"
_GUILD_OBJ  = discord.Object(id=int(GUILD_ID)) if GUILD_ID else None


# ── Bridge helpers ─────────────────────────────────────────────────────────────

def _bridge(endpoint: str, params: Optional[dict] = None, timeout: int = 8) -> Tuple[int, str]:
    """
    Call a vv_bot_bridge endpoint synchronously.
    Returns (http_status_code, body_text).
    Never raises — connection errors return (0, error_message).
    """
    url = BRIDGE_BASE + endpoint
    if params:
        url += "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return e.code, body
    except Exception as exc:
        return 0, str(exc)


async def _call(endpoint: str, params: Optional[dict] = None, timeout: int = 8) -> Tuple[int, str]:
    """Async wrapper so bridge calls never block the Discord event loop."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: _bridge(endpoint, params, timeout))


def _reply(status: int, body: str) -> str:
    """Turn a bridge response into a human-friendly Discord message."""
    if status == 200:
        return f"✅ {body}"
    if status == 503:
        # Bridge is reachable but the engine/driver isn't ready.
        return f"⚠️ {body or 'VerseView is not connected — start the engine first (/start).'}"
    if status == 0:
        return f"❌ Could not reach the VerseView bridge ({body}). Is the app running?"
    return f"❌ Bridge error {status}: {body}"


# ── Verse-modifier control panel (buttons) ─────────────────────────────────────

PANEL_PREFIX = "🎛️ **Verse control**"


def _panel_text(ref: str, note: str = "") -> str:
    txt = f"{PANEL_PREFIX} — `{ref}`"
    if note:
        txt += f"\n{note}"
    return txt


async def _repost_panel(interaction: discord.Interaction, ref: str, note: str):
    """Delete the message the button lives on and post a FRESH panel.

    This is the verse-modifier "refresh" behaviour: every action retires the old
    buttons and posts a new message with a brand-new working set, so the panel
    never goes stale and the latest action is always reflected at the bottom of
    the channel.
    """
    new_view = VerseControlView(ref)
    try:
        await interaction.channel.send(content=_panel_text(ref, note), view=new_view)
    except Exception as exc:
        logger.error(f"Could not post refreshed panel: {exc}")
    try:
        await interaction.message.delete()
    except Exception:
        pass  # already gone, or missing Manage Messages — non-fatal


class VerseControlView(discord.ui.View):
    """Buttons attached to a verse message. timeout=None keeps them live for the
    whole bot session (they stop working only if the bot process restarts)."""

    def __init__(self, ref: str):
        super().__init__(timeout=None)
        self.ref = ref

    @discord.ui.button(label="Re-send", emoji="🔁", style=discord.ButtonStyle.success)
    async def resend(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        status, body = await _call("/goto", {"ref": self.ref})
        await _repost_panel(interaction, self.ref, _reply(status, body))

    @discord.ui.button(label="Clear", emoji="⛔", style=discord.ButtonStyle.danger)
    async def clear(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        status, body = await _call("/clear")
        await _repost_panel(interaction, self.ref, _reply(status, body))

    @discord.ui.button(label="Prev", emoji="◀", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        status, body = await _call("/prev")
        await _repost_panel(interaction, self.ref, _reply(status, body))

    @discord.ui.button(label="Next", emoji="▶", style=discord.ButtonStyle.secondary)
    async def next_verse(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        status, body = await _call("/next")
        await _repost_panel(interaction, self.ref, _reply(status, body))


# ── Client factory ─────────────────────────────────────────────────────────────

def build_client() -> discord.Client:
    """Create a fresh client + command tree and register all commands.

    A factory (rather than a module-level singleton) so the reconnect supervisor
    can rebuild a clean client after an unrecoverable session failure — a closed
    discord.Client cannot be reused.
    """
    intents = discord.Intents.default()
    client  = discord.Client(intents=intents)
    tree    = app_commands.CommandTree(client)

    # ── Engine power ──────────────────────────────────────────────────────────
    @tree.command(name="start", description="Power on the VerseView engine on the host machine")
    async def cmd_start(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        status, body = await _call("/start", timeout=12)
        await interaction.followup.send(_reply(status, body or "Starting…"))
        # The engine needs a few seconds to launch Chrome and connect. Poll once
        # and report the outcome so the remote operator gets real confirmation.
        if status == 200:
            await asyncio.sleep(10)
            _, st = await _call("/status")
            await interaction.followup.send(f"📊 {st}")

    @tree.command(name="stop", description="Power off the VerseView engine")
    async def cmd_stop(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        status, body = await _call("/stop")
        await interaction.followup.send(_reply(status, body or "Stopping…"))

    # ── Verse override + control panel ────────────────────────────────────────
    @tree.command(name="verse", description="Present a Bible verse  (e.g. John 3:16)")
    @app_commands.describe(ref="Bible reference, e.g. John 3:16 or 1 Cor 13:4")
    async def cmd_verse(interaction: discord.Interaction, ref: str):
        await interaction.response.defer(ephemeral=False)
        status, body = await _call("/goto", {"ref": ref})
        note = _reply(status, body or f"Presented {ref}")
        if status == 200:
            # Post the verse-modifier control panel with fresh buttons.
            await interaction.followup.send(content=_panel_text(ref, note),
                                            view=VerseControlView(ref))
        else:
            await interaction.followup.send(note)

    @tree.command(name="clear", description="Clear the verse off the screen (panic / blank)")
    async def cmd_clear(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        status, body = await _call("/clear")
        await interaction.followup.send(_reply(status, body or "Cleared"))

    # ── Navigation ────────────────────────────────────────────────────────────
    @tree.command(name="present", description="Re-present the current verse")
    async def cmd_present(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        status, body = await _call("/present")
        await interaction.followup.send(_reply(status, body or "Presented"))

    @tree.command(name="next", description="Go to the next verse")
    async def cmd_next(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        status, body = await _call("/next")
        await interaction.followup.send(_reply(status, body or "Next"))

    @tree.command(name="prev", description="Go to the previous verse")
    async def cmd_prev(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        status, body = await _call("/prev")
        await interaction.followup.send(_reply(status, body or "Previous"))

    @tree.command(name="close", description="Close the current presentation")
    async def cmd_close(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        status, body = await _call("/close")
        await interaction.followup.send(_reply(status, body or "Closed"))

    @tree.command(name="status", description="Show VerseView engine / connection state")
    async def cmd_status(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        status, body = await _call("/status")
        if status == 200:
            await interaction.followup.send(body, ephemeral=True)
        else:
            await interaction.followup.send(_reply(status, body), ephemeral=True)

    @client.event
    async def on_ready():
        if _GUILD_OBJ:
            tree.copy_global_to(guild=_GUILD_OBJ)
            await tree.sync(guild=_GUILD_OBJ)
            logger.info(f"Slash commands synced to guild {GUILD_ID} (instant)")
            print(f"[OK] Slash commands synced instantly to guild {GUILD_ID}", flush=True)
        else:
            await tree.sync()
            logger.warning(
                "Slash commands synced GLOBALLY — may take up to 1 hour to appear in Discord. "
                "Set VV_GUILD_ID env var for instant sync."
            )
            print("[OK] Slash commands synced globally (may take up to 60 min to appear -- set VV_GUILD_ID for instant sync)", flush=True)

        logger.info(f"Discord bot ready -- logged in as {client.user} (id={client.user.id})")
        logger.info(f"Bridge target: {BRIDGE_BASE}")
        print("[OK] Discord bot online as " + str(client.user), flush=True)

    return client


# ── Reconnect supervisor ────────────────────────────────────────────────────────

async def _run_forever():
    """Keep the bot online.

    discord.py already auto-reconnects to the gateway across transient network
    drops (WiFi blips, Discord restarts) while a session is alive. This outer
    loop adds recovery from a *full* client failure: it rebuilds a clean client
    and retries with capped exponential backoff. An invalid token is fatal and
    is NOT retried (retrying would just spin forever).
    """
    backoff = 5
    while True:
        client = build_client()
        try:
            await client.start(TOKEN)
        except discord.LoginFailure:
            logger.error("Invalid Discord token — check VV_BOT_TOKEN. Not retrying.")
            return
        except Exception as exc:
            logger.error(f"Bot session ended ({exc}) — reconnecting in {backoff}s")
        else:
            logger.warning(f"Bot session closed — reconnecting in {backoff}s")
        finally:
            try:
                if not client.is_closed():
                    await client.close()
            except Exception:
                pass

        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, 60)   # 5 → 10 → 20 → 40 → 60s cap


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        asyncio.run(_run_forever())
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        logger.error(f"Bot crashed: {exc}")
        sys.exit(1)
