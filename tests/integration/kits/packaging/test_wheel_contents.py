"""Integration tests for wheel packaging integrity.

These tests build an actual wheel package using `uv build` and verify that all
required data files are included. The wheel is built once per test session and
shared across all tests via a session-scoped fixture.

This is an integration test (Layer 5) because it:
- Executes real build system (uv build)
- Creates real filesystem artifacts
- Tests the complete packaging pipeline
"""

import subprocess
import zipfile
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def build_wheel(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build the wheel once per test session and return wheel path."""
    # Get the package directory (erk-kits)
    # From tests/integration/kits/packaging/ -> go up 5 levels to project root
    project_root = Path(__file__).parent.parent.parent.parent.parent
    package_dir = project_root / "packages" / "erk-kits"
    tmp_path = tmp_path_factory.mktemp("wheel_build")
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()

    # Run kit-build first to ensure artifacts are copied from source locations
    # This is required because artifact .md files are gitignored and only
    # populated by the build step
    subprocess.run(
        ["uv", "run", "erk", "dev", "kit-build"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=True,
    )

    # Build the wheel
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(dist_dir)],
        cwd=package_dir,
        capture_output=True,
        text=True,
        check=True,
    )

    # Find the wheel file
    wheel_files = list(dist_dir.glob("*.whl"))
    if not wheel_files:
        msg = f"No wheel file found in {dist_dir}"
        raise FileNotFoundError(msg)

    return wheel_files[0]


def test_wheel_contains_registry(build_wheel: Path) -> None:
    """Test that registry.yaml is included in the wheel."""
    with zipfile.ZipFile(build_wheel) as wheel:
        files = wheel.namelist()
        assert any("erk_kits/data/kits/registry.yaml" in f for f in files)


@pytest.mark.parametrize(
    "kit_name",
    ["erk"],
)
def test_wheel_contains_kit_yaml(build_wheel: Path, kit_name: str) -> None:
    """Test that each kit's kit.yaml is included in the wheel."""
    with zipfile.ZipFile(build_wheel) as wheel:
        files = wheel.namelist()
        expected_path = f"erk_kits/data/kits/{kit_name}/kit.yaml"
        assert any(expected_path in f for f in files), f"Missing {expected_path}"


@pytest.mark.parametrize(
    ("kit_name", "skill_name", "reference_file"),
    [
        ("erk", "gt-graphite", "gt-reference.md"),
    ],
)
def test_wheel_contains_skill_references(
    build_wheel: Path,
    kit_name: str,
    skill_name: str,
    reference_file: str,
) -> None:
    """Test that skill reference files are included in the wheel."""
    with zipfile.ZipFile(build_wheel) as wheel:
        files = wheel.namelist()
        expected_path = (
            f"erk_kits/data/kits/{kit_name}/skills/{skill_name}/references/{reference_file}"
        )
        assert any(expected_path in f for f in files), f"Missing {expected_path}"


@pytest.mark.parametrize(
    ("kit_name", "skill_name"),
    [
        ("erk", "gt-graphite"),
    ],
)
def test_wheel_contains_skill_markdown(
    build_wheel: Path,
    kit_name: str,
    skill_name: str,
) -> None:
    """Test that skill SKILL.md files are included in the wheel."""
    with zipfile.ZipFile(build_wheel) as wheel:
        files = wheel.namelist()
        expected_path = f"erk_kits/data/kits/{kit_name}/skills/{skill_name}/SKILL.md"
        assert any(expected_path in f for f in files), f"Missing {expected_path}"


@pytest.mark.parametrize(
    ("kit_name", "command_script"),
    [
        ("erk", "restack_preflight.py"),
        ("erk", "restack_continue.py"),
        ("erk", "restack_finalize.py"),
        ("erk", "quick_submit.py"),
    ],
)
def test_wheel_contains_scripts(
    build_wheel: Path,
    kit_name: str,
    command_script: str,
) -> None:
    """Test that kit CLI command scripts are included in the wheel."""
    with zipfile.ZipFile(build_wheel) as wheel:
        files = wheel.namelist()
        expected_path = f"erk_kits/data/kits/{kit_name}/scripts/{kit_name}/{command_script}"
        assert any(expected_path in f for f in files), f"Missing {expected_path}"


def test_wheel_contains_all_init_files(build_wheel: Path) -> None:
    """Test that all __init__.py files are included in data directories."""
    expected_init_files = [
        "erk_kits/data/__init__.py",
        "erk_kits/data/kits/__init__.py",
        "erk_kits/data/kits/erk/__init__.py",
    ]

    with zipfile.ZipFile(build_wheel) as wheel:
        files = wheel.namelist()
        for init_file in expected_init_files:
            assert any(init_file in f for f in files), f"Missing {init_file}"
