"""Tests for the pure extract_plan_title() function."""

from pathlib import Path

from erk.cli.commands.exec.scripts.exit_plan_mode_hook import extract_plan_title


class TestExtractPlanTitle:
    """Tests for the pure extract_plan_title() function."""

    def test_extracts_h1_heading(self, tmp_path: Path) -> None:
        """Extract title from first H1 heading."""
        plan_file = tmp_path / "plan.md"
        plan_file.write_text("# My Plan Title\n\nSome content here.\n", encoding="utf-8")
        assert extract_plan_title(plan_file) == "My Plan Title"

    def test_extracts_from_task_section(self, tmp_path: Path) -> None:
        """Extract title from ## Task section when no H1."""
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(
            "## Task\nDo the thing with feature X\n\n## Details\nMore info.",
            encoding="utf-8",
        )
        assert extract_plan_title(plan_file) == "Do the thing with feature X"

    def test_skips_generic_plan_heading(self, tmp_path: Path) -> None:
        """Skip generic '# Plan' heading and fall back to ## Task."""
        plan_file = tmp_path / "plan.md"
        plan_file.write_text("# Plan\n\n## Task\nActual task description\n", encoding="utf-8")
        assert extract_plan_title(plan_file) == "Actual task description"

    def test_skips_generic_implementation_plan_heading(self, tmp_path: Path) -> None:
        """Skip generic '# Implementation Plan' heading."""
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(
            "# Implementation Plan\n\n## Task\nBuild the widget\n", encoding="utf-8"
        )
        assert extract_plan_title(plan_file) == "Build the widget"

    def test_returns_none_for_no_file(self) -> None:
        """Return None when plan_file_path is None."""
        assert extract_plan_title(None) is None

    def test_returns_none_for_nonexistent_file(self, tmp_path: Path) -> None:
        """Return None when file doesn't exist."""
        nonexistent = tmp_path / "does_not_exist.md"
        assert extract_plan_title(nonexistent) is None

    def test_returns_none_for_empty_file(self, tmp_path: Path) -> None:
        """Return None when file is empty."""
        plan_file = tmp_path / "plan.md"
        plan_file.write_text("", encoding="utf-8")
        assert extract_plan_title(plan_file) is None

    def test_returns_none_when_no_title_found(self, tmp_path: Path) -> None:
        """Return None when no valid title pattern found."""
        plan_file = tmp_path / "plan.md"
        plan_file.write_text(
            "Some random content\nwithout any headings\nor task section.", encoding="utf-8"
        )
        assert extract_plan_title(plan_file) is None

    def test_prefers_h1_over_task_section(self, tmp_path: Path) -> None:
        """H1 heading takes precedence over ## Task section."""
        plan_file = tmp_path / "plan.md"
        plan_file.write_text("# Better Title\n\n## Task\nTask description\n", encoding="utf-8")
        assert extract_plan_title(plan_file) == "Better Title"
