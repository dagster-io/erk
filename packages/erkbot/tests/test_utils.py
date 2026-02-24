import unittest
from unittest.mock import MagicMock

from erkbot.config import Settings
from erkbot.utils import (
    build_one_shot_progress_text,
    chunk_for_slack,
    extract_one_shot_links,
    extract_slack_message_ts,
    strip_ansi,
    tail_output_lines,
)


class TestUtils(unittest.TestCase):
    def test_build_progress_text(self) -> None:
        settings = Settings(SLACK_BOT_TOKEN="x", SLACK_APP_TOKEN="y")
        text = build_one_shot_progress_text(
            lines=["Creating branch...", "Pushing..."],
            running=True,
            settings=settings,
        )
        self.assertIn("⏳ Running `erk one-shot`", text)
        self.assertIn("Creating branch...", text)

    def test_extract_links(self) -> None:
        output = "PR: https://github.com/example/repo/pull/9\nRun: https://github.com/example/repo/actions/runs/123"
        pr_url, run_url = extract_one_shot_links(output)
        self.assertEqual(pr_url, "https://github.com/example/repo/pull/9")
        self.assertEqual(run_url, "https://github.com/example/repo/actions/runs/123")

    def test_tail_output_lines(self) -> None:
        output = "\n".join([f"line-{i}" for i in range(10)])
        tail = tail_output_lines(output, max_lines=3)
        self.assertEqual(tail, "line-7\nline-8\nline-9")

    def test_chunk_for_slack(self) -> None:
        text = "a\n" + ("b" * 20)
        chunks = chunk_for_slack(text, max_chars=10)
        self.assertGreater(len(chunks), 1)

    def test_extract_slack_message_ts_from_dict(self) -> None:
        self.assertEqual(extract_slack_message_ts({"ts": "123.45"}), "123.45")

    def test_extract_slack_message_ts_from_object(self) -> None:
        obj = MagicMock()
        obj.get.return_value = "678.90"
        self.assertEqual(extract_slack_message_ts(obj), "678.90")

    def test_strip_ansi_removes_sgr_codes(self) -> None:
        text = "\x1b[1m\x1b[0m\x1b[1mpr\x1b[0m\x1b[1m \x1b[0m"
        self.assertEqual(strip_ansi(text), "pr ")

    def test_strip_ansi_removes_osc8_hyperlinks(self) -> None:
        text = "\x1b]8;;https://example.com\x1b\\#42\x1b]8;;\x1b\\"
        self.assertEqual(strip_ansi(text), "#42")

    def test_strip_ansi_preserves_plain_text(self) -> None:
        text = "No plans found matching the criteria."
        self.assertEqual(strip_ansi(text), text)

    def test_strip_ansi_handles_mixed_content(self) -> None:
        text = (
            "Found 2 plan(s):\n"
            "\x1b[1mpr\x1b[0m  \x1b[1mstage\x1b[0m\n"
            "\x1b]8;;https://github.com/test/repo/issues/1\x1b\\#1\x1b]8;;\x1b\\"
            "  \x1b[36mimpl\x1b[0m"
        )
        result = strip_ansi(text)
        self.assertIn("Found 2 plan(s):", result)
        self.assertIn("pr", result)
        self.assertIn("#1", result)
        self.assertIn("impl", result)
        self.assertNotIn("\x1b", result)


if __name__ == "__main__":
    unittest.main()
