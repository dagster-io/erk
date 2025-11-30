from datetime import datetime
from pathlib import Path

import pytest
from erk_shared.naming import (
    WORKTREE_DATE_SUFFIX_FORMAT,
    default_branch_for_worktree,
    derive_branch_name_from_title,
    ensure_unique_worktree_name,
    extract_trailing_number,
    sanitize_branch_component,
    sanitize_worktree_name,
    strip_plan_from_filename,
)


def _get_current_date_suffix() -> str:
    """Get the current date suffix for plan-derived worktrees."""
    return datetime.now().strftime(WORKTREE_DATE_SUFFIX_FORMAT)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Foo", "foo"),
        (" Foo Bar ", "foo-bar"),
        ("A/B C", "a/b-c"),
        ("@@weird!!name??", "weird-name"),
        # Test truncation to 31 characters
        ("a" * 35, "a" * 31),
        (
            "this-is-a-very-long-branch-name-that-exceeds-thirty-characters",
            "this-is-a-very-long-branch-name",
        ),
        ("exactly-31-characters-long-oka", "exactly-31-characters-long-oka"),
        (
            "32-characters-long-should-be-abc",
            "32-characters-long-should-be-ab",
        ),  # Truncates to 31
        ("short", "short"),
        # Test long names with trailing hyphens are stripped
        (
            "branch-name-with-dash-at-position-31-",
            "branch-name-with-dash-at-positi",
        ),
        # Test very long names truncate to 31
        (
            "1234567890123456789012345678901-extra",
            "1234567890123456789012345678901",
        ),  # Hyphen at position 31 stripped
    ],
)
def test_sanitize_branch_component(value: str, expected: str) -> None:
    assert sanitize_branch_component(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("feature X", "feature-x"),
        ("/ / ", "work"),
    ],
)
def test_default_branch_for_worktree(value: str, expected: str) -> None:
    assert default_branch_for_worktree(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Foo", "foo"),
        ("Add_Auth_Feature", "add-auth-feature"),
        ("My_Cool_Plan", "my-cool-plan"),
        ("FOO_BAR_BAZ", "foo-bar-baz"),
        ("feature__with___multiple___underscores", "feature-with-multiple-underscor"),
        ("name-with-hyphens", "name-with-hyphens"),
        ("Mixed_Case-Hyphen_Underscore", "mixed-case-hyphen-underscore"),
        ("@@weird!!name??", "weird-name"),
        ("   spaces   ", "spaces"),
        ("---", "work"),
        # Test truncation to 31 characters
        ("a" * 35, "a" * 31),
        (
            "this-is-a-very-long-worktree-name-that-exceeds-thirty-characters",
            "this-is-a-very-long-worktree-na",
        ),
        ("exactly-31-characters-long-oka", "exactly-31-characters-long-oka"),
        (
            "32-characters-long-should-be-abc",
            "32-characters-long-should-be-ab",
        ),  # Truncates to 31
        # Test truncation with trailing hyphen removal
        (
            "worktree-name-with-dash-at-position-31-",
            "worktree-name-with-dash-at-posi",
        ),
        # Test truncation that ends with hyphen is stripped
        (
            "1234567890123456789012345678901-extra",
            "1234567890123456789012345678901",
        ),  # Hyphen at position 31 stripped
    ],
)
def test_sanitize_worktree_name(value: str, expected: str) -> None:
    assert sanitize_worktree_name(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("devclikit-extraction-plan", "devclikit-extraction"),
        ("my-feature-plan", "my-feature"),
        ("plan-for-auth", "for-auth"),
        ("plan-something", "something"),
        ("something-plan", "something"),
        ("something-plan-else", "something-else"),
        ("plan-my-plan-feature", "my-feature"),
        ("my-plan-feature-plan", "my-feature"),
        ("plan", "plan"),
        ("my_feature_plan", "my_feature"),
        ("my feature plan", "my feature"),
        ("my-feature_plan", "my-feature"),
        ("MY-FEATURE-PLAN", "MY-FEATURE"),
        ("My-Feature-Plan", "My-Feature"),
        ("my-feature-PLAN", "my-feature"),
        ("airplane-feature", "airplane-feature"),
        ("explain-system", "explain-system"),
        ("planted-tree", "planted-tree"),
        ("planning-session", "planning-session"),
        ("plans-document", "plans-document"),
        ("-plan-feature", "feature"),
        ("feature-plan-", "feature"),
        ("my-feature-implementation-plan", "my-feature"),
        ("implementation-plan-for-auth", "for-auth"),
        ("implementation_plan_feature", "feature"),
        ("feature implementation plan", "feature"),
        ("my-feature_implementation-plan", "my-feature"),
        ("implementation_plan-for-auth", "for-auth"),
        ("IMPLEMENTATION-PLAN-FEATURE", "FEATURE"),
        ("Implementation-Plan-Feature", "Feature"),
        ("my-IMPLEMENTATION-plan", "my"),
        ("my-implementation-plan-feature", "my-feature"),
        ("plan-implementation-plan", "implementation"),
        ("plan implementation plan", "implementation"),
        ("implementation-plan", "implementation"),
        ("implementation_plan", "implementation"),
        ("IMPLEMENTATION-PLAN", "IMPLEMENTATION"),
        ("reimplementation-feature", "reimplementation-feature"),
        ("implantation-system", "implantation-system"),
    ],
)
def test_strip_plan_from_filename(value: str, expected: str) -> None:
    assert strip_plan_from_filename(value) == expected


@pytest.mark.parametrize(
    ("name", "expected_base", "expected_number"),
    [
        ("my-feature", "my-feature", None),
        ("my-feature-2", "my-feature", 2),
        ("fix-42", "fix", 42),
        ("feature-3-test", "feature-3-test", None),  # Number in middle, not trailing
        ("test-123", "test", 123),
        ("no-number", "no-number", None),
        ("v2-feature-10", "v2-feature", 10),
    ],
)
def test_extract_trailing_number(
    name: str, expected_base: str, expected_number: int | None
) -> None:
    """Test extracting trailing numbers from worktree names."""
    base, number = extract_trailing_number(name)
    assert base == expected_base
    assert number == expected_number


def test_ensure_unique_worktree_name_first_time(tmp_path: Path) -> None:
    """Test first-time worktree creation gets only datetime suffix."""
    from erk_shared.git.real import RealGit

    repo_dir = tmp_path / "erks"
    repo_dir.mkdir()

    git_ops = RealGit()
    result = ensure_unique_worktree_name("my-feature", repo_dir, git_ops)

    # Should have datetime suffix in format -YY-MM-DD-HHMM
    date_suffix = _get_current_date_suffix()
    assert result == f"my-feature-{date_suffix}"
    assert not (repo_dir / result).exists()


def test_ensure_unique_worktree_name_duplicate_same_minute(tmp_path: Path) -> None:
    """Test duplicate worktree in same minute adds -2 after datetime suffix."""
    from erk_shared.git.real import RealGit

    repo_dir = tmp_path / "erks"
    repo_dir.mkdir()

    date_suffix = _get_current_date_suffix()
    existing_name = f"my-feature-{date_suffix}"
    (repo_dir / existing_name).mkdir()

    git_ops = RealGit()
    result = ensure_unique_worktree_name("my-feature", repo_dir, git_ops)

    assert result == f"my-feature-{date_suffix}-2"
    assert not (repo_dir / result).exists()
    assert (repo_dir / existing_name).exists()


def test_ensure_unique_worktree_name_multiple_duplicates(tmp_path: Path) -> None:
    """Test multiple duplicates increment correctly."""
    from erk_shared.git.real import RealGit

    repo_dir = tmp_path / "erks"
    repo_dir.mkdir()

    date_suffix = _get_current_date_suffix()
    (repo_dir / f"my-feature-{date_suffix}").mkdir()
    (repo_dir / f"my-feature-{date_suffix}-2").mkdir()
    (repo_dir / f"my-feature-{date_suffix}-3").mkdir()

    git_ops = RealGit()
    result = ensure_unique_worktree_name("my-feature", repo_dir, git_ops)

    assert result == f"my-feature-{date_suffix}-4"


def test_ensure_unique_worktree_name_with_existing_number(tmp_path: Path) -> None:
    """Test name with existing number in base preserves it."""
    from erk_shared.git.real import RealGit

    repo_dir = tmp_path / "erks"
    repo_dir.mkdir()

    git_ops = RealGit()
    date_suffix = _get_current_date_suffix()
    result = ensure_unique_worktree_name("fix-v3", repo_dir, git_ops)

    # Base name has number, should preserve it in datetime-suffixed name
    assert result == f"fix-v3-{date_suffix}"

    # Create it and try again
    (repo_dir / result).mkdir()
    result2 = ensure_unique_worktree_name("fix-v3", repo_dir, git_ops)

    assert result2 == f"fix-v3-{date_suffix}-2"


def test_sanitize_branch_component_truncates_at_31_chars() -> None:
    """Branch names should truncate to 31 characters maximum."""
    # Exactly 31 characters
    assert len(sanitize_branch_component("a" * 31)) == 31

    # 32 characters truncates to 31
    assert len(sanitize_branch_component("a" * 32)) == 31

    # Long descriptive name gets truncated
    long_name = "fix-dependency-injection-in-simplesubmitpy-to-eliminate-test-mocking"
    result = sanitize_branch_component(long_name)
    assert len(result) == 31
    assert not result.endswith("-")  # No trailing hyphens after truncation


def test_sanitize_branch_component_matches_worktree_length() -> None:
    """Branch and worktree names should have same length for same input."""
    test_name = "very-long-feature-name-that-exceeds-thirty-characters-easily"
    branch = sanitize_branch_component(test_name)
    worktree = sanitize_worktree_name(test_name)
    assert len(branch) == len(worktree)
    assert len(branch) == 31


def test_very_long_title_truncates_to_45_chars_total() -> None:
    """Regression test: 99-char title should truncate to max 45 chars total with datetime suffix.

    This tests the bug fix where `erk implement` created excessively long branch names.
    Example: "refactor erk implement command to support interactive and
    non-interactive execution modes"

    Note: The 31-char limit includes rstrip("-") after truncation,
    so actual length may be <= 31.
    """
    # 89-character title that caused the original bug
    long_title = (
        "refactor erk implement command to support interactive and non-interactive execution modes"
    )

    # Sanitize the worktree name (should be <= 31 chars max, trailing hyphens stripped)
    base_name = sanitize_worktree_name(long_title)
    assert len(base_name) <= 31

    # With datetime suffix (-YY-MM-DD-HHMM = 14 chars including hyphen), total should be <= 45 chars
    date_suffix = "25-11-23-1430"
    name_with_date = f"{base_name}-{date_suffix}"
    assert len(name_with_date) <= 45

    # Verify the base name is correctly truncated (30 chars after rstrip of trailing hyphen)
    assert base_name == "refactor-erk-implement-command"
    assert len(base_name) == 30  # 31 chars truncated, then trailing hyphen stripped


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("My Feature", "my-feature"),
        ("Fix Bug #123!", "fix-bug-123"),
        ("Simple", "simple"),
        ("With_Underscores", "with-underscores"),
        ("UPPERCASE", "uppercase"),
        ("spaces  multiple   here", "spaces-multiple-here"),
        ("leading---hyphens", "leading-hyphens"),
        ("trailing---", "trailing"),
        ("---both---", "both"),
        # Test 30-char truncation (different from sanitize_branch_component's 31)
        ("a" * 40, "a" * 30),
        ("abcdefghijklmnopqrstuvwxyz-1234567890", "abcdefghijklmnopqrstuvwxyz-123"),
        # Trailing hyphen after truncation is removed
        ("this-is-thirty-chars-exact-yes", "this-is-thirty-chars-exact-yes"),  # Exactly 30
        ("this-is-thirty-one-chars-exact", "this-is-thirty-one-chars-exact"),  # 31 chars -> 30
        # Test non-alphanumeric characters
        ("feat: add something", "feat-add-something"),
        ("feat/add/something", "feat-add-something"),
        ("feat(scope): message", "feat-scope-message"),
    ],
)
def test_derive_branch_name_from_title(title: str, expected: str) -> None:
    """Test derive_branch_name_from_title matches workflow logic."""
    assert derive_branch_name_from_title(title) == expected


def test_derive_branch_name_truncates_to_30_chars() -> None:
    """Branch names from titles should truncate to 30 characters maximum.

    This matches the workflow logic in dispatch-erk-queue-git.yml which uses:
    BRANCH_NAME="${BRANCH_NAME:0:30}"
    """
    # Exactly 30 characters
    assert len(derive_branch_name_from_title("a" * 30)) == 30

    # 31 characters truncates to 30
    assert len(derive_branch_name_from_title("a" * 31)) == 30

    # Long descriptive name gets truncated
    long_name = "fix-dependency-injection-in-simplesubmitpy-to-eliminate-test-mocking"
    result = derive_branch_name_from_title(long_name)
    assert len(result) == 30
    assert not result.endswith("-")  # No trailing hyphens after truncation
