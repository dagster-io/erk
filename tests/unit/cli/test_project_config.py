"""Tests for project config loading and merging."""

from pathlib import Path

from erk.cli.config import (
    LoadedConfig,
    ProjectConfig,
    load_project_config,
    merge_configs,
)


class TestLoadProjectConfig:
    """Tests for load_project_config function."""

    def test_returns_defaults_when_file_missing(self, tmp_path: Path) -> None:
        """Returns default config when project.toml doesn't exist."""
        result = load_project_config(tmp_path)

        assert result.name is None
        assert result.env == {}
        assert result.post_create_commands == []
        assert result.post_create_shell is None

    def test_loads_name(self, tmp_path: Path) -> None:
        """Loads custom project name."""
        cfg_path = tmp_path / ".erk" / "project.toml"
        cfg_path.parent.mkdir(parents=True)
        cfg_path.write_text('name = "my-custom-project"\n', encoding="utf-8")

        result = load_project_config(tmp_path)

        assert result.name == "my-custom-project"

    def test_loads_env(self, tmp_path: Path) -> None:
        """Loads env variables."""
        cfg_path = tmp_path / ".erk" / "project.toml"
        cfg_path.parent.mkdir(parents=True)
        cfg_path.write_text(
            '[env]\nDAGSTER_HOME = "{project_root}"\nOTHER = "value"\n',
            encoding="utf-8",
        )

        result = load_project_config(tmp_path)

        assert result.env == {"DAGSTER_HOME": "{project_root}", "OTHER": "value"}

    def test_loads_post_create_commands(self, tmp_path: Path) -> None:
        """Loads post_create commands."""
        cfg_path = tmp_path / ".erk" / "project.toml"
        cfg_path.parent.mkdir(parents=True)
        cfg_path.write_text(
            '[post_create]\ncommands = ["source .venv/bin/activate", "make install"]\n',
            encoding="utf-8",
        )

        result = load_project_config(tmp_path)

        assert result.post_create_commands == ["source .venv/bin/activate", "make install"]

    def test_loads_post_create_shell(self, tmp_path: Path) -> None:
        """Loads post_create shell."""
        cfg_path = tmp_path / ".erk" / "project.toml"
        cfg_path.parent.mkdir(parents=True)
        cfg_path.write_text('[post_create]\nshell = "zsh"\n', encoding="utf-8")

        result = load_project_config(tmp_path)

        assert result.post_create_shell == "zsh"

    def test_loads_full_config(self, tmp_path: Path) -> None:
        """Loads all fields from a complete config."""
        cfg_path = tmp_path / ".erk" / "project.toml"
        cfg_path.parent.mkdir(parents=True)
        cfg_path.write_text(
            """
name = "dagster-open-platform"

[env]
DAGSTER_HOME = "{project_root}"

[post_create]
shell = "bash"
commands = [
    "source .venv/bin/activate",
]
""",
            encoding="utf-8",
        )

        result = load_project_config(tmp_path)

        assert result.name == "dagster-open-platform"
        assert result.env == {"DAGSTER_HOME": "{project_root}"}
        assert result.post_create_shell == "bash"
        assert result.post_create_commands == ["source .venv/bin/activate"]


class TestMergeConfigs:
    """Tests for merge_configs function."""

    def test_merges_env_project_overrides_repo(self) -> None:
        """Project env values override repo env values."""
        repo_config = LoadedConfig(
            env={"VAR1": "repo_val1", "VAR2": "repo_val2"},
            post_create_commands=[],
            post_create_shell=None,
        )
        project_config = ProjectConfig(
            name=None,
            env={"VAR2": "project_val2", "VAR3": "project_val3"},
            post_create_commands=[],
            post_create_shell=None,
        )

        result = merge_configs(repo_config, project_config)

        assert result.env == {
            "VAR1": "repo_val1",  # From repo
            "VAR2": "project_val2",  # Project overrides repo
            "VAR3": "project_val3",  # From project
        }

    def test_concatenates_commands(self) -> None:
        """Commands are concatenated: repo first, then project."""
        repo_config = LoadedConfig(
            env={},
            post_create_commands=["repo_cmd1", "repo_cmd2"],
            post_create_shell=None,
        )
        project_config = ProjectConfig(
            name=None,
            env={},
            post_create_commands=["proj_cmd1", "proj_cmd2"],
            post_create_shell=None,
        )

        result = merge_configs(repo_config, project_config)

        assert result.post_create_commands == [
            "repo_cmd1",
            "repo_cmd2",
            "proj_cmd1",
            "proj_cmd2",
        ]

    def test_project_shell_overrides_repo_shell(self) -> None:
        """Project shell overrides repo shell when set."""
        repo_config = LoadedConfig(
            env={},
            post_create_commands=[],
            post_create_shell="bash",
        )
        project_config = ProjectConfig(
            name=None,
            env={},
            post_create_commands=[],
            post_create_shell="zsh",
        )

        result = merge_configs(repo_config, project_config)

        assert result.post_create_shell == "zsh"

    def test_uses_repo_shell_when_project_shell_none(self) -> None:
        """Uses repo shell when project shell is None."""
        repo_config = LoadedConfig(
            env={},
            post_create_commands=[],
            post_create_shell="bash",
        )
        project_config = ProjectConfig(
            name=None,
            env={},
            post_create_commands=[],
            post_create_shell=None,
        )

        result = merge_configs(repo_config, project_config)

        assert result.post_create_shell == "bash"

    def test_merges_empty_configs(self) -> None:
        """Handles merging empty configs."""
        repo_config = LoadedConfig(env={}, post_create_commands=[], post_create_shell=None)
        project_config = ProjectConfig(
            name=None, env={}, post_create_commands=[], post_create_shell=None
        )

        result = merge_configs(repo_config, project_config)

        assert result.env == {}
        assert result.post_create_commands == []
        assert result.post_create_shell is None


class TestProjectConfig:
    """Tests for ProjectConfig dataclass."""

    def test_frozen(self) -> None:
        """ProjectConfig is immutable."""
        import pytest

        cfg = ProjectConfig(
            name="test",
            env={},
            post_create_commands=[],
            post_create_shell=None,
        )

        with pytest.raises(AttributeError):
            cfg.name = "new-name"  # type: ignore[misc]
