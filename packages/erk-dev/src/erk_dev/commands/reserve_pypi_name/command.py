"""Reserve PyPI package name command."""

import json
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path

import click

from erk_dev.cli.output import user_output

PYPI_README_TEXT = "This package name is reserved."


def validate_package_name(name: str) -> None:
    """Validate the provided package name against PyPI constraints."""
    if not name:
        user_output("✗ Package name cannot be empty")
        raise SystemExit(1)

    allowed_characters = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-")
    if not set(name).issubset(allowed_characters):
        user_output(f"✗ Invalid package name: {name}")
        user_output("  Name must contain only letters, digits, _, -, .")
        raise SystemExit(1)

    start_character = name[0]
    if start_character in "_-.":
        user_output(f"✗ Package name cannot start with: {start_character}")
        raise SystemExit(1)

    end_character = name[-1]
    if end_character in "_-.":
        user_output(f"✗ Package name cannot end with: {end_character}")
        raise SystemExit(1)


def module_name_from_package(package_name: str) -> str:
    """Create a valid module name from the package name."""
    module_name = package_name.replace("-", "_").replace(".", "_")
    if module_name[0].isdigit():
        module_name = f"pkg_{module_name}"
    return module_name


def ensure_command_available(command: str) -> None:
    """Ensure a required CLI command is available."""
    if shutil.which(command) is None:
        user_output(f"✗ Required command not found: {command}")
        user_output("  Install uv: https://github.com/astral-sh/uv")
        raise SystemExit(1)


def format_toml_string(value: str) -> str:
    """Render a TOML string literal with proper escaping."""
    return json.dumps(value)


def render_pyproject(package_name: str, module_name: str, description: str, version: str) -> str:
    """Render the pyproject.toml contents."""
    project_name = format_toml_string(package_name)
    escaped_description = format_toml_string(description)
    readme_text = format_toml_string(PYPI_README_TEXT)
    packages_value = format_toml_string(f"src/{module_name}")

    return (
        "[build-system]\n"
        'requires = ["hatchling"]\n'
        'build-backend = "hatchling.build"\n'
        "\n"
        "[project]\n"
        f"name = {project_name}\n"
        f'version = "{version}"\n'
        f"description = {escaped_description}\n"
        f'readme = {{text = {readme_text}, content-type = "text/plain"}}\n'
        'requires-python = ">=3.13"\n'
        "\n"
        "[tool.hatch.build.targets.wheel]\n"
        f"packages = [{packages_value}]\n"
    )


def render_init_py(version: str) -> str:
    """Render the contents of __init__.py."""
    return f'"""Reserved package name."""\n\n__version__ = "{version}"\n'


def write_project_files(
    project_dir: Path,
    module_name: str,
    package_name: str,
    description: str,
    version: str,
) -> None:
    """Create the minimal package structure."""
    src_dir = project_dir / "src" / module_name
    if src_dir.exists():
        user_output(f"✗ Temporary structure already exists: {src_dir}")
        raise SystemExit(1)

    src_dir.mkdir(parents=True)

    init_path = src_dir / "__init__.py"
    init_path.write_text(render_init_py(version), encoding="utf-8")

    pyproject_path = project_dir / "pyproject.toml"
    pyproject_content = render_pyproject(package_name, module_name, description, version)
    pyproject_path.write_text(pyproject_content, encoding="utf-8")


def run_command(command: list[str], cwd: Path, description: str) -> None:
    """Run a subprocess command with error reporting."""
    if not cwd.exists():
        user_output(f"✗ Working directory does not exist: {cwd}")
        raise SystemExit(1)

    user_output(f"  ▶ {description}: {shlex.join(command)}")
    subprocess.run(command, check=True, cwd=cwd)


def build_package(project_dir: Path) -> list[Path]:
    """Build package artifacts using uv build."""
    dist_dir = project_dir / "dist"
    if dist_dir.exists() and dist_dir.is_dir():
        shutil.rmtree(dist_dir)

    run_command(["uv", "build"], project_dir, "uv build")

    if not dist_dir.exists():
        user_output("✗ Build completed but dist directory not found")
        raise SystemExit(1)

    artifacts = sorted(dist_dir.glob("*"))
    if not artifacts:
        user_output("✗ No artifacts produced by build")
        raise SystemExit(1)

    return artifacts


def publish_artifacts(project_dir: Path, artifacts: list[Path]) -> None:
    """Publish built artifacts to PyPI using uvx uv-publish."""
    if not artifacts:
        user_output("✗ No artifacts available for publishing")
        raise SystemExit(1)

    publish_command = ["uvx", "uv-publish"] + [str(artifact) for artifact in artifacts]
    run_command(publish_command, project_dir / "dist", "uvx uv-publish")


def confirm_publish(name: str, force: bool) -> None:
    """Prompt for confirmation before publishing."""
    if force:
        return

    message = f"This will publish a minimal package named '{name}' to PyPI.\nContinue?"
    if not click.confirm(message, default=False):
        user_output("Aborted by user.")
        raise SystemExit(1)


@click.command(name="reserve-pypi-name")
@click.option("--name", required=True, help="Package name to reserve")
@click.option(
    "--description",
    default="Reserved package name",
    show_default=True,
    help="Package description",
)
@click.option(
    "--version",
    default="0.0.1",
    show_default=True,
    help="Package version to publish",
)
@click.option("--dry-run", is_flag=True, help="Show operations without publishing")
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
def reserve_pypi_name_command(
    name: str, description: str, version: str, dry_run: bool, force: bool
) -> None:
    """Reserve a package name on PyPI by publishing a placeholder package."""
    validate_package_name(name)
    module_name = module_name_from_package(name)

    ensure_command_available("uv")
    ensure_command_available("uvx")

    if dry_run:
        user_output(f"[DRY RUN] Would reserve PyPI package name '{name}' version '{version}'")
        user_output(
            f"[DRY RUN] Would create temporary project structure with module '{module_name}'"
        )
        user_output("[DRY RUN] Would write pyproject.toml and __init__.py")
        user_output("[DRY RUN] Would run: uv build")
        user_output("[DRY RUN] Would run: uvx uv-publish <artifacts>")
        user_output("[DRY RUN] Would remove temporary directory after completion")
        user_output(f"[DRY RUN] PyPI project URL: https://pypi.org/project/{name}/")
        return

    confirm_publish(name, force)

    with tempfile.TemporaryDirectory(prefix="reserve-pypi-name-") as temp_dir:
        project_dir = Path(temp_dir)
        user_output(f"Creating temporary project at {project_dir}")
        write_project_files(project_dir, module_name, name, description, version)

        user_output("Building package artifacts...")
        artifacts = build_package(project_dir)

        user_output("Publishing artifacts to PyPI...")
        publish_artifacts(project_dir, artifacts)

    user_output(f"✓ Reserved PyPI package name '{name}'.")
    user_output(f"  View project: https://pypi.org/project/{name}/")
