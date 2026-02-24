import asyncio
from collections.abc import Awaitable, Callable
from shutil import which

from click.testing import CliRunner

from erk import cli
from erkbot.models import RunResult


async def run_erk_plan_list() -> RunResult:
    result = await asyncio.to_thread(CliRunner().invoke, cli, ["plan", "list"])
    output = (result.output or "").strip() or "(no output)"
    return RunResult(exit_code=result.exit_code, output=output)


async def run_erk_one_shot(message: str, *, timeout_seconds: float) -> RunResult:
    if which("uv") is None:
        return RunResult(exit_code=127, output="Failed to start process: uv was not found in PATH")

    try:
        process = await asyncio.create_subprocess_exec(
            "uv",
            "run",
            "erk",
            "one-shot",
            message,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            process.communicate(), timeout=timeout_seconds
        )
    except TimeoutError:
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=2)
        except TimeoutError:
            process.kill()
            await process.wait()
        output = "(no output)"
        return RunResult(exit_code=124, output=output, timed_out=True)

    stdout = (stdout_bytes or b"").decode()
    stderr = (stderr_bytes or b"").decode()
    output = "\n".join(part for part in [stdout, stderr] if part).strip() or "(no output)"
    return RunResult(exit_code=process.returncode or 0, output=output)


async def stream_erk_one_shot(
    message: str,
    *,
    timeout_seconds: float,
    on_line: Callable[[str], Awaitable[None]] | None,
) -> RunResult:
    if which("uv") is None:
        return RunResult(exit_code=127, output="Failed to start process: uv was not found in PATH")

    process = await asyncio.create_subprocess_exec(
        "uv",
        "run",
        "erk",
        "one-shot",
        message,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )

    lines: list[str] = []

    async def _read_lines() -> None:
        if process.stdout is None:
            return
        while True:
            raw_line = await process.stdout.readline()
            if not raw_line:
                break
            line = raw_line.decode().rstrip("\n")
            lines.append(line)
            if on_line is not None:
                await on_line(line)

    try:
        await asyncio.wait_for(_read_lines(), timeout=timeout_seconds)
    except TimeoutError:
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=2)
        except TimeoutError:
            process.kill()
            await process.wait()
        output = "\n".join(lines).strip() or "(no output)"
        return RunResult(exit_code=124, output=output, timed_out=True)

    await process.wait()
    output = "\n".join(lines).strip() or "(no output)"
    return RunResult(exit_code=process.returncode or 0, output=output)
