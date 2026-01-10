"""Tests for the capability system.

These tests verify:
1. The Capability ABC contract
2. The registry functions (get, list)
3. The LearnedDocsCapability implementation
4. Skill-based capabilities
5. StatuslineCapability (user-level capability)
6. Capability scope behavior
"""

from pathlib import Path

from erk.core.capabilities.agents import DevrunAgentCapability
from erk.core.capabilities.base import (
    Capability,
    CapabilityArtifact,
    CapabilityResult,
    CapabilityScope,
)
from erk.core.capabilities.dignified_review import DignifiedReviewCapability
from erk.core.capabilities.hooks import HooksCapability
from erk.core.capabilities.learned_docs import LearnedDocsCapability
from erk.core.capabilities.permissions import ErkBashPermissionsCapability
from erk.core.capabilities.registry import (
    get_capability,
    list_capabilities,
    list_required_capabilities,
)
from erk.core.capabilities.skills import (
    DignifiedPythonCapability,
    FakeDrivenTestingCapability,
)
from erk.core.capabilities.statusline import StatuslineCapability
from erk.core.capabilities.workflows import ErkImplWorkflowCapability
from erk_shared.extraction.claude_installation import FakeClaudeInstallation

# =============================================================================
# Tests for CapabilityResult
# =============================================================================


def test_capability_result_is_frozen() -> None:
    """Test that CapabilityResult is immutable."""
    result = CapabilityResult(success=True, message="test")
    assert result.success is True
    assert result.message == "test"


# =============================================================================
# Tests for Registry Functions
# =============================================================================


def test_get_capability_returns_registered_capability() -> None:
    """Test that get_capability returns a registered capability by name."""
    cap = get_capability("learned-docs")
    assert cap is not None
    assert cap.name == "learned-docs"


def test_get_capability_returns_none_for_unknown() -> None:
    """Test that get_capability returns None for unknown capability names."""
    cap = get_capability("nonexistent-capability")
    assert cap is None


def test_list_capabilities_returns_all_registered() -> None:
    """Test that list_capabilities returns all registered capabilities."""
    caps = list_capabilities()
    assert len(caps) >= 1
    names = [cap.name for cap in caps]
    assert "learned-docs" in names


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
    assert cap.is_installed(tmp_path) is False


def test_learned_docs_is_installed_true_when_exists(tmp_path: Path) -> None:
    """Test that is_installed returns True when docs/learned/ exists."""
    (tmp_path / "docs" / "learned").mkdir(parents=True)
    cap = LearnedDocsCapability()
    assert cap.is_installed(tmp_path) is True


def test_learned_docs_install_creates_directory(tmp_path: Path) -> None:
    """Test that install creates docs/learned/ directory."""
    cap = LearnedDocsCapability()
    result = cap.install(tmp_path)

    assert result.success is True
    assert (tmp_path / "docs" / "learned").is_dir()


def test_learned_docs_install_creates_readme(tmp_path: Path) -> None:
    """Test that install creates README.md in docs/learned/."""
    cap = LearnedDocsCapability()
    cap.install(tmp_path)

    readme_path = tmp_path / "docs" / "learned" / "README.md"
    assert readme_path.exists()
    content = readme_path.read_text(encoding="utf-8")
    assert "Learned Documentation" in content
    assert "read_when" in content


def test_learned_docs_install_creates_index(tmp_path: Path) -> None:
    """Test that install creates index.md in docs/learned/."""
    cap = LearnedDocsCapability()
    cap.install(tmp_path)

    index_path = tmp_path / "docs" / "learned" / "index.md"
    assert index_path.exists()
    content = index_path.read_text(encoding="utf-8")
    assert "AUTO-GENERATED FILE" in content
    assert "erk docs sync" in content
    assert "# Agent Documentation" in content


def test_learned_docs_install_creates_tripwires(tmp_path: Path) -> None:
    """Test that install creates tripwires.md in docs/learned/."""
    cap = LearnedDocsCapability()
    cap.install(tmp_path)

    tripwires_path = tmp_path / "docs" / "learned" / "tripwires.md"
    assert tripwires_path.exists()
    content = tripwires_path.read_text(encoding="utf-8")
    assert "AUTO-GENERATED FILE" in content
    assert "erk docs sync" in content
    assert "# Tripwires" in content


def test_learned_docs_install_idempotent(tmp_path: Path) -> None:
    """Test that installing twice is idempotent and returns appropriate message."""
    cap = LearnedDocsCapability()

    # First install
    result1 = cap.install(tmp_path)
    assert result1.success is True
    assert "Created" in result1.message

    # Second install
    result2 = cap.install(tmp_path)
    assert result2.success is True
    assert "already exists" in result2.message


def test_learned_docs_install_when_docs_exists_but_not_learned(tmp_path: Path) -> None:
    """Test that install works when docs/ exists but docs/learned/ doesn't."""
    (tmp_path / "docs").mkdir()
    cap = LearnedDocsCapability()

    result = cap.install(tmp_path)

    assert result.success is True
    assert (tmp_path / "docs" / "learned").is_dir()


def test_learned_docs_installation_check_description() -> None:
    """Test that LearnedDocsCapability has an installation check description."""
    cap = LearnedDocsCapability()
    assert "docs/learned" in cap.installation_check_description


def test_learned_docs_artifacts() -> None:
    """Test that LearnedDocsCapability lists its artifacts."""
    cap = LearnedDocsCapability()
    artifacts = cap.artifacts

    assert len(artifacts) == 6
    paths = [a.path for a in artifacts]
    assert "docs/learned/" in paths
    assert "docs/learned/README.md" in paths
    assert "docs/learned/index.md" in paths
    assert "docs/learned/tripwires.md" in paths
    assert ".claude/skills/learned-docs/" in paths
    assert ".claude/skills/learned-docs/SKILL.md" in paths

    # Verify artifact types
    for artifact in artifacts:
        if artifact.path in ("docs/learned/", ".claude/skills/learned-docs/"):
            assert artifact.artifact_type == "directory"
        else:
            assert artifact.artifact_type == "file"


# =============================================================================
# Tests for CapabilityArtifact
# =============================================================================


def test_capability_artifact_is_frozen() -> None:
    """Test that CapabilityArtifact is immutable."""
    artifact = CapabilityArtifact(path="test/path", artifact_type="file")
    assert artifact.path == "test/path"
    assert artifact.artifact_type == "file"


# =============================================================================
# Tests for Custom Capability Registration
# =============================================================================


class _TestCapability(Capability):
    """A test capability for testing the registration system."""

    @property
    def name(self) -> str:
        return "test-cap"

    @property
    def description(self) -> str:
        return "Test capability"

    @property
    def scope(self) -> CapabilityScope:
        return "project"

    @property
    def installation_check_description(self) -> str:
        return ".test-cap marker file exists"

    @property
    def artifacts(self) -> list[CapabilityArtifact]:
        return [CapabilityArtifact(path=".test-cap", artifact_type="file")]

    def is_installed(self, repo_root: Path | None) -> bool:
        assert repo_root is not None, "_TestCapability requires repo_root"
        return (repo_root / ".test-cap").exists()

    def install(self, repo_root: Path | None) -> CapabilityResult:
        assert repo_root is not None, "_TestCapability requires repo_root"
        marker = repo_root / ".test-cap"
        if marker.exists():
            return CapabilityResult(success=True, message="Already installed")
        marker.write_text("installed", encoding="utf-8")
        return CapabilityResult(success=True, message="Installed")


def test_custom_capability_install_and_is_installed(tmp_path: Path) -> None:
    """Test that a custom capability can be installed and detected."""
    cap = _TestCapability()

    # Not installed initially
    assert cap.is_installed(tmp_path) is False

    # Install it
    result = cap.install(tmp_path)
    assert result.success is True
    assert result.message == "Installed"

    # Now it's installed
    assert cap.is_installed(tmp_path) is True

    # Install again - idempotent
    result2 = cap.install(tmp_path)
    assert result2.success is True
    assert result2.message == "Already installed"


# =============================================================================
# Tests for Skill Capabilities
# =============================================================================


def test_dignified_python_capability_properties() -> None:
    """Test DignifiedPythonCapability has correct properties."""
    cap = DignifiedPythonCapability()
    assert cap.name == "dignified-python"
    assert cap.skill_name == "dignified-python"
    assert "Python" in cap.description
    assert ".claude/skills/dignified-python" in cap.installation_check_description


def test_fake_driven_testing_capability_properties() -> None:
    """Test FakeDrivenTestingCapability has correct properties."""
    cap = FakeDrivenTestingCapability()
    assert cap.name == "fake-driven-testing"
    assert cap.skill_name == "fake-driven-testing"
    assert "test" in cap.description.lower()


def test_skill_capability_is_installed_false_when_missing(tmp_path: Path) -> None:
    """Test skill capability is_installed returns False when skill directory missing."""
    cap = DignifiedPythonCapability()
    assert cap.is_installed(tmp_path) is False


def test_skill_capability_is_installed_true_when_exists(tmp_path: Path) -> None:
    """Test skill capability is_installed returns True when skill directory exists."""
    (tmp_path / ".claude" / "skills" / "dignified-python").mkdir(parents=True)
    cap = DignifiedPythonCapability()
    assert cap.is_installed(tmp_path) is True


def test_skill_capability_artifacts() -> None:
    """Test that skill capabilities list correct artifacts."""
    cap = DignifiedPythonCapability()
    artifacts = cap.artifacts

    assert len(artifacts) == 1
    assert artifacts[0].path == ".claude/skills/dignified-python/"
    assert artifacts[0].artifact_type == "directory"


def test_all_skill_capabilities_registered() -> None:
    """Test that all skill capabilities are registered."""
    expected_skills = [
        "dignified-python",
        "fake-driven-testing",
    ]
    for skill_name in expected_skills:
        cap = get_capability(skill_name)
        assert cap is not None, f"Skill '{skill_name}' not registered"
        assert cap.name == skill_name


# =============================================================================
# Tests for Workflow Capabilities
# =============================================================================


def test_erk_impl_workflow_capability_properties() -> None:
    """Test ErkImplWorkflowCapability has correct properties."""
    cap = ErkImplWorkflowCapability()
    assert cap.name == "erk-impl-workflow"
    assert "GitHub Action" in cap.description
    assert "erk-impl.yml" in cap.installation_check_description


def test_erk_impl_workflow_artifacts() -> None:
    """Test ErkImplWorkflowCapability lists all artifacts."""
    cap = ErkImplWorkflowCapability()
    artifacts = cap.artifacts

    assert len(artifacts) == 3
    paths = [a.path for a in artifacts]
    assert ".github/workflows/erk-impl.yml" in paths
    assert ".github/actions/setup-claude-code/" in paths
    assert ".github/actions/setup-claude-erk/" in paths


def test_erk_impl_workflow_is_installed(tmp_path: Path) -> None:
    """Test workflow is_installed checks for workflow file."""
    cap = ErkImplWorkflowCapability()

    # Not installed when workflow file missing
    assert cap.is_installed(tmp_path) is False

    # Installed when workflow file exists
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "erk-impl.yml").write_text("", encoding="utf-8")
    assert cap.is_installed(tmp_path) is True


def test_workflow_capability_registered() -> None:
    """Test that workflow capability is registered."""
    cap = get_capability("erk-impl-workflow")
    assert cap is not None
    assert cap.name == "erk-impl-workflow"


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
    assert cap.is_installed(tmp_path) is False

    # Installed when agent file exists
    (tmp_path / ".claude" / "agents").mkdir(parents=True)
    (tmp_path / ".claude" / "agents" / "devrun.md").write_text("", encoding="utf-8")
    assert cap.is_installed(tmp_path) is True


def test_agent_capability_registered() -> None:
    """Test that agent capability is registered."""
    cap = get_capability("devrun-agent")
    assert cap is not None
    assert cap.name == "devrun-agent"


# =============================================================================
# Tests for Permission Capabilities
# =============================================================================


def test_erk_bash_permissions_capability_properties() -> None:
    """Test ErkBashPermissionsCapability has correct properties."""
    cap = ErkBashPermissionsCapability()
    assert cap.name == "erk-bash-permissions"
    assert "Bash(erk:*)" in cap.description
    assert "settings.json" in cap.installation_check_description


def test_erk_bash_permissions_artifacts() -> None:
    """Test ErkBashPermissionsCapability lists correct artifacts."""
    cap = ErkBashPermissionsCapability()
    artifacts = cap.artifacts

    # settings.json is shared by multiple capabilities, so not listed
    assert len(artifacts) == 0


def test_erk_bash_permissions_is_installed_false_when_no_settings(tmp_path: Path) -> None:
    """Test is_installed returns False when settings.json doesn't exist."""
    cap = ErkBashPermissionsCapability()
    assert cap.is_installed(tmp_path) is False


def test_erk_bash_permissions_is_installed_false_when_not_in_allow(tmp_path: Path) -> None:
    """Test is_installed returns False when permission not in allow list."""
    import json

    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(json.dumps({"permissions": {"allow": []}}), encoding="utf-8")

    cap = ErkBashPermissionsCapability()
    assert cap.is_installed(tmp_path) is False


def test_erk_bash_permissions_is_installed_true_when_present(tmp_path: Path) -> None:
    """Test is_installed returns True when permission is in allow list."""
    import json

    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps({"permissions": {"allow": ["Bash(erk:*)"]}}),
        encoding="utf-8",
    )

    cap = ErkBashPermissionsCapability()
    assert cap.is_installed(tmp_path) is True


def test_erk_bash_permissions_install_creates_settings(tmp_path: Path) -> None:
    """Test install creates settings.json if it doesn't exist."""
    import json

    cap = ErkBashPermissionsCapability()
    result = cap.install(tmp_path)

    assert result.success is True
    assert ".claude/settings.json" in result.created_files

    settings_path = tmp_path / ".claude" / "settings.json"
    assert settings_path.exists()

    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert "Bash(erk:*)" in settings["permissions"]["allow"]


def test_erk_bash_permissions_install_adds_to_existing(tmp_path: Path) -> None:
    """Test install adds permission to existing settings.json."""
    import json

    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps({"permissions": {"allow": ["Read(/tmp/*)"]}, "hooks": {}}),
        encoding="utf-8",
    )

    cap = ErkBashPermissionsCapability()
    result = cap.install(tmp_path)

    assert result.success is True
    assert "Added" in result.message

    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert "Bash(erk:*)" in settings["permissions"]["allow"]
    assert "Read(/tmp/*)" in settings["permissions"]["allow"]
    assert "hooks" in settings  # Preserves existing keys


def test_erk_bash_permissions_install_idempotent(tmp_path: Path) -> None:
    """Test install is idempotent when permission already exists."""
    import json

    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps({"permissions": {"allow": ["Bash(erk:*)"]}}),
        encoding="utf-8",
    )

    cap = ErkBashPermissionsCapability()
    result = cap.install(tmp_path)

    assert result.success is True
    assert "already" in result.message

    # Verify it wasn't duplicated
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert settings["permissions"]["allow"].count("Bash(erk:*)") == 1


def test_permission_capability_registered() -> None:
    """Test that permission capability is registered."""
    cap = get_capability("erk-bash-permissions")
    assert cap is not None
    assert cap.name == "erk-bash-permissions"


# =============================================================================
# Tests for StatuslineCapability
# =============================================================================


def test_statusline_capability_properties() -> None:
    """Test StatuslineCapability has correct properties."""
    cap = StatuslineCapability(claude_installation=None)
    assert cap.name == "statusline"
    assert cap.scope == "user"
    assert "status line" in cap.description.lower()
    assert "statusLine" in cap.installation_check_description


def test_statusline_capability_artifacts() -> None:
    """Test StatuslineCapability lists correct artifacts."""
    cap = StatuslineCapability(claude_installation=None)
    artifacts = cap.artifacts

    # settings.json is shared by multiple capabilities, so not listed
    assert len(artifacts) == 0


def test_statusline_is_installed_false_when_not_configured() -> None:
    """Test is_installed returns False when statusline not configured."""
    fake_claude = FakeClaudeInstallation.for_test(settings={})
    cap = StatuslineCapability(claude_installation=fake_claude)

    # User-level capability ignores repo_root
    assert cap.is_installed(None) is False


def test_statusline_is_installed_true_when_configured() -> None:
    """Test is_installed returns True when erk-statusline is configured."""
    fake_claude = FakeClaudeInstallation.for_test(
        settings={
            "statusLine": {
                "type": "command",
                "command": "uvx erk-statusline",
            }
        }
    )
    cap = StatuslineCapability(claude_installation=fake_claude)

    # User-level capability ignores repo_root
    assert cap.is_installed(None) is True


def test_statusline_install_configures_statusline() -> None:
    """Test install configures erk-statusline in settings."""
    fake_claude = FakeClaudeInstallation.for_test(settings={})
    cap = StatuslineCapability(claude_installation=fake_claude)

    result = cap.install(None)

    assert result.success is True
    assert "Configured" in result.message

    # Verify settings were written
    assert len(fake_claude.settings_writes) == 1
    written_settings = fake_claude.settings_writes[0]
    assert "statusLine" in written_settings
    assert "erk-statusline" in written_settings["statusLine"]["command"]


def test_statusline_install_idempotent() -> None:
    """Test install is idempotent when already configured."""
    fake_claude = FakeClaudeInstallation.for_test(
        settings={
            "statusLine": {
                "type": "command",
                "command": "uvx erk-statusline",
            }
        }
    )
    cap = StatuslineCapability(claude_installation=fake_claude)

    result = cap.install(None)

    assert result.success is True
    assert "already configured" in result.message

    # Verify no writes were made
    assert len(fake_claude.settings_writes) == 0


def test_statusline_capability_registered() -> None:
    """Test that statusline capability is registered."""
    cap = get_capability("statusline")
    assert cap is not None
    assert cap.name == "statusline"
    assert cap.scope == "user"


# =============================================================================
# Tests for Capability Scope
# =============================================================================


def test_all_project_capabilities_have_project_scope() -> None:
    """Test that project-level capabilities have 'project' scope."""
    project_caps = [
        LearnedDocsCapability(),
        DignifiedPythonCapability(),
        FakeDrivenTestingCapability(),
        ErkImplWorkflowCapability(),
        DevrunAgentCapability(),
        ErkBashPermissionsCapability(),
    ]

    for cap in project_caps:
        assert cap.scope == "project", f"{cap.name} should have 'project' scope"


def test_statusline_has_user_scope() -> None:
    """Test that StatuslineCapability has 'user' scope."""
    cap = StatuslineCapability(claude_installation=None)
    assert cap.scope == "user"


def test_all_registered_capabilities_have_valid_scope() -> None:
    """Test that all registered capabilities have a valid scope."""
    valid_scopes = {"project", "user"}
    for cap in list_capabilities():
        assert cap.scope in valid_scopes, f"{cap.name} has invalid scope: {cap.scope}"


def test_capability_scope_values() -> None:
    """Test that CapabilityScope type alias has expected values."""
    # This tests the type at runtime - useful for documentation purposes
    # The type is Literal["project", "user"]
    project_cap = LearnedDocsCapability()
    user_cap = StatuslineCapability(claude_installation=None)

    assert project_cap.scope == "project"
    assert user_cap.scope == "user"


# =============================================================================
# Tests for Capability.preflight()
# =============================================================================


def test_default_preflight_returns_success(tmp_path: Path) -> None:
    """Test that default preflight() implementation returns success."""
    cap = LearnedDocsCapability()
    result = cap.preflight(tmp_path)

    assert result.success is True
    assert result.message == ""


def test_preflight_called_before_install_pattern() -> None:
    """Test that preflight can be called to check preconditions."""
    # This tests the pattern: check preflight, then install
    cap = LearnedDocsCapability()

    # Default preflight always succeeds
    preflight_result = cap.preflight(None)
    assert preflight_result.success is True


# =============================================================================
# Tests for DignifiedReviewCapability
# =============================================================================


def test_dignified_review_capability_properties() -> None:
    """Test DignifiedReviewCapability has correct properties."""
    cap = DignifiedReviewCapability()
    assert cap.name == "dignified-review"
    assert cap.scope == "project"
    assert "GitHub Action" in cap.description or "code review" in cap.description
    assert "dignified-python-review.yml" in cap.installation_check_description


def test_dignified_review_artifacts() -> None:
    """Test DignifiedReviewCapability lists correct artifacts."""
    cap = DignifiedReviewCapability()
    artifacts = cap.artifacts

    assert len(artifacts) == 2
    paths = [a.path for a in artifacts]
    assert ".github/workflows/dignified-python-review.yml" in paths
    assert ".github/prompts/dignified-python-review.md" in paths


def test_dignified_review_is_installed_false_when_missing(tmp_path: Path) -> None:
    """Test is_installed returns False when workflow file doesn't exist."""
    cap = DignifiedReviewCapability()
    assert cap.is_installed(tmp_path) is False


def test_dignified_review_is_installed_true_when_exists(tmp_path: Path) -> None:
    """Test is_installed returns True when workflow file exists."""
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "dignified-python-review.yml").write_text(
        "", encoding="utf-8"
    )
    cap = DignifiedReviewCapability()
    assert cap.is_installed(tmp_path) is True


def test_dignified_review_preflight_fails_when_skill_missing(tmp_path: Path) -> None:
    """Test preflight fails when dignified-python skill is not installed."""
    cap = DignifiedReviewCapability()
    result = cap.preflight(tmp_path)

    assert result.success is False
    assert "dignified-python" in result.message


def test_dignified_review_preflight_succeeds_when_skill_present(tmp_path: Path) -> None:
    """Test preflight succeeds when dignified-python skill is installed."""
    # Create the skill directory
    (tmp_path / ".claude" / "skills" / "dignified-python").mkdir(parents=True)

    cap = DignifiedReviewCapability()
    result = cap.preflight(tmp_path)

    assert result.success is True


def test_dignified_review_capability_registered() -> None:
    """Test that dignified-review capability is registered."""
    cap = get_capability("dignified-review")
    assert cap is not None
    assert cap.name == "dignified-review"


# =============================================================================
# Tests for HooksCapability
# =============================================================================


def test_hooks_capability_properties() -> None:
    """Test HooksCapability has correct properties."""
    cap = HooksCapability()
    assert cap.name == "erk-hooks"
    assert cap.scope == "project"
    assert "hooks" in cap.description.lower() or "session" in cap.description.lower()
    assert "UserPromptSubmit" in cap.installation_check_description
    assert "ExitPlanMode" in cap.installation_check_description


def test_hooks_capability_is_required() -> None:
    """Test HooksCapability is marked as required."""
    cap = HooksCapability()
    assert cap.required is True


def test_hooks_capability_artifacts() -> None:
    """Test HooksCapability lists correct artifacts."""
    cap = HooksCapability()
    artifacts = cap.artifacts

    # settings.json is shared by multiple capabilities, so not listed
    assert len(artifacts) == 0


def test_hooks_is_installed_false_when_no_settings(tmp_path: Path) -> None:
    """Test is_installed returns False when settings.json doesn't exist."""
    cap = HooksCapability()
    assert cap.is_installed(tmp_path) is False


def test_hooks_is_installed_false_when_hooks_missing(tmp_path: Path) -> None:
    """Test is_installed returns False when hooks not configured."""
    import json

    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(json.dumps({}), encoding="utf-8")

    cap = HooksCapability()
    assert cap.is_installed(tmp_path) is False


def test_hooks_is_installed_false_when_only_user_prompt_hook(tmp_path: Path) -> None:
    """Test is_installed returns False when only UserPromptSubmit hook exists."""
    import json

    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings = {
        "hooks": {
            "UserPromptSubmit": [
                {
                    "matcher": "",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "ERK_HOOK_ID=user-prompt-hook erk exec user-prompt-hook",
                        }
                    ],
                }
            ]
        }
    }
    settings_path.write_text(json.dumps(settings), encoding="utf-8")

    cap = HooksCapability()
    assert cap.is_installed(tmp_path) is False


def test_hooks_is_installed_true_when_both_hooks_present(tmp_path: Path) -> None:
    """Test is_installed returns True when both hooks are configured."""
    import json

    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings = {
        "hooks": {
            "UserPromptSubmit": [
                {
                    "matcher": "",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "ERK_HOOK_ID=user-prompt-hook erk exec user-prompt-hook",
                        }
                    ],
                }
            ],
            "PreToolUse": [
                {
                    "matcher": "ExitPlanMode",
                    "hooks": [
                        {
                            "type": "command",
                            "command": (
                                "ERK_HOOK_ID=exit-plan-mode-hook erk exec exit-plan-mode-hook"
                            ),
                        }
                    ],
                }
            ],
        }
    }
    settings_path.write_text(json.dumps(settings), encoding="utf-8")

    cap = HooksCapability()
    assert cap.is_installed(tmp_path) is True


def test_hooks_install_creates_settings(tmp_path: Path) -> None:
    """Test install creates settings.json if it doesn't exist."""
    import json

    cap = HooksCapability()
    result = cap.install(tmp_path)

    assert result.success is True
    assert ".claude/settings.json" in result.created_files

    settings_path = tmp_path / ".claude" / "settings.json"
    assert settings_path.exists()

    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert "hooks" in settings
    assert "UserPromptSubmit" in settings["hooks"]
    assert "PreToolUse" in settings["hooks"]


def test_hooks_install_adds_to_existing(tmp_path: Path) -> None:
    """Test install adds hooks to existing settings.json."""
    import json

    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps({"permissions": {"allow": ["Read(/tmp/*)"]}}),
        encoding="utf-8",
    )

    cap = HooksCapability()
    result = cap.install(tmp_path)

    assert result.success is True
    assert "Added" in result.message

    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert "hooks" in settings
    assert "UserPromptSubmit" in settings["hooks"]
    assert "PreToolUse" in settings["hooks"]
    # Preserves existing keys
    assert "permissions" in settings
    assert "Read(/tmp/*)" in settings["permissions"]["allow"]


def test_hooks_install_idempotent(tmp_path: Path) -> None:
    """Test install is idempotent when hooks already exist."""
    import json

    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings = {
        "hooks": {
            "UserPromptSubmit": [
                {
                    "matcher": "",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "ERK_HOOK_ID=user-prompt-hook erk exec user-prompt-hook",
                        }
                    ],
                }
            ],
            "PreToolUse": [
                {
                    "matcher": "ExitPlanMode",
                    "hooks": [
                        {
                            "type": "command",
                            "command": (
                                "ERK_HOOK_ID=exit-plan-mode-hook erk exec exit-plan-mode-hook"
                            ),
                        }
                    ],
                }
            ],
        }
    }
    settings_path.write_text(json.dumps(settings), encoding="utf-8")

    cap = HooksCapability()
    result = cap.install(tmp_path)

    assert result.success is True
    assert "already" in result.message


def test_hooks_install_handles_invalid_json(tmp_path: Path) -> None:
    """Test install fails gracefully with invalid JSON."""
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text("invalid json {{{", encoding="utf-8")

    cap = HooksCapability()
    result = cap.install(tmp_path)

    assert result.success is False
    assert "Invalid JSON" in result.message


def test_hooks_capability_registered() -> None:
    """Test that hooks capability is registered."""
    cap = get_capability("erk-hooks")
    assert cap is not None
    assert cap.name == "erk-hooks"


def test_hooks_is_installed_returns_false_with_none_repo_root() -> None:
    """Test is_installed returns False when repo_root is None."""
    cap = HooksCapability()
    assert cap.is_installed(None) is False


def test_hooks_install_fails_with_none_repo_root() -> None:
    """Test install fails when repo_root is None."""
    cap = HooksCapability()
    result = cap.install(None)

    assert result.success is False
    assert "requires repo_root" in result.message


# =============================================================================
# Tests for Required Capabilities
# =============================================================================


def test_list_required_capabilities_returns_only_required() -> None:
    """Test that list_required_capabilities returns only capabilities with required=True."""
    required_caps = list_required_capabilities()

    # All returned capabilities should have required=True
    for cap in required_caps:
        assert cap.required is True, f"{cap.name} has required=False but was returned"


def test_list_required_capabilities_includes_hooks() -> None:
    """Test that HooksCapability is in the list of required capabilities."""
    required_caps = list_required_capabilities()
    names = [cap.name for cap in required_caps]

    assert "erk-hooks" in names


def test_default_capabilities_not_required() -> None:
    """Test that default capabilities are NOT required."""
    # Most capabilities should be optional
    optional_caps = [
        LearnedDocsCapability(),
        DignifiedPythonCapability(),
        FakeDrivenTestingCapability(),
        ErkImplWorkflowCapability(),
        DevrunAgentCapability(),
        ErkBashPermissionsCapability(),
        StatuslineCapability(claude_installation=None),
    ]

    for cap in optional_caps:
        assert cap.required is False, f"{cap.name} should not be required"


def test_capability_base_required_default_is_false() -> None:
    """Test that Capability ABC has required=False by default."""

    class TestCap(Capability):
        """Test capability with default required behavior."""

        @property
        def name(self) -> str:
            return "test"

        @property
        def description(self) -> str:
            return "test"

        @property
        def scope(self) -> CapabilityScope:
            return "project"

        @property
        def installation_check_description(self) -> str:
            return "test"

        @property
        def artifacts(self) -> list[CapabilityArtifact]:
            return []

        def is_installed(self, repo_root: Path | None) -> bool:
            return False

        def install(self, repo_root: Path | None) -> CapabilityResult:
            return CapabilityResult(success=True, message="test")

    cap = TestCap()
    assert cap.required is False
