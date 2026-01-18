"""Tests for shell integration message with clipboard copy in land command."""

import base64
from pathlib import Path

import click
import pytest

from erk.cli.activation import ensure_land_script
from erk.core.display_utils import copy_to_clipboard_osc52
from erk_shared.output.output import user_output


def test_land_shell_integration_message_emits_osc52_clipboard_sequence(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Land shell integration message emits OSC 52 sequence to copy command."""
    # Set up land script path
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    land_script = ensure_land_script(repo_root)

    # Simulate the shell integration message output (extracted from land_cmd.py)
    args_str = " --up"
    source_cmd = f"source {land_script}{args_str}"

    clipboard_hint = click.style("(copied to clipboard)", dim=True)
    user_output("This command requires shell integration.\n")
    user_output(f"Run: {source_cmd}  {clipboard_hint}")
    user_output(copy_to_clipboard_osc52(source_cmd), nl=False)

    captured = capsys.readouterr()

    # Should contain OSC 52 escape sequence for clipboard
    assert "\033]52;c;" in captured.err, "Expected OSC 52 clipboard sequence"
    assert "\033\\" in captured.err, "Expected OSC 52 terminator"

    # Verify the base64-encoded content is the source command
    osc52_start = captured.err.index("\033]52;c;") + 7
    osc52_end = captured.err.index("\033\\", osc52_start)
    encoded_content = captured.err[osc52_start:osc52_end]
    decoded_content = base64.b64decode(encoded_content).decode("utf-8")
    assert decoded_content == source_cmd


def test_land_shell_integration_message_shows_clipboard_hint(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Land shell integration message shows '(copied to clipboard)' hint."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    land_script = ensure_land_script(repo_root)

    source_cmd = f"source {land_script}"
    clipboard_hint = click.style("(copied to clipboard)", dim=True)
    user_output("This command requires shell integration.\n")
    user_output(f"Run: {source_cmd}  {clipboard_hint}")
    user_output(copy_to_clipboard_osc52(source_cmd), nl=False)

    captured = capsys.readouterr()
    assert "(copied to clipboard)" in captured.err


def test_land_shell_integration_message_includes_all_flags(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Land shell integration message includes all passed flags in copied command."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    land_script = ensure_land_script(repo_root)

    # Simulate args reconstruction (matches land_cmd.py logic)
    args: list[str] = []
    args.append("--up")
    args.append("-f")
    args.append("--no-pull")
    args.append("--no-delete")
    args_str = " " + " ".join(args)
    source_cmd = f"source {land_script}{args_str}"

    clipboard_hint = click.style("(copied to clipboard)", dim=True)
    user_output("This command requires shell integration.\n")
    user_output(f"Run: {source_cmd}  {clipboard_hint}")
    user_output(copy_to_clipboard_osc52(source_cmd), nl=False)

    captured = capsys.readouterr()

    # Extract and decode clipboard content
    osc52_start = captured.err.index("\033]52;c;") + 7
    osc52_end = captured.err.index("\033\\", osc52_start)
    encoded_content = captured.err[osc52_start:osc52_end]
    decoded_content = base64.b64decode(encoded_content).decode("utf-8")

    # Verify all flags are included
    assert "--up" in decoded_content
    assert "-f" in decoded_content
    assert "--no-pull" in decoded_content
    assert "--no-delete" in decoded_content


def test_land_shell_integration_message_includes_target_argument(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Land shell integration message includes target argument (PR number/branch)."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    land_script = ensure_land_script(repo_root)

    # Simulate args reconstruction with target
    args: list[str] = []
    target = "123"  # PR number
    args.append(target)
    args.append("--up")
    args_str = " " + " ".join(args)
    source_cmd = f"source {land_script}{args_str}"

    clipboard_hint = click.style("(copied to clipboard)", dim=True)
    user_output("This command requires shell integration.\n")
    user_output(f"Run: {source_cmd}  {clipboard_hint}")
    user_output(copy_to_clipboard_osc52(source_cmd), nl=False)

    captured = capsys.readouterr()

    # Extract and decode clipboard content
    osc52_start = captured.err.index("\033]52;c;") + 7
    osc52_end = captured.err.index("\033\\", osc52_start)
    encoded_content = captured.err[osc52_start:osc52_end]
    decoded_content = base64.b64decode(encoded_content).decode("utf-8")

    # Verify target is included
    assert "123" in decoded_content
    assert "--up" in decoded_content
