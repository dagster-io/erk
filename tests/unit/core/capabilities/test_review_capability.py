"""Tests for ReviewCapability base class and review capabilities.

Tests the review definition installation and preflight checking behavior.
"""

from pathlib import Path

from erk.capabilities.reviews.dignified_code_simplifier import (
    DignifiedCodeSimplifierReviewDefCapability,
)
from erk.capabilities.reviews.dignified_python import DignifiedPythonReviewDefCapability
from erk.capabilities.reviews.tripwires import TripwiresReviewDefCapability


def test_tripwires_review_name() -> None:
    """Test TripwiresReviewDefCapability properties."""
    capability = TripwiresReviewDefCapability()
    assert capability.review_name == "tripwires"
    assert capability.name == "review-tripwires"
    assert "tripwires" in capability.description.lower()


def test_dignified_python_review_name() -> None:
    """Test DignifiedPythonReviewDefCapability properties."""
    capability = DignifiedPythonReviewDefCapability()
    assert capability.review_name == "dignified-python"
    assert capability.name == "review-dignified-python"
    assert "python" in capability.description.lower()


def test_dignified_code_simplifier_review_name() -> None:
    """Test DignifiedCodeSimplifierReviewDefCapability properties."""
    capability = DignifiedCodeSimplifierReviewDefCapability()
    assert capability.review_name == "dignified-code-simplifier"
    assert capability.name == "review-dignified-code-simplifier"
    assert "simplif" in capability.description.lower()


def test_is_installed_returns_false_when_no_repo_root() -> None:
    """Test is_installed returns False when repo_root is None."""
    capability = TripwiresReviewDefCapability()
    assert capability.is_installed(repo_root=None) is False


def test_is_installed_returns_false_when_review_missing(tmp_path: Path) -> None:
    """Test is_installed returns False when review file doesn't exist."""
    capability = TripwiresReviewDefCapability()
    assert capability.is_installed(repo_root=tmp_path) is False


def test_is_installed_returns_true_when_review_exists(tmp_path: Path) -> None:
    """Test is_installed returns True when review file exists."""
    reviews_dir = tmp_path / ".claude" / "reviews"
    reviews_dir.mkdir(parents=True)
    (reviews_dir / "tripwires.md").write_text("# Tripwires", encoding="utf-8")

    capability = TripwiresReviewDefCapability()
    assert capability.is_installed(repo_root=tmp_path) is True


def test_preflight_fails_without_repo_root() -> None:
    """Test preflight fails when repo_root is None."""
    capability = TripwiresReviewDefCapability()
    result = capability.preflight(repo_root=None)
    assert result.success is False
    assert "requires repo_root" in result.message


def test_preflight_fails_without_code_reviews_system(tmp_path: Path) -> None:
    """Test preflight fails when code-reviews-system is not installed."""
    capability = TripwiresReviewDefCapability()
    result = capability.preflight(repo_root=tmp_path)
    assert result.success is False
    assert "code-reviews-system" in result.message


def test_preflight_succeeds_with_code_reviews_system(tmp_path: Path) -> None:
    """Test preflight succeeds when code-reviews-system workflow exists."""
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "code-reviews.yml").write_text("name: code-reviews", encoding="utf-8")

    capability = TripwiresReviewDefCapability()
    result = capability.preflight(repo_root=tmp_path)
    assert result.success is True


def test_install_fails_without_repo_root() -> None:
    """Test install fails when repo_root is None."""
    capability = TripwiresReviewDefCapability()
    result = capability.install(repo_root=None)
    assert result.success is False
    assert "requires repo_root" in result.message


def test_uninstall_fails_without_repo_root() -> None:
    """Test uninstall fails when repo_root is None."""
    capability = TripwiresReviewDefCapability()
    result = capability.uninstall(repo_root=None)
    assert result.success is False
    assert "requires repo_root" in result.message


def test_uninstall_succeeds_when_not_installed(tmp_path: Path) -> None:
    """Test uninstall succeeds gracefully when review doesn't exist."""
    capability = TripwiresReviewDefCapability()
    result = capability.uninstall(repo_root=tmp_path)
    assert result.success is True
    assert "does not exist" in result.message


def test_uninstall_removes_review_file(tmp_path: Path) -> None:
    """Test uninstall removes the review file."""
    reviews_dir = tmp_path / ".claude" / "reviews"
    reviews_dir.mkdir(parents=True)
    review_file = reviews_dir / "tripwires.md"
    review_file.write_text("# Tripwires", encoding="utf-8")

    capability = TripwiresReviewDefCapability()
    result = capability.uninstall(repo_root=tmp_path)

    assert result.success is True
    assert "Removed" in result.message
    assert not review_file.exists()


def test_installation_check_description() -> None:
    """Test installation_check_description is informative."""
    capability = TripwiresReviewDefCapability()
    assert ".claude/reviews/tripwires.md" in capability.installation_check_description


def test_artifacts_lists_review_file() -> None:
    """Test artifacts includes the review file."""
    capability = TripwiresReviewDefCapability()
    artifacts = capability.artifacts
    assert len(artifacts) == 1
    assert artifacts[0].path == ".claude/reviews/tripwires.md"
    assert artifacts[0].artifact_type == "file"


def test_managed_artifacts_lists_review() -> None:
    """Test managed_artifacts declares the review artifact."""
    capability = TripwiresReviewDefCapability()
    managed = capability.managed_artifacts
    assert len(managed) == 1
    assert managed[0].name == "tripwires"
    assert managed[0].artifact_type == "review"


def test_scope_is_project() -> None:
    """Test review capabilities are project-scoped."""
    capability = TripwiresReviewDefCapability()
    assert capability.scope == "project"
