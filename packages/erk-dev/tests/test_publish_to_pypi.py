"""Tests for publish-to-pypi command."""

from pathlib import Path

from erk_dev.commands.publish_to_pypi.command import get_workspace_packages


def test_get_workspace_packages_returns_expected_packages(tmp_path: Path) -> None:
    """Verify get_workspace_packages returns the correct package list.

    This test ensures erk-sh-bootstrap is NOT included in the main release
    workflow (it has its own separate publishing process).
    """
    # Create minimal pyproject.toml files for validation
    (tmp_path / "pyproject.toml").write_text('version = "0.1.0"')
    packages_dir = tmp_path / "packages"

    for pkg in ["erk-shared", "erk-statusline"]:
        pkg_dir = packages_dir / pkg
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "pyproject.toml").write_text('version = "0.1.0"')

    packages = get_workspace_packages(tmp_path)
    package_names = [p.name for p in packages]

    # Verify expected packages are included
    assert "erk" in package_names
    assert "erk-shared" in package_names
    assert "erk-statusline" in package_names

    # Verify erk-sh-bootstrap is NOT included (separate release workflow)
    assert "erk-sh-bootstrap" not in package_names

    # Verify exact count (3 packages)
    assert len(packages) == 3
