"""Tests for erk-sh-bootstrap CLI."""

from __future__ import annotations

from pathlib import Path

import pytest
from erk_sh_bootstrap.cli import ErkNotFound, find_local_erk


class TestFindLocalErk:
    """Test find_local_erk() function."""

    def test_finds_erk_in_cwd_venv(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should find erk in .venv/bin/erk in current directory."""
        venv_bin = tmp_path / ".venv" / "bin"
        venv_bin.mkdir(parents=True)
        erk_path = venv_bin / "erk"
        erk_path.touch()

        monkeypatch.chdir(tmp_path)

        result = find_local_erk()

        assert result == str(erk_path)

    def test_finds_erk_in_parent_venv(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should find erk in parent directory's .venv/bin/erk."""
        venv_bin = tmp_path / ".venv" / "bin"
        venv_bin.mkdir(parents=True)
        erk_path = venv_bin / "erk"
        erk_path.touch()

        subdir = tmp_path / "src" / "mypackage"
        subdir.mkdir(parents=True)
        monkeypatch.chdir(subdir)

        result = find_local_erk()

        assert result == str(erk_path)

    def test_prefers_closer_venv(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should prefer the closest .venv when multiple exist."""
        # Create parent venv
        parent_venv_bin = tmp_path / ".venv" / "bin"
        parent_venv_bin.mkdir(parents=True)
        parent_erk = parent_venv_bin / "erk"
        parent_erk.touch()

        # Create child venv
        child_dir = tmp_path / "child"
        child_venv_bin = child_dir / ".venv" / "bin"
        child_venv_bin.mkdir(parents=True)
        child_erk = child_venv_bin / "erk"
        child_erk.touch()

        monkeypatch.chdir(child_dir)

        result = find_local_erk()

        assert result == str(child_erk)

    def test_finds_venv_named_venv(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should find erk in venv/bin/erk (alternative naming)."""
        venv_bin = tmp_path / "venv" / "bin"
        venv_bin.mkdir(parents=True)
        erk_path = venv_bin / "erk"
        erk_path.touch()

        monkeypatch.chdir(tmp_path)

        result = find_local_erk()

        assert result == str(erk_path)

    def test_prefers_dot_venv_over_venv(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should prefer .venv over venv when both exist."""
        # Create .venv
        dot_venv_bin = tmp_path / ".venv" / "bin"
        dot_venv_bin.mkdir(parents=True)
        dot_venv_erk = dot_venv_bin / "erk"
        dot_venv_erk.touch()

        # Create venv
        venv_bin = tmp_path / "venv" / "bin"
        venv_bin.mkdir(parents=True)
        venv_erk = venv_bin / "erk"
        venv_erk.touch()

        monkeypatch.chdir(tmp_path)

        result = find_local_erk()

        assert result == str(dot_venv_erk)

    def test_returns_not_found_when_no_venv_found(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should return ErkNotFound(venv_found=False) when no venv exists."""
        monkeypatch.chdir(tmp_path)

        result = find_local_erk()

        assert result == ErkNotFound(venv_found=False)

    def test_returns_not_found_when_venv_exists_but_no_erk(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should return ErkNotFound(venv_found=True) when venv exists but has no erk binary."""
        venv_bin = tmp_path / ".venv" / "bin"
        venv_bin.mkdir(parents=True)

        monkeypatch.chdir(tmp_path)

        result = find_local_erk()

        assert result == ErkNotFound(venv_found=True)

    def test_erk_venv_env_override(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should use ERK_VENV environment variable when set."""
        # Create regular venv
        regular_venv_bin = tmp_path / ".venv" / "bin"
        regular_venv_bin.mkdir(parents=True)
        regular_erk = regular_venv_bin / "erk"
        regular_erk.touch()

        # Create custom venv
        custom_venv = tmp_path / "custom-venv"
        custom_venv_bin = custom_venv / "bin"
        custom_venv_bin.mkdir(parents=True)
        custom_erk = custom_venv_bin / "erk"
        custom_erk.touch()

        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("ERK_VENV", str(custom_venv))

        result = find_local_erk()

        assert result == str(custom_erk)

    def test_erk_venv_env_invalid_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should fall back to search when ERK_VENV points to invalid path."""
        # Create regular venv
        regular_venv_bin = tmp_path / ".venv" / "bin"
        regular_venv_bin.mkdir(parents=True)
        regular_erk = regular_venv_bin / "erk"
        regular_erk.touch()

        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("ERK_VENV", "/nonexistent/venv")

        result = find_local_erk()

        assert result == str(regular_erk)

    def test_erk_venv_env_no_erk_binary(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Should fall back to search when ERK_VENV exists but has no erk binary."""
        # Create regular venv
        regular_venv_bin = tmp_path / ".venv" / "bin"
        regular_venv_bin.mkdir(parents=True)
        regular_erk = regular_venv_bin / "erk"
        regular_erk.touch()

        # Create custom venv without erk
        custom_venv = tmp_path / "custom-venv"
        custom_venv_bin = custom_venv / "bin"
        custom_venv_bin.mkdir(parents=True)

        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("ERK_VENV", str(custom_venv))

        result = find_local_erk()

        assert result == str(regular_erk)
