import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from erkbot.runner import run_erk_one_shot, run_erk_plan_list, stream_erk_one_shot


class TestRunErkPlanList(unittest.IsolatedAsyncioTestCase):
    @patch("erkbot.runner.CliRunner")
    async def test_strips_ansi_codes_from_output(self, mock_runner_cls: MagicMock) -> None:
        """plan list output with ANSI codes (from Rich Console) is stripped."""
        ansi_output = (
            "\x1b[1mpr    \x1b[0m\x1b[1m \x1b[0m\x1b[1mstage   \x1b[0m\n"
            "\x1b]8;;https://github.com/test/repo/issues/1\x1b\\#1\x1b]8;;\x1b\\"
            "     \x1b[36mimpl\x1b[0m"
        )
        invoke_result = MagicMock()
        invoke_result.output = ansi_output
        invoke_result.exit_code = 0
        mock_runner_cls.return_value.invoke.return_value = invoke_result

        result = await run_erk_plan_list()

        self.assertEqual(result.exit_code, 0)
        self.assertNotIn("\x1b", result.output)
        self.assertIn("pr", result.output)
        self.assertIn("#1", result.output)

    @patch("erkbot.runner.CliRunner")
    async def test_passes_all_users_flag(self, mock_runner_cls: MagicMock) -> None:
        """plan list is invoked with --all-users so the bot shows all plans."""
        invoke_result = MagicMock()
        invoke_result.output = "No plans found matching the criteria."
        invoke_result.exit_code = 0
        mock_runner_cls.return_value.invoke.return_value = invoke_result

        await run_erk_plan_list()

        _call_args = mock_runner_cls.return_value.invoke.call_args
        cli_args = _call_args[0][1]
        self.assertIn("--all-users", cli_args)
        self.assertIn("pr", cli_args)
        self.assertIn("list", cli_args)
        self.assertNotIn("plan", cli_args)

    @patch("click.testing.CliRunner.invoke")
    async def test_run_erk_plan_list_constructs_cli_runner(self, mock_invoke: MagicMock) -> None:
        """Real CliRunner() constructor is called — catches incompatible kwargs."""
        invoke_result = MagicMock()
        invoke_result.output = "plan output"
        invoke_result.exit_code = 0
        mock_invoke.return_value = invoke_result

        result = await run_erk_plan_list()

        self.assertEqual(result.exit_code, 0)
        self.assertIn("plan output", result.output)


class TestRunErkOneShot(unittest.IsolatedAsyncioTestCase):
    @patch("erkbot.runner.asyncio.create_subprocess_exec", new_callable=AsyncMock)
    async def test_run_one_shot_passes_single_argument(self, mock_create: AsyncMock) -> None:
        process = AsyncMock()
        process.communicate.return_value = (b"ok", b"")
        process.returncode = 0
        mock_create.return_value = process

        message = "fix this; rm -rf / && echo pwned"
        result = await run_erk_one_shot(message, timeout_seconds=60)

        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.output, "ok")
        mock_create.assert_called_once_with(
            "uv",
            "run",
            "erk",
            "one-shot",
            message,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )


class TestStreamErkOneShot(unittest.IsolatedAsyncioTestCase):
    @patch("erkbot.runner.asyncio.create_subprocess_exec", new_callable=AsyncMock)
    async def test_stream_one_shot_emits_lines_and_uses_safe_args(
        self, mock_create: AsyncMock
    ) -> None:
        process = AsyncMock()
        lines_iter = iter([b"Creating branch...\n", b"Done!\n", b""])
        process.stdout.readline = AsyncMock(side_effect=lines_iter)
        process.returncode = 0
        mock_create.return_value = process

        seen_lines: list[str] = []

        async def capture_line(line: str) -> None:
            seen_lines.append(line)

        message = "fix this; rm -rf / && echo pwned"
        result = await stream_erk_one_shot(message, timeout_seconds=60, on_line=capture_line)

        self.assertEqual(result.exit_code, 0)
        self.assertEqual(seen_lines, ["Creating branch...", "Done!"])
        self.assertEqual(result.output, "Creating branch...\nDone!")
        mock_create.assert_called_once_with(
            "uv",
            "run",
            "erk",
            "one-shot",
            message,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

    @patch("erkbot.runner.asyncio.create_subprocess_exec", new_callable=AsyncMock)
    async def test_stream_one_shot_timeout(self, mock_create: AsyncMock) -> None:
        process = AsyncMock()

        # readline never returns empty bytes, simulating a process that never finishes
        async def _hang() -> bytes:
            await asyncio.sleep(10)
            return b""

        process.stdout.readline = AsyncMock(side_effect=_hang)
        process.returncode = None
        mock_create.return_value = process

        result = await stream_erk_one_shot("hello", timeout_seconds=0.01, on_line=None)

        self.assertEqual(result.exit_code, 124)
        self.assertTrue(result.timed_out)
        process.terminate.assert_called_once()


if __name__ == "__main__":
    unittest.main()
