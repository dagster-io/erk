from pathlib import Path
from unittest import mock

import pytest

from erk.cli.commands.init import create_and_save_global_config
from erk.cli.commands.wt.create_cmd import make_env_content
from erk.cli.config import load_config
from erk.core.context import context_for_test
from erk.core.init_utils import discover_presets
from erk_shared.context.types import GlobalConfig
from erk_shared.gateway.erk_installation.fake import FakeErkInstallation
from erk_shared.gateway.erk_installation.real import RealErkInstallation
from tests.fakes.shell import FakeShell


def test_global_config_test_factory_method(tmp_path: Path) -> None:
    """Test GlobalConfig.test() factory method creates config with defaults."""
    config = GlobalConfig.test(tmp_path / "erks")

    assert config.erk_root == tmp_path / "erks"
    assert config.use_graphite is True
    assert config.shell_setup_complete is True
    assert config.github_planning is True
    assert config.show_hidden_commands is False


def test_global_config_test_factory_with_overrides(tmp_path: Path) -> None:
    """Test GlobalConfig.test() factory method respects overrides."""
    config = GlobalConfig.test(
        tmp_path / "erks",
        use_graphite=False,
        shell_setup_complete=False,
        show_hidden_commands=True,
    )

    assert config.erk_root == tmp_path / "erks"
    assert config.use_graphite is False
    assert config.shell_setup_complete is False
    assert config.github_planning is True  # Still default
    assert config.show_hidden_commands is True


def test_load_config_defaults(tmp_path: Path) -> None:
    cfg = load_config(tmp_path)
    assert cfg.env == {}
    assert cfg.post_create_commands == []
    assert cfg.post_create_shell is None


def test_env_rendering(tmp_path: Path) -> None:
    # Write a config to the primary location (.erk/config.toml)
    config_dir = tmp_path / "config_dir"
    erk_dir = config_dir / ".erk"
    erk_dir.mkdir(parents=True)
    (erk_dir / "config.toml").write_text(
        """
        [env]
        DAGSTER_GIT_REPO_DIR = "{worktree_path}"
        CUSTOM_NAME = "{name}"

        [post_create]
        shell = "bash"
        commands = ["echo hi"]
        """.strip()
    )

    cfg = load_config(config_dir)
    wt_path = tmp_path / "worktrees" / "foo"
    repo_root = tmp_path
    content = make_env_content(cfg, worktree_path=wt_path, repo_root=repo_root, name="foo")

    assert 'DAGSTER_GIT_REPO_DIR="' + str(wt_path) + '"' in content
    assert 'CUSTOM_NAME="foo"' in content
    assert 'WORKTREE_PATH="' + str(wt_path) + '"' in content
    assert 'REPO_ROOT="' + str(repo_root) + '"' in content
    assert 'WORKTREE_NAME="foo"' in content


# NOTE: Tests removed during FakeConfigStore deprecation (Phase 3a)
# These tests were testing the FakeConfigStore interface which has been
# removed. If these behaviors need coverage, they should be tested via
# RealConfigStore or GlobalConfig directly.

# def test_load_global_config_valid(tmp_path: Path) -> None:
#     ... (removed - was testing FakeConfigStore)

# def test_load_global_config_missing_file(tmp_path: Path) -> None:
#     ... (removed - was testing FakeConfigStore)


def test_load_global_config_missing_erk_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Test that RealConfigStore validates required fields
    config_file = tmp_path / "config.toml"
    config_file.write_text("use_graphite = true\n", encoding="utf-8")

    # Patch Path.home to return tmp_path so ops looks in tmp_path/.erk/
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

    # Create .erk dir and write config there
    erk_dir = tmp_path / ".erk"
    erk_dir.mkdir()
    (erk_dir / "config.toml").write_text("use_graphite = true\n", encoding="utf-8")

    installation = RealErkInstallation()
    with pytest.raises(ValueError, match="Missing 'erk_root'"):
        installation.load_config()


def test_real_config_store_roundtrip_show_hidden_commands(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that RealConfigStore correctly saves and loads show_hidden_commands."""
    # Patch Path.home to use tmp_path
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

    # Create .erk dir
    erk_dir = tmp_path / ".erk"
    erk_dir.mkdir()

    installation = RealErkInstallation()

    # Create and save config with show_hidden_commands=True
    config = GlobalConfig(
        erk_root=tmp_path / "erks",
        use_graphite=True,
        shell_setup_complete=True,
        github_planning=True,
        show_hidden_commands=True,
    )
    installation.save_config(config)

    # Load and verify
    loaded = installation.load_config()
    assert loaded.show_hidden_commands is True

    # Verify the field is in the saved file
    content = (erk_dir / "config.toml").read_text(encoding="utf-8")
    assert "show_hidden_commands = true" in content


def test_real_config_store_loads_show_hidden_commands_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that RealConfigStore defaults show_hidden_commands to False if missing."""
    # Patch Path.home to use tmp_path
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

    # Create .erk dir with config that doesn't have show_hidden_commands
    erk_dir = tmp_path / ".erk"
    erk_dir.mkdir()
    (erk_dir / "config.toml").write_text(
        f"""
erk_root = "{tmp_path / "erks"}"
use_graphite = true
shell_setup_complete = true
""".strip(),
        encoding="utf-8",
    )

    installation = RealErkInstallation()
    loaded = installation.load_config()

    # Should default to False
    assert loaded.show_hidden_commands is False


def test_create_global_config_creates_parent_directory(tmp_path: Path) -> None:
    # Test that create_and_save_global_config creates parent directory
    config_file = tmp_path / ".erk" / "config.toml"
    assert not config_file.parent.exists()

    # Create test context with FakeErkInstallation
    erk_installation = FakeErkInstallation(config=None)
    ctx = context_for_test(
        shell=FakeShell(),
        erk_installation=erk_installation,
        global_config=None,
        cwd=tmp_path,
    )

    with mock.patch("erk.cli.commands.init.detect_graphite", return_value=False):
        create_and_save_global_config(ctx, Path("/tmp/erks"), shell_setup_complete=False)

    # Verify config was saved to in-memory installation
    assert erk_installation.config_exists()
    loaded = erk_installation.load_config()
    assert loaded.erk_root == Path("/tmp/erks")


# def test_create_global_config_detects_graphite(tmp_path: Path) -> None:
#     ... (removed - was testing FakeConfigStore)


def test_discover_presets(tmp_path: Path) -> None:
    # Create structure: tmp_path/presets/*.toml
    presets_dir = tmp_path / "presets"
    presets_dir.mkdir()
    (presets_dir / "generic.toml").write_text("# generic preset\n", encoding="utf-8")
    (presets_dir / "dagster.toml").write_text("# dagster preset\n", encoding="utf-8")
    (presets_dir / "custom.toml").write_text("# custom preset\n", encoding="utf-8")
    (presets_dir / "README.md").write_text("# readme\n", encoding="utf-8")
    (presets_dir / "subdir").mkdir()

    presets = discover_presets(presets_dir)

    assert presets == ["custom", "dagster", "generic"]


def test_discover_presets_missing_directory(tmp_path: Path) -> None:
    # Test with non-existent presets directory
    presets_dir = tmp_path / "nonexistent"

    presets = discover_presets(presets_dir)

    assert presets == []


def test_load_config_with_post_create_commands(tmp_path: Path) -> None:
    # Write config to primary location (.erk/config.toml)
    config_dir = tmp_path / "config_dir"
    erk_dir = config_dir / ".erk"
    erk_dir.mkdir(parents=True)
    (erk_dir / "config.toml").write_text(
        """
        [env]
        FOO = "bar"

        [post_create]
        shell = "bash"
        commands = [
            "uv venv",
            "uv run make dev_install",
            "echo 'setup complete'"
        ]
        """.strip(),
        encoding="utf-8",
    )

    cfg = load_config(config_dir)
    assert cfg.env == {"FOO": "bar"}
    assert cfg.post_create_shell == "bash"
    assert cfg.post_create_commands == [
        "uv venv",
        "uv run make dev_install",
        "echo 'setup complete'",
    ]


def test_load_config_with_partial_post_create(tmp_path: Path) -> None:
    # Write config to primary location (.erk/config.toml)
    config_dir = tmp_path / "config_dir"
    erk_dir = config_dir / ".erk"
    erk_dir.mkdir(parents=True)
    (erk_dir / "config.toml").write_text(
        """
        [post_create]
        commands = ["echo 'hello'"]
        """.strip(),
        encoding="utf-8",
    )

    cfg = load_config(config_dir)
    assert cfg.env == {}
    assert cfg.post_create_shell is None
    assert cfg.post_create_commands == ["echo 'hello'"]
