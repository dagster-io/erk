import unittest
from unittest.mock import MagicMock, patch

from erk_slack_bot.runner import run_erk_one_shot, stream_erk_one_shot


class TestRunErkOneShot(unittest.TestCase):
    @patch("erk_slack_bot.runner.subprocess.run")
    def test_run_one_shot_passes_single_argument(self, mock_run) -> None:  # type: ignore[no-untyped-def]
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")

        message = "fix this; rm -rf / && echo pwned"
        result = run_erk_one_shot(message, timeout_seconds=60)

        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.output, "ok")
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        self.assertEqual(args, ["uv", "run", "erk", "one-shot", message])
        self.assertEqual(mock_run.call_args.kwargs["shell"], False)


class TestStreamErkOneShot(unittest.TestCase):
    @patch("erk_slack_bot.runner.subprocess.Popen")
    def test_stream_one_shot_emits_lines_and_uses_safe_args(self, mock_popen) -> None:  # type: ignore[no-untyped-def]
        process = MagicMock()
        process.stdout = iter(["Creating branch...\n", "Done!\n"])
        process.poll.return_value = 0
        process.wait.return_value = 0
        mock_popen.return_value = process

        seen_lines: list[str] = []
        message = "fix this; rm -rf / && echo pwned"
        result = stream_erk_one_shot(message, timeout_seconds=60, on_line=seen_lines.append)

        self.assertEqual(result.exit_code, 0)
        self.assertEqual(seen_lines, ["Creating branch...", "Done!"])
        self.assertEqual(result.output, "Creating branch...\nDone!")
        args = mock_popen.call_args[0][0]
        self.assertEqual(args, ["uv", "run", "erk", "one-shot", message])
        self.assertEqual(mock_popen.call_args.kwargs["shell"], False)

    @patch("erk_slack_bot.runner.subprocess.Popen")
    def test_stream_one_shot_timeout(self, mock_popen) -> None:  # type: ignore[no-untyped-def]
        process = MagicMock()
        process.stdout = None
        process.poll.return_value = None
        process.wait.return_value = 0
        mock_popen.return_value = process

        result = stream_erk_one_shot("hello", timeout_seconds=0.01, on_line=None)

        self.assertEqual(result.exit_code, 124)
        self.assertTrue(result.timed_out)
        process.terminate.assert_called_once()


if __name__ == "__main__":
    unittest.main()
