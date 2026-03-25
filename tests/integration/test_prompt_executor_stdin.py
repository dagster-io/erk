"""Integration tests for prompt executor stdin piping.

Verifies that ClaudeCliPromptExecutor passes prompts via stdin
rather than as CLI arguments, avoiding ARG_MAX limits.
"""

import os
import stat
import sys
from pathlib import Path

import pytest

from erk.core.prompt_executor import ClaudeCliPromptExecutor

# A minimal Python script that acts as a fake claude CLI.
# Reads all of stdin and writes it to stdout.
# If FAKE_CLAUDE_STDIN_FILE env var is set, also writes stdin to that file
# (useful for passthrough tests where stdout is not captured).
FAKE_CLAUDE_SCRIPT = f"""\
#!{sys.executable}
import os
import sys

prompt = sys.stdin.read()

sink = os.environ.get("FAKE_CLAUDE_STDIN_FILE")
if sink:
    with open(sink, "w") as f:
        f.write(prompt)

sys.stdout.write(prompt)
"""


@pytest.fixture()
def fake_claude_on_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a fake 'claude' executable and prepend its directory to PATH."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_claude = bin_dir / "claude"
    fake_claude.write_text(FAKE_CLAUDE_SCRIPT)
    fake_claude.chmod(fake_claude.stat().st_mode | stat.S_IEXEC)

    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    return fake_claude


def test_execute_prompt_delivers_prompt_via_stdin(
    fake_claude_on_path: Path,
    tmp_path: Path,
) -> None:
    """Prompt is delivered via stdin and round-trips through the subprocess."""
    executor = ClaudeCliPromptExecutor(console=None)
    prompt = "Hello, this is a test prompt"

    result = executor.execute_prompt(
        prompt=prompt,
        model="test-model",
        cwd=tmp_path,
        system_prompt=None,
        tools=None,
        dangerous=False,
    )

    assert result.success is True
    assert result.output == prompt


def test_execute_prompt_handles_large_prompt_via_stdin(
    fake_claude_on_path: Path,
    tmp_path: Path,
) -> None:
    """Large prompts that would exceed ARG_MAX work via stdin.

    macOS ARG_MAX is ~1MB. A 500KB prompt would fail with
    'Argument list too long' if passed as a CLI argument.
    """
    executor = ClaudeCliPromptExecutor(console=None)
    prompt = "x" * (500 * 1024)

    result = executor.execute_prompt(
        prompt=prompt,
        model="test-model",
        cwd=tmp_path,
        system_prompt=None,
        tools=None,
        dangerous=False,
    )

    assert result.success is True
    assert result.output == prompt


def test_execute_prompt_passthrough_delivers_prompt_via_stdin(
    fake_claude_on_path: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Passthrough method delivers prompt via stdin."""
    executor = ClaudeCliPromptExecutor(console=None)
    prompt = "Hello from passthrough"

    # Have the fake script write stdin to a file so we can verify
    stdin_file = tmp_path / "captured_stdin.txt"
    monkeypatch.setenv("FAKE_CLAUDE_STDIN_FILE", str(stdin_file))

    exit_code = executor.execute_prompt_passthrough(
        prompt=prompt,
        model="test-model",
        cwd=tmp_path,
        tools=None,
        dangerous=False,
    )

    assert exit_code == 0
    assert stdin_file.read_text() == prompt
