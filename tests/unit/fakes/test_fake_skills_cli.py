"""Tests for FakeSkillsCli test infrastructure.

Verifies that FakeSkillsCli correctly records calls and returns
configured results for test assertions.
"""

from erk_shared.gateway.skills_cli.fake import FakeSkillsCli
from erk_shared.gateway.skills_cli.types import SkillsCliResult


def test_fake_skills_cli_available() -> None:
    """Test is_available returns configured value."""
    cli = FakeSkillsCli(available=True)
    assert cli.is_available() is True

    cli_unavailable = FakeSkillsCli(available=False)
    assert cli_unavailable.is_available() is False


def test_fake_skills_cli_list_skills_default() -> None:
    """Test list_skills returns default success result."""
    cli = FakeSkillsCli(available=True)
    result = cli.list_skills(source="/some/path")
    assert result.success is True
    assert result.exit_code == 0


def test_fake_skills_cli_list_skills_custom_result() -> None:
    """Test list_skills returns configured custom result."""
    custom = SkillsCliResult(success=True, exit_code=0, message="Found 5 skills")
    cli = FakeSkillsCli(available=True, list_result=custom)
    result = cli.list_skills(source="/some/path")
    assert result.message == "Found 5 skills"


def test_fake_skills_cli_add_records_calls() -> None:
    """Test add_skills records calls for assertion."""
    cli = FakeSkillsCli(available=True)

    cli.add_skills(
        source="/path/to/erk",
        skill_names=["dignified-python", "fake-driven-testing"],
        agents=["claude-code"],
    )

    assert len(cli.add_calls) == 1
    call = cli.add_calls[0]
    assert call.source == "/path/to/erk"
    assert call.skill_names == ["dignified-python", "fake-driven-testing"]
    assert call.agents == ["claude-code"]


def test_fake_skills_cli_remove_records_calls() -> None:
    """Test remove_skills records calls for assertion."""
    cli = FakeSkillsCli(available=True)

    cli.remove_skills(
        skill_names=["dignified-python"],
        agents=["claude-code"],
    )

    assert len(cli.remove_calls) == 1
    call = cli.remove_calls[0]
    assert call.skill_names == ["dignified-python"]
    assert call.agents == ["claude-code"]


def test_fake_skills_cli_add_returns_configured_result() -> None:
    """Test add_skills returns configured result."""
    failure = SkillsCliResult(success=False, exit_code=1, message="install failed")
    cli = FakeSkillsCli(available=True, add_result=failure)

    result = cli.add_skills(
        source="/path",
        skill_names=["test"],
        agents=["claude-code"],
    )

    assert result.success is False
    assert result.exit_code == 1


def test_fake_skills_cli_multiple_add_calls() -> None:
    """Test multiple add calls are tracked independently."""
    cli = FakeSkillsCli(available=True)

    cli.add_skills(source="/path1", skill_names=["skill-a"], agents=["claude-code"])
    cli.add_skills(source="/path2", skill_names=["skill-b"], agents=["codex"])

    assert len(cli.add_calls) == 2
    assert cli.add_calls[0].source == "/path1"
    assert cli.add_calls[1].source == "/path2"
