"""Tests for missing artifact detection."""

from pathlib import Path

from erk.artifacts.artifact_health import find_missing_artifacts
from erk.artifacts.models import CompletenessCheckResult
from erk_shared.gateway.installation.fake import FakeErkInstallation


def test_find_missing_artifacts_no_missing(tmp_path: Path) -> None:
    """All bundled artifacts present locally."""
    import json

    from erk.core.claude_settings import add_erk_hooks

    # Create bundled and project with same files
    bundled_claude = tmp_path / "bundled" / ".claude"
    bundled_cmd = bundled_claude / "commands" / "erk"
    bundled_cmd.mkdir(parents=True)
    (bundled_cmd / "plan-save.md").write_text("content")

    project_claude = tmp_path / "project" / ".claude"
    project_cmd = project_claude / "commands" / "erk"
    project_cmd.mkdir(parents=True)
    (project_cmd / "plan-save.md").write_text("content")

    # Add settings.json with hooks to avoid missing hooks
    settings = add_erk_hooks({})
    (project_claude / "settings.json").write_text(json.dumps(settings), encoding="utf-8")

    installation = FakeErkInstallation(
        bundled_claude_dir=bundled_claude,
        bundled_github_dir=tmp_path / "bundled" / ".github",
        current_version="1.0.0",
    )

    result = find_missing_artifacts(tmp_path / "project", installation=installation)

    assert isinstance(result, CompletenessCheckResult)
    assert result.missing == {}
    assert result.skipped_reason is None


def test_find_missing_artifacts_missing_command(tmp_path: Path) -> None:
    """Bundled command missing locally."""
    # Bundled has plan-save.md
    bundled_claude = tmp_path / "bundled" / ".claude"
    bundled_cmd = bundled_claude / "commands" / "erk"
    bundled_cmd.mkdir(parents=True)
    (bundled_cmd / "plan-save.md").write_text("content")
    (bundled_cmd / "pr-submit.md").write_text("content")

    # Project missing plan-save.md
    project_cmd = tmp_path / "project" / ".claude" / "commands" / "erk"
    project_cmd.mkdir(parents=True)
    (project_cmd / "pr-submit.md").write_text("content")

    installation = FakeErkInstallation(
        bundled_claude_dir=bundled_claude,
        bundled_github_dir=tmp_path / "bundled" / ".github",
        current_version="1.0.0",
    )

    result = find_missing_artifacts(tmp_path / "project", installation=installation)

    assert "commands/erk" in result.missing
    assert "plan-save.md" in result.missing["commands/erk"]
    assert "pr-submit.md" not in result.missing["commands/erk"]


def test_find_missing_artifacts_missing_skill_file(tmp_path: Path) -> None:
    """Bundled skill file missing locally."""
    # Bundled skill with multiple files
    bundled_claude = tmp_path / "bundled" / ".claude"
    bundled_skill = bundled_claude / "skills" / "dignified-python"
    bundled_skill.mkdir(parents=True)
    (bundled_skill / "SKILL.md").write_text("skill")
    (bundled_skill / "cli-patterns.md").write_text("patterns")

    # Project missing cli-patterns.md
    project_skill = tmp_path / "project" / ".claude" / "skills" / "dignified-python"
    project_skill.mkdir(parents=True)
    (project_skill / "SKILL.md").write_text("skill")

    installation = FakeErkInstallation(
        bundled_claude_dir=bundled_claude,
        bundled_github_dir=tmp_path / "bundled" / ".github",
        current_version="1.0.0",
    )

    result = find_missing_artifacts(tmp_path / "project", installation=installation)

    assert "skills/dignified-python" in result.missing
    assert "cli-patterns.md" in result.missing["skills/dignified-python"]


def test_find_missing_artifacts_skip_erk_repo(tmp_path: Path) -> None:
    """Skip check when running in erk repo."""
    # Create pyproject.toml with erk name
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "erk"\n', encoding="utf-8")

    # Create .claude dir (otherwise would skip for different reason)
    (tmp_path / ".claude").mkdir()

    installation = FakeErkInstallation(
        bundled_claude_dir=tmp_path / "bundled",
        bundled_github_dir=tmp_path / "bundled_github",
        current_version="1.0.0",
    )

    result = find_missing_artifacts(tmp_path, installation=installation)

    assert result.missing == {}
    assert result.skipped_reason == "erk-repo"


def test_find_missing_artifacts_skip_no_claude_dir(tmp_path: Path) -> None:
    """Skip check when no .claude/ directory."""
    installation = FakeErkInstallation(
        bundled_claude_dir=tmp_path / "bundled",
        bundled_github_dir=tmp_path / "bundled_github",
        current_version="1.0.0",
    )

    result = find_missing_artifacts(tmp_path, installation=installation)

    assert result.missing == {}
    assert result.skipped_reason == "no-claude-dir"


def test_find_missing_artifacts_missing_workflow(tmp_path: Path) -> None:
    """Bundled workflow missing locally."""
    # Bundled has erk-impl.yml
    bundled_github = tmp_path / "bundled" / ".github"
    bundled_workflows = bundled_github / "workflows"
    bundled_workflows.mkdir(parents=True)
    (bundled_workflows / "erk-impl.yml").write_text("workflow")

    # Bundled .claude also needs to exist to prevent no-bundled-dir skip
    bundled_claude = tmp_path / "bundled" / ".claude"
    bundled_claude.mkdir(parents=True)

    # Project missing erk-impl.yml
    project_workflows = tmp_path / "project" / ".github" / "workflows"
    project_workflows.mkdir(parents=True)

    # Claude directory exists
    project_claude = tmp_path / "project" / ".claude"
    project_claude.mkdir(parents=True)

    installation = FakeErkInstallation(
        bundled_claude_dir=bundled_claude,
        bundled_github_dir=bundled_github,
        current_version="1.0.0",
    )

    result = find_missing_artifacts(tmp_path / "project", installation=installation)

    assert ".github/workflows" in result.missing
    assert "erk-impl.yml" in result.missing[".github/workflows"]


def test_find_missing_artifacts_missing_hooks_no_settings(tmp_path: Path) -> None:
    """All hooks missing when settings.json doesn't exist."""
    # Bundled .claude exists
    bundled_claude = tmp_path / "bundled" / ".claude"
    bundled_claude.mkdir(parents=True)

    # Project .claude exists but no settings.json
    project_claude = tmp_path / "project" / ".claude"
    project_claude.mkdir(parents=True)

    installation = FakeErkInstallation(
        bundled_claude_dir=bundled_claude,
        bundled_github_dir=tmp_path / "bundled" / ".github",
        current_version="1.0.0",
    )

    result = find_missing_artifacts(tmp_path / "project", installation=installation)

    assert "settings.json" in result.missing
    # Both bundled hooks should be missing
    assert "exit-plan-mode-hook" in result.missing["settings.json"]
    assert "user-prompt-hook" in result.missing["settings.json"]


def test_find_missing_artifacts_partial_hooks(tmp_path: Path) -> None:
    """Only missing hooks are reported."""
    import json

    from erk.core.claude_settings import ERK_USER_PROMPT_HOOK_COMMAND

    # Bundled .claude exists
    bundled_claude = tmp_path / "bundled" / ".claude"
    bundled_claude.mkdir(parents=True)

    # Project has user-prompt-hook but not exit-plan-mode-hook
    project_claude = tmp_path / "project" / ".claude"
    project_claude.mkdir(parents=True)

    settings = {
        "hooks": {
            "UserPromptSubmit": [
                {
                    "matcher": "",
                    "hooks": [{"type": "command", "command": ERK_USER_PROMPT_HOOK_COMMAND}],
                }
            ],
        }
    }
    (project_claude / "settings.json").write_text(json.dumps(settings), encoding="utf-8")

    installation = FakeErkInstallation(
        bundled_claude_dir=bundled_claude,
        bundled_github_dir=tmp_path / "bundled" / ".github",
        current_version="1.0.0",
    )

    result = find_missing_artifacts(tmp_path / "project", installation=installation)

    assert "settings.json" in result.missing
    # Only exit-plan-mode-hook should be missing
    assert "exit-plan-mode-hook" in result.missing["settings.json"]
    assert "user-prompt-hook" not in result.missing["settings.json"]


def test_find_missing_artifacts_all_hooks_present(tmp_path: Path) -> None:
    """No missing hooks when all are configured."""
    import json

    from erk.core.claude_settings import add_erk_hooks

    # Bundled .claude exists
    bundled_claude = tmp_path / "bundled" / ".claude"
    bundled_claude.mkdir(parents=True)

    # Project has all hooks configured
    project_claude = tmp_path / "project" / ".claude"
    project_claude.mkdir(parents=True)

    settings = add_erk_hooks({})
    (project_claude / "settings.json").write_text(json.dumps(settings), encoding="utf-8")

    installation = FakeErkInstallation(
        bundled_claude_dir=bundled_claude,
        bundled_github_dir=tmp_path / "bundled" / ".github",
        current_version="1.0.0",
    )

    result = find_missing_artifacts(tmp_path / "project", installation=installation)

    # No hooks should be missing
    assert "settings.json" not in result.missing
