"""
voting/tests_chat.py
────────────────────
Unit tests for the SCRUM-11 chat-analysis modules (parser / analytics /
sentiment). They use SimpleTestCase because the feature is stateless and needs
no database. Run with:

    python manage.py test voting.tests_chat
"""

import os

from django.test import SimpleTestCase, TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from voting.chat_parser import parse_chat
from voting.chat_analytics import analyze_activity
from voting.chat_sentiment import analyze_sentiment, classify


FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "sample_chat_en.txt")


def load_sample():
    with open(FIXTURE, encoding="utf-8") as fh:
        return fh.read()


class ChatParserTests(SimpleTestCase):
    def setUp(self):
        self.messages, self.stats = parse_chat(load_sample())

    def test_parses_expected_message_count(self):
        self.assertEqual(self.stats["parsed_messages"], 32)
        self.assertEqual(len(self.messages), 32)

    def test_skips_system_notice(self):
        self.assertEqual(self.stats["system_lines"], 1)
        # The encryption notice must not appear as a real message.
        for m in self.messages:
            self.assertNotIn("end-to-end encrypted", m["text"])

    def test_detects_three_participants(self):
        authors = sorted({m["author"] for m in self.messages})
        self.assertEqual(authors, ["Alice", "Bob", "Charlie"])

    def test_merges_multiline_message(self):
        multiline = [m for m in self.messages if "\n" in m["text"]]
        self.assertEqual(len(multiline), 1)
        self.assertIn("spans", multiline[0]["text"])
        self.assertIn("multiple lines", multiline[0]["text"])
        self.assertEqual(self.stats["continuation_lines"], 1)

    def test_flags_media_message(self):
        media = [m for m in self.messages if m["is_media"]]
        self.assertEqual(len(media), 1)
        self.assertEqual(self.stats["media_messages"], 1)

    def test_parses_datetime_correctly(self):
        first = self.messages[0]
        self.assertEqual(first["author"], "Alice")
        self.assertEqual(first["datetime"].year, 2024)
        self.assertEqual(first["datetime"].hour, 9)
        self.assertEqual(first["datetime"].minute, 5)

    def test_parses_pm_time_to_24h(self):
        # "8:40 PM" must become hour 20.
        evening = [m for m in self.messages if m["datetime"].hour == 20]
        self.assertTrue(evening)

    def test_handles_ios_format(self):
        ios = "[1/5/24, 10:15:00 PM] Dana: Testing iOS export format here."
        messages, stats = parse_chat(ios)
        self.assertEqual(stats["parsed_messages"], 1)
        self.assertEqual(messages[0]["author"], "Dana")
        self.assertEqual(messages[0]["datetime"].hour, 22)

    def test_handles_24h_clock(self):
        line = "1/5/24, 14:30 - Eve: Twenty-four hour clock message."
        messages, _ = parse_chat(line)
        self.assertEqual(messages[0]["datetime"].hour, 14)

    def test_empty_input_is_safe(self):
        messages, stats = parse_chat("")
        self.assertEqual(messages, [])
        self.assertEqual(stats["parsed_messages"], 0)


class ChatAnalyticsTests(SimpleTestCase):
    def setUp(self):
        messages, _ = parse_chat(load_sample())
        self.result = analyze_activity(messages)

    def test_summary_totals(self):
        summary = self.result["summary"]
        self.assertEqual(summary["total_messages"], 32)
        self.assertEqual(summary["days"], 3)
        self.assertEqual(summary["avg_messages_per_day"], round(32 / 3, 2))
        self.assertEqual(summary["participants"], ["Alice", "Bob", "Charlie"])

    def test_activity_by_hour_has_24_slots_summing_to_total(self):
        hours = self.result["activity_by_hour"]
        self.assertEqual(len(hours), 24)
        self.assertEqual(sum(h["count"] for h in hours), 32)

    def test_peak_hour_is_21(self):
        # 9 PM is the busiest hour in the sample (7 messages).
        self.assertEqual(self.result["peak_hour"], 21)

    def test_per_participant_counts(self):
        counts = {p["name"]: p["messages"] for p in self.result["per_participant"]}
        self.assertEqual(counts, {"Alice": 11, "Bob": 11, "Charlie": 10})

    def test_per_participant_active_hours_non_empty(self):
        for p in self.result["per_participant"]:
            self.assertTrue(p["active_hours"])
            self.assertTrue(all(0 <= h <= 23 for h in p["active_hours"]))

    def test_date_range(self):
        rng = self.result["summary"]["date_range"]
        self.assertTrue(rng["start"].startswith("2024-01-01"))
        self.assertTrue(rng["end"].startswith("2024-01-03"))

    def test_empty_messages_safe(self):
        result = analyze_activity([])
        self.assertEqual(result["summary"]["total_messages"], 0)
        self.assertIsNone(result["peak_hour"])
        self.assertEqual(len(result["activity_by_hour"]), 24)


class ChatSentimentTests(SimpleTestCase):
    def setUp(self):
        messages, _ = parse_chat(load_sample())
        self.result = analyze_sentiment(messages)

    def test_classify_basic_cases(self):
        self.assertEqual(classify("I love this, it's amazing and wonderful!"), "positive")
        self.assertEqual(classify("This is terrible, I hate it, worst ever."), "negative")
        self.assertEqual(classify(""), "neutral")

    def test_media_messages_excluded(self):
        # 32 messages, 1 of them is <Media omitted>, so 31 are analyzed.
        self.assertEqual(self.result["sentiment"]["analyzed"], 31)

    def test_counts_sum_to_analyzed(self):
        s = self.result["sentiment"]
        self.assertEqual(s["positive"] + s["negative"] + s["neutral"], s["analyzed"])

    def test_expected_distribution(self):
        s = self.result["sentiment"]
        self.assertEqual(s["positive"], 20)
        self.assertEqual(s["negative"], 8)
        self.assertEqual(s["neutral"], 3)

    def test_overall_tone_positive(self):
        self.assertEqual(self.result["sentiment"]["overall"], "positive")

    def test_percentages_present(self):
        s = self.result["sentiment"]
        self.assertAlmostEqual(
            s["positive_pct"] + s["negative_pct"] + s["neutral_pct"], 100.0, delta=0.2
        )

    def test_per_participant_sentiment(self):
        rows = self.result["per_participant_sentiment"]
        self.assertEqual([r["name"] for r in rows], ["Alice", "Bob", "Charlie"])
        for r in rows:
            self.assertIn(r["overall"], {"positive", "negative", "neutral"})

    def test_empty_messages_safe(self):
        result = analyze_sentiment([])
        self.assertEqual(result["sentiment"]["analyzed"], 0)
        self.assertEqual(result["sentiment"]["overall"], "neutral")
        self.assertEqual(result["per_participant_sentiment"], [])


class ChatApiTests(TestCase):
    """End-to-end checks for POST /api/chat/analyze/."""

    def setUp(self):
        self.url = reverse("chat-analyze")
        self.sample = load_sample()

    def _login(self):
        session = self.client.session
        session["user_id"] = 1
        session.save()

    def test_requires_authentication(self):
        resp = self.client.post(self.url, {"text": self.sample})
        self.assertEqual(resp.status_code, 401)

    def test_analyze_pasted_text(self):
        self._login()
        resp = self.client.post(self.url, {"text": self.sample})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["summary"]["total_messages"], 32)
        self.assertEqual(data["peak_hour"], 21)
        self.assertEqual(data["sentiment"]["overall"], "positive")
        self.assertEqual(len(data["activity_by_hour"]), 24)

    def test_analyze_uploaded_file(self):
        self._login()
        upload = SimpleUploadedFile(
            "chat.txt", self.sample.encode("utf-8"), content_type="text/plain"
        )
        resp = self.client.post(self.url, {"file": upload})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["summary"]["participants"], ["Alice", "Bob", "Charlie"])

    def test_empty_payload_rejected(self):
        self._login()
        resp = self.client.post(self.url, {"text": "   "})
        self.assertEqual(resp.status_code, 400)

    def test_garbage_text_rejected(self):
        self._login()
        resp = self.client.post(self.url, {"text": "just some random text with no chat format"})
        self.assertEqual(resp.status_code, 400)
