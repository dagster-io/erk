"""Tests for erk kit installer module.

These are Layer 4 tests (business logic over fakes) that verify kit
installation functionality with real filesystem operations in temporary
directories.
"""

from pathlib import Path

from erk.core.kit_installer import DEFAULT_KITS, install_erk_kits, sync_erk_kits


def test_install_erk_kits_creates_artifacts(tmp_path: Path) -> None:
    """Test that install_erk_kits creates Claude Code artifacts."""
    results = install_erk_kits(repo_root=tmp_path, use_graphite=False)

    # Should install default kits (no gt kit when use_graphite=False)
    assert len(results) >= len(DEFAULT_KITS)

    # Verify artifacts were created
    claude_dir = tmp_path / ".claude"
    assert claude_dir.exists()

    # Verify at least one kit was installed
    assert any(r.was_updated for r in results)


def test_install_erk_kits_includes_graphite_kit(tmp_path: Path) -> None:
    """Test that install_erk_kits includes gt kit when use_graphite=True."""
    results = install_erk_kits(repo_root=tmp_path, use_graphite=True)

    # Should include gt kit
    kit_ids = {r.kit_id for r in results}
    assert "gt" in kit_ids


def test_install_erk_kits_excludes_graphite_kit(tmp_path: Path) -> None:
    """Test that install_erk_kits excludes gt kit when use_graphite=False."""
    results = install_erk_kits(repo_root=tmp_path, use_graphite=False)

    # Should not include gt kit
    kit_ids = {r.kit_id for r in results}
    assert "gt" not in kit_ids


def test_install_erk_kits_graceful_on_nonexistent_dir(tmp_path: Path) -> None:
    """Test that install_erk_kits handles nonexistent directory gracefully."""
    nonexistent = tmp_path / "does-not-exist"

    # Should not raise exception, returns empty list
    results = install_erk_kits(repo_root=nonexistent, use_graphite=False)

    assert results == []


def test_sync_erk_kits_updates_kits(tmp_path: Path) -> None:
    """Test that sync_erk_kits updates installed kits."""
    # Install kits first
    install_erk_kits(repo_root=tmp_path, use_graphite=False)

    # Sync should update kits
    results = sync_erk_kits(repo_root=tmp_path)

    # Should have synced at least one kit
    assert len(results) > 0


def test_sync_erk_kits_no_config_returns_empty(tmp_path: Path) -> None:
    """Test that sync_erk_kits returns empty list when no config exists."""
    # No kits installed, so no dot-agent.toml
    results = sync_erk_kits(repo_root=tmp_path)

    assert results == []


def test_default_kits_constant() -> None:
    """Test that DEFAULT_KITS contains expected kits."""
    assert "erk" in DEFAULT_KITS
    assert "devrun" in DEFAULT_KITS
    assert "dignified-python" in DEFAULT_KITS
    assert "fake-driven-testing" in DEFAULT_KITS
    # gt is NOT in defaults (added conditionally)
    assert "gt" not in DEFAULT_KITS
