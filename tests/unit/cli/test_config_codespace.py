"""Tests for codespace config parsing.

Verifies that [codespace] name and working_directory are parsed from
config.toml and config.local.toml, threaded through merge functions,
and local overrides base.
"""

from pathlib import Path

from erk.cli.config import (
    ProjectConfig,
    load_config,
    load_local_config,
    merge_configs,
    merge_configs_with_local,
)
from erk_shared.context.types import LoadedConfig


def test_parse_codespace_name_from_config(tmp_path: Path) -> None:
    """[codespace] name is parsed from config.toml."""
    erk_dir = tmp_path / ".erk"
    erk_dir.mkdir()
    config_path = erk_dir / "config.toml"
    config_path.write_text(
        '[codespace]\nname = "my-compass-codespace"\n',
        encoding="utf-8",
    )

    result = load_config(tmp_path)

    assert result.codespace_name == "my-compass-codespace"


def test_parse_codespace_working_directory_from_config(tmp_path: Path) -> None:
    """[codespace] working_directory is parsed from config.toml."""
    erk_dir = tmp_path / ".erk"
    erk_dir.mkdir()
    config_path = erk_dir / "config.toml"
    config_path.write_text(
        '[codespace]\nworking_directory = "/workspaces/dagster-compass"\n',
        encoding="utf-8",
    )

    result = load_config(tmp_path)

    assert result.codespace_working_directory == "/workspaces/dagster-compass"


def test_parse_codespace_both_fields_from_config(tmp_path: Path) -> None:
    """Both [codespace] fields are parsed from config.toml."""
    erk_dir = tmp_path / ".erk"
    erk_dir.mkdir()
    config_path = erk_dir / "config.toml"
    config_path.write_text(
        '[codespace]\nname = "mybox"\nworking_directory = "/workspaces/repo"\n',
        encoding="utf-8",
    )

    result = load_config(tmp_path)

    assert result.codespace_name == "mybox"
    assert result.codespace_working_directory == "/workspaces/repo"


def test_parse_codespace_from_local_config(tmp_path: Path) -> None:
    """[codespace] fields are parsed from config.local.toml."""
    erk_dir = tmp_path / ".erk"
    erk_dir.mkdir()
    config_path = erk_dir / "config.local.toml"
    config_path.write_text(
        '[codespace]\nname = "local-box"\nworking_directory = "/workspaces/local"\n',
        encoding="utf-8",
    )

    result = load_local_config(tmp_path)

    assert result.codespace_name == "local-box"
    assert result.codespace_working_directory == "/workspaces/local"


def test_codespace_fields_default_to_none(tmp_path: Path) -> None:
    """Codespace fields are None when no [codespace] section exists."""
    result = load_config(tmp_path)

    assert result.codespace_name is None
    assert result.codespace_working_directory is None


def test_codespace_fields_none_when_section_empty(tmp_path: Path) -> None:
    """Codespace fields are None when [codespace] section has no keys."""
    erk_dir = tmp_path / ".erk"
    erk_dir.mkdir()
    config_path = erk_dir / "config.toml"
    config_path.write_text("[codespace]\n", encoding="utf-8")

    result = load_config(tmp_path)

    assert result.codespace_name is None
    assert result.codespace_working_directory is None


def test_merge_configs_passes_codespace_from_repo() -> None:
    """merge_configs passes through codespace fields from repo config."""
    repo_config = LoadedConfig.test(
        codespace_name="repo-box",
        codespace_working_directory="/workspaces/repo",
    )
    project_config = ProjectConfig(
        name=None,
        env={},
        post_create_commands=[],
        post_create_shell=None,
    )

    result = merge_configs(repo_config, project_config)

    assert result.codespace_name == "repo-box"
    assert result.codespace_working_directory == "/workspaces/repo"


def test_merge_configs_with_local_overrides_codespace_name() -> None:
    """Local config overrides base codespace_name."""
    base = LoadedConfig.test(codespace_name="base-box")
    local = LoadedConfig.test(codespace_name="local-box")

    result = merge_configs_with_local(base_config=base, local_config=local)

    assert result.codespace_name == "local-box"


def test_merge_configs_with_local_overrides_working_directory() -> None:
    """Local config overrides base codespace_working_directory."""
    base = LoadedConfig.test(codespace_working_directory="/base/dir")
    local = LoadedConfig.test(codespace_working_directory="/local/dir")

    result = merge_configs_with_local(base_config=base, local_config=local)

    assert result.codespace_working_directory == "/local/dir"


def test_merge_configs_with_local_keeps_base_when_local_is_none() -> None:
    """Base codespace fields are kept when local is None."""
    base = LoadedConfig.test(
        codespace_name="base-box",
        codespace_working_directory="/base/dir",
    )
    local = LoadedConfig.test()

    result = merge_configs_with_local(base_config=base, local_config=local)

    assert result.codespace_name == "base-box"
    assert result.codespace_working_directory == "/base/dir"


def test_merge_configs_with_local_both_none() -> None:
    """Codespace fields are None when neither base nor local sets them."""
    base = LoadedConfig.test()
    local = LoadedConfig.test()

    result = merge_configs_with_local(base_config=base, local_config=local)

    assert result.codespace_name is None
    assert result.codespace_working_directory is None
