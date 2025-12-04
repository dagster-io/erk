"""Tests for shell wrapper script logic order.

These tests verify that shell wrappers check for script files BEFORE checking
exit status. This is critical for commands like `erk down --delete-current` where:

1. The Python handler generates an activation script (cd to target directory)
2. The command might return non-zero (e.g., gt delete fails)
3. The shell wrapper MUST still source the script to complete navigation

The fix ensures:
- Script check comes BEFORE exit status check
- User navigates to correct directory even if later operations fail
"""

import re
from pathlib import Path


def test_zsh_wrapper_checks_script_before_exit_status() -> None:
    """Verify zsh wrapper checks for script file before exit status."""
    wrapper_path = (
        Path(__file__).parents[3] / "src" / "erk" / "cli" / "shell_integration" / "zsh_wrapper.sh"
    )
    content = wrapper_path.read_text(encoding="utf-8")

    # Find the position of key patterns
    script_check_match = re.search(
        r'if \[ -n "\$script_path" \] && \[ -f "\$script_path" \]',
        content,
    )
    exit_status_check_match = re.search(
        r"\[ \$exit_status -ne 0 \] && return \$exit_status",
        content,
    )

    # Both patterns must exist
    assert script_check_match is not None, "Script check pattern not found in zsh wrapper"
    assert exit_status_check_match is not None, "Exit status check pattern not found in zsh wrapper"

    # Script check MUST come before exit status check
    assert script_check_match.start() < exit_status_check_match.start(), (
        "zsh wrapper must check for script BEFORE checking exit status. "
        "This ensures navigation works even when commands partially fail."
    )


def test_bash_wrapper_checks_script_before_exit_status() -> None:
    """Verify bash wrapper checks for script file before exit status."""
    wrapper_path = (
        Path(__file__).parents[3] / "src" / "erk" / "cli" / "shell_integration" / "bash_wrapper.sh"
    )
    content = wrapper_path.read_text(encoding="utf-8")

    # Find the position of key patterns
    script_check_match = re.search(
        r'if \[ -n "\$script_path" \] && \[ -f "\$script_path" \]',
        content,
    )
    exit_status_check_match = re.search(
        r"\[ \$exit_status -ne 0 \] && return \$exit_status",
        content,
    )

    # Both patterns must exist
    assert script_check_match is not None, "Script check pattern not found in bash wrapper"
    assert exit_status_check_match is not None, (
        "Exit status check pattern not found in bash wrapper"
    )

    # Script check MUST come before exit status check
    assert script_check_match.start() < exit_status_check_match.start(), (
        "bash wrapper must check for script BEFORE checking exit status. "
        "This ensures navigation works even when commands partially fail."
    )


def test_fish_wrapper_checks_script_before_exit_status() -> None:
    """Verify fish wrapper checks for script file before exit status."""
    wrapper_path = (
        Path(__file__).parents[3]
        / "src"
        / "erk"
        / "cli"
        / "shell_integration"
        / "fish_wrapper.fish"
    )
    content = wrapper_path.read_text(encoding="utf-8")

    # Find the position of key patterns (fish syntax)
    script_check_match = re.search(
        r'if test -n "\$script_path" -a -f "\$script_path"',
        content,
    )
    exit_status_check_match = re.search(
        r"if test \$exit_status -ne 0",
        content,
    )

    # Both patterns must exist
    assert script_check_match is not None, "Script check pattern not found in fish wrapper"
    assert exit_status_check_match is not None, (
        "Exit status check pattern not found in fish wrapper"
    )

    # Script check MUST come before exit status check
    assert script_check_match.start() < exit_status_check_match.start(), (
        "fish wrapper must check for script BEFORE checking exit status. "
        "This ensures navigation works even when commands partially fail."
    )


def test_zsh_wrapper_sources_script_regardless_of_exit_code_comment() -> None:
    """Verify zsh wrapper has comment explaining the script-first logic."""
    wrapper_path = (
        Path(__file__).parents[3] / "src" / "erk" / "cli" / "shell_integration" / "zsh_wrapper.sh"
    )
    content = wrapper_path.read_text(encoding="utf-8")

    # The wrapper should have a comment explaining WHY script check comes first
    assert "regardless of exit code" in content.lower(), (
        "zsh wrapper should have a comment explaining that scripts are sourced "
        "regardless of exit code"
    )


def test_bash_wrapper_sources_script_regardless_of_exit_code_comment() -> None:
    """Verify bash wrapper has comment explaining the script-first logic."""
    wrapper_path = (
        Path(__file__).parents[3] / "src" / "erk" / "cli" / "shell_integration" / "bash_wrapper.sh"
    )
    content = wrapper_path.read_text(encoding="utf-8")

    # The wrapper should have a comment explaining WHY script check comes first
    assert "regardless of exit code" in content.lower(), (
        "bash wrapper should have a comment explaining that scripts are sourced "
        "regardless of exit code"
    )


def test_fish_wrapper_sources_script_regardless_of_exit_code_comment() -> None:
    """Verify fish wrapper has comment explaining the script-first logic."""
    wrapper_path = (
        Path(__file__).parents[3]
        / "src"
        / "erk"
        / "cli"
        / "shell_integration"
        / "fish_wrapper.fish"
    )
    content = wrapper_path.read_text(encoding="utf-8")

    # The wrapper should have a comment explaining WHY script check comes first
    assert "regardless of exit code" in content.lower(), (
        "fish wrapper should have a comment explaining that scripts are sourced "
        "regardless of exit code"
    )
