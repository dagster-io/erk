"""Tests for CLI preamble artifact sync check."""

from pathlib import Path
from unittest.mock import patch

import pytest

from erk.artifacts.models import ArtifactState
from erk.artifacts.preamble import check_and_prompt_artifact_sync
from erk.artifacts.state import save_artifact_state


def test_preamble_skips_when_no_sync_flag(tmp_project: Path) -> None:
    """Test that preamble does nothing when no_sync=True."""
    # No state file exists, but should not fail because no_sync=True
    check_and_prompt_artifact_sync(tmp_project, no_sync=True)
    # No exception means success


def test_preamble_skips_in_dev_mode(tmp_project: Path) -> None:
    """Test that preamble skips check in dev mode."""
    # Create dev mode indicator
    (tmp_project / "packages" / "erk-kits").mkdir(parents=True)

    # No state file exists, but should not fail because dev mode
    check_and_prompt_artifact_sync(tmp_project, no_sync=False)
    # No exception means success


def test_preamble_passes_when_up_to_date(tmp_project: Path) -> None:
    """Test that preamble passes when artifacts are up to date."""
    save_artifact_state(tmp_project, ArtifactState(version="1.0.0"))

    with patch("erk.artifacts.staleness.get_current_version", return_value="1.0.0"):
        check_and_prompt_artifact_sync(tmp_project, no_sync=False)
    # No exception means success


def test_preamble_skips_when_not_initialized(tmp_project: Path) -> None:
    """Test that preamble silently skips when project is not initialized.

    Artifact sync is optional - projects that haven't run 'erk init' with
    the artifact sync feature should not be blocked from using erk commands.
    """
    with patch("erk.artifacts.staleness.get_current_version", return_value="1.0.0"):
        check_and_prompt_artifact_sync(tmp_project, no_sync=False)
    # No exception means success - not initialized is silently skipped


def test_preamble_fails_stale_non_tty(tmp_project: Path) -> None:
    """Test that preamble fails when stale in non-TTY mode."""
    save_artifact_state(tmp_project, ArtifactState(version="1.0.0"))

    with (
        patch("erk.artifacts.staleness.get_current_version", return_value="2.0.0"),
        patch("sys.stdin.isatty", return_value=False),
    ):
        with pytest.raises(SystemExit) as exc_info:
            check_and_prompt_artifact_sync(tmp_project, no_sync=False)

    assert exc_info.value.code == 1


def test_preamble_prompts_stale_tty_user_declines(tmp_project: Path) -> None:
    """Test that preamble prompts in TTY mode when stale, user declines."""
    save_artifact_state(tmp_project, ArtifactState(version="1.0.0"))

    with (
        patch("erk.artifacts.staleness.get_current_version", return_value="2.0.0"),
        patch("sys.stdin.isatty", return_value=True),
        patch("click.confirm", return_value=False),
        patch("click.echo"),
    ):
        # User declined, so function returns without syncing
        check_and_prompt_artifact_sync(tmp_project, no_sync=False)
        # No exception means success (user declined)


def test_preamble_prompts_stale_tty_user_accepts(tmp_project: Path) -> None:
    """Test that preamble prompts in TTY mode when stale, user accepts sync."""
    save_artifact_state(tmp_project, ArtifactState(version="1.0.0"))

    mock_sync_result = type("SyncResult", (), {"artifacts_installed": 5})()

    with (
        patch("erk.artifacts.staleness.get_current_version", return_value="2.0.0"),
        patch("sys.stdin.isatty", return_value=True),
        patch("click.confirm", return_value=True),
        patch("click.echo"),
        # Patch at the module where the inline import happens
        patch("erk.artifacts.sync.sync_artifacts", return_value=mock_sync_result),
    ):
        check_and_prompt_artifact_sync(tmp_project, no_sync=False)
        # No exception means success (sync completed)
