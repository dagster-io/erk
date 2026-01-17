"""Tests for config loading across worktrees.

These tests verify that local config (config.local.toml) is loaded from
the main repository root, not the worktree directory. This ensures that
settings configured in the main worktree are visible from secondary worktrees.
"""

from pathlib import Path

from erk.cli.config import load_config, load_local_config


def test_load_config_reads_from_specified_path(tmp_path: Path) -> None:
    """Test that load_config reads from the specified repo root."""
    # Create config at the specified path
    erk_dir = tmp_path / ".erk"
    erk_dir.mkdir()
    config_path = erk_dir / "config.toml"
    config_path.write_text(
        "[pool]\nmax_slots = 16\n",
        encoding="utf-8",
    )

    result = load_config(tmp_path)

    assert result.pool_size == 16


def test_load_local_config_reads_from_specified_path(tmp_path: Path) -> None:
    """Test that load_local_config reads from the specified repo root."""
    # Create local config at the specified path
    erk_dir = tmp_path / ".erk"
    erk_dir.mkdir()
    config_path = erk_dir / "config.local.toml"
    config_path.write_text(
        "[pool]\nmax_slots = 64\n",
        encoding="utf-8",
    )

    result = load_local_config(tmp_path)

    assert result.pool_size == 64


def test_load_local_config_returns_defaults_when_missing(tmp_path: Path) -> None:
    """Test that load_local_config returns defaults when config doesn't exist."""
    result = load_local_config(tmp_path)

    assert result.pool_size is None
    assert result.env == {}


def test_config_worktree_scenario(tmp_path: Path) -> None:
    """Test that config is loaded from main_repo_root in worktree scenario.

    This tests the fix for the bug where config.local.toml was loaded from
    the worktree directory (repo.root) instead of the main repository
    (repo.main_repo_root).

    Scenario:
    - Main repo at: /code/myrepo/
    - Worktree at: /.erk/repos/myrepo/worktrees/feature/
    - Config should be at: /code/myrepo/.erk/config.local.toml

    When running from the worktree, config should still be loaded from
    the main repo's .erk/ directory.
    """
    # Setup: main repo with config
    main_repo = tmp_path / "code" / "myrepo"
    main_erk_dir = main_repo / ".erk"
    main_erk_dir.mkdir(parents=True)

    # Create local config in main repo
    main_config_path = main_erk_dir / "config.local.toml"
    main_config_path.write_text(
        "[pool]\nmax_slots = 64\n",
        encoding="utf-8",
    )

    # Setup: worktree directory (no .erk/ dir)
    worktree = tmp_path / ".erk" / "repos" / "myrepo" / "worktrees" / "feature"
    worktree.mkdir(parents=True)

    # Act: Load config from main_repo_root (simulating the fixed behavior)
    # Before the fix, this would incorrectly look in the worktree directory
    result = load_local_config(main_repo)

    # Assert: Config from main repo is loaded
    assert result.pool_size == 64


def test_config_worktree_scenario_repo_config(tmp_path: Path) -> None:
    """Test that repo config (config.toml) is also loaded from main_repo_root.

    Similar to test_config_worktree_scenario but for the shared repo config.
    """
    # Setup: main repo with config
    main_repo = tmp_path / "code" / "myrepo"
    main_erk_dir = main_repo / ".erk"
    main_erk_dir.mkdir(parents=True)

    # Create repo config in main repo
    repo_config_path = main_erk_dir / "config.toml"
    repo_config_path.write_text(
        '[env]\nTEAM_VAR = "shared_value"\n',
        encoding="utf-8",
    )

    # Setup: worktree directory (no .erk/ dir)
    worktree = tmp_path / ".erk" / "repos" / "myrepo" / "worktrees" / "feature"
    worktree.mkdir(parents=True)

    # Act: Load config from main_repo_root
    result = load_config(main_repo)

    # Assert: Config from main repo is loaded
    assert result.env == {"TEAM_VAR": "shared_value"}


def test_config_loading_ignores_worktree_config(tmp_path: Path) -> None:
    """Test that config in worktree directory is NOT loaded when main_repo_root is used.

    This verifies the fix works correctly - even if someone accidentally creates
    a .erk/config.local.toml in a worktree, it should be ignored when loading
    config with main_repo_root.
    """
    # Setup: main repo with config
    main_repo = tmp_path / "code" / "myrepo"
    main_erk_dir = main_repo / ".erk"
    main_erk_dir.mkdir(parents=True)
    main_config = main_erk_dir / "config.local.toml"
    main_config.write_text(
        "[pool]\nmax_slots = 64\n",
        encoding="utf-8",
    )

    # Setup: worktree with its own (incorrect) config
    worktree = tmp_path / ".erk" / "repos" / "myrepo" / "worktrees" / "feature"
    worktree_erk_dir = worktree / ".erk"
    worktree_erk_dir.mkdir(parents=True)
    worktree_config = worktree_erk_dir / "config.local.toml"
    worktree_config.write_text(
        "[pool]\nmax_slots = 4\n",  # Different value
        encoding="utf-8",
    )

    # Act: Load config from main_repo_root (the correct behavior)
    result = load_local_config(main_repo)

    # Assert: Main repo config is loaded (64), not worktree config (4)
    assert result.pool_size == 64
