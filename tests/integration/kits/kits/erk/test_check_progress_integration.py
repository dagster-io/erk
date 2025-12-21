"""Integration tests for check-progress kit CLI command.

Tests the complete schema validation workflow for progress.md files.
"""

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from erk_kits.data.kits.erk.scripts.erk.check_progress import check_progress


@pytest.fixture
def valid_progress_file(tmp_path: Path) -> Path:
    """Create .impl/ folder with valid progress.md."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    progress_md = impl_dir / "progress.md"
    progress_md.write_text(
        """---
completed_steps: 1
total_steps: 3
steps:
  - text: '1. First step'
    completed: true
  - text: '2. Second step'
    completed: false
  - text: '3. Third step'
    completed: false
---

# Progress Tracking

- [x] 1. First step
- [ ] 2. Second step
- [ ] 3. Third step
""",
        encoding="utf-8",
    )

    return progress_md


def test_check_progress_valid_file(
    valid_progress_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that check-progress validates a correct progress.md."""
    monkeypatch.chdir(valid_progress_file.parent.parent)

    runner = CliRunner()
    result = runner.invoke(check_progress, ["--json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["valid"] is True
    assert data["errors"] == []


def test_check_progress_valid_file_normal_mode(
    valid_progress_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test human-readable output for valid progress.md."""
    monkeypatch.chdir(valid_progress_file.parent.parent)

    runner = CliRunner()
    result = runner.invoke(check_progress, [])

    assert result.exit_code == 0
    assert "progress.md schema is valid" in result.output


def test_check_progress_empty_steps(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that empty steps array is valid."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    progress_md = impl_dir / "progress.md"
    progress_md.write_text(
        """---
completed_steps: 0
total_steps: 0
steps: []
---

# Progress Tracking

No steps detected in plan.
""",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(check_progress, ["--json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["valid"] is True
    assert data["errors"] == []


def test_check_progress_missing_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test error when progress.md doesn't exist."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()
    # No progress.md created

    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(check_progress, ["--json"])

    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["valid"] is False
    assert "progress.md file not found" in data["errors"]


def test_check_progress_no_frontmatter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test error when progress.md has no YAML frontmatter."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    progress_md = impl_dir / "progress.md"
    progress_md.write_text(
        """# Progress Tracking

No steps detected in plan.
""",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(check_progress, ["--json"])

    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["valid"] is False
    assert "Missing 'steps' field" in data["errors"]


def test_check_progress_missing_steps_field(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test error when steps field is missing."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    progress_md = impl_dir / "progress.md"
    progress_md.write_text(
        """---
completed_steps: 0
total_steps: 0
---

# Progress
""",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(check_progress, ["--json"])

    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["valid"] is False
    assert "Missing 'steps' field" in data["errors"]


def test_check_progress_inconsistent_counts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test error when completed_steps doesn't match actual count."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    progress_md = impl_dir / "progress.md"
    progress_md.write_text(
        """---
completed_steps: 3
total_steps: 2
steps:
  - text: '1. Step one'
    completed: true
  - text: '2. Step two'
    completed: false
---

# Progress
""",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(check_progress, ["--json"])

    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["valid"] is False
    # Should have error about completed_steps mismatch
    assert any("completed_steps" in e and "actual count" in e for e in data["errors"])


def test_check_progress_normal_mode_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test normal mode outputs errors to stderr."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    progress_md = impl_dir / "progress.md"
    progress_md.write_text(
        """---
completed_steps: 0
---

# Progress
""",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(check_progress, [])

    assert result.exit_code == 1
    assert "Error:" in result.output


def test_check_progress_step_missing_text(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test error when step is missing text field."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    progress_md = impl_dir / "progress.md"
    progress_md.write_text(
        """---
completed_steps: 0
total_steps: 1
steps:
  - completed: false
---

# Progress
""",
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)

    runner = CliRunner()
    result = runner.invoke(check_progress, ["--json"])

    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["valid"] is False
    assert "Step 1 missing 'text' field" in data["errors"]
