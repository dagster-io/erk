"""Tests for project config loading and merging."""

from pathlib import Path

from erk.cli.config import (
    LegacyConfigLocation,
    LoadedConfig,
    ProjectConfig,
    detect_legacy_config_locations,
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


class TestDetectLegacyConfigLocations:
    """Tests for detect_legacy_config_locations function."""

    def test_no_legacy_configs(self, tmp_path: Path) -> None:
        """Returns empty list when no legacy configs exist."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        metadata_dir = tmp_path / "metadata"
        metadata_dir.mkdir()

        result = detect_legacy_config_locations(repo_root, metadata_dir)

        assert result == []

    def test_detects_repo_root_config(self, tmp_path: Path) -> None:
        """Detects config.toml at repo root."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        (repo_root / "config.toml").write_text("[env]", encoding="utf-8")

        result = detect_legacy_config_locations(repo_root, None)

        assert len(result) == 1
        assert result[0].path == repo_root / "config.toml"
        assert "repo root" in result[0].description

    def test_detects_metadata_dir_config(self, tmp_path: Path) -> None:
        """Detects config.toml in metadata directory."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        metadata_dir = tmp_path / "metadata"
        metadata_dir.mkdir()
        (metadata_dir / "config.toml").write_text("[env]", encoding="utf-8")

        result = detect_legacy_config_locations(repo_root, metadata_dir)

        assert len(result) == 1
        assert result[0].path == metadata_dir / "config.toml"
        assert "metadata dir" in result[0].description

    def test_detects_both_legacy_locations(self, tmp_path: Path) -> None:
        """Detects both repo root and metadata dir configs."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        (repo_root / "config.toml").write_text("[env]", encoding="utf-8")
        metadata_dir = tmp_path / "metadata"
        metadata_dir.mkdir()
        (metadata_dir / "config.toml").write_text("[env]", encoding="utf-8")

        result = detect_legacy_config_locations(repo_root, metadata_dir)

        assert len(result) == 2
        # Repo root is first
        assert result[0].path == repo_root / "config.toml"
        assert result[1].path == metadata_dir / "config.toml"

    def test_handles_none_metadata_dir(self, tmp_path: Path) -> None:
        """Handles None metadata_dir gracefully."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        result = detect_legacy_config_locations(repo_root, None)

        assert result == []


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

    def test_loads_from_repo_root_fallback(self, tmp_path: Path) -> None:
        """Loads config from repo root as fallback."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        (repo_root / "config.toml").write_text(
            '[env]\nLEGACY = "value"\n',
            encoding="utf-8",
        )

        result = load_config(repo_root)

        assert result.env == {"LEGACY": "value"}

    def test_loads_from_metadata_dir_fallback(self, tmp_path: Path) -> None:
        """Loads config from metadata directory as fallback."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        metadata_dir = tmp_path / "metadata"
        metadata_dir.mkdir()
        (metadata_dir / "config.toml").write_text(
            '[env]\nMETADATA = "val"\n',
            encoding="utf-8",
        )

        result = load_config(repo_root, legacy_metadata_dir=metadata_dir)

        assert result.env == {"METADATA": "val"}

    def test_primary_location_takes_precedence_over_repo_root(self, tmp_path: Path) -> None:
        """Primary location (.erk/config.toml) takes precedence over repo root."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        # Create legacy config at repo root
        (repo_root / "config.toml").write_text(
            '[env]\nSOURCE = "legacy"\n',
            encoding="utf-8",
        )
        # Create primary config
        erk_dir = repo_root / ".erk"
        erk_dir.mkdir()
        (erk_dir / "config.toml").write_text(
            '[env]\nSOURCE = "primary"\n',
            encoding="utf-8",
        )

        result = load_config(repo_root)

        assert result.env == {"SOURCE": "primary"}

    def test_primary_location_takes_precedence_over_metadata_dir(self, tmp_path: Path) -> None:
        """Primary location takes precedence over metadata directory."""
        repo_root = tmp_path / "repo"
        erk_dir = repo_root / ".erk"
        erk_dir.mkdir(parents=True)
        (erk_dir / "config.toml").write_text(
            '[env]\nSOURCE = "primary"\n',
            encoding="utf-8",
        )
        metadata_dir = tmp_path / "metadata"
        metadata_dir.mkdir()
        (metadata_dir / "config.toml").write_text(
            '[env]\nSOURCE = "metadata"\n',
            encoding="utf-8",
        )

        result = load_config(repo_root, legacy_metadata_dir=metadata_dir)

        assert result.env == {"SOURCE": "primary"}

    def test_repo_root_fallback_takes_precedence_over_metadata_dir(self, tmp_path: Path) -> None:
        """Repo root fallback takes precedence over metadata directory."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        (repo_root / "config.toml").write_text(
            '[env]\nSOURCE = "repo_root"\n',
            encoding="utf-8",
        )
        metadata_dir = tmp_path / "metadata"
        metadata_dir.mkdir()
        (metadata_dir / "config.toml").write_text(
            '[env]\nSOURCE = "metadata"\n',
            encoding="utf-8",
        )

        result = load_config(repo_root, legacy_metadata_dir=metadata_dir)

        assert result.env == {"SOURCE": "repo_root"}

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


class TestLegacyConfigLocation:
    """Tests for LegacyConfigLocation dataclass."""

    def test_frozen(self) -> None:
        """LegacyConfigLocation is immutable."""
        import pytest

        loc = LegacyConfigLocation(
            path=Path("/some/path"),
            description="test",
        )

        with pytest.raises(AttributeError):
            loc.path = Path("/other")  # type: ignore[misc]
