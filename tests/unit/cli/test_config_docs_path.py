"""Tests for docs_path config parsing.

Verifies that [docs] path is parsed from config.toml and config.local.toml,
threaded through merge functions, and local overrides base.
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


def test_parse_docs_path_from_config(tmp_path: Path) -> None:
    """Test that [docs] path is parsed from config.toml."""
    erk_dir = tmp_path / ".erk"
    erk_dir.mkdir()
    config_path = erk_dir / "config.toml"
    config_path.write_text(
        '[docs]\npath = "/Users/me/code/my-docs-repo"\n',
        encoding="utf-8",
    )

    result = load_config(tmp_path)

    assert result.docs_path == "/Users/me/code/my-docs-repo"


def test_parse_docs_path_from_local_config(tmp_path: Path) -> None:
    """Test that [docs] path is parsed from config.local.toml."""
    erk_dir = tmp_path / ".erk"
    erk_dir.mkdir()
    config_path = erk_dir / "config.local.toml"
    config_path.write_text(
        '[docs]\npath = "/Users/me/code/private-docs"\n',
        encoding="utf-8",
    )

    result = load_local_config(tmp_path)

    assert result.docs_path == "/Users/me/code/private-docs"


def test_docs_path_defaults_to_none(tmp_path: Path) -> None:
    """Test that docs_path is None when no [docs] section exists."""
    result = load_config(tmp_path)

    assert result.docs_path is None


def test_docs_path_none_when_no_path_key(tmp_path: Path) -> None:
    """Test that docs_path is None when [docs] exists but path is missing."""
    erk_dir = tmp_path / ".erk"
    erk_dir.mkdir()
    config_path = erk_dir / "config.toml"
    config_path.write_text(
        "[docs]\n",
        encoding="utf-8",
    )

    result = load_config(tmp_path)

    assert result.docs_path is None


def test_merge_configs_passes_docs_path_from_repo() -> None:
    """Test that merge_configs passes through docs_path from repo config."""
    repo_config = LoadedConfig.test(docs_path="/external/docs")
    project_config = ProjectConfig(
        name=None,
        env={},
        post_create_commands=[],
        post_create_shell=None,
    )

    result = merge_configs(repo_config, project_config)

    assert result.docs_path == "/external/docs"


def test_merge_configs_with_local_overrides_docs_path() -> None:
    """Test that local config overrides base docs_path."""
    base = LoadedConfig.test(docs_path="/base/docs")
    local = LoadedConfig.test(docs_path="/local/docs")

    result = merge_configs_with_local(base_config=base, local_config=local)

    assert result.docs_path == "/local/docs"


def test_merge_configs_with_local_keeps_base_when_local_is_none() -> None:
    """Test that base docs_path is kept when local is None."""
    base = LoadedConfig.test(docs_path="/base/docs")
    local = LoadedConfig.test(docs_path=None)

    result = merge_configs_with_local(base_config=base, local_config=local)

    assert result.docs_path == "/base/docs"


def test_merge_configs_with_local_both_none() -> None:
    """Test that docs_path is None when neither base nor local sets it."""
    base = LoadedConfig.test()
    local = LoadedConfig.test()

    result = merge_configs_with_local(base_config=base, local_config=local)

    assert result.docs_path is None
