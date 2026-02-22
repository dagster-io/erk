"""Tests for shell_utils module."""

from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

import pytest

from erk.cli.shell_utils import cleanup_stale_scripts, write_script_to_temp


def test_write_script_to_temp(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test that temp scripts are written with correct metadata."""
    temp_dir = tmp_path / "temp"
    temp_dir.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(temp_dir))

    script_content = "cd /foo\necho 'hello'\n"

    temp_path = write_script_to_temp(
        script_content,
        command_name="test",
        comment="test comment",
    )

    # File should exist
    assert temp_path.exists()

    # Should be in temp directory
    assert temp_path.parent == Path(tempfile.gettempdir())

    # Should have correct pattern
    assert temp_path.name.startswith("erk-test-")
    assert temp_path.name.endswith(".sh")

    # Should contain metadata header
    content = temp_path.read_text()
    assert "#!/bin/bash" in content
    assert "# erk test" in content
    assert "# test comment" in content
    assert script_content in content


def test_cleanup_stale_scripts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Test that old scripts are removed."""
    temp_dir = tmp_path / "temp"
    temp_dir.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(temp_dir))

    # Create an old script
    old_script = Path(tempfile.gettempdir()) / "erk-old-12345678.sh"
    old_script.write_text("# old script\n")

    # Set mtime to 2 hours ago
    two_hours_ago = time.time() - 7200
    os.utime(old_script, (two_hours_ago, two_hours_ago))

    # Create a new script
    new_script = Path(tempfile.gettempdir()) / "erk-new-87654321.sh"
    new_script.write_text("# new script\n")

    # Cleanup scripts older than 1 hour
    cleanup_stale_scripts(max_age_seconds=3600)

    # Old should be gone, new should remain
    assert not old_script.exists()
    assert new_script.exists()
