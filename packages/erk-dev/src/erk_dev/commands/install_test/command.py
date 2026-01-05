"""Docker-based installation testing for erk."""

import subprocess
from pathlib import Path

import click

from erk_dev.cli.output import machine_output, user_output


def get_repo_root() -> Path:
    """Get the erk repository root directory."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise click.ClickException("Not in a git repository")
    return Path(result.stdout.strip())


def get_install_test_dir() -> Path:
    """Get the dev/install-test directory path."""
    return get_repo_root() / "dev" / "install-test"


def get_fixtures_repos_dir() -> Path:
    """Get the fixtures/repos directory path."""
    return get_install_test_dir() / "fixtures" / "repos"


def run_docker_command(args: list[str], repo_root: Path) -> None:
    """Run a docker command with the erk source mounted."""
    cmd = [
        "docker",
        "run",
        "-it",
        "--rm",
        "-v",
        f"{repo_root}:/home/testuser/erk-source:ro",
        "erk-install-test",
        *args,
    ]
    subprocess.run(cmd, check=False)


@click.group(name="install-test")
def install_test_command() -> None:
    """Docker-based installation testing for erk.

    Test erk installation and upgrade scenarios in isolated Docker containers.
    Useful for catching "not on my machine" problems users hit when installing
    erk on repos that already have configuration.

    \b
    Quick start:
        erk-dev install-test build   # Build the Docker image (one-time)
        erk-dev install-test shell   # Interactive exploration
    """


@install_test_command.command(name="build")
def build() -> None:
    """Build the erk-install-test Docker image.

    This needs to be run once before using other install-test commands,
    and again whenever the Dockerfile or fixtures change.
    """
    install_test_dir = get_install_test_dir()
    if not install_test_dir.exists():
        raise click.ClickException(f"Install test directory not found: {install_test_dir}")

    user_output("Building erk-install-test Docker image...")
    subprocess.run(
        ["docker", "build", "-t", "erk-install-test", str(install_test_dir)],
        check=True,
    )
    user_output("Docker image built successfully.")


@install_test_command.command(name="shell")
def shell() -> None:
    """Start interactive shell in test container.

    Drops you into a shell where you can manually test erk installation.
    Helper functions are available:

    \b
      install_erk          - Install erk from mounted source
      setup_test_repo      - Create test repo with .erk config
      setup_repo_fixture   - Create test repo from repo fixture
      list_repo_fixtures   - List available repo fixtures
    """
    repo_root = get_repo_root()
    run_docker_command(["shell"], repo_root)


@install_test_command.command(name="fresh")
def fresh() -> None:
    """Test fresh install on repo with existing .erk config.

    Creates a test git repository with current .erk configuration,
    installs erk from source, and runs basic commands.
    Drops to shell for manual exploration afterward.
    """
    repo_root = get_repo_root()
    run_docker_command(["fresh"], repo_root)


@install_test_command.command(name="upgrade")
def upgrade() -> None:
    """Test upgrade scenario (from older config format).

    Note: Until erk is published to PyPI, this behaves the same as 'fresh'.
    Future: Install old version from PyPI first, then upgrade to source.
    """
    repo_root = get_repo_root()
    run_docker_command(["upgrade"], repo_root)


@install_test_command.command(name="repo")
@click.argument("name")
def repo(name: str) -> None:
    """Test with specific repo fixture.

    Creates a test repo configured like a specific repository (e.g., dagster-compass),
    installs erk from source, and runs basic commands.

    \b
    Example:
        erk-dev install-test repo dagster-compass
    """
    # Verify the fixture exists
    fixtures_dir = get_fixtures_repos_dir()
    fixture_path = fixtures_dir / name
    if not fixture_path.exists():
        available = list_available_repos()
        if available:
            repos_list = "\n  ".join(available)
            raise click.ClickException(
                f"Repo fixture '{name}' not found.\n\nAvailable fixtures:\n  {repos_list}"
            )
        else:
            raise click.ClickException(f"Repo fixture '{name}' not found. No fixtures available.")

    repo_root = get_repo_root()
    run_docker_command(["repo", name], repo_root)


def list_available_repos() -> list[str]:
    """List available repo fixtures."""
    fixtures_dir = get_fixtures_repos_dir()
    if not fixtures_dir.exists():
        return []
    return sorted(d.name for d in fixtures_dir.iterdir() if d.is_dir())


@install_test_command.command(name="list-repos")
def list_repos() -> None:
    """List available repo fixtures.

    Shows all repositories that have test fixtures configured.
    Use with 'erk-dev install-test repo <name>' to test specific repos.
    """
    repos = list_available_repos()
    if repos:
        user_output("Available repo fixtures:")
        for repo_name in repos:
            machine_output(f"  {repo_name}")
    else:
        user_output("No repo fixtures available.")
        user_output("Add fixtures in dev/install-test/fixtures/repos/")
