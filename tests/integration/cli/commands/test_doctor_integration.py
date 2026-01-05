"""Integration tests for erk doctor command.

These tests verify that `erk doctor` correctly validates hook configurations
using real git repositories and actual CLI invocations.
"""

import json
import subprocess
from pathlib import Path

import pytest

from tests.integration.conftest import init_git_repo


def test_doctor_passes_user_prompt_hook_check(tmp_path: Path) -> None:
    """Test that doctor passes when UserPromptSubmit hook is correctly configured.

    Creates a real git repository with the expected hook configuration and
    verifies that `erk doctor` reports the hook check as passing.
    """
    # Arrange: Set up real git repository
    repo = tmp_path / "repo"
    repo.mkdir()
    init_git_repo(repo, "main")

    # Set up .claude/settings.json with the expected hook format
    claude_dir = repo / ".claude"
    claude_dir.mkdir()
    settings = {
        "hooks": {
            "UserPromptSubmit": [
                {
                    "matcher": "*",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "ERK_HOOK_ID=user-prompt-hook erk exec user-prompt-hook",
                            "timeout": 30,
                        }
                    ],
                }
            ]
        }
    }
    (claude_dir / "settings.json").write_text(json.dumps(settings), encoding="utf-8")

    # Act: Run erk doctor --verbose to see individual check messages
    result = subprocess.run(
        ["erk", "doctor", "--verbose"],
        cwd=repo,
        capture_output=True,
        text=True,
    )

    # Assert: UserPromptSubmit hook check should pass
    # The check message is "UserPromptSubmit hook configured"
    output = result.stdout + result.stderr
    assert "userpromptsubmit hook configured" in output.lower()


@pytest.mark.parametrize(
    "wrong_command",
    [
        "old-erk-hook.py",
        "some-other-script.sh",
        "uv run scripts/erk-user-prompt-hook.py",
    ],
)
def test_doctor_fails_user_prompt_hook_check_wrong_command(
    tmp_path: Path, wrong_command: str
) -> None:
    """Test that doctor fails when UserPromptSubmit hook has wrong command.

    Creates a real git repository with an incorrect hook command and
    verifies that `erk doctor` reports the hook check as failing.
    """
    # Arrange: Set up real git repository
    repo = tmp_path / "repo"
    repo.mkdir()
    init_git_repo(repo, "main")

    # Set up .claude/settings.json with a wrong hook command
    claude_dir = repo / ".claude"
    claude_dir.mkdir()
    settings = {
        "hooks": {
            "UserPromptSubmit": [
                {
                    "matcher": "*",
                    "hooks": [
                        {
                            "type": "command",
                            "command": wrong_command,
                            "timeout": 30,
                        }
                    ],
                }
            ]
        }
    }
    (claude_dir / "settings.json").write_text(json.dumps(settings), encoding="utf-8")

    # Act: Run erk doctor and capture output
    result = subprocess.run(
        ["erk", "doctor"],
        cwd=repo,
        capture_output=True,
        text=True,
    )

    # Assert: UserPromptSubmit hook check should fail
    # The check message is "UserPromptSubmit hook missing unified hook script"
    output = result.stdout + result.stderr
    assert "userpromptsubmit hook missing" in output.lower()
