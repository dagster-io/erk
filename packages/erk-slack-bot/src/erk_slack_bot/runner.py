import subprocess
import time
from collections.abc import Callable
from queue import Queue
from shutil import which
from threading import Thread

from click.testing import CliRunner

from erk import cli
from erk_slack_bot.models import RunResult


def run_erk_plan_list() -> RunResult:
    result = CliRunner().invoke(cli, ["plan", "list"])
    output = (result.output or "").strip() or "(no output)"
    return RunResult(exit_code=result.exit_code, output=output)


def run_erk_one_shot(message: str, *, timeout_seconds: float) -> RunResult:
    if which("uv") is None:
        return RunResult(exit_code=127, output="Failed to start process: uv was not found in PATH")

    try:
        result = subprocess.run(
            ["uv", "run", "erk", "one-shot", message],
            capture_output=True,
            text=True,
            shell=False,
            check=False,
            timeout=timeout_seconds,
        )
    except FileNotFoundError as exc:
        return RunResult(exit_code=127, output=f"Failed to start process: {exc}")
    except subprocess.TimeoutExpired as exc:
        output = "\n".join(part for part in [exc.stdout or "", exc.stderr or ""] if part).strip()
        return RunResult(exit_code=124, output=output or "(no output)", timed_out=True)

    output = (
        "\n".join(part for part in [result.stdout, result.stderr] if part).strip() or "(no output)"
    )
    return RunResult(exit_code=result.returncode, output=output)


def stream_erk_one_shot(
    message: str,
    *,
    timeout_seconds: float,
    on_line: Callable[[str], None] | None,
) -> RunResult:
    if which("uv") is None:
        return RunResult(exit_code=127, output="Failed to start process: uv was not found in PATH")

    process = subprocess.Popen(
        ["uv", "run", "erk", "one-shot", message],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        shell=False,
        bufsize=1,
    )

    queue: Queue[str | None] = Queue()
    lines: list[str] = []

    def _read_stdout() -> None:
        stdout = process.stdout
        if stdout is None:
            queue.put(None)
            return
        for raw_line in stdout:
            queue.put(raw_line.rstrip("\n"))
        queue.put(None)

    reader = Thread(target=_read_stdout, daemon=True)
    reader.start()

    start_time = time.monotonic()
    reader_done = False

    while True:
        elapsed = time.monotonic() - start_time
        if elapsed > timeout_seconds:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            output = "\n".join(lines).strip() or "(no output)"
            return RunResult(exit_code=124, output=output, timed_out=True)

        if reader_done and process.poll() is not None:
            break

        if queue.empty():
            time.sleep(0.2)
            continue

        item = queue.get_nowait()

        if item is None:
            reader_done = True
            continue

        lines.append(item)
        if on_line is not None:
            on_line(item)

    return_code = process.wait()
    output = "\n".join(lines).strip() or "(no output)"
    return RunResult(exit_code=return_code, output=output)
