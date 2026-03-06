"""Tests for agent capabilities.

Tests DevrunAgentCapability.
"""

from pathlib import Path

from erk.capabilities.agents.devrun import DevrunAgentCapability
from erk.core.capabilities.registry import get_capability

# =============================================================================
# Tests for Agent Capabilities
# =============================================================================


def test_devrun_agent_capability_properties() -> None:
    """Test DevrunAgentCapability has correct properties."""
    cap = DevrunAgentCapability()
    assert cap.name == "devrun-agent"
    assert "pytest" in cap.description or "execution" in cap.description.lower()
    assert "devrun" in cap.installation_check_description


def test_devrun_agent_artifacts() -> None:
    """Test DevrunAgentCapability lists correct artifacts."""
    cap = DevrunAgentCapability()
    artifacts = cap.artifacts

    assert len(artifacts) == 1
    assert artifacts[0].path == ".claude/agents/devrun.md"
    assert artifacts[0].artifact_type == "file"


def test_devrun_agent_is_installed(tmp_path: Path) -> None:
    """Test agent is_installed checks for agent file."""
    cap = DevrunAgentCapability()

    # Not installed when agent file missing
    assert cap.is_installed(tmp_path, backend="claude") is False

    # Installed when agent file exists
    (tmp_path / ".claude" / "agents").mkdir(parents=True)
    (tmp_path / ".claude" / "agents" / "devrun.md").write_text("", encoding="utf-8")
    assert cap.is_installed(tmp_path, backend="claude") is True


def test_agent_capability_registered() -> None:
    """Test that agent capability is registered."""
    cap = get_capability("devrun-agent")
    assert cap is not None
    assert cap.name == "devrun-agent"
