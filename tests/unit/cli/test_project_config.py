"""Tests for project config loading and merging."""

from pathlib import Path

from erk.cli.config import (
    LoadedConfig,
    ProjectConfig,
    load_config,
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
        repo_config = LoadedConfig.test(env={"VAR1": "repo_val1", "VAR2": "repo_val2"})
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
        repo_config = LoadedConfig.test(post_create_commands=["repo_cmd1", "repo_cmd2"])
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
        repo_config = LoadedConfig.test(post_create_shell="bash")
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
        repo_config = LoadedConfig.test(post_create_shell="bash")
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
        repo_config = LoadedConfig.test()
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
            cfg.name = "new-name"  # type: ignore[misc] -- intentionally mutating frozen dataclass to test immutability


class TestLoadConfig:
    """Tests for load_config function."""

    def test_returns_defaults_when_no_config_exists(self, tmp_path: Path) -> None:
        """Returns default config when no config.toml exists anywhere."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        result = load_config(repo_root)

        assert result.env == {}
        assert result.post_create_commands == []
        assert result.post_create_shell is None

    def test_loads_from_primary_location(self, tmp_path: Path) -> None:
        """Loads config from .erk/config.toml (primary location)."""
        repo_root = tmp_path / "repo"
        erk_dir = repo_root / ".erk"
        erk_dir.mkdir(parents=True)
        (erk_dir / "config.toml").write_text(
            '[env]\nFOO = "bar"\n',
            encoding="utf-8",
        )

        result = load_config(repo_root)

        assert result.env == {"FOO": "bar"}

    def test_ignores_legacy_repo_root_config(self, tmp_path: Path) -> None:
        """Does not load config from legacy repo root location.

        Legacy configs at repo root are detected by 'erk doctor', not loaded.
        """
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        (repo_root / "config.toml").write_text(
            '[env]\nLEGACY = "value"\n',
            encoding="utf-8",
        )

        result = load_config(repo_root)

        # Legacy location is NOT loaded - use 'erk doctor' to detect and migrate
        assert result.env == {}

    def test_loads_post_create_commands(self, tmp_path: Path) -> None:
        """Loads post_create commands from config."""
        repo_root = tmp_path / "repo"
        erk_dir = repo_root / ".erk"
        erk_dir.mkdir(parents=True)
        (erk_dir / "config.toml").write_text(
            '[post_create]\ncommands = ["cmd1", "cmd2"]\nshell = "bash"\n',
            encoding="utf-8",
        )

        result = load_config(repo_root)

        assert result.post_create_commands == ["cmd1", "cmd2"]
        assert result.post_create_shell == "bash"

    def test_loads_plans_repo(self, tmp_path: Path) -> None:
        """Loads plans.repo from config."""
        repo_root = tmp_path / "repo"
        erk_dir = repo_root / ".erk"
        erk_dir.mkdir(parents=True)
        (erk_dir / "config.toml").write_text(
            '[plans]\nrepo = "owner/plans-repo"\n',
            encoding="utf-8",
        )

        result = load_config(repo_root)

        assert result.plans_repo == "owner/plans-repo"

    def test_plans_repo_defaults_to_none(self, tmp_path: Path) -> None:
        """plans_repo defaults to None when [plans] section absent."""
        repo_root = tmp_path / "repo"
        erk_dir = repo_root / ".erk"
        erk_dir.mkdir(parents=True)
        (erk_dir / "config.toml").write_text(
            '[env]\nFOO = "bar"\n',
            encoding="utf-8",
        )

        result = load_config(repo_root)

        assert result.plans_repo is None

    def test_loads_full_config_with_plans_repo(self, tmp_path: Path) -> None:
        """Loads full config including plans.repo."""
        repo_root = tmp_path / "repo"
        erk_dir = repo_root / ".erk"
        erk_dir.mkdir(parents=True)
        (erk_dir / "config.toml").write_text(
            """
[env]
FOO = "bar"

[post_create]
shell = "bash"
commands = ["cmd1"]

[plans]
repo = "owner/plans-repo"
""",
            encoding="utf-8",
        )

        result = load_config(repo_root)

        assert result.env == {"FOO": "bar"}
        assert result.post_create_shell == "bash"
        assert result.post_create_commands == ["cmd1"]
        assert result.plans_repo == "owner/plans-repo"

    def test_loads_pool_max_slots(self, tmp_path: Path) -> None:
        """Loads pool.max_slots from config."""
        repo_root = tmp_path / "repo"
        erk_dir = repo_root / ".erk"
        erk_dir.mkdir(parents=True)
        (erk_dir / "config.toml").write_text(
            "[pool]\nmax_slots = 8\n",
            encoding="utf-8",
        )

        result = load_config(repo_root)

        assert result.pool_size == 8

    def test_pool_size_defaults_to_none(self, tmp_path: Path) -> None:
        """pool_size defaults to None when [pool] section absent."""
        repo_root = tmp_path / "repo"
        erk_dir = repo_root / ".erk"
        erk_dir.mkdir(parents=True)
        (erk_dir / "config.toml").write_text(
            '[env]\nFOO = "bar"\n',
            encoding="utf-8",
        )

        result = load_config(repo_root)

        assert result.pool_size is None

    def test_loads_full_config_with_pool(self, tmp_path: Path) -> None:
        """Loads full config including pool.max_slots."""
        repo_root = tmp_path / "repo"
        erk_dir = repo_root / ".erk"
        erk_dir.mkdir(parents=True)
        (erk_dir / "config.toml").write_text(
            """
[env]
FOO = "bar"

[pool]
max_slots = 6

[plans]
repo = "owner/plans-repo"
""",
            encoding="utf-8",
        )

        result = load_config(repo_root)

        assert result.env == {"FOO": "bar"}
        assert result.pool_size == 6
        assert result.plans_repo == "owner/plans-repo"

    def test_loads_pool_checkout_commands(self, tmp_path: Path) -> None:
        """Loads pool.checkout.commands from config."""
        repo_root = tmp_path / "repo"
        erk_dir = repo_root / ".erk"
        erk_dir.mkdir(parents=True)
        (erk_dir / "config.toml").write_text(
            '[pool.checkout]\ncommands = ["git fetch origin", "echo hello"]\n',
            encoding="utf-8",
        )

        result = load_config(repo_root)

        assert result.pool_checkout_commands == ["git fetch origin", "echo hello"]

    def test_loads_pool_checkout_shell(self, tmp_path: Path) -> None:
        """Loads pool.checkout.shell from config."""
        repo_root = tmp_path / "repo"
        erk_dir = repo_root / ".erk"
        erk_dir.mkdir(parents=True)
        (erk_dir / "config.toml").write_text(
            '[pool.checkout]\nshell = "zsh"\n',
            encoding="utf-8",
        )

        result = load_config(repo_root)

        assert result.pool_checkout_shell == "zsh"

    def test_pool_checkout_defaults_to_empty(self, tmp_path: Path) -> None:
        """pool_checkout_commands defaults to empty list when section absent."""
        repo_root = tmp_path / "repo"
        erk_dir = repo_root / ".erk"
        erk_dir.mkdir(parents=True)
        (erk_dir / "config.toml").write_text(
            '[env]\nFOO = "bar"\n',
            encoding="utf-8",
        )

        result = load_config(repo_root)

        assert result.pool_checkout_commands == []
        assert result.pool_checkout_shell is None

    def test_loads_full_pool_config(self, tmp_path: Path) -> None:
        """Loads full pool config including checkout section."""
        repo_root = tmp_path / "repo"
        erk_dir = repo_root / ".erk"
        erk_dir.mkdir(parents=True)
        (erk_dir / "config.toml").write_text(
            """
[pool]
max_slots = 4

[pool.checkout]
shell = "bash"
commands = ["git fetch origin", "uv sync"]
""",
            encoding="utf-8",
        )

        result = load_config(repo_root)

        assert result.pool_size == 4
        assert result.pool_checkout_shell == "bash"
        assert result.pool_checkout_commands == ["git fetch origin", "uv sync"]
