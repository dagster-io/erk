"""Integration tests for RealSkillsCli gateway.

Tests the real skills CLI (npx skills) against the local erk repository.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

from erk_shared.gateway.skills_cli.real import RealSkillsCli

# Skip all tests if npx is not available
pytestmark = pytest.mark.integration


@pytest.fixture
def skills_cli() -> RealSkillsCli:
    return RealSkillsCli()


@pytest.fixture
def erk_repo_root() -> Path:
    """Return the root of the erk repository for use as a skill source."""
    # Navigate from this test file to the repo root
    return Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def temp_project(tmp_path: Path) -> Path:
    """Create a temporary git-initialized project directory."""
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    return tmp_path


def test_real_skills_cli_is_available(skills_cli: RealSkillsCli) -> None:
    """Test that npx is available on the system."""
    result = skills_cli.is_available()
    # npx should be available in CI and dev environments
    assert result is True


@pytest.mark.skipif(shutil.which("npx") is None, reason="npx not available")
def test_real_skills_cli_list_skills(
    skills_cli: RealSkillsCli,
    erk_repo_root: Path,
) -> None:
    """Test listing skills from the local erk repository."""
    result = skills_cli.list_skills(source=str(erk_repo_root))
    assert result.success is True
    assert result.exit_code == 0


@pytest.mark.skipif(shutil.which("npx") is None, reason="npx not available")
def test_real_skills_cli_add_skill(
    skills_cli: RealSkillsCli,
    erk_repo_root: Path,
    temp_project: Path,
) -> None:
    """Test installing a skill to a temporary project using cwd parameter."""
    result = skills_cli.add_skills(
        source=str(erk_repo_root),
        skill_names=["dignified-python"],
        agents=["claude-code"],
        cwd=temp_project,
    )
    assert result.success is True
    assert result.exit_code == 0

    # Verify the skill was installed
    agents_dir = temp_project / ".agents" / "skills" / "dignified-python"
    assert agents_dir.exists()
    assert (agents_dir / "SKILL.md").exists()


@pytest.mark.skipif(shutil.which("npx") is None, reason="npx not available")
def test_real_skills_cli_remove_skill(
    skills_cli: RealSkillsCli,
    erk_repo_root: Path,
    temp_project: Path,
) -> None:
    """Test removing a skill after installing it."""
    # Install first
    skills_cli.add_skills(
        source=str(erk_repo_root),
        skill_names=["dignified-python"],
        agents=["claude-code"],
        cwd=temp_project,
    )

    # Then remove
    result = skills_cli.remove_skills(
        skill_names=["dignified-python"],
        agents=["claude-code"],
        cwd=temp_project,
    )
    assert result.success is True
    assert result.exit_code == 0
