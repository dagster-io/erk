"""Tests for the pure abbreviate_for_header() function."""

from erk.cli.commands.exec.scripts.exit_plan_mode_hook import abbreviate_for_header


class TestAbbreviateForHeader:
    """Tests for the pure abbreviate_for_header() function."""

    def test_short_branch_not_truncated(self) -> None:
        """Short branch names are not truncated."""
        assert abbreviate_for_header("feature-x") == "br:feature-x"

    def test_long_branch_truncated(self) -> None:
        """Long branch names are truncated to 9 chars."""
        # "P4535-add-feature" -> truncated to "P4535-add"
        assert abbreviate_for_header("P4535-add-feature") == "br:P4535-add"

    def test_issue_prefix_branch(self) -> None:
        """Issue-prefixed branches show issue number."""
        assert abbreviate_for_header("P4535-foo") == "br:P4535-foo"

    def test_none_returns_default(self) -> None:
        """None returns 'Plan Action' fallback."""
        assert abbreviate_for_header(None) == "Plan Action"

    def test_exactly_nine_chars(self) -> None:
        """Branch name exactly 9 chars is not truncated."""
        assert abbreviate_for_header("123456789") == "br:123456789"

    def test_ten_chars_truncated(self) -> None:
        """Branch name of 10 chars is truncated to 9."""
        assert abbreviate_for_header("1234567890") == "br:123456789"

    def test_main_branch(self) -> None:
        """Main branch is shown as-is."""
        assert abbreviate_for_header("main") == "br:main"

    def test_master_branch(self) -> None:
        """Master branch is shown as-is."""
        assert abbreviate_for_header("master") == "br:master"
