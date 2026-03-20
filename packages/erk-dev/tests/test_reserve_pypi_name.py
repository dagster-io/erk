"""Tests for the reserve_pypi_name helpers."""

from pathlib import Path

import pytest

from erk_dev.commands.reserve_pypi_name import command as reserve_command


def test_validate_package_name_accepts_valid_name() -> None:
    """Valid package names should pass validation."""
    reserve_command.validate_package_name("example-package")


def test_validate_package_name_rejects_invalid_characters() -> None:
    """Invalid characters should raise SystemExit."""
    with pytest.raises(SystemExit):
        reserve_command.validate_package_name("invalid$name")


def test_validate_package_name_rejects_starting_punctuation() -> None:
    """Names starting with punctuation should be rejected."""
    with pytest.raises(SystemExit):
        reserve_command.validate_package_name("-example")


def test_module_name_from_package_converts_hyphenated_names() -> None:
    """Hyphenated package names should be converted to valid module names."""
    result = reserve_command.module_name_from_package("my-package.name")
    assert result == "my_package_name"


def test_module_name_from_package_prefixes_numeric_start() -> None:
    """Names starting with digits should be prefixed for module usage."""
    result = reserve_command.module_name_from_package("123package")
    assert result == "pkg_123package"


def test_render_pyproject_contains_required_fields() -> None:
    """Rendered pyproject.toml should include expected metadata."""
    content = reserve_command.render_pyproject("demo", "demo_pkg", "Reserved description", "0.0.1")
    assert 'name = "demo"' in content
    assert 'version = "0.0.1"' in content
    assert 'description = "Reserved description"' in content
    assert 'packages = ["src/demo_pkg"]' in content


def test_render_pyproject_uses_provided_version() -> None:
    """Rendered pyproject.toml should use the specified version."""
    content = reserve_command.render_pyproject("demo", "demo_pkg", "Reserved description", "0.0.2")
    assert 'version = "0.0.2"' in content


def test_write_project_files_creates_structure(tmp_path: Path) -> None:
    """write_project_files should create src structure and pyproject.toml."""
    reserve_command.write_project_files(tmp_path, "demo_pkg", "demo", "A description", "0.0.1")

    init_path = tmp_path / "src" / "demo_pkg" / "__init__.py"
    pyproject_path = tmp_path / "pyproject.toml"

    assert init_path.exists()
    assert pyproject_path.exists()

    init_content = init_path.read_text(encoding="utf-8")
    pyproject_content = pyproject_path.read_text(encoding="utf-8")

    assert '__version__ = "0.0.1"' in init_content
    assert 'name = "demo"' in pyproject_content


def test_write_project_files_uses_provided_version(tmp_path: Path) -> None:
    """write_project_files should use the specified version in generated files."""
    reserve_command.write_project_files(tmp_path, "demo_pkg", "demo", "A description", "0.0.2")

    init_content = (tmp_path / "src" / "demo_pkg" / "__init__.py").read_text(encoding="utf-8")
    pyproject_content = (tmp_path / "pyproject.toml").read_text(encoding="utf-8")

    assert '__version__ = "0.0.2"' in init_content
    assert 'version = "0.0.2"' in pyproject_content


def test_write_project_files_fails_if_structure_exists(tmp_path: Path) -> None:
    """Existing src directory should trigger SystemExit."""
    (tmp_path / "src" / "demo_pkg").mkdir(parents=True)

    with pytest.raises(SystemExit):
        reserve_command.write_project_files(tmp_path, "demo_pkg", "demo", "A description", "0.0.1")
