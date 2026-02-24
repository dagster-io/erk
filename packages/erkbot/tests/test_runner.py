import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from erkbot.runner import run_erk_one_shot, stream_erk_one_shot


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
