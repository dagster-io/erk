"""Tests for CodeReviewsSystemCapability.

Tests the unified code reviews workflow infrastructure installation.
"""

from pathlib import Path

from erk.core.capabilities.code_reviews_system import CodeReviewsSystemCapability


def test_name_is_code_reviews_system() -> None:
    """Test capability name."""
    capability = CodeReviewsSystemCapability()
    assert capability.name == "code-reviews-system"


def test_description_mentions_code_reviews() -> None:
    """Test description is informative."""
    capability = CodeReviewsSystemCapability()
    assert "code review" in capability.description.lower()


def test_scope_is_project() -> None:
    """Test capability is project-scoped."""
    capability = CodeReviewsSystemCapability()
    assert capability.scope == "project"


def test_is_installed_returns_false_when_no_repo_root() -> None:
    """Test is_installed returns False when repo_root is None."""
    capability = CodeReviewsSystemCapability()
    assert capability.is_installed(repo_root=None) is False


def test_is_installed_returns_false_when_workflow_missing(tmp_path: Path) -> None:
    """Test is_installed returns False when workflow doesn't exist."""
    capability = CodeReviewsSystemCapability()
    assert capability.is_installed(repo_root=tmp_path) is False


def test_is_installed_returns_true_when_workflow_exists(tmp_path: Path) -> None:
    """Test is_installed returns True when code-reviews.yml exists."""
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "code-reviews.yml").write_text("name: code-reviews", encoding="utf-8")

    capability = CodeReviewsSystemCapability()
    assert capability.is_installed(repo_root=tmp_path) is True


def test_install_fails_without_repo_root() -> None:
    """Test install fails when repo_root is None."""
    capability = CodeReviewsSystemCapability()
    result = capability.install(repo_root=None)
    assert result.success is False
    assert "requires repo_root" in result.message


def test_uninstall_fails_without_repo_root() -> None:
    """Test uninstall fails when repo_root is None."""
    capability = CodeReviewsSystemCapability()
    result = capability.uninstall(repo_root=None)
    assert result.success is False
    assert "requires repo_root" in result.message


def test_uninstall_succeeds_when_not_installed(tmp_path: Path) -> None:
    """Test uninstall succeeds gracefully when not installed."""
    capability = CodeReviewsSystemCapability()
    result = capability.uninstall(repo_root=tmp_path)
    assert result.success is True
    assert "not installed" in result.message


def test_uninstall_removes_workflow(tmp_path: Path) -> None:
    """Test uninstall removes the workflow file."""
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    workflow_file = workflow_dir / "code-reviews.yml"
    workflow_file.write_text("name: code-reviews", encoding="utf-8")

    capability = CodeReviewsSystemCapability()
    result = capability.uninstall(repo_root=tmp_path)

    assert result.success is True
    assert "code-reviews.yml" in result.message
    assert not workflow_file.exists()


def test_uninstall_removes_actions(tmp_path: Path) -> None:
    """Test uninstall removes the setup actions."""
    # Create workflow
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "code-reviews.yml").write_text("name: code-reviews", encoding="utf-8")

    # Create actions
    actions_dir = tmp_path / ".github" / "actions"
    action1_dir = actions_dir / "setup-claude-code"
    action1_dir.mkdir(parents=True)
    (action1_dir / "action.yml").write_text("name: setup-claude-code", encoding="utf-8")

    action2_dir = actions_dir / "setup-claude-erk"
    action2_dir.mkdir(parents=True)
    (action2_dir / "action.yml").write_text("name: setup-claude-erk", encoding="utf-8")

    capability = CodeReviewsSystemCapability()
    result = capability.uninstall(repo_root=tmp_path)

    assert result.success is True
    assert not action1_dir.exists()
    assert not action2_dir.exists()


def test_installation_check_description() -> None:
    """Test installation_check_description is informative."""
    capability = CodeReviewsSystemCapability()
    assert "code-reviews.yml" in capability.installation_check_description


def test_artifacts_lists_all_items() -> None:
    """Test artifacts includes workflow, actions, and reviews directory."""
    capability = CodeReviewsSystemCapability()
    artifacts = capability.artifacts

    paths = [a.path for a in artifacts]
    assert ".github/workflows/code-reviews.yml" in paths
    assert ".github/actions/setup-claude-code/" in paths
    assert ".github/actions/setup-claude-erk/" in paths
    assert ".claude/reviews/" in paths


def test_managed_artifacts_lists_workflow_and_actions() -> None:
    """Test managed_artifacts declares workflow and actions."""
    capability = CodeReviewsSystemCapability()
    managed = capability.managed_artifacts

    names = [(m.name, m.artifact_type) for m in managed]
    assert ("code-reviews", "workflow") in names
    assert ("setup-claude-code", "action") in names
    assert ("setup-claude-erk", "action") in names
