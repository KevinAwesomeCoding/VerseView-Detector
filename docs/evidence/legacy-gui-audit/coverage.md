# Legacy GUI audit coverage appendix

This is static source coverage, not a record of clicking or executing every control.
Source line numbers and source hashes are in inventory.json. Constructor/factory
sites can create multiple controls in loops; their count is not a feature count.

## All function definitions, including nested callbacks

| Source | Definition | Functional group |
| --- | --- | --- |
| vv_gui.py:39 | `_get_python_executable` | startup / bootstrap |
| vv_gui.py:74 | `_read_build_version` | startup / bootstrap |
| vv_gui.py:102 | `__init__` | startup / bootstrap |
| vv_gui.py:107 | `emit` | startup / bootstrap |
| vv_gui.py:151 | `__init__` | startup / bootstrap |
| vv_gui.py:222 | `_f` | visual helpers |
| vv_gui.py:226 | `_section_card` | visual helpers |
| vv_gui.py:244 | `_card_field` | visual helpers |
| vv_gui.py:259 | `_neutral_button` | visual helpers |
| vv_gui.py:272 | `_build_ui` | main screen / nested callbacks |
| vv_gui.py:463 | `_on_divider_drag` | main screen / nested callbacks |
| vv_gui.py:567 | `_on_sugg_divider_drag` | main screen / nested callbacks |
| vv_gui.py:648 | `sep_label` | main screen / nested callbacks |
| vv_gui.py:660 | `add_entry` | main screen / nested callbacks |
| vv_gui.py:668 | `add_option` | main screen / nested callbacks |
| vv_gui.py:686 | `_on_ml_raw_toggle` | main screen / nested callbacks |
| vv_gui.py:698 | `_on_lang_changed` | main screen / nested callbacks |
| vv_gui.py:898 | `_build_bot_tab` | Discord setup and runtime |
| vv_gui.py:920 | `field_row` | Discord setup and runtime |
| vv_gui.py:940 | `_toggle_token_vis` | Discord setup and runtime |
| vv_gui.py:1004 | `_load_bot_config` | Discord setup and runtime |
| vv_gui.py:1016 | `_save_bot_config` | Discord setup and runtime |
| vv_gui.py:1020 | `_auto_start_bot` | Discord setup and runtime |
| vv_gui.py:1025 | `_on_bridge_ready` | Discord setup and runtime |
| vv_gui.py:1032 | `_update` | Discord setup and runtime |
| vv_gui.py:1052 | `_bot_log` | Discord setup and runtime |
| vv_gui.py:1053 | `_append` | Discord setup and runtime |
| vv_gui.py:1060 | `_ensure_bridge` | Discord setup and runtime |
| vv_gui.py:1079 | `_start_bot` | Discord setup and runtime |
| vv_gui.py:1150 | `_stream` | Discord setup and runtime |
| vv_gui.py:1157 | `_stop_bot` | Discord setup and runtime |
| vv_gui.py:1163 | `_on_bot_stopped` | Discord setup and runtime |
| vv_gui.py:1180 | `_opt_checkbox` | Options / live engine mutations |
| vv_gui.py:1190 | `_build_options` | Options / live engine mutations |
| vv_gui.py:1202 | `_update_conf` | Options / live engine mutations |
| vv_gui.py:1319 | `_on_dual_stt_toggle` | dual-STT controls |
| vv_gui.py:1326 | `_toggle_dual_stt` | dual-STT controls |
| vv_gui.py:1338 | `_build_dual_stt` | dual-STT controls |
| vv_gui.py:1384 | `_on_sec_lang_changed` | dual-STT controls |
| vv_gui.py:1402 | `_toggle_options` | dual-STT controls |
| vv_gui.py:1415 | `_build_advanced` | advanced settings / local models |
| vv_gui.py:1740 | `_set_local_llm_state` | advanced settings / local models |
| vv_gui.py:1751 | `_on_local_llm_toggle` | advanced settings / local models |
| vv_gui.py:1757 | `_local_llm_conn_fields` | advanced settings / local models |
| vv_gui.py:1796 | `_test_local_llm` | advanced settings / local models |
| vv_gui.py:1816 | `_done` | advanced settings / local models |
| vv_gui.py:1830 | `_task` | advanced settings / local models |
| vv_gui.py:1843 | `_warm_local_llm` | advanced settings / local models |
| vv_gui.py:1866 | `_done` | advanced settings / local models |
| vv_gui.py:1880 | `_task` | advanced settings / local models |
| vv_gui.py:1893 | `_auto_warm_local_llm` | advanced settings / local models |
| vv_gui.py:1909 | `_toggle_advanced` | advanced settings / local models |
| vv_gui.py:1925 | `_record_panic_key` | panic shortcut |
| vv_gui.py:1934 | `on_press` | panic shortcut |
| vv_gui.py:1946 | `recorder` | panic shortcut |
| vv_gui.py:1959 | `_panic_shortcut` | panic shortcut |
| vv_gui.py:1966 | `_on_panic_recorded` | panic shortcut |
| vv_gui.py:1982 | `_load_into_ui` | settings load / collect |
| vv_gui.py:2178 | `_setup_role_model` | settings load / collect |
| vv_gui.py:2234 | `_collect_settings` | settings load / collect |
| vv_gui.py:2336 | `_sync_settings_on_launch` | sync / settings import-export / Google credentials |
| vv_gui.py:2344 | `_sync_settings_now` | sync / settings import-export / Google credentials |
| vv_gui.py:2358 | `_do_settings_sync` | sync / settings import-export / Google credentials |
| vv_gui.py:2413 | `_save_settings` | sync / settings import-export / Google credentials |
| vv_gui.py:2419 | `_export_settings` | sync / settings import-export / Google credentials |
| vv_gui.py:2441 | `_import_settings` | sync / settings import-export / Google credentials |
| vv_gui.py:2459 | `_import_gcp_credentials` | sync / settings import-export / Google credentials |
| vv_gui.py:2489 | `_update_gcp_cred_status` | sync / settings import-export / Google credentials |
| vv_gui.py:2529 | `_set_context` | context / microphones |
| vv_gui.py:2556 | `_refresh_context` | context / microphones |
| vv_gui.py:2560 | `is_inside` | context / microphones |
| vv_gui.py:2577 | `_populate_mics` | context / microphones |
| vv_gui.py:2600 | `_attach_log_handler` | transcript / diagnostic display |
| vv_gui.py:2606 | `_set_dual_log_view` | transcript / diagnostic display |
| vv_gui.py:2610 | `_update_log_headers` | transcript / diagnostic display |
| vv_gui.py:2620 | `_set_dual_log_view` | transcript / diagnostic display |
| vv_gui.py:2641 | `_append_log` | transcript / diagnostic display |
| vv_gui.py:2650 | `_do` | transcript / diagnostic display |
| vv_gui.py:2667 | `_clear_log` | transcript / diagnostic display |
| vv_gui.py:2676 | `_update_delivery_diagnostics` | transcript / diagnostic display |
| vv_gui.py:2694 | `_lang_code` | normalizers |
| vv_gui.py:2705 | `_sec_lang_code` | normalizers |
| vv_gui.py:2715 | `_stt_engine_code` | normalizers |
| vv_gui.py:2730 | `_sec_engine_code` | normalizers |
| vv_gui.py:2746 | `_mic_index` | normalizers |
| vv_gui.py:2750 | `_safe_int` | normalizers |
| vv_gui.py:2755 | `_safe_float` | normalizers |
| vv_gui.py:2761 | `_role_code` | normalizers |
| vv_gui.py:2769 | `_desktop_state` | desktop controls / approval |
| vv_gui.py:2783 | `_desktop_start` | desktop controls / approval |
| vv_gui.py:2787 | `_desktop_tick` | desktop controls / approval |
| vv_gui.py:2799 | `_desktop_confirm` | desktop controls / approval |
| vv_gui.py:2804 | `_user_confirm_callback` | desktop controls / approval |
| vv_gui.py:2809 | `_ask` | desktop controls / approval |
| vv_gui.py:2826 | `_get_scheduled_language` | schedule |
| vv_gui.py:2832 | `_apply_schedule_dual_stt` | schedule |
| vv_gui.py:2887 | `_check_restore_session` | recovery / startup automation |
| vv_gui.py:2980 | `_check_auto_start` | recovery / startup automation |
| vv_gui.py:3004 | `_start` | engine start-stop |
| vv_gui.py:3188 | `_run_engine` | engine start-stop |
| vv_gui.py:3202 | `_stop` | engine start-stop |
| vv_gui.py:3209 | `_on_stopped` | engine start-stop |
| vv_gui.py:3238 | `_get_sermon_notes_dir` | notes / memory reset |
| vv_gui.py:3253 | `_generate_summary` | notes / memory reset |
| vv_gui.py:3254 | `_task` | notes / memory reset |
| vv_gui.py:3262 | `_show_summary_window` | notes / memory reset |
| vv_gui.py:3276 | `_save` | notes / memory reset |
| vv_gui.py:3311 | `_clear_sermon_memory` | notes / memory reset |
| vv_gui.py:3325 | `_check_for_update_bg` | updater |
| vv_gui.py:3329 | `_run` | updater |
| vv_gui.py:3336 | `_manual_check_update` | updater |
| vv_gui.py:3346 | `_run` | updater |
| vv_gui.py:3360 | `_show_update_badge` | updater |
| vv_gui.py:3371 | `_show_update_dialog` | updater |
| vv_gui.py:3473 | `_apply_update` | updater |
| vv_gui.py:3482 | `on_progress` | updater |
| vv_gui.py:3486 | `on_done` | updater |
| vv_gui.py:3491 | `on_error` | updater |
| vv_gui.py:3503 | `_on_atem_toggle` | ATEM integration |
| vv_gui.py:3522 | `_scan_atem_ip` | ATEM integration |
| vv_gui.py:3528 | `_run` | ATEM integration |
| vv_gui.py:3541 | `_toggle_atem_keyer_manual` | ATEM integration |
| vv_gui.py:3551 | `_connect_and_fire` | ATEM integration |
| vv_gui.py:3583 | `_turn_off` | ATEM integration |
| vv_gui.py:3619 | `_toggle_pin` | pin / worship / visual helper |
| vv_gui.py:3628 | `_toggle_worship_mode` | pin / worship / visual helper |
| vv_gui.py:3639 | `_sync_scrollframe_bg` | pin / worship / visual helper |
| vv_gui.py:3645 | `_patch` | pin / worship / visual helper |
| vv_gui.py:3664 | `_clear_verse_history` | history / manual verse / chapter browser |
| vv_gui.py:3693 | `_resolve_book` | history / manual verse / chapter browser |
| vv_gui.py:3714 | `_send_manual_verse` | history / manual verse / chapter browser |
| vv_gui.py:3791 | `_update_chapter_browser_loop` | history / manual verse / chapter browser |
| vv_gui.py:3814 | `_load` | history / manual verse / chapter browser |
| vv_gui.py:3823 | `_populate_chapter_browser` | history / manual verse / chapter browser |
| vv_gui.py:3851 | `_send_chapter_verse` | history / manual verse / chapter browser |
| vv_gui.py:3877 | `_open_verse_popup` | history / manual verse / chapter browser |
| vv_gui.py:3891 | `_load_verse` | history / manual verse / chapter browser |
| vv_gui.py:3893 | `_update` | history / manual verse / chapter browser |
| vv_gui.py:3905 | `_resend` | history / manual verse / chapter browser |
| vv_gui.py:3937 | `_build_suggestions_panel` | suggestions |
| vv_gui.py:4006 | `_refresh_watcher_status` | suggestions |
| vv_gui.py:4046 | `_on_watcher_suggestion` | suggestions |
| vv_gui.py:4066 | `_render_suggestion` | suggestions |
| vv_gui.py:4122 | `_style_suggestion_row` | suggestions |
| vv_gui.py:4150 | `_send_suggestion` | suggestions |
| vv_gui.py:4188 | `_remove_suggestion_by_ref` | suggestions |
| vv_gui.py:4196 | `_destroy_sugg_row` | suggestions |
| vv_gui.py:4202 | `_expire_suggestions_loop` | suggestions |
| vv_gui.py:4220 | `_clear_suggestions` | suggestions |
| vv_gui.py:4228 | `_hide_sugg_placeholder` | suggestions |
| vv_gui.py:4235 | `_show_sugg_placeholder` | suggestions |
| vv_gui.py:4245 | `_build_session_snapshot` | checkpoint / close / emergency |
| vv_gui.py:4269 | `_autosave_session_loop` | checkpoint / close / emergency |
| vv_gui.py:4291 | `_emergency_quit` | checkpoint / close / emergency |
| vv_gui.py:4346 | `_history_badge` | checkpoint / close / emergency |
| vv_gui.py:4368 | `_update_history_loop` | checkpoint / close / emergency |
| vv_gui.py:4419 | `_emergency_save` | checkpoint / close / emergency |
| vv_gui.py:4475 | `on_closing` | checkpoint / close / emergency |
| vv_gui.py:4495 | `_finish_close` | checkpoint / close / emergency |
| vv_gui.py:4552 | `_run_bot_mode` | entry point / signals |
| vv_gui.py:4588 | `_signal_handler` | entry point / signals |
| live_points_app.py:16 | `__init__` | Live Points / audience display |
| live_points_app.py:35 | `_resize_wraplength` | Live Points / audience display |
| live_points_app.py:38 | `update_text` | Live Points / audience display |
| live_points_app.py:44 | `__init__` | Live Points / audience display |
| live_points_app.py:49 | `_build_tab` | Live Points / audience display |
| live_points_app.py:140 | `_toggle_audience_display` | Live Points / audience display |
| live_points_app.py:162 | `_reset_display_button` | Live Points / audience display |
| live_points_app.py:170 | `update_live_points` | Live Points / audience display |
| live_points_app.py:171 | `_update` | Live Points / audience display |
| live_points_app.py:179 | `get_prompt` | Live Points / audience display |
| live_points_app.py:182 | `set_prompt` | Live Points / audience display |
| live_points_app.py:186 | `get_screen` | Live Points / audience display |
| live_points_app.py:189 | `set_screen` | Live Points / audience display |
| live_points_app.py:192 | `get_current_display` | Live Points / audience display |
| live_points_app.py:196 | `is_live_llm_enabled` | Live Points / audience display |
| live_points_app.py:200 | `get_live_llm_enabled` | Live Points / audience display |
| live_points_app.py:204 | `set_live_llm_enabled` | Live Points / audience display |

## Inventoried control/factory call sites

| Source | Parent function | Kind | Label or field / callback |
| --- | --- | --- | --- |
| vv_gui.py:253 | `_card_field` | CTkEntry | placeholder |
| vv_gui.py:267 | `_neutral_button` | CTkButton | text → command |
| vv_gui.py:273 | `_build_ui` | CTkTabview | self |
| vv_gui.py:319 | `_build_ui` | CTkButton | '▶  Start' → self._start |
| vv_gui.py:327 | `_build_ui` | CTkButton | '■  Stop' → self._stop |
| vv_gui.py:348 | `_build_ui` | CTkButton | '⏻' → self._emergency_quit |
| vv_gui.py:361 | `_build_ui` | CTkButton | '📌' → self._toggle_pin |
| vv_gui.py:372 | `_build_ui` | CTkButton | '⟳ Check for Update' → self._manual_check_update |
| vv_gui.py:381 | `_build_ui` | CTkButton | '🎵 Worship' → self._toggle_worship_mode |
| vv_gui.py:433 | `_build_ui` | CTkTextbox | self._log_container |
| vv_gui.py:447 | `_build_ui` | CTkTextbox | self._log_container |
| vv_gui.py:492 | `_build_ui` | CTkButton | 'Clear' → self._clear_verse_history |
| vv_gui.py:553 | `_build_ui` | CTkEntry | 'e.g. gen 3 2  or  john 3:16' |
| vv_gui.py:602 | `_build_ui` | CTkTextbox | diagnostics |
| vv_gui.py:613 | `_build_ui` | _neutral_button | action_frame; 'Clear Log'; self._clear_log |
| vv_gui.py:618 | `_build_ui` | CTkButton | '📝  Generate Sermon Notes' → self._generate_summary |
| vv_gui.py:626 | `_build_ui` | CTkButton | '🗑  Clear Memory' → self._clear_sermon_memory |
| vv_gui.py:662 | `add_entry` | CTkEntry | placeholder |
| vv_gui.py:671 | `add_option` | CTkOptionMenu | var |
| vv_gui.py:678 | `_build_ui` | sep_label | 'Language' |
| vv_gui.py:679 | `_build_ui` | add_option | ['English', 'Malayalam', 'Hindi', 'Multi-Language'] |
| vv_gui.py:690 | `_build_ui` | CTkCheckBox | 'Show Malayalam 🇮🇳' → _on_ml_raw_toggle |
| vv_gui.py:727 | `_build_ui` | sep_label | 'STT Engine' |
| vv_gui.py:728 | `_build_ui` | add_option | ['Deepgram', 'AssemblyAI (Universal-3 Pro)', 'AssemblyAI (Universal-3 Multilingual)', 'Gladia', 'Google Cloud STT', 'Local Whisper'] |
| vv_gui.py:743 | `_build_ui` | CTkButton | '▶   Dual STT Mode' → self._toggle_dual_stt |
| vv_gui.py:760 | `_build_ui` | sep_label | 'Bible Translation' |
| vv_gui.py:761 | `_build_ui` | add_option | ['KJV', 'WEB', 'ASV', 'NET', 'NLT', 'NIV', 'ESV', 'NASB', 'NKJV', 'AMP', 'CSB', 'MSG', 'OEB', 'WEBBE'] |
| vv_gui.py:769 | `_build_ui` | sep_label | 'Microphone' |
| vv_gui.py:771 | `_build_ui` | CTkOptionMenu | self.mic_var |
| vv_gui.py:774 | `_build_ui` | _neutral_button | right; '↺  Refresh Mics'; self._populate_mics |
| vv_gui.py:781 | `_build_ui` | sep_label | 'VerseView URL' |
| vv_gui.py:782 | `_build_ui` | add_entry | 'http://localhost:50010/control.html' |
| vv_gui.py:786 | `_build_ui` | sep_label | '📌  Current Context' |
| vv_gui.py:800 | `_build_ui` | CTkEntry | 'e.g. John' |
| vv_gui.py:801 | `_build_ui` | CTkEntry | 'e.g. 3' |
| vv_gui.py:802 | `_build_ui` | CTkEntry | 'e.g. 16' |
| vv_gui.py:810 | `_build_ui` | CTkButton | '📌  Set Context' → self._set_context |
| vv_gui.py:821 | `_build_ui` | CTkButton | '▶   Options' → self._toggle_options |
| vv_gui.py:838 | `_build_ui` | CTkButton | '▶   Advanced Settings' → self._toggle_advanced |
| vv_gui.py:853 | `_build_ui` | CTkButton | '💾  Save Settings' → self._save_settings |
| vv_gui.py:861 | `_build_ui` | _neutral_button | right; '📤  Export Settings'; self._export_settings |
| vv_gui.py:866 | `_build_ui` | _neutral_button | right; '📥  Import Settings'; self._import_settings |
| vv_gui.py:924 | `field_row` | CTkEntry | placeholder |
| vv_gui.py:937 | `_build_bot_tab` | CTkEntry | 'Bot token' |
| vv_gui.py:945 | `_build_bot_tab` | CTkButton | '👁' → _toggle_token_vis |
| vv_gui.py:963 | `_build_bot_tab` | CTkButton | '▶  Start Bot' → self._start_bot |
| vv_gui.py:971 | `_build_bot_tab` | CTkButton | '■  Stop Bot' → self._stop_bot |
| vv_gui.py:993 | `_build_bot_tab` | CTkTextbox | tab |
| vv_gui.py:1182 | `_opt_checkbox` | CTkCheckBox | text → command |
| vv_gui.py:1194 | `_build_options` | _section_card | f; 'Detection Behavior' |
| vv_gui.py:1206 | `_build_options` | CTkSlider | self.conf_var → _update_conf |
| vv_gui.py:1214 | `_build_options` | _opt_checkbox | card; 2; 'Require Manual Confirmation (Ask Y/N for low-confidence verses)'; self.manual_var; lambda: setattr(engine, 'REQUIRE_MANUAL_CONFIRM', self.manual_var.get()) |
| vv_gui.py:1218 | `_build_options` | _opt_checkbox | card; 3; 'Require Verification (Hear verse twice before displaying)'; self.verify_var; lambda: setattr(engine, 'REQUIRE_VERIFY', self.verify_var.get()) |
| vv_gui.py:1222 | `_build_options` | _opt_checkbox | card; 4; 'Verse Interrupt (wait for speaker to say verse; 60s timeout; new ref cancels)'; self.verse_interrupt_var; lambda: setattr(engine, 'VERSE_INTERRUPT_ENABLED', self.verse_interrupt_var.get()) |
| vv_gui.py:1226 | `_build_options` | _opt_checkbox | card; 5; "Spoken Numeral Mode ('John three sixteen' → John 3:16, no 'verse' keyword)"; self.spoken_numeral_var; lambda: setattr(engine, 'SPOKEN_NUMERAL_MODE', self.spoken_numeral_var.get()) |
| vv_gui.py:1230 | `_build_options` | _opt_checkbox | card; 6; "Smart Amen (auto-clear screen on 'Let us pray')"; self.smart_amen_var; lambda: setattr(engine, 'SMART_AMEN_ENABLED', self.smart_amen_var.get()) |
| vv_gui.py:1236 | `_build_options` | _section_card | f; 'Language & Transliteration' |
| vv_gui.py:1238 | `_build_options` | CTkCheckBox | 'Malayalam Transliteration — Manglish / Romanized output (Sarvam translit mode)' → lambda: setattr(engine, 'MALAYALAM_TRANSLITERATION', self.ml_translit_var.get()) |
| vv_gui.py:1249 | `_build_options` | _section_card | f; 'Session & Startup' |
| vv_gui.py:1251 | `_build_options` | _opt_checkbox | card; 0; 'Auto-Save Sermon Notes on App Close'; self.auto_save_var |
| vv_gui.py:1253 | `_build_options` | _opt_checkbox | card; 1; 'Auto-Start on Launch (starts engine automatically)'; self.auto_start_var |
| vv_gui.py:1255 | `_build_options` | _opt_checkbox | card; 2; 'Smart Schedule (auto-set language by day & time)'; self.smart_schedule_var |
| vv_gui.py:1263 | `_build_options` | _section_card | f; '🎬  ATEM Chroma Key Overlay' |
| vv_gui.py:1265 | `_build_options` | _opt_checkbox | card; 0; 'Enable ATEM Keyer on Verse Display'; self.atem_var; self._on_atem_toggle |
| vv_gui.py:1273 | `_build_options` | CTkEntry | 'Auto (or enter IP)' |
| vv_gui.py:1275 | `_build_options` | CTkButton | '🔍' → self._scan_atem_ip |
| vv_gui.py:1284 | `_build_options` | CTkEntry | '5.0' |
| vv_gui.py:1290 | `_build_options` | CTkButton | '◼  Keyer: OFF' → self._toggle_atem_keyer_manual |
| vv_gui.py:1301 | `_build_options` | _section_card | f; 'Panic Keybind' |
| vv_gui.py:1304 | `_build_options` | CTkButton | 'Panic Key: esc' → self._record_panic_key |
| vv_gui.py:1347 | `_build_dual_stt` | CTkCheckBox | 'Enable Dual STT (run a second STT stream in parallel)' → self._on_dual_stt_toggle |
| vv_gui.py:1363 | `_build_dual_stt` | CTkOptionMenu | self.sec_lang_var |
| vv_gui.py:1376 | `_build_dual_stt` | CTkOptionMenu | self.sec_engine_var |
| vv_gui.py:1419 | `_build_advanced` | _section_card | f; 'Audio & Timing' |
| vv_gui.py:1430 | `_build_advanced` | _card_field | card; i; lbl |
| vv_gui.py:1437 | `_build_advanced` | CTkOptionMenu | self.llm_var |
| vv_gui.py:1442 | `_build_advanced` | _section_card | f; 'API Keys' |
| vv_gui.py:1460 | `_build_advanced` | _card_field | card; j; lbl |
| vv_gui.py:1468 | `_build_advanced` | _section_card | f; 'Google Cloud Credentials' |
| vv_gui.py:1469 | `_build_advanced` | _neutral_button | card; '📁  Import Service-Account JSON…'; self._import_gcp_credentials |
| vv_gui.py:1482 | `_build_advanced` | _section_card | f; 'Settings Sync' |
| vv_gui.py:1483 | `_build_advanced` | _card_field | card; 0; 'Sync URL' |
| vv_gui.py:1486 | `_build_advanced` | _neutral_button | card; '⬇  Pull Now'; self._sync_settings_now |
| vv_gui.py:1497 | `_build_advanced` | _section_card | f; '🖥️  Local LLM (Ollama)' |
| vv_gui.py:1499 | `_build_advanced` | CTkCheckBox | 'Use Local LLM (off by default — cloud providers unchanged)' → self._on_local_llm_toggle |
| vv_gui.py:1519 | `_build_advanced` | _card_field | sub; 0; 'Local Ollama Endpoint' |
| vv_gui.py:1542 | `_build_advanced` | _card_field | sub; 2 + i; lbl |
| vv_gui.py:1557 | `_build_advanced` | _neutral_button | sub; '🔌  Test Connection'; self._test_local_llm |
| vv_gui.py:1572 | `_build_advanced` | _neutral_button | sub; '🔥  Warm Selected Local Model'; self._warm_local_llm |
| vv_gui.py:1584 | `_build_advanced` | CTkCheckBox | 'Warm Local Model at Service Start (off by default)' |
| vv_gui.py:1632 | `_build_advanced` | CTkOptionMenu | var |
| vv_gui.py:1644 | `_build_advanced` | CTkOptionMenu | dd_var |
| vv_gui.py:1656 | `_build_advanced` | CTkEntry | 'e.g. my-custom-model' |
| vv_gui.py:1686 | `_build_advanced` | CTkOptionMenu | self.local_llm_failure_var |
| vv_gui.py:1706 | `_build_advanced` | _section_card | f; 'Contextual Watcher (Experimental)' |
| vv_gui.py:1708 | `_build_advanced` | CTkCheckBox | 'Enable Contextual Verse Watcher (AI suggestions — off by default)' |
| vv_gui.py:1720 | `_build_advanced` | CTkOptionMenu | self.watcher_provider_var |
| vv_gui.py:1736 | `_build_advanced` | _card_field | card; 2 + k; lbl |
| vv_gui.py:3271 | `_show_summary_window` | CTkTextbox | win |
| vv_gui.py:3303 | `_show_summary_window` | CTkButton | '💾 Save to File' → _save |
| vv_gui.py:3437 | `_show_update_dialog` | CTkTextbox | notes_frame |
| vv_gui.py:3460 | `_show_update_dialog` | CTkButton | 'Install Update' → lambda: self._apply_update(win, apply_btn, info) |
| vv_gui.py:3467 | `_show_update_dialog` | CTkButton | 'Later' → win.destroy |
| vv_gui.py:3838 | `_populate_chapter_browser` | CTkButton | ref → lambda r=ref: self._send_chapter_verse(r) |
| vv_gui.py:3886 | `_open_verse_popup` | CTkTextbox | win |
| vv_gui.py:3913 | `_open_verse_popup` | CTkButton | '🔁 Send Again' → _resend |
| vv_gui.py:3961 | `_build_suggestions_panel` | CTkButton | 'Clear' → self._clear_suggestions |
| vv_gui.py:4099 | `_render_suggestion` | CTkButton | row → lambda r=ref: self._send_suggestion(r) |
| vv_gui.py:4391 | `_update_history_loop` | CTkButton | lbl → lambda r=ref: self._open_verse_popup(r) |
| live_points_app.py:63 | `_build_tab` | CTkButton | '🖥️  Launch Audience Display' → self._toggle_audience_display |
| live_points_app.py:73 | `_build_tab` | CTkCheckBox | 'Enable AI Live Outline (tokens)' |
| live_points_app.py:88 | `_build_tab` | CTkOptionMenu | self.screen_var |
| live_points_app.py:109 | `_build_tab` | CTkTextbox | self.parent |
| live_points_app.py:123 | `_build_tab` | CTkTextbox | self.parent |

## Every event, timer and command binding

| Source | Function | Binding |
| --- | --- | --- |
| vv_gui.py:195 | `__init__` | `self.after(250, self._desktop_tick)` |
| vv_gui.py:199 | `__init__` | `self.bind('<Shift-Escape>', lambda e: self._panic_shortcut())` |
| vv_gui.py:201 | `__init__` | `self.after(500, self._check_auto_start)` |
| vv_gui.py:203 | `__init__` | `self.after(800, self._check_restore_session)` |
| vv_gui.py:205 | `__init__` | `self.after(1000, self._update_history_loop)` |
| vv_gui.py:206 | `__init__` | `self.after(1500, self._update_chapter_browser_loop)` |
| vv_gui.py:211 | `__init__` | `self.after(self._AUTOSAVE_INTERVAL_MS, self._autosave_session_loop)` |
| vv_gui.py:213 | `__init__` | `self.after(15000, self._check_for_update_bg)` |
| vv_gui.py:215 | `__init__` | `self.after(3000, self._sync_settings_on_launch)` |
| vv_gui.py:476 | `_build_ui` | `self._log_divider.bind('<B1-Motion>', _on_divider_drag)` |
| vv_gui.py:477 | `_build_ui` | `self._log_divider.bind('<Button-1>', _on_divider_drag)` |
| vv_gui.py:519 | `_build_ui` | `self.after(200, lambda: self._sync_scrollframe_bg(self.history_scroll_frame, _log_fg))` |
| vv_gui.py:546 | `_build_ui` | `self.after(200, lambda: self._sync_scrollframe_bg(self.chapter_browser_frame, _log_fg))` |
| vv_gui.py:560 | `_build_ui` | `self.manual_verse_entry.bind('<Return>', lambda e: self._send_manual_verse())` |
| vv_gui.py:587 | `_build_ui` | `self._sugg_divider.bind('<B1-Motion>', _on_sugg_divider_drag)` |
| vv_gui.py:588 | `_build_ui` | `self._sugg_divider.bind('<Button-1>', _on_sugg_divider_drag)` |
| vv_gui.py:606 | `_build_ui` | `self.after(500, self._update_delivery_diagnostics)` |
| vv_gui.py:723 | `_build_ui` | `self.lang_menu.configure(command=_on_lang_changed)` |
| vv_gui.py:738 | `_build_ui` | `self.stt_engine_menu.configure(command=lambda _: self._update_log_headers())` |
| vv_gui.py:890 | `_build_ui` | `self.after(2000, self._refresh_context)` |
| vv_gui.py:1050 | `_on_bridge_ready` | `self.after(0, _update)` |
| vv_gui.py:1058 | `_bot_log` | `self.after(0, _append)` |
| vv_gui.py:1153 | `_stream` | `self.after(0, self._on_bot_stopped)` |
| vv_gui.py:1399 | `_build_dual_stt` | `self.sec_lang_menu.configure(command=_on_sec_lang_changed)` |
| vv_gui.py:1400 | `_build_dual_stt` | `self.sec_engine_menu.configure(command=lambda _: self._update_log_headers())` |
| vv_gui.py:1839 | `_task` | `self.after(0, lambda: _done(ok, msg, elapsed))` |
| vv_gui.py:1889 | `_task` | `self.after(0, lambda: _done(ok, msg, elapsed))` |
| vv_gui.py:1902 | `_auto_warm_local_llm` | `self.after(0, lambda: self._append_log(f'❌ Local LLM auto-warm error: {e}'))` |
| vv_gui.py:1907 | `_auto_warm_local_llm` | `self.after(0, lambda line=line: self._append_log(line))` |
| vv_gui.py:1941 | `on_press` | `self.after(0, lambda: self._on_panic_recorded(key_name))` |
| vv_gui.py:1953 | `recorder` | `self.after(0, lambda: self._on_panic_recorded(self.panic_var.get()))` |
| vv_gui.py:2394 | `_do_settings_sync` | `self.after(0, self._load_into_ui)` |
| vv_gui.py:2401 | `_do_settings_sync` | `self.after(0, lambda: mb.showinfo('Sync Complete', msg))` |
| vv_gui.py:2407 | `_do_settings_sync` | `self.after(0, lambda: mb.showerror('Sync Failed', err))` |
| vv_gui.py:2410 | `_do_settings_sync` | `self.after(0, lambda: self.btn_sync_now.configure(state='normal', text='⬇  Pull Now'))` |
| vv_gui.py:2574 | `_refresh_context` | `self.after(2000, self._refresh_context)` |
| vv_gui.py:2664 | `_append_log` | `self.after(0, _do)` |
| vv_gui.py:2691 | `_update_delivery_diagnostics` | `self.after(500, self._update_delivery_diagnostics)` |
| vv_gui.py:2797 | `_desktop_tick` | `self.after(250, self._desktop_tick)` |
| vv_gui.py:2818 | `_user_confirm_callback` | `self.after(0, _ask)` |
| vv_gui.py:2994 | `_check_auto_start` | `self.after(3000, self._start)` |
| vv_gui.py:3001 | `_check_auto_start` | `self.after(1500, self._start_bot)` |
| vv_gui.py:3174 | `_start` | `self.after(2000, self._refresh_context)` |
| vv_gui.py:3196 | `_run_engine` | `self.after(0, lambda msg=err_msg: mb.showerror('Engine Error', msg))` |
| vv_gui.py:3199 | `_run_engine` | `self.after(0, self._on_stopped)` |
| vv_gui.py:3232 | `_on_stopped` | `self.after(200, self._finish_close)` |
| vv_gui.py:3257 | `_task` | `self.after(0, lambda: self._show_summary_window(summary))` |
| vv_gui.py:3269 | `_show_summary_window` | `self.after(100, lambda: win.attributes('-topmost', False))` |
| vv_gui.py:3333 | `_run` | `self.after(0, self._show_update_badge)` |
| vv_gui.py:3350 | `_run` | `self.after(0, self._show_update_badge)` |
| vv_gui.py:3351 | `_run` | `self.after(0, self._show_update_dialog)` |
| vv_gui.py:3353 | `_run` | `self.after(0, lambda: self.btn_update.configure(text='✅ Up to date', state='normal'))` |
| vv_gui.py:3356 | `_run` | `self.after(4000, lambda: self.btn_update.configure(text='⟳ Check for Update'))` |
| vv_gui.py:3362 | `_show_update_badge` | `self.btn_update.configure(text='🔄 Update Available', fg_color=COL_WARN, hover_color=COL_WARN_HOVER, border_width=0, text_color='white', state='normal', command=self._show_update_dialog)` |
| vv_gui.py:3393 | `_show_update_dialog` | `self.after(200, lambda: win.attributes('-topmost', False))` |
| vv_gui.py:3483 | `on_progress` | `self.after(0, lambda: self._upd_progress.set(pct / 100))` |
| vv_gui.py:3484 | `on_progress` | `self.after(0, lambda: self._upd_status.configure(text=f'Downloading... {pct}%'))` |
| vv_gui.py:3487 | `on_done` | `self.after(0, lambda: self._upd_status.configure(text='✅ Done — restarting...'))` |
| vv_gui.py:3488 | `on_done` | `self.after(0, lambda: self._upd_progress.set(1.0))` |
| vv_gui.py:3489 | `on_done` | `self.after(1500, _updater.restart_app)` |
| vv_gui.py:3492 | `on_error` | `self.after(0, lambda: self._upd_status.configure(text=f'❌ {msg[:80]}', text_color='#cc4444'))` |
| vv_gui.py:3494 | `on_error` | `self.after(0, lambda: apply_btn.configure(state='normal', text='Retry'))` |
| vv_gui.py:3531 | `_run` | `self.after(0, lambda: self.atem_ip_entry.delete(0, 'end'))` |
| vv_gui.py:3532 | `_run` | `self.after(0, lambda: self.atem_ip_entry.insert(0, ip))` |
| vv_gui.py:3536 | `_run` | `self.after(0, lambda: self.atem_scan_btn.configure(text='🔍', state='normal'))` |
| vv_gui.py:3556 | `_connect_and_fire` | `self.after(0, lambda: self.atem_test_btn.configure(text='◼  Keyer: OFF', fg_color='#4a4a4a'))` |
| vv_gui.py:3567 | `_connect_and_fire` | `self.after(0, lambda: self.atem_test_btn.configure(text='🟢  Keyer: ON', fg_color='#2a7a2a', hover_color='#226622'))` |
| vv_gui.py:3571 | `_connect_and_fire` | `self.after(0, lambda: self.atem_test_btn.configure(text='◼  Keyer: OFF', fg_color='#4a4a4a'))` |
| vv_gui.py:3576 | `_connect_and_fire` | `self.after(0, lambda: self.atem_test_btn.configure(text='◼  Keyer: OFF', fg_color='#4a4a4a'))` |
| vv_gui.py:3613 | `_turn_off` | `self.after(0, lambda: self.atem_test_btn.configure(text='◼  Keyer: OFF', fg_color='#4a4a4a', hover_color='#555555'))` |
| vv_gui.py:3816 | `_load` | `self.after(0, lambda: self._populate_chapter_browser(b, c, verses))` |
| vv_gui.py:3821 | `_update_chapter_browser_loop` | `self.after(2000, self._update_chapter_browser_loop)` |
| vv_gui.py:3884 | `_open_verse_popup` | `self.after(150, lambda: win.attributes('-topmost', False))` |
| vv_gui.py:3901 | `_load_verse` | `self.after(0, _update)` |
| vv_gui.py:4002 | `_build_suggestions_panel` | `self.after(5000, self._expire_suggestions_loop)` |
| vv_gui.py:4004 | `_build_suggestions_panel` | `self.after(2000, self._refresh_watcher_status)` |
| vv_gui.py:4043 | `_refresh_watcher_status` | `self.after(2000, self._refresh_watcher_status)` |
| vv_gui.py:4062 | `_on_watcher_suggestion` | `self.after(0, lambda: self._render_suggestion(ref, confidence, status_val, stream, reasoning))` |
| vv_gui.py:4218 | `_expire_suggestions_loop` | `self.after(5000, self._expire_suggestions_loop)` |
| vv_gui.py:4289 | `_autosave_session_loop` | `self.after(self._AUTOSAVE_INTERVAL_MS, self._autosave_session_loop)` |
| vv_gui.py:4416 | `_update_history_loop` | `self.after(1000, self._update_history_loop)` |
| vv_gui.py:4581 | `module` | `app.protocol('WM_DELETE_WINDOW', app.on_closing)` |
| live_points_app.py:22 | `__init__` | `self.bind('<Escape>', lambda e: self.destroy())` |
| live_points_app.py:33 | `__init__` | `self.bind('<Configure>', self._resize_wraplength)` |
| live_points_app.py:157 | `_toggle_audience_display` | `self.display_win.bind('<Destroy>', lambda e: self._reset_display_button())` |
| live_points_app.py:176 | `update_live_points` | `self.parent.after(0, _update)` |

## Passive widgets, containers, child windows and progress bars

These additional constructor sites complete the explicit CTk widget inventory.
Fonts, Tk variables and layout method calls are not counted as widget sites.

| Source | Parent function | Kind | Text |
| --- | --- | --- | --- |
| vv_gui.py:231 | `_section_card` | CTkLabel | title |
| vv_gui.py:235 | `_section_card` | CTkFrame |  |
| vv_gui.py:249 | `_card_field` | CTkLabel | label |
| vv_gui.py:301 | `_build_ui` | CTkFrame |  |
| vv_gui.py:311 | `_build_ui` | CTkFrame |  |
| vv_gui.py:315 | `_build_ui` | CTkFrame |  |
| vv_gui.py:335 | `_build_ui` | CTkLabel | '● Stopped' |
| vv_gui.py:343 | `_build_ui` | CTkFrame |  |
| vv_gui.py:357 | `_build_ui` | CTkFrame |  |
| vv_gui.py:398 | `_build_ui` | CTkFrame |  |
| vv_gui.py:409 | `_build_ui` | CTkFrame |  |
| vv_gui.py:416 | `_build_ui` | CTkFrame |  |
| vv_gui.py:424 | `_build_ui` | CTkLabel | 'Primary' |
| vv_gui.py:442 | `_build_ui` | CTkLabel | 'Secondary' |
| vv_gui.py:458 | `_build_ui` | CTkFrame |  |
| vv_gui.py:483 | `_build_ui` | CTkFrame |  |
| vv_gui.py:502 | `_build_ui` | CTkFrame |  |
| vv_gui.py:509 | `_build_ui` | CTkScrollableFrame |  |
| vv_gui.py:523 | `_build_ui` | CTkFrame |  |
| vv_gui.py:529 | `_build_ui` | CTkFrame |  |
| vv_gui.py:536 | `_build_ui` | CTkScrollableFrame |  |
| vv_gui.py:583 | `_build_ui` | CTkFrame |  |
| vv_gui.py:598 | `_build_ui` | CTkFrame |  |
| vv_gui.py:600 | `_build_ui` | CTkLabel | 'Verse Delivery Diagnostics' |
| vv_gui.py:609 | `_build_ui` | CTkFrame |  |
| vv_gui.py:637 | `_build_ui` | CTkScrollableFrame |  |
| vv_gui.py:650 | `sep_label` | CTkLabel | text |
| vv_gui.py:754 | `_build_ui` | CTkFrame |  |
| vv_gui.py:789 | `_build_ui` | CTkFrame |  |
| vv_gui.py:795 | `_build_ui` | CTkLabel | 'Book' |
| vv_gui.py:796 | `_build_ui` | CTkLabel | 'Chapter' |
| vv_gui.py:797 | `_build_ui` | CTkLabel | 'Verse' |
| vv_gui.py:832 | `_build_ui` | CTkFrame |  |
| vv_gui.py:849 | `_build_ui` | CTkFrame |  |
| vv_gui.py:871 | `_build_ui` | CTkFrame |  |
| vv_gui.py:873 | `_build_ui` | CTkLabel | f'🏷  v{APP_VERSION}' |
| vv_gui.py:879 | `_build_ui` | CTkLabel | f'build: {BUILD_VERSION}' |
| vv_gui.py:904 | `_build_bot_tab` | CTkLabel | '🤖  Discord Bot Control' |
| vv_gui.py:910 | `_build_bot_tab` | CTkLabel | 'Connection' |
| vv_gui.py:915 | `_build_bot_tab` | CTkFrame |  |
| vv_gui.py:921 | `field_row` | CTkLabel | label |
| vv_gui.py:929 | `_build_bot_tab` | CTkLabel | 'Bot Token' |
| vv_gui.py:932 | `_build_bot_tab` | CTkFrame |  |
| vv_gui.py:960 | `_build_bot_tab` | CTkFrame |  |
| vv_gui.py:980 | `_build_bot_tab` | CTkLabel | '● Stopped' |
| vv_gui.py:988 | `_build_bot_tab` | CTkLabel | 'Bot Log' |
| vv_gui.py:1195 | `_build_options` | CTkLabel | 'Confidence Threshold: 75%' |
| vv_gui.py:1257 | `_build_options` | CTkLabel | 'Sat → Malayalam    ·    Sun 9:10 → English    ·    10:40 → Malayalam    ·    4:40 PM → Hindi' |
| vv_gui.py:1267 | `_build_options` | CTkFrame |  |
| vv_gui.py:1271 | `_build_options` | CTkLabel | 'ATEM IP' |
| vv_gui.py:1282 | `_build_options` | CTkLabel | 'Key On (s)' |
| vv_gui.py:1313 | `_build_options` | CTkLabel | '⌨️  Panic Key: Shift + Escape (fixed on macOS)' |
| vv_gui.py:1340 | `_build_dual_stt` | CTkFrame |  |
| vv_gui.py:1354 | `_build_dual_stt` | CTkFrame |  |
| vv_gui.py:1359 | `_build_dual_stt` | CTkLabel | 'Secondary Language' |
| vv_gui.py:1372 | `_build_dual_stt` | CTkLabel | 'Secondary Engine' |
| vv_gui.py:1433 | `_build_advanced` | CTkLabel | 'LLM Fallback' |
| vv_gui.py:1474 | `_build_advanced` | CTkLabel | '' |
| vv_gui.py:1510 | `_build_advanced` | CTkFrame |  |
| vv_gui.py:1523 | `_build_advanced` | CTkLabel | 'Use http://127.0.0.1:11434 on the model host. Use your protected HTTPS endpoint on remote VerseView computers.' |
| vv_gui.py:1546 | `_build_advanced` | CTkLabel | 'Leave both optional fields blank for a local endpoint. A remote endpoint behind Cloudflare Access needs a service token pasted into Extra Headers — see docs/LOCAL_LLM_REMOTE_ACCESS.md.' |
| vv_gui.py:1562 | `_build_advanced` | CTkLabel | '' |
| vv_gui.py:1577 | `_build_advanced` | CTkLabel | '' |
| vv_gui.py:1594 | `_build_advanced` | CTkLabel | 'Route to Local LLM (per role — not all-or-nothing)' |
| vv_gui.py:1622 | `_build_advanced` | CTkFrame |  |
| vv_gui.py:1625 | `_build_advanced` | CTkLabel | lbl |
| vv_gui.py:1627 | `_build_advanced` | CTkLabel | f'({helper})' |
| vv_gui.py:1637 | `_build_advanced` | CTkLabel | 'Suggested Model' |
| vv_gui.py:1652 | `_build_advanced` | CTkLabel | 'Custom Override' |
| vv_gui.py:1662 | `_build_advanced` | CTkLabel | 'Effective model resolution: 1) Custom override 2) Suggested dropdown 3) Default. Blank fields fall back to recommended models.' |
| vv_gui.py:1672 | `_build_advanced` | CTkLabel | 'Contextual Watcher → choose "Local LLM" in its own Watcher Provider dropdown below.\nStart there: it is a simple classification task, runs fully in parallel, and never blocks the live transcript — the lowest-risk place to try a local model.' |
| vv_gui.py:1682 | `_build_advanced` | CTkLabel | 'If Local LLM fails' |
| vv_gui.py:1690 | `_build_advanced` | CTkLabel | "Unreachable / timed out / bad reply → the error is logged, then either the role's cloud provider is used, or that one cycle is skipped. Either way the app never blocks, stalls the transcript, or crashes." |
| vv_gui.py:1716 | `_build_advanced` | CTkLabel | 'Watcher Provider' |
| vv_gui.py:3264 | `_show_summary_window` | CTkToplevel |  |
| vv_gui.py:3388 | `_show_update_dialog` | CTkToplevel |  |
| vv_gui.py:3396 | `_show_update_dialog` | CTkLabel | '🔄  VerseView Update Available' |
| vv_gui.py:3402 | `_show_update_dialog` | CTkFrame |  |
| vv_gui.py:3406 | `_show_update_dialog` | CTkLabel | f"  🏷  {info['tag_name']}  " |
| vv_gui.py:3420 | `_show_update_dialog` | CTkLabel | desc |
| vv_gui.py:3429 | `_show_update_dialog` | CTkFrame |  |
| vv_gui.py:3431 | `_show_update_dialog` | CTkLabel | "📝 What's Changed" |
| vv_gui.py:3449 | `_show_update_dialog` | CTkProgressBar |  |
| vv_gui.py:3453 | `_show_update_dialog` | CTkLabel | '' |
| vv_gui.py:3457 | `_show_update_dialog` | CTkFrame |  |
| vv_gui.py:3807 | `_update_chapter_browser_loop` | CTkLabel | 'Loading...' |
| vv_gui.py:3829 | `_populate_chapter_browser` | CTkLabel | 'No verses loaded.\nCheck translation.' |
| vv_gui.py:3879 | `_open_verse_popup` | CTkToplevel |  |
| vv_gui.py:3948 | `_build_suggestions_panel` | CTkFrame |  |
| vv_gui.py:3953 | `_build_suggestions_panel` | CTkFrame |  |
| vv_gui.py:3956 | `_build_suggestions_panel` | CTkLabel | '💡 Verse Suggestions  ·  AI Watcher' |
| vv_gui.py:3972 | `_build_suggestions_panel` | CTkLabel | '⚪ Watcher: checking…' |
| vv_gui.py:3980 | `_build_suggestions_panel` | CTkScrollableFrame |  |
| vv_gui.py:3992 | `_build_suggestions_panel` | CTkLabel | 'No suggestions yet — the AI watcher will surface likely references here while a session is running.' |
| vv_gui.py:4088 | `_render_suggestion` | CTkFrame |  |
| vv_gui.py:4095 | `_render_suggestion` | CTkLabel |  |
| vv_gui.py:4387 | `_update_history_loop` | CTkFrame |  |
| vv_gui.py:4405 | `_update_history_loop` | CTkLabel | badge_text |
| live_points_app.py:23 | `__init__` | CTkLabel | '' |
| live_points_app.py:56 | `_build_tab` | CTkFrame |  |
| live_points_app.py:60 | `_build_tab` | CTkFrame |  |
| live_points_app.py:82 | `_build_tab` | CTkLabel | 'Monitor:' |
| live_points_app.py:95 | `_build_tab` | CTkLabel | 'Start the main Engine in the VerseView tab to begin transcribing.' |
| live_points_app.py:103 | `_build_tab` | CTkLabel | '⚙️  AI Behavior Prompt (Instructions for Groq LLM)' |
| live_points_app.py:117 | `_build_tab` | CTkLabel | '👁️  Live Display Preview' |
