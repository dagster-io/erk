"""Tests for workflow configuration loading."""

from pathlib import Path

from erk.cli.commands.pr.dispatch.operation import load_workflow_config


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
