import copy
import datetime as dt
import unittest
from service_schedule import scheduled_language, effective_start_settings


class ScheduleTests(unittest.TestCase):
    def test_local_weekdays_and_saturday(self):
        for day in range(12, 17):
            self.assertIsNone(scheduled_language(dt.datetime(2026, 10, day, 18)))
        self.assertEqual(scheduled_language(dt.datetime(2026, 10, 17, 0)), 'Malayalam')
        self.assertEqual(scheduled_language(dt.datetime(2026, 10, 17, 23, 59)), 'Malayalam')

    def test_sunday_exact_boundaries(self):
        for hour, minute, expected in [(9, 9, None), (9, 10, 'English'), (10, 39, 'English'),
                                       (10, 40, 'Malayalam'), (16, 39, 'Malayalam'), (16, 40, 'Hindi'), (23, 59, 'Hindi')]:
            with self.subTest(time=(hour, minute)):
                self.assertEqual(scheduled_language(dt.datetime(2026, 10, 18, hour, minute)), expected)

    def test_disabled_or_no_service_keeps_saved_choices(self):
        values = {'language': 'Hindi', 'smart_schedule': False, 'dual_stt_enabled': True}
        self.assertEqual(effective_start_settings(values, dt.datetime(2026, 10, 18, 12)), (values, None))
        values['smart_schedule'] = True
        self.assertEqual(effective_start_settings(values, dt.datetime(2026, 10, 18, 8)), (values, None))

    def test_service_rules_keep_primary_provider_settings_and_guards(self):
        values = {'smart_schedule': True, 'language': 'English', 'stt_engine': 'sarvam',
                  'secondary_language': 'ml', 'secondary_stt_engine': 'sarvam',
                  'cooldown': 7, 'dedup_window': 91, 'manual_confirm': True,
                  'deepgram_api_key': 'private', 'future': {'keep': True}}
        original = copy.deepcopy(values)
        effective, language = effective_start_settings(values, dt.datetime(2026, 10, 18, 17))
        self.assertEqual(language, 'Hindi')
        self.assertEqual((effective['dual_stt_enabled'], effective['secondary_language'], effective['secondary_stt_engine']), (True, 'en', 'deepgram'))
        for key in ['stt_engine', 'cooldown', 'dedup_window', 'manual_confirm', 'deepgram_api_key', 'future']:
            self.assertEqual(effective[key], values[key])
        self.assertEqual(values, original)
        effective, _ = effective_start_settings(values, dt.datetime(2026, 10, 18, 10))
        self.assertFalse(effective['dual_stt_enabled'])
        self.assertEqual(effective['secondary_language'], 'ml')

    def test_saved_english_secondary_choices_survive(self):
        for provider in ['deepgram', 'assemblyai', 'assemblyai_pro', 'assemblyai_multilingual']:
            effective, _ = effective_start_settings({'smart_schedule': True, 'secondary_stt_engine': provider}, dt.datetime(2026, 10, 17))
            self.assertEqual(effective['secondary_stt_engine'], provider)
