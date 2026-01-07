"""Tests for statusline context creation."""

from __future__ import annotations

from pathlib import Path

from erk_shared.context.types import GlobalConfig
from erk_shared.gateway.erk_installation.fake import FakeErkInstallation
from erk_shared.gateway.graphite.disabled import GraphiteDisabled, GraphiteDisabledReason
from erk_shared.gateway.graphite.real import RealGraphite
from erk_statusline.context import resolve_graphite


class TestResolveGraphite:
    """Test resolve_graphite() helper function."""

    def test_no_config_returns_graphite_disabled(self) -> None:
        """When no config exists, should return GraphiteDisabled."""
        installation = FakeErkInstallation(config=None)

        result = resolve_graphite(installation)

        assert isinstance(result, GraphiteDisabled)
        assert result.reason == GraphiteDisabledReason.CONFIG_DISABLED

    def test_config_with_graphite_disabled_returns_graphite_disabled(self) -> None:
        """When config has use_graphite=false, should return GraphiteDisabled."""
        config = GlobalConfig(
            erk_root=Path("/fake/erk"),
            use_graphite=False,
            shell_setup_complete=True,
            show_pr_info=True,
            github_planning=True,
            fix_conflicts_require_dangerous_flag=True,
            show_hidden_commands=False,
        )
        installation = FakeErkInstallation(config=config)

        result = resolve_graphite(installation)

        assert isinstance(result, GraphiteDisabled)
        assert result.reason == GraphiteDisabledReason.CONFIG_DISABLED

    def test_config_with_graphite_enabled_but_not_installed_returns_not_installed(self) -> None:
        """When config has use_graphite=true but gt not installed, should return NOT_INSTALLED."""
        config = GlobalConfig(
            erk_root=Path("/fake/erk"),
            use_graphite=True,
            shell_setup_complete=True,
            show_pr_info=True,
            github_planning=True,
            fix_conflicts_require_dangerous_flag=True,
            show_hidden_commands=False,
        )
        installation = FakeErkInstallation(config=config)

        result = resolve_graphite(installation, gt_installed=False)

        assert isinstance(result, GraphiteDisabled)
        assert result.reason == GraphiteDisabledReason.NOT_INSTALLED

    def test_config_with_graphite_enabled_and_installed_returns_real_graphite(self) -> None:
        """When config has use_graphite=true and gt installed, should return RealGraphite."""
        config = GlobalConfig(
            erk_root=Path("/fake/erk"),
            use_graphite=True,
            shell_setup_complete=True,
            show_pr_info=True,
            github_planning=True,
            fix_conflicts_require_dangerous_flag=True,
            show_hidden_commands=False,
        )
        installation = FakeErkInstallation(config=config)

        result = resolve_graphite(installation, gt_installed=True)

        assert isinstance(result, RealGraphite)
