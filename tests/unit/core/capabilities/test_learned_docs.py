"""Tests for LearnedDocsCapability.

Tests install, uninstall, is_installed, and artifact declarations.
"""

from pathlib import Path

from erk.capabilities.learned_docs import LearnedDocsCapability

# =============================================================================
# Tests for LearnedDocsCapability
# =============================================================================


def test_learned_docs_capability_name() -> None:
    """Test that LearnedDocsCapability has correct name."""
    cap = LearnedDocsCapability()
    assert cap.name == "learned-docs"


def test_learned_docs_capability_description() -> None:
    """Test that LearnedDocsCapability has a description."""
    cap = LearnedDocsCapability()
    assert cap.description == "Autolearning documentation system"


def test_learned_docs_is_installed_false_when_missing(tmp_path: Path) -> None:
    """Test that is_installed returns False when docs/learned/ doesn't exist."""
    cap = LearnedDocsCapability()
    assert cap.is_installed(tmp_path, backend="claude") is False


def test_learned_docs_is_installed_true_when_all_three_dirs_exist(tmp_path: Path) -> None:
    """Test that is_installed returns True when all three directories exist."""
    (tmp_path / "docs" / "learned").mkdir(parents=True)
    (tmp_path / ".claude" / "skills" / "learned-docs").mkdir(parents=True)
    (tmp_path / ".claude" / "agents" / "learn").mkdir(parents=True)
    cap = LearnedDocsCapability()
    assert cap.is_installed(tmp_path, backend="claude") is True


def test_learned_docs_is_installed_false_when_only_docs_learned(tmp_path: Path) -> None:
    """Test that is_installed returns False when only docs/learned/ exists."""
    (tmp_path / "docs" / "learned").mkdir(parents=True)
    cap = LearnedDocsCapability()
    assert cap.is_installed(tmp_path, backend="claude") is False


def test_learned_docs_is_installed_false_when_only_skill(tmp_path: Path) -> None:
    """Test that is_installed returns False when only the skill directory exists."""
    (tmp_path / ".claude" / "skills" / "learned-docs").mkdir(parents=True)
    cap = LearnedDocsCapability()
    assert cap.is_installed(tmp_path, backend="claude") is False


def test_learned_docs_is_installed_false_when_only_agents(tmp_path: Path) -> None:
    """Test that is_installed returns False when only the agents directory exists."""
    (tmp_path / ".claude" / "agents" / "learn").mkdir(parents=True)
    cap = LearnedDocsCapability()
    assert cap.is_installed(tmp_path, backend="claude") is False


def test_learned_docs_is_installed_false_when_two_of_three(tmp_path: Path) -> None:
    """Test that is_installed returns False when only two of three directories exist."""
    (tmp_path / "docs" / "learned").mkdir(parents=True)
    (tmp_path / ".claude" / "skills" / "learned-docs").mkdir(parents=True)
    cap = LearnedDocsCapability()
    assert cap.is_installed(tmp_path, backend="claude") is False


def test_learned_docs_install_creates_directory(tmp_path: Path) -> None:
    """Test that install creates docs/learned/ directory."""
    cap = LearnedDocsCapability()
    result = cap.install(tmp_path, backend="claude")

    assert result.success is True
    assert (tmp_path / "docs" / "learned").is_dir()


def test_learned_docs_install_creates_readme(tmp_path: Path) -> None:
    """Test that install creates README.md in docs/learned/."""
    cap = LearnedDocsCapability()
    cap.install(tmp_path, backend="claude")

    readme_path = tmp_path / "docs" / "learned" / "README.md"
    assert readme_path.exists()
    content = readme_path.read_text(encoding="utf-8")
    assert "Learned Documentation" in content
    assert "read_when" in content


def test_learned_docs_install_creates_index(tmp_path: Path) -> None:
    """Test that install creates index.md in docs/learned/."""
    cap = LearnedDocsCapability()
    cap.install(tmp_path, backend="claude")

    index_path = tmp_path / "docs" / "learned" / "index.md"
    assert index_path.exists()
    content = index_path.read_text(encoding="utf-8")
    assert "AUTO-GENERATED FILE" in content
    assert "erk docs sync" in content
    assert "# Agent Documentation" in content


def test_learned_docs_install_creates_docs_learned_directory(tmp_path: Path) -> None:
    """Test that install creates docs/learned/ directory.

    Note: Category tripwires (e.g., architecture/tripwires.md) are auto-generated
    by 'erk docs sync' from document frontmatter, not during capability install.
    """
    cap = LearnedDocsCapability()
    cap.install(tmp_path, backend="claude")

    docs_dir = tmp_path / "docs" / "learned"
    assert docs_dir.exists()
    assert (docs_dir / "README.md").exists()
    assert (docs_dir / "index.md").exists()


def test_learned_docs_install_idempotent(tmp_path: Path) -> None:
    """Test that installing twice is idempotent and returns appropriate message."""
    cap = LearnedDocsCapability()

    # First install
    result1 = cap.install(tmp_path, backend="claude")
    assert result1.success is True
    assert "Created" in result1.message

    # Second install
    result2 = cap.install(tmp_path, backend="claude")
    assert result2.success is True
    assert "already exists" in result2.message


def test_learned_docs_install_when_docs_exists_but_not_learned(tmp_path: Path) -> None:
    """Test that install works when docs/ exists but docs/learned/ doesn't."""
    (tmp_path / "docs").mkdir()
    cap = LearnedDocsCapability()

    result = cap.install(tmp_path, backend="claude")

    assert result.success is True
    assert (tmp_path / "docs" / "learned").is_dir()


def test_learned_docs_installation_check_description() -> None:
    """Test that LearnedDocsCapability has an installation check description."""
    cap = LearnedDocsCapability()
    desc = cap.installation_check_description
    assert "docs/learned/" in desc
    assert ".claude/skills/learned-docs/" in desc
    assert ".claude/agents/learn/" in desc


def test_learned_docs_artifacts() -> None:
    """Test that LearnedDocsCapability lists its artifacts."""
    cap = LearnedDocsCapability()
    artifacts = cap.artifacts

    # Category tripwires (e.g., architecture/tripwires.md) are auto-generated
    # by 'erk docs sync', not listed as static artifacts
    assert len(artifacts) == 7
    paths = [a.path for a in artifacts]
    assert "docs/learned/" in paths
    assert "docs/learned/README.md" in paths
    assert "docs/learned/index.md" in paths
    assert ".claude/skills/learned-docs/" in paths
    assert ".claude/skills/learned-docs/SKILL.md" in paths
    assert ".claude/agents/learn/" in paths
    assert ".claude/commands/erk/learn.md" in paths

    # Verify artifact types
    for artifact in artifacts:
        if artifact.path in (
            "docs/learned/",
            ".claude/skills/learned-docs/",
            ".claude/agents/learn/",
        ):
            assert artifact.artifact_type == "directory"
        else:
            assert artifact.artifact_type == "file"


# =============================================================================
# Tests for LearnedDocsCapability Uninstall
# =============================================================================


def test_learned_docs_uninstall_preserves_docs_learned(tmp_path: Path) -> None:
    """Test that uninstall preserves docs/learned/ directory."""
    cap = LearnedDocsCapability()
    cap.install(tmp_path, backend="claude")

    result = cap.uninstall(tmp_path, backend="claude")

    assert result.success is True
    assert "preserved" in result.message
    assert (tmp_path / "docs" / "learned").exists()


def test_learned_docs_uninstall_removes_skill_and_agents(tmp_path: Path) -> None:
    """Test that uninstall removes skill, agents, and command but not docs."""
    cap = LearnedDocsCapability()
    cap.install(tmp_path, backend="claude")

    result = cap.uninstall(tmp_path, backend="claude")

    assert result.success is True
    assert not (tmp_path / ".claude" / "skills" / "learned-docs").exists()
    assert not (tmp_path / ".claude" / "agents" / "learn").exists()
    assert not (tmp_path / ".claude" / "commands" / "erk" / "learn.md").exists()
    assert (tmp_path / "docs" / "learned").exists()


def test_learned_docs_uninstall_when_not_installed(tmp_path: Path) -> None:
    """Test that uninstall succeeds when nothing is installed."""
    cap = LearnedDocsCapability()
    result = cap.uninstall(tmp_path, backend="claude")

    assert result.success is True
    assert "not installed" in result.message
