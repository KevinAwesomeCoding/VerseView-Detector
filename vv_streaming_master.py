# ── SESSION RESTORE ──────────────────────────────────────────────────────────
# Add this function to vv_streaming_master.py.
# Placement: directly after clear_sermon_buffer() (around line 890).

def restore_session(data: dict) -> None:
    """Restore engine globals from a previously saved session dict.

    * Memory-only — does NOT restart the engine or connect to VerseView.
    * Uses .get() with safe fallbacks throughout so a partial or old session
      file never crashes the app.
    * Logs each restored field at INFO level.
    """
    global full_sermon_transcript, verses_cited, _verse_history
    global current_book, current_chapter, current_verse
    global _session_verse_high_water, _advance_transcript_offset
    global _last_explicit_ref_time

    try:
        transcript = data.get("full_sermon_transcript", "")
        if isinstance(transcript, str):
            full_sermon_transcript = transcript
            logger.info(f"✅ Restored: full_sermon_transcript ({len(transcript)} chars)")
        else:
            logger.warning("⚠️ Restore: full_sermon_transcript was not a string — skipped")

        cited = data.get("verses_cited", [])
        if isinstance(cited, list):
            verses_cited = [str(v) for v in cited]
            logger.info(f"✅ Restored: verses_cited ({len(verses_cited)} refs)")
        else:
            logger.warning("⚠️ Restore: verses_cited was not a list — skipped")

        history = data.get("verse_history", [])
        if isinstance(history, list):
            _verse_history = [
                {
                    "ref":   str(item.get("ref",   "")),
                    "time":  str(item.get("time",  "")),
                    "layer": str(item.get("layer", "RESTORED")),
                }
                for item in history
                if isinstance(item, dict)
            ]
            logger.info(f"✅ Restored: verse_history ({len(_verse_history)} entries)")
        else:
            logger.warning("⚠️ Restore: verse_history was not a list — skipped")

        book = data.get("current_book")
        if book is not None:
            current_book = str(book)
            logger.info(f"✅ Restored: current_book = {current_book}")

        chapter = data.get("current_chapter")
        if chapter is not None:
            current_chapter = str(chapter)
            logger.info(f"✅ Restored: current_chapter = {current_chapter}")

        verse = data.get("current_verse")
        if verse is not None:
            current_verse = str(verse)
            logger.info(f"✅ Restored: current_verse = {current_verse}")

        high_water = data.get("session_verse_high_water", {})
        if isinstance(high_water, dict):
            _session_verse_high_water = {
                str(k): int(v)
                for k, v in high_water.items()
                if isinstance(v, (int, float))
            }
            logger.info(f"✅ Restored: session_verse_high_water ({len(_session_verse_high_water)} keys)")
        else:
            logger.warning("⚠️ Restore: session_verse_high_water was not a dict — skipped")

        offset = data.get("advance_transcript_offset", 0)
        try:
            _advance_transcript_offset = int(offset)
            logger.info(f"✅ Restored: advance_transcript_offset = {_advance_transcript_offset}")
        except (TypeError, ValueError):
            logger.warning("⚠️ Restore: advance_transcript_offset was not an int — defaulted to 0")

        # lastexplicitreftime is saved as 0.0 on close so it never falsely
        # 'expires' a context on restore.
        _last_explicit_ref_time = float(data.get("last_explicit_ref_time", 0.0))
        logger.info(f"✅ Restored: last_explicit_ref_time = {_last_explicit_ref_time}")

    except Exception as e:
        logger.error(f"❌ restore_session failed unexpectedly: {e}")
