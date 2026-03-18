"""Tests for skill-based capabilities.

Tests bundled skill capabilities and codex portable skills.
"""

from pathlib import Path

from erk.capabilities.skills.bundled import bundled_skills
from erk.core.capabilities.codex_portable import codex_portable_skills
from erk.core.capabilities.registry import get_capability

# =============================================================================
# Tests for Skill Capabilities
# =============================================================================


def test_fake_driven_testing_capability_properties() -> None:
    """Test fake-driven-testing capability has correct properties via registry."""
    cap = get_capability("fake-driven-testing")
    assert cap is not None
    assert cap.name == "fake-driven-testing"
    assert "test" in cap.description.lower()
    assert ".claude/skills/fake-driven-testing" in cap.installation_check_description


def test_skill_capability_is_installed_false_when_missing(tmp_path: Path) -> None:
    """Test skill capability is_installed returns False when skill directory missing."""
    cap = get_capability("fake-driven-testing")
    assert cap is not None
    assert cap.is_installed(tmp_path, backend="claude") is False


def test_skill_capability_is_installed_true_when_exists(tmp_path: Path) -> None:
    """Test skill capability is_installed returns True when skill directory exists."""
    (tmp_path / ".claude" / "skills" / "fake-driven-testing").mkdir(parents=True)
    cap = get_capability("fake-driven-testing")
    assert cap is not None
    assert cap.is_installed(tmp_path, backend="claude") is True


def test_skill_capability_artifacts() -> None:
    """Test that skill capabilities list correct artifacts."""
    cap = get_capability("fake-driven-testing")
    assert cap is not None
    artifacts = cap.artifacts

    assert len(artifacts) == 1
    assert artifacts[0].path == ".claude/skills/fake-driven-testing/"
    assert artifacts[0].artifact_type == "directory"


def test_all_skill_capabilities_registered() -> None:
    """Test that all bundled skill capabilities are registered."""
    for skill_name in bundled_skills():
        cap = get_capability(skill_name)
        assert cap is not None, f"Skill '{skill_name}' not registered"
        assert cap.name == skill_name


def test_all_codex_portable_skills_have_capability() -> None:
    """Drift prevention: every codex_portable_skills() entry must have a registered capability."""
    for skill_name in codex_portable_skills():
        cap = get_capability(skill_name)
        assert cap is not None, (
            f"Skill '{skill_name}' is in codex_portable_skills() but has no registered capability. "
            f"Add it to bundled_skills() in bundled.py or create a dedicated capability class."
        )
