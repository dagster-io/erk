"""Smoke tests for code_stats.py."""

import subprocess
import sys
from pathlib import Path

# Add the scripts directory to the path - must come before code_stats import
SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

import pytest  # noqa: E402
from code_stats import (  # noqa: E402
    CategoryStats,
    DiffIndicators,
    DiffStats,
    categorize_by_content,
    fmt_num,
)


class TestDiffStats:
    def test_net_calculations(self) -> None:
        stats = DiffStats(
            py_add=100,
            py_del=30,
            py_test_add=50,
            py_test_del=10,
            md_add=20,
            md_del=5,
        )
        assert stats.py_net == 70
        assert stats.py_test_net == 40
        assert stats.md_net == 15
        assert stats.total_net == 125


class TestCategoryStats:
    def test_total_calculation(self) -> None:
        stats = CategoryStats(prs=[], py=100, py_test=50, md=25)
        assert stats.total == 175


class TestFmtNum:
    def test_positive_number(self) -> None:
        assert fmt_num(1234) == "+1,234"

    def test_negative_number(self) -> None:
        assert fmt_num(-1234) == "-1,234"

    def test_zero(self) -> None:
        assert fmt_num(0) == "+0"


class TestCategorizeByContent:
    def test_slash_command_is_user_feature(self) -> None:
        indicators = DiffIndicators(slash_command=True)
        assert categorize_by_content("Add new command", indicators) == "user_feature"

    def test_cli_command_for_erk_is_user_feature(self) -> None:
        indicators = DiffIndicators(cli_command=True)
        assert categorize_by_content("Add erk stack list command", indicators) == "user_feature"

    def test_cli_command_with_internal_api_is_internal(self) -> None:
        indicators = DiffIndicators(cli_command=True, internal_api=True)
        assert categorize_by_content("Add erk stack list command", indicators) == "internal"

    def test_skill_is_user_feature(self) -> None:
        indicators = DiffIndicators(skill=True)
        assert categorize_by_content("Add new skill", indicators) == "user_feature"

    def test_fix_at_start_is_bug_fix(self) -> None:
        indicators = DiffIndicators()
        assert categorize_by_content("Fix broken test", indicators) == "bug_fix"

    def test_fix_with_bug_indicator_is_bug_fix(self) -> None:
        indicators = DiffIndicators(bug_fix=True)
        assert categorize_by_content("Something fix here", indicators) == "bug_fix"

    def test_docs_only_is_docs(self) -> None:
        indicators = DiffIndicators(docs_only=True)
        assert categorize_by_content("Update documentation", indicators) == "docs"

    def test_migration_with_keyword_is_migration(self) -> None:
        indicators = DiffIndicators(config_migration=True)
        assert categorize_by_content("Migrate config to new format", indicators) == "migration"

    def test_internal_api_is_internal(self) -> None:
        indicators = DiffIndicators(internal_api=True)
        assert categorize_by_content("Update gateway interface", indicators) == "internal"

    def test_refactor_keyword_is_refactor(self) -> None:
        indicators = DiffIndicators()
        assert categorize_by_content("Refactor authentication module", indicators) == "refactor"

    def test_consolidate_keyword_is_refactor(self) -> None:
        indicators = DiffIndicators()
        assert categorize_by_content("Consolidate utilities", indicators) == "refactor"

    def test_add_abstraction_is_internal(self) -> None:
        indicators = DiffIndicators()
        assert categorize_by_content("Add session abstraction", indicators) == "internal"

    def test_improve_command_is_user_improvement(self) -> None:
        indicators = DiffIndicators()
        assert categorize_by_content("Improve command output", indicators) == "user_improvement"

    def test_improve_internal_is_internal(self) -> None:
        indicators = DiffIndicators()
        assert categorize_by_content("Improve performance", indicators) == "internal"

    def test_add_workflow_command_is_user_feature(self) -> None:
        indicators = DiffIndicators()
        assert categorize_by_content("Add workflow command", indicators) == "user_feature"

    def test_generic_add_is_internal(self) -> None:
        indicators = DiffIndicators()
        assert categorize_by_content("Add helper function", indicators) == "internal"

    def test_implement_is_internal(self) -> None:
        indicators = DiffIndicators()
        assert categorize_by_content("Implement new feature", indicators) == "internal"

    def test_unknown_is_other(self) -> None:
        indicators = DiffIndicators()
        assert categorize_by_content("Random changes", indicators) == "other"


class TestTableAlignment:
    """Tests for table output alignment."""

    def test_all_emojis_have_string_length_1(self) -> None:
        """All category emojis should be single codepoint (no variation selectors)."""
        from code_stats import CATEGORY_DATA

        for text, _, emoji in CATEGORY_DATA:
            assert len(emoji) == 1, (
                f"Emoji for '{text}' has length {len(emoji)}, expected 1. emoji={repr(emoji)}"
            )

    def test_all_emojis_have_display_width_2(self) -> None:
        """All category emojis should have East Asian Width 'W' (Wide)."""
        import unicodedata

        from code_stats import CATEGORY_DATA

        for text, _, emoji in CATEGORY_DATA:
            eaw = unicodedata.east_asian_width(emoji)
            assert eaw == "W", (
                f"Emoji for '{text}' has East Asian Width '{eaw}', expected 'W'. "
                f"emoji={repr(emoji)}"
            )


class TestScriptExecution:
    """Smoke test that the script can be executed."""

    def test_script_imports_successfully(self) -> None:
        """Verify the script can be imported without errors."""
        # This test passes if we got here - imports are at module level
        from code_stats import main

        assert callable(main)

    def test_script_runs_with_help_or_version(self) -> None:
        """Verify the script can at least start execution."""
        script_path = SCRIPTS_DIR / "code_stats.py"
        # Run with a date far in the future so no PRs are found (fast execution)
        result = subprocess.run(
            [sys.executable, str(script_path), "2099-01-01"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        # Should complete without error (may have empty results)
        assert result.returncode == 0
        assert "PRs Merged Since" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
