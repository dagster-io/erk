"""Tests for workflow configuration loading."""

from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.submit import load_workflow_config, submit_cmd
from tests.commands.submit.conftest import create_plan, setup_submit_context


def test_load_workflow_config_file_not_found(tmp_path: Path) -> None:
    """Test load_workflow_config returns empty dict when config file doesn't exist."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    result = load_workflow_config(repo_root, "plan-implement.yml")

    assert result == {}


def test_load_workflow_config_valid_toml(tmp_path: Path) -> None:
    """Test load_workflow_config returns string dict from valid TOML."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create workflow config in .erk/config.toml
    config_dir = repo_root / ".erk"
    config_dir.mkdir(parents=True)
    config_file = config_dir / "config.toml"
    config_file.write_text(
        '[workflows.dispatch-erk-queue]\nmodel_name = "claude-sonnet-4-5"\n',
        encoding="utf-8",
    )

    result = load_workflow_config(repo_root, "erk/dispatch-erk-queue.yml")

    assert result == {
        "model_name": "claude-sonnet-4-5",
    }


def test_load_workflow_config_converts_values_to_strings(tmp_path: Path) -> None:
    """Test load_workflow_config converts non-string values to strings."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Create workflow config in .erk/config.toml with non-string values
    config_dir = repo_root / ".erk"
    config_dir.mkdir(parents=True)
    config_file = config_dir / "config.toml"
    config_file.write_text(
        '[workflows.my-workflow]\ntimeout = 300\nenabled = true\nname = "test"\n',
        encoding="utf-8",
    )

    result = load_workflow_config(repo_root, "my-workflow.yml")

    # All values should be strings
    assert result == {
        "timeout": "300",
        "enabled": "True",
        "name": "test",
    }


def test_load_workflow_config_strips_yml_extension(tmp_path: Path) -> None:
    """Test load_workflow_config strips .yml extension from workflow name."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    config_dir = repo_root / ".erk"
    config_dir.mkdir(parents=True)
    config_file = config_dir / "config.toml"
    config_file.write_text('[workflows.my-workflow]\nkey = "value"\n', encoding="utf-8")

    # Pass with .yml extension
    result = load_workflow_config(repo_root, "my-workflow.yml")

    assert result == {"key": "value"}


def test_load_workflow_config_strips_yaml_extension(tmp_path: Path) -> None:
    """Test load_workflow_config strips .yaml extension from workflow name."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    config_dir = repo_root / ".erk"
    config_dir.mkdir(parents=True)
    config_file = config_dir / "config.toml"
    config_file.write_text('[workflows.my-workflow]\nkey = "value"\n', encoding="utf-8")

    # Pass with .yaml extension
    result = load_workflow_config(repo_root, "my-workflow.yaml")

    assert result == {"key": "value"}


def test_load_workflow_config_missing_workflows_section(tmp_path: Path) -> None:
    """Test load_workflow_config returns empty dict when workflows section missing."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    config_dir = repo_root / ".erk"
    config_dir.mkdir(parents=True)

    # Create config.toml with other sections but no [workflows]
    config_file = config_dir / "config.toml"
    config_file.write_text(
        '[env]\nSOME_VAR = "value"\n\n[post_create]\nshell = "bash"\n',
        encoding="utf-8",
    )

    result = load_workflow_config(repo_root, "plan-implement.yml")

    assert result == {}


def test_load_workflow_config_missing_specific_workflow(tmp_path: Path) -> None:
    """Test load_workflow_config returns empty dict when specific workflow section missing."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    config_dir = repo_root / ".erk"
    config_dir.mkdir(parents=True)

    # Create config.toml with [workflows] but not [workflows.plan-implement]
    config_file = config_dir / "config.toml"
    config_file.write_text(
        '[workflows.other-workflow]\nsome_key = "some_value"\n',
        encoding="utf-8",
    )

    result = load_workflow_config(repo_root, "plan-implement.yml")

    assert result == {}


def test_submit_uses_workflow_config(tmp_path: Path) -> None:
    """Test submit includes workflow config inputs when triggering workflow."""
    plan = create_plan("123", "Test with workflow config")
    repo_root = tmp_path / "repo"

    ctx, _, fake_github, _, _, repo_root = setup_submit_context(
        tmp_path,
        {"123": plan},
        git_kwargs={
            "current_branches": {repo_root: "main"},
            "trunk_branches": {repo_root: "master"},
        },
    )

    # Create workflow config in .erk/config.toml (inside repo_root created by setup_submit_context)
    config_dir = repo_root / ".erk"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "config.toml"
    config_file.write_text(
        '[workflows.plan-implement]\nmodel_name = "claude-sonnet-4-5"\n',
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(submit_cmd, ["123"], obj=ctx)

    assert result.exit_code == 0, result.output

    # Verify workflow was triggered with config inputs
    assert len(fake_github.triggered_workflows) == 1
    workflow, inputs = fake_github.triggered_workflows[0]
    assert workflow == "plan-implement.yml"
    # Required inputs
    assert inputs["plan_id"] == "123"
    # Config-based input from .erk/config.toml
    assert inputs["model_name"] == "claude-sonnet-4-5"
