"""Tests for get-closing-text kit CLI command.

Tests the closing text generation for PR body based on .impl/plan-ref.json or branch name.
Uses FakeGit for dependency injection instead of mocking subprocess.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.get_closing_text import get_closing_text
from erk_shared.context.context import ErkContext
from erk_shared.gateway.git.fake import FakeGit


def test_get_closing_text_with_issue_reference(tmp_path: Path) -> None:
    """Test get-closing-text outputs 'Closes #N' when plan-ref.json exists."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    plan_ref_json = impl_dir / "plan-ref.json"
    plan_ref_json.write_text(
        json.dumps(
            {
                "provider": "github",
                "plan_id": "776",
                "url": "https://github.com/org/repo/issues/776",
                "created_at": "2025-01-01T00:00:00Z",
                "synced_at": "2025-01-01T00:00:00Z",
                "labels": ["erk-plan"],
                "objective_id": None,
            }
        ),
        encoding="utf-8",
    )

    git = FakeGit(current_branches={tmp_path: "P776-feature-01-04-1234"})
    ctx = ErkContext.for_test(git=git, cwd=tmp_path)

    runner = CliRunner()
    result = runner.invoke(get_closing_text, [], obj=ctx)

    assert result.exit_code == 0
    assert result.output.strip() == "Closes #776"


def test_get_closing_text_no_impl_folder_with_branch_fallback(tmp_path: Path) -> None:
    """Test get-closing-text outputs nothing when branch doesn't resolve."""
    # No .impl/ folder - P-prefix branches no longer resolve
    git = FakeGit(current_branches={tmp_path: "P123-add-feature-01-04-1234"})
    ctx = ErkContext.for_test(git=git, cwd=tmp_path)

    runner = CliRunner()
    result = runner.invoke(get_closing_text, [], obj=ctx)

    assert result.exit_code == 0
    assert result.output == ""


def test_get_closing_text_no_impl_folder_no_issue_in_branch(tmp_path: Path) -> None:
    """Test get-closing-text outputs nothing when no .impl/ and branch has no issue."""
    # Branch name without issue number pattern
    git = FakeGit(current_branches={tmp_path: "feature-branch"})
    ctx = ErkContext.for_test(git=git, cwd=tmp_path)

    runner = CliRunner()
    result = runner.invoke(get_closing_text, [], obj=ctx)

    assert result.exit_code == 0
    assert result.output == ""


def test_get_closing_text_no_issue_json(tmp_path: Path) -> None:
    """Test get-closing-text outputs nothing when .impl/ exists but no plan-ref.json."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    # Branch without issue prefix
    git = FakeGit(current_branches={tmp_path: "main"})
    ctx = ErkContext.for_test(git=git, cwd=tmp_path)

    runner = CliRunner()
    result = runner.invoke(get_closing_text, [], obj=ctx)

    assert result.exit_code == 0
    assert result.output == ""


def test_get_closing_text_with_impl_context(tmp_path: Path) -> None:
    """Test get-closing-text works with .erk/impl-context/ folder."""
    impl_dir = tmp_path / ".erk" / "impl-context"
    impl_dir.mkdir(parents=True)

    plan_ref_json = impl_dir / "plan-ref.json"
    plan_ref_json.write_text(
        json.dumps(
            {
                "provider": "github",
                "plan_id": "2935",
                "url": "https://github.com/dagster-io/erk/issues/2935",
                "created_at": "2025-01-01T00:00:00Z",
                "synced_at": "2025-01-01T00:00:00Z",
                "labels": ["erk-plan"],
                "objective_id": None,
            }
        ),
        encoding="utf-8",
    )

    git = FakeGit(current_branches={tmp_path: "P2935-feature"})
    ctx = ErkContext.for_test(git=git, cwd=tmp_path)

    runner = CliRunner()
    result = runner.invoke(get_closing_text, [], obj=ctx)

    assert result.exit_code == 0
    assert result.output.strip() == "Closes #2935"


def test_get_closing_text_prefers_impl_over_impl_context(tmp_path: Path) -> None:
    """Test get-closing-text prefers .impl/ when both folders exist."""
    # Create both folders with different plan numbers
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()
    (impl_dir / "plan-ref.json").write_text(
        json.dumps(
            {
                "provider": "github",
                "plan_id": "100",
                "url": "https://github.com/org/repo/issues/100",
                "created_at": "2025-01-01T00:00:00Z",
                "synced_at": "2025-01-01T00:00:00Z",
                "labels": ["erk-plan"],
                "objective_id": None,
            }
        ),
        encoding="utf-8",
    )

    impl_context_dir = tmp_path / ".erk" / "impl-context"
    impl_context_dir.mkdir(parents=True)
    (impl_context_dir / "plan-ref.json").write_text(
        json.dumps(
            {
                "provider": "github",
                "plan_id": "200",
                "url": "https://github.com/org/repo/issues/200",
                "created_at": "2025-01-01T00:00:00Z",
                "synced_at": "2025-01-01T00:00:00Z",
                "labels": ["erk-plan"],
                "objective_id": None,
            }
        ),
        encoding="utf-8",
    )

    git = FakeGit(current_branches={tmp_path: "P100-feature"})
    ctx = ErkContext.for_test(git=git, cwd=tmp_path)

    runner = CliRunner()
    result = runner.invoke(get_closing_text, [], obj=ctx)

    assert result.exit_code == 0
    assert result.output.strip() == "Closes #100"


def test_get_closing_text_invalid_json(tmp_path: Path) -> None:
    """Test get-closing-text outputs nothing when JSON invalid and branch doesn't resolve."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    plan_ref_json = impl_dir / "plan-ref.json"
    plan_ref_json.write_text("not valid json {{{", encoding="utf-8")

    # With invalid JSON and branch not resolving, no closing text
    git = FakeGit(current_branches={tmp_path: "P42-feature"})
    ctx = ErkContext.for_test(git=git, cwd=tmp_path)

    runner = CliRunner()
    result = runner.invoke(get_closing_text, [], obj=ctx)

    # No closing text since both JSON and branch detection fail
    assert result.exit_code == 0
    assert result.output == ""


def test_get_closing_text_detached_head(tmp_path: Path) -> None:
    """Test get-closing-text outputs nothing when on detached HEAD."""
    # Detached HEAD - get_current_branch returns None
    git = FakeGit(current_branches={tmp_path: None})
    ctx = ErkContext.for_test(git=git, cwd=tmp_path)

    runner = CliRunner()
    result = runner.invoke(get_closing_text, [], obj=ctx)

    assert result.exit_code == 0
    assert result.output == ""


def test_get_closing_text_branch_issue_json_mismatch(tmp_path: Path) -> None:
    """Test get-closing-text succeeds when plan-ref.json exists (branch no longer matters)."""
    impl_dir = tmp_path / ".impl"
    impl_dir.mkdir()

    plan_ref_json = impl_dir / "plan-ref.json"
    plan_ref_json.write_text(
        json.dumps(
            {
                "provider": "github",
                "plan_id": "99",
                "url": "https://github.com/org/repo/issues/99",
                "created_at": "2025-01-01T00:00:00Z",
                "synced_at": "2025-01-01T00:00:00Z",
                "labels": ["erk-plan"],
                "objective_id": None,
            }
        ),
        encoding="utf-8",
    )

    # Branch pattern doesn't matter since it no longer resolves
    git = FakeGit(current_branches={tmp_path: "P42-wrong-issue-01-04-1234"})
    ctx = ErkContext.for_test(git=git, cwd=tmp_path)

    runner = CliRunner()
    result = runner.invoke(get_closing_text, [], obj=ctx)

    assert result.exit_code == 0
    assert result.output.strip() == "Closes #99"
