"""Unit tests for plan_content module."""

from pathlib import Path

from erk_shared.gateway.claude_installation.fake import FakeClaudeInstallation
from erk_shared.plan_store.plan_content import extract_title_from_plan, resolve_plan_content

# extract_title_from_plan tests


def test_extract_title_from_plan_returns_first_heading() -> None:
    """Verify first markdown heading is extracted as title."""
    content = "# My Feature Plan\n\nSome description"

    result = extract_title_from_plan(content)

    assert result == "My Feature Plan"


def test_extract_title_from_plan_strips_whitespace() -> None:
    """Verify whitespace around title is stripped."""
    content = "#   Spaced Title   \n\nContent"

    result = extract_title_from_plan(content)

    assert result == "Spaced Title"


def test_extract_title_from_plan_returns_untitled_when_no_heading() -> None:
    """Verify fallback to 'Untitled Plan' when no heading found."""
    content = "Some text without any headings\n\nMore text"

    result = extract_title_from_plan(content)

    assert result == "Untitled Plan"


def test_extract_title_from_plan_ignores_h2_headings() -> None:
    """Verify only h1 headings are considered."""
    content = "## H2 Heading\n\n### H3 Heading"

    result = extract_title_from_plan(content)

    assert result == "Untitled Plan"


def test_extract_title_from_plan_skips_leading_blank_lines() -> None:
    """Verify heading is found even after leading blank lines."""
    content = "\n\n\n# Heading After Blanks\n\nContent"

    result = extract_title_from_plan(content)

    assert result == "Heading After Blanks"


def test_extract_title_from_plan_empty_string() -> None:
    """Verify empty string returns fallback."""
    result = extract_title_from_plan("")

    assert result == "Untitled Plan"


# resolve_plan_content tests


def test_resolve_plan_content_plan_file_takes_priority(tmp_path: Path) -> None:
    """Verify plan_file parameter has highest priority."""
    plan_file = tmp_path / "explicit-plan.md"
    plan_file.write_text("# Explicit Plan", encoding="utf-8")

    fake_claude = FakeClaudeInstallation.for_test(
        plans={"other": "# Other Plan"},
    )

    result = resolve_plan_content(
        plan_file=plan_file,
        session_id="test-session",
        repo_root=tmp_path,
        claude_installation=fake_claude,
        cwd=tmp_path,
    )

    assert result == "# Explicit Plan"


def test_resolve_plan_content_scratch_dir_over_claude_plans(tmp_path: Path) -> None:
    """Verify scratch directory plan takes priority over claude_installation."""
    session_id = "test-session"
    scratch_dir = tmp_path / ".erk" / "scratch" / "sessions" / session_id
    scratch_dir.mkdir(parents=True)
    (scratch_dir / "plan.md").write_text("# Scratch Plan", encoding="utf-8")

    fake_claude = FakeClaudeInstallation.for_test(
        plans={"other": "# Claude Plan"},
    )

    result = resolve_plan_content(
        plan_file=None,
        session_id=session_id,
        repo_root=tmp_path,
        claude_installation=fake_claude,
        cwd=tmp_path,
    )

    assert result == "# Scratch Plan"


def test_resolve_plan_content_falls_back_to_claude_installation(tmp_path: Path) -> None:
    """Verify fallback to claude_installation when no scratch plan exists."""
    fake_claude = FakeClaudeInstallation.for_test(
        plans={"fallback": "# Claude Plan"},
    )

    result = resolve_plan_content(
        plan_file=None,
        session_id="no-scratch-session",
        repo_root=tmp_path,
        claude_installation=fake_claude,
        cwd=tmp_path,
    )

    assert result == "# Claude Plan"


def test_resolve_plan_content_returns_none_when_no_plan(tmp_path: Path) -> None:
    """Verify None is returned when no plan found anywhere."""
    fake_claude = FakeClaudeInstallation.for_test()

    result = resolve_plan_content(
        plan_file=None,
        session_id="empty-session",
        repo_root=tmp_path,
        claude_installation=fake_claude,
        cwd=tmp_path,
    )

    assert result is None


def test_resolve_plan_content_no_session_id_uses_claude_installation(tmp_path: Path) -> None:
    """Verify scratch is skipped when session_id is None."""
    fake_claude = FakeClaudeInstallation.for_test(
        plans={"plan": "# No Session Plan"},
    )

    result = resolve_plan_content(
        plan_file=None,
        session_id=None,
        repo_root=tmp_path,
        claude_installation=fake_claude,
        cwd=tmp_path,
    )

    assert result == "# No Session Plan"
