"""Context store utility commands."""

import asyncio
import shutil
import subprocess
import tempfile
from pathlib import Path

import click
from dotenv import find_dotenv, load_dotenv

from csbot.contextengine.contextstore_protocol import ContextStore
from csbot.contextengine.diff import compute_diff
from csbot.contextengine.loader import load_context_store
from csbot.contextengine.protocol import ReadOnlyContextStoreManager
from csbot.contextengine.serializer import serialize_context_store
from csbot.local_context_store.git.file_tree import FilesystemFileTree
from csbot.local_context_store.github.config import GithubConfig
from csbot.slackbot.slackbot_core import CompassBotServerConfig, load_bot_server_config_from_yaml
from csbot.slackbot.usercron.storage import UserCronStorage


class SimpleContextStore:
    """Simple context store wrapper for CLI commands."""

    def __init__(self, context_store: ContextStore):
        self._context_store = context_store

    async def get_context_store(self) -> ContextStore:
        return self._context_store


def load_bot_config(config_path: str) -> CompassBotServerConfig:
    """Load bot configuration from YAML file."""
    load_dotenv(find_dotenv(usecwd=True), override=True)

    p = Path(config_path)
    config_yaml = p.read_text(encoding="utf-8")
    bot_config = load_bot_server_config_from_yaml(config_yaml, p.parent.absolute())
    return bot_config


def clone_repo_if_needed(repo_name: str, target_dir: Path, github_token: str | None = None) -> Path:
    """Clone a repository if it doesn't exist.

    Args:
        repo_name: Repository name in format 'owner/repo'
        target_dir: Target directory for cloned repositories
        github_token: Optional GitHub token for authentication

    Returns:
        Path to the cloned repository

    Raises:
        click.Abort: If cloning fails
    """
    if "/" not in repo_name:
        click.echo(f"❌ Invalid repo format: {repo_name} (expected owner/repo)", err=True)
        raise click.Abort()

    # Determine target path
    repo_target = target_dir / repo_name.split("/")[-1]

    # Check if already exists
    if repo_target.exists():
        click.echo(f"✅ Repository already exists at {repo_target}")
        return repo_target

    # Clone the repository
    click.echo(f"📥 Cloning {repo_name}...")

    try:
        # Build git clone URL
        if github_token:
            git_url = f"https://{github_token}@github.com/{repo_name}.git"
        else:
            git_url = f"git@github.com:{repo_name}.git"

        # Create parent directory
        repo_target.parent.mkdir(parents=True, exist_ok=True)

        # Clone with shallow depth for faster cloning
        result = subprocess.run(
            ["git", "clone", "--depth", "1", git_url, str(repo_target)],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0:
            click.echo(f"   ✅ Successfully cloned to {repo_target}")
            return repo_target
        else:
            error_msg = result.stderr.strip() or result.stdout.strip()
            click.echo(f"   ❌ Failed: {error_msg}", err=True)
            raise click.Abort()

    except subprocess.TimeoutExpired:
        click.echo("   ❌ Timeout: Clone took longer than 60 seconds", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"   ❌ Error: {e}", err=True)
        raise click.Abort()


def resolve_path_or_org(path_or_org: str, config_file: str | None = None) -> Path:
    """Resolve path_or_org to a Path.

    If path_or_org is an existing directory, returns it as-is.
    Otherwise, treats it as an org name and clones dagster-compass/<org>.

    Args:
        path_or_org: Either a file path or an org name
        config_file: Optional bot config file for GitHub authentication

    Returns:
        Path to the context store repository
    """
    path_obj = Path(path_or_org)
    if path_obj.exists() and path_obj.is_dir():
        return path_obj

    # Treat as org name - clone dagster-compass/<org>
    repo_name = f"dagster-compass/{path_or_org}"
    target_dir = Path.home() / ".compass" / "repos"

    # Get GitHub token if config provided
    github_token = None
    if config_file:
        try:
            bot_config = load_bot_config(config_file)
            auth_source = bot_config.github.get_auth_source()
            github_token = auth_source.get_token()
        except Exception as e:
            click.echo(f"⚠️  Could not load GitHub token from config: {e}", err=True)
            raise click.Abort()

    return clone_repo_if_needed(repo_name, target_dir, github_token)


@click.group()
def context_store():
    """Context store utility commands."""
    pass


@context_store.command()
@click.option(
    "--config-file",
    required=True,
    help="Path to bot configuration YAML file",
)
@click.option(
    "--repos-file",
    required=True,
    help="Path to file containing GitHub repo names (one per line, format: owner/repo)",
)
def check_project_files(config_file: str, repos_file: str):
    """Check if contextstore_project.yaml exists in GitHub repositories.

    This command reads a file containing GitHub repository names (one per line)
    and checks if each repository has a contextstore_project.yaml file.
    Reports any repositories that are missing this file.

    Example:
        compass-dev context-store check-project-files \\
            --config-file local.csbot.config.yaml \\
            --repos-file repos.txt
    """
    # Load bot config
    bot_config = load_bot_config(config_file)
    auth_source = bot_config.github.get_auth_source()
    github_client = auth_source.get_github_client()

    # Read repos from file
    repos_path = Path(repos_file)
    if not repos_path.exists():
        click.echo(f"Error: File not found: {repos_file}", err=True)
        return

    repo_names = [
        line.strip() for line in repos_path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]

    if not repo_names:
        click.echo("No repositories found in file", err=True)
        return

    click.echo(f"📊 Checking {len(repo_names)} repositories for contextstore_project.yaml")
    click.echo("=" * 60)
    click.echo()

    missing_repos = []
    found_repos = []
    error_repos = []

    for repo_name in repo_names:
        try:
            repo = github_client.get_repo(repo_name)
            try:
                # Check if file exists by trying to get its contents
                repo.get_contents("contextstore_project.yaml")
                found_repos.append(repo_name)
                click.echo(f"✅ {repo_name} - File exists")
            except Exception:
                # File doesn't exist
                missing_repos.append(repo_name)
                click.echo(f"❌ {repo_name} - File missing")
        except Exception as e:
            error_repos.append((repo_name, str(e)))
            click.echo(f"⚠️  {repo_name} - Error: {e}", err=True)

    # Summary
    click.echo()
    click.echo("=" * 60)
    click.echo("📋 Summary")
    click.echo(f"Total repositories: {len(repo_names)}")
    click.echo(f"✅ Found: {len(found_repos)}")
    click.echo(f"❌ Missing: {len(missing_repos)}")
    click.echo(f"⚠️  Errors: {len(error_repos)}")

    if missing_repos:
        click.echo()
        click.echo("Repositories missing contextstore_project.yaml:")
        for repo in missing_repos:
            click.echo(f"  - {repo}")

    if error_repos:
        click.echo()
        click.echo("Repositories with errors:")
        for repo, error in error_repos:
            click.echo(f"  - {repo}: {error}")


@context_store.command()
@click.argument("path_or_org", type=str)
@click.option(
    "--show-diffs",
    is_flag=True,
    help="Show detailed content differences for files that differ",
)
@click.option(
    "--copy-reserialized",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    help="Copy the reserialized directory to the specified path for further inspection",
)
@click.option(
    "--config-file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help="Optional bot config file for GitHub authentication (for cloning org repos)",
)
@click.option("--load-only", is_flag=True, help="Only load and display the repo")
def inspect(
    path_or_org: str,
    show_diffs: bool,
    copy_reserialized: Path | None,
    config_file: str | None,
    load_only: bool,
):
    """Inspect a context store at the given path or org name.

    This command accepts either:
    - A file path to a local context store repository
    - An org name (will clone dagster-compass/<org> to ~/.compass/repos/<org>)

    This command:
    1. Loads the context store from the given path
    2. Pretty prints its contents
    3. Creates a temporary copy of the repository
    4. Re-serializes the context store to the temp directory
    5. Reports any differences between original and re-serialized versions
    6. Optionally copies the reserialized version for further inspection

    Examples:
        compass-dev context-store inspect /path/to/context-store
        compass-dev context-store inspect prod --show-diffs
        compass-dev context-store inspect dev --copy-reserialized /tmp/reserialized
    """
    path = resolve_path_or_org(path_or_org, config_file)

    click.echo(f"🔍 Inspecting context store at: {path}")
    click.echo("=" * 80)
    click.echo()

    # Step 1: Load the context store
    try:
        tree = FilesystemFileTree(path)
        context_store = load_context_store(tree)
        click.echo("✅ Successfully loaded context store")
    except Exception as e:
        click.echo(f"❌ Error loading context store: {e}", err=True)
        raise click.Abort()

    # Step 2: Pretty print the context store
    click.echo()
    click.echo("📊 Context Store Contents")
    click.echo("-" * 80)

    # Print project info
    click.echo(f"\n🏢 Project: {context_store.project.project_name}")
    click.echo(f"   Version: {context_store.project.version}")
    if context_store.project.teams:
        click.echo(f"   Teams: {len(context_store.project.teams)}")
        for team_name, members in context_store.project.teams.items():
            click.echo(f"     - {team_name}: {len(members)} members")

    # Print system prompt
    if context_store.system_prompt:
        click.echo(f"\n📝 System Prompt: {len(context_store.system_prompt)} characters")

    # Print datasets
    click.echo(f"\n📊 Datasets: {len(context_store.datasets)}")
    if context_store.datasets:
        by_connection = {}
        for dataset, _ in context_store.datasets:
            if dataset.connection not in by_connection:
                by_connection[dataset.connection] = []
            by_connection[dataset.connection].append(dataset.table_name)

        for connection, tables in sorted(by_connection.items()):
            click.echo(f"   {connection}: {len(tables)} tables")
            for table in sorted(tables):
                click.echo(f"     - {table}")

    # Print general context
    click.echo(f"\n📚 General Context: {len(context_store.general_context)} entries")
    if context_store.general_context:
        by_group = {}
        for named_context in context_store.general_context:
            if named_context.group not in by_group:
                by_group[named_context.group] = []
            by_group[named_context.group].append(named_context.name)

        for group, names in sorted(by_group.items()):
            click.echo(f"   {group}: {len(names)} entries")
            for name in sorted(names):
                click.echo(f"     - {name}")

    # Print general cronjobs
    click.echo(f"\n⏰ General Cron Jobs: {len(context_store.general_cronjobs)}")
    for name, job in sorted(context_store.general_cronjobs.items()):
        # Handle potential surrogate characters in strings
        thread_safe = job.thread.encode("utf-8", errors="replace").decode("utf-8", errors="replace")
        click.echo(f"   {name}:")
        click.echo(f"     - cron: {job.cron}")
        click.echo(f"     - thread: {thread_safe}")

    # Print channels
    click.echo(f"\n📢 Channels: {len(context_store.channels)}")
    for channel_name, channel_context in sorted(context_store.channels.items()):
        click.echo(f"   {channel_name}:")
        if channel_context.system_prompt:
            click.echo(f"     - system_prompt: {len(channel_context.system_prompt)} characters")
        click.echo(f"     - context: {len(channel_context.context)} entries")
        click.echo(f"     - cron_jobs: {len(channel_context.cron_jobs)}")

    if load_only:
        return

    # Step 3: Create temp directory and copy original repo
    click.echo()
    click.echo("🔄 Round-trip Test")
    click.echo("-" * 80)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        original_copy = temp_path / "original"
        reserialized_copy = temp_path / "reserialized"

        # Copy original
        click.echo(f"📁 Copying original to: {original_copy}")
        shutil.copytree(path, original_copy)

        # Step 4: Re-serialize to temp directory
        click.echo(f"💾 Re-serializing to: {reserialized_copy}")
        reserialized_copy.mkdir()
        try:
            serialize_context_store(context_store, reserialized_copy)
            click.echo("✅ Re-serialization successful")
        except Exception as e:
            click.echo(f"❌ Error re-serializing: {e}", err=True)
            raise click.Abort()

        # Step 5: Compare directories
        click.echo()
        click.echo("🔍 Comparing original vs re-serialized...")

        # Files to ignore in comparison
        ignored_files = {Path(".gitignore"), Path("README.md")}

        original_files = set()
        for item in original_copy.rglob("*"):
            if item.is_file() and ".git" not in item.parts:
                rel_path = item.relative_to(original_copy)
                # Ignore specific files and any file named .gitkeep
                if rel_path not in ignored_files and item.name != ".gitkeep":
                    original_files.add(rel_path)

        reserialized_files = set()
        for item in reserialized_copy.rglob("*"):
            if item.is_file():
                rel_path = item.relative_to(reserialized_copy)
                # Ignore specific files and any file named .gitkeep
                if rel_path not in ignored_files and item.name != ".gitkeep":
                    reserialized_files.add(rel_path)

        # Check for file structure differences
        only_in_original_set = original_files - reserialized_files
        only_in_reserialized_set = reserialized_files - original_files

        # Check for content differences in common files
        content_diffs = []
        common_files = original_files & reserialized_files
        for file in sorted(common_files):
            file1_path = original_copy / file
            file2_path = reserialized_copy / file

            content1 = file1_path.read_text()
            content2 = file2_path.read_text()

            if content1 != content2:
                content_diffs.append(file)

        # Report results
        if not only_in_original_set and not only_in_reserialized_set and not content_diffs:
            click.echo("✅ No differences found! Round-trip successful.")
        else:
            click.echo("⚠️  DIFFERENCES FOUND")

            if only_in_original_set:
                click.echo(f"  Files only in original ({len(only_in_original_set)}):")
                for file in sorted(only_in_original_set):
                    click.echo(f"    - {file}")

            if only_in_reserialized_set:
                click.echo(f"  Files only in reserialized ({len(only_in_reserialized_set)}):")
                for file in sorted(only_in_reserialized_set):
                    click.echo(f"    - {file}")

            if content_diffs:
                click.echo(f"  Files with different content ({len(content_diffs)}):")
                for file in content_diffs:
                    click.echo(f"    - {file}")

                    # Show detailed diff if requested
                    if show_diffs:
                        import difflib

                        file1_path = original_copy / file
                        file2_path = reserialized_copy / file

                        content1 = file1_path.read_text()
                        content2 = file2_path.read_text()
                        lines1 = content1.splitlines()
                        lines2 = content2.splitlines()

                        diff_lines = list(
                            difflib.unified_diff(
                                lines1,
                                lines2,
                                fromfile=f"original/{file}",
                                tofile=f"reserialized/{file}",
                                lineterm="",
                            )
                        )
                        if diff_lines:
                            for diff_line in diff_lines[:50]:
                                click.echo(f"      {diff_line}")
                            if len(diff_lines) > 50:
                                click.echo(f"      ... ({len(diff_lines) - 50} more lines)")

        # Copy reserialized directory if requested
        if copy_reserialized:
            click.echo()
            click.echo(f"📁 Copying reserialized directory to: {copy_reserialized}")
            try:
                if copy_reserialized.exists():
                    click.echo("   ⚠️  Target directory already exists, removing it first...")
                    shutil.rmtree(copy_reserialized)
                shutil.copytree(reserialized_copy, copy_reserialized)
                click.echo(f"   ✅ Successfully copied to {copy_reserialized}")
            except Exception as e:
                click.echo(f"   ❌ Error copying: {e}", err=True)

    click.echo()
    click.echo("=" * 80)
    click.echo("✅ Inspection complete")


def _compare_directories(dir1: Path, dir2: Path, show_diffs: bool = False) -> list[str]:
    """Compare two directories and return a list of differences.

    Args:
        dir1: First directory to compare
        dir2: Second directory to compare
        show_diffs: If True, show detailed content differences for differing files

    Returns:
        List of difference descriptions
    """
    differences = []

    # Files to ignore in comparison
    ignored_files = {Path(".gitignore"), Path("README.md")}

    # Get all files in both directories (relative paths)
    def get_all_files(directory: Path) -> set[Path]:
        files = set()
        for item in directory.rglob("*"):
            if item.is_file() and ".git" not in item.parts:
                rel_path = item.relative_to(directory)
                # Ignore specific files and any file named .gitkeep
                if rel_path not in ignored_files and rel_path.name != ".gitkeep":
                    files.add(rel_path)
        return files

    files1 = get_all_files(dir1)
    files2 = get_all_files(dir2)

    # Files only in dir1
    only_in_1 = files1 - files2
    for file in sorted(only_in_1):
        differences.append(f"❌ File only in original: {file}")

    # Files only in dir2
    only_in_2 = files2 - files1
    for file in sorted(only_in_2):
        differences.append(f"➕ File only in reserialized: {file}")

    # Files in both - compare contents
    common_files = files1 & files2
    for file in sorted(common_files):
        file1_path = dir1 / file
        file2_path = dir2 / file

        content1 = file1_path.read_text()
        content2 = file2_path.read_text()

        if content1 != content2:
            differences.append(f"📝 Content differs: {file}")
            # Show line-by-line diff summary
            lines1 = content1.splitlines()
            lines2 = content2.splitlines()
            if len(lines1) != len(lines2):
                differences.append(
                    f"   Lines: {len(lines1)} (original) vs {len(lines2)} (reserialized)"
                )

            # Show detailed diff if requested
            if show_diffs:
                import difflib

                diff_lines = list(
                    difflib.unified_diff(
                        lines1,
                        lines2,
                        fromfile=f"original/{file}",
                        tofile=f"reserialized/{file}",
                        lineterm="",
                    )
                )
                if diff_lines:
                    differences.append("   Diff:")
                    for diff_line in diff_lines[:50]:  # Limit to first 50 lines
                        differences.append(f"   {diff_line}")
                    if len(diff_lines) > 50:
                        differences.append(f"   ... ({len(diff_lines) - 50} more lines)")

    return differences


@context_store.command()
@click.argument(
    "repos_file", type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path)
)
@click.option(
    "--target-dir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=Path.home() / ".compass" / "repos",
    help="Target directory for cloned repositories (default: ~/.compass/repos)",
)
@click.option(
    "--config-file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help="Optional bot config file for GitHub authentication (uses git default if not provided)",
)
def clone_repos(repos_file: Path, target_dir: Path, config_file: str | None):
    """Clone multiple context store repositories from a file.

    This command reads a file containing repository names (one per line, format: owner/repo)
    and clones them into the specified target directory.

    Example repos file content:
        dagster-compass/dev
        dagster-compass/prod
        my-org/data-context

    Example:
        compass-dev context-store clone-repos repos.txt
        compass-dev context-store clone-repos repos.txt --target-dir /custom/path
        compass-dev context-store clone-repos repos.txt --config-file local.csbot.config.yaml
    """
    # Read repos from file
    if not repos_file.exists():
        click.echo(f"❌ File not found: {repos_file}", err=True)
        raise click.Abort()

    repo_names = [
        line.strip()
        for line in repos_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

    if not repo_names:
        click.echo("❌ No repositories found in file", err=True)
        raise click.Abort()

    # Create target directory
    target_dir.mkdir(parents=True, exist_ok=True)

    # Get GitHub authentication if config provided
    github_token = None
    if config_file:
        try:
            bot_config = load_bot_config(config_file)
            auth_source = bot_config.github.get_auth_source()
            github_token = auth_source.get_token()
        except Exception as e:
            click.echo(f"⚠️  Could not load GitHub token from config: {e}", err=True)
            raise

    click.echo(f"📦 Cloning {len(repo_names)} repositories to: {target_dir}")
    click.echo("=" * 80)
    click.echo()

    successful = []
    failed = []
    skipped = []

    for repo_name in repo_names:
        # Parse owner/repo format
        if "/" not in repo_name:
            click.echo(f"⚠️  Skipping invalid repo format: {repo_name}", err=True)
            failed.append((repo_name, "Invalid format (expected owner/repo)"))
            continue

        # Determine target path
        repo_target = target_dir / repo_name.split("/")[-1]

        # Check if already exists
        if repo_target.exists():
            click.echo(f"⏭️  {repo_name} - Already exists, skipping")
            skipped.append(repo_name)
            continue

        # Clone the repository
        click.echo(f"📥 Cloning {repo_name}...")

        try:
            # Build git clone URL
            if github_token:
                # Use token authentication
                git_url = f"https://{github_token}@github.com/{repo_name}.git"
            else:
                # Use default git authentication (SSH or HTTPS depending on git config)
                git_url = f"git@github.com:{repo_name}.git"

            # Create parent directory
            repo_target.parent.mkdir(parents=True, exist_ok=True)

            # Clone with shallow depth for faster cloning
            result = subprocess.run(
                ["git", "clone", "--depth", "1", git_url, str(repo_target)],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                click.echo(f"   ✅ Successfully cloned to {repo_target}")
                successful.append(repo_name)
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                click.echo(f"   ❌ Failed: {error_msg}", err=True)
                failed.append((repo_name, error_msg))

        except subprocess.TimeoutExpired:
            click.echo("   ❌ Timeout: Clone took longer than 60 seconds", err=True)
            failed.append((repo_name, "Timeout after 60 seconds"))
        except Exception as e:
            click.echo(f"   ❌ Error: {e}", err=True)
            failed.append((repo_name, str(e)))

    # Summary
    click.echo()
    click.echo("=" * 80)
    click.echo("📋 Summary")
    click.echo(f"Total repositories: {len(repo_names)}")
    click.echo(f"✅ Successfully cloned: {len(successful)}")
    click.echo(f"⏭️  Skipped (already exist): {len(skipped)}")
    click.echo(f"❌ Failed: {len(failed)}")

    if successful:
        click.echo()
        click.echo("Successfully cloned:")
        for repo in successful:
            click.echo(f"  ✓ {repo}")

    if skipped:
        click.echo()
        click.echo("Skipped (already exist):")
        for repo in skipped:
            click.echo(f"  ⏭️  {repo}")

    if failed:
        click.echo()
        click.echo("Failed to clone:")
        for repo, error in failed:
            click.echo(f"  ✗ {repo}")
            click.echo(f"    Error: {error}")


@context_store.command()
@click.argument("path_or_org", type=str)
@click.option(
    "--refresh",
    is_flag=True,
    help="Pull latest changes from git before printing",
)
@click.option(
    "--config-file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help="Optional bot config file for GitHub authentication (for cloning org repos)",
)
def prettyprint(path_or_org: str, refresh: bool, config_file: str | None):
    """Pretty print a context store at the given path or org name.

    This command accepts either:
    - A file path to a local context store repository
    - An org name (will clone dagster-compass/<org> to ~/.compass/repos/<org>)

    Examples:
        compass-dev context-store prettyprint /path/to/context-store
        compass-dev context-store prettyprint prod --refresh
        compass-dev context-store prettyprint dev --config-file local.csbot.config.yaml
    """
    path = resolve_path_or_org(path_or_org, config_file)

    click.echo(f"📊 Pretty printing context store at: {path}")
    click.echo("=" * 80)
    click.echo()

    # Refresh git repository if requested
    if refresh:
        click.echo("🔄 Refreshing git repository...")
        try:
            result = subprocess.run(
                ["git", "-C", str(path), "pull"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                click.echo(f"✅ Git pull successful: {result.stdout.strip()}")
            else:
                click.echo(f"⚠️  Git pull failed: {result.stderr.strip()}", err=True)
                click.echo("Continuing with existing repository state...")
        except subprocess.TimeoutExpired:
            click.echo("⚠️  Git pull timeout after 30 seconds", err=True)
            click.echo("Continuing with existing repository state...")
        except Exception as e:
            click.echo(f"⚠️  Error refreshing git repository: {e}", err=True)
            click.echo("Continuing with existing repository state...")
        click.echo()

    # Load the context store
    try:
        tree = FilesystemFileTree(path)
        context_store = load_context_store(tree)
        click.echo("✅ Successfully loaded context store")
    except Exception as e:
        click.echo(f"❌ Error loading context store: {e}", err=True)
        raise click.Abort()

    # Pretty print the context store
    click.echo()
    click.echo("📋 Context Store Contents")
    click.echo("-" * 80)

    # Print project info
    click.echo(f"\n🏢 Project: {context_store.project.project_name}")
    click.echo(f"   Version: {context_store.project.version}")
    if context_store.project.teams:
        click.echo(f"   Teams: {len(context_store.project.teams)}")
        for team_name, members in context_store.project.teams.items():
            click.echo(f"     - {team_name}: {len(members)} members")
            for member in members:
                click.echo(f"       • {member}")

    # Print system prompt
    if context_store.system_prompt:
        click.echo(f"\n📝 System Prompt: {len(context_store.system_prompt)} characters")
        click.echo("   Preview:")
        preview = context_store.system_prompt[:200]
        if len(context_store.system_prompt) > 200:
            preview += "..."
        for line in preview.split("\n"):
            click.echo(f"   {line}")

    # Print datasets
    click.echo(f"\n📊 Datasets: {len(context_store.datasets)}")
    if context_store.datasets:
        by_connection = {}
        for dataset, _ in context_store.datasets:
            if dataset.connection not in by_connection:
                by_connection[dataset.connection] = []
            by_connection[dataset.connection].append(dataset.table_name)

        for connection, tables in sorted(by_connection.items()):
            click.echo(f"   {connection}: {len(tables)} tables")
            for table in sorted(tables):
                click.echo(f"     - {table}")

    # Print general context
    click.echo(f"\n📚 General Context: {len(context_store.general_context)} entries")
    if context_store.general_context:
        by_group = {}
        for named_context in context_store.general_context:
            if named_context.group not in by_group:
                by_group[named_context.group] = []
            by_group[named_context.group].append((named_context.name, named_context.context))

        for group, contexts in sorted(by_group.items()):
            click.echo(f"   {group}: {len(contexts)} entries")
            for name, context in sorted(contexts, key=lambda x: x[0]):
                click.echo(f"     - {name}")
                click.echo(f"       Topic: {context.topic}")
                if context.search_keywords:
                    click.echo(f"       Keywords: {context.search_keywords}")

    # Print general cronjobs
    click.echo(f"\n⏰ General Cron Jobs: {len(context_store.general_cronjobs)}")
    for name, job in sorted(context_store.general_cronjobs.items()):
        thread_safe = job.thread.encode("utf-8", errors="replace").decode("utf-8", errors="replace")
        click.echo(f"   {name}:")
        click.echo(f"     - cron: {job.cron}")
        click.echo(f"     - thread: {thread_safe}")

    # Print channels
    click.echo(f"\n📢 Channels: {len(context_store.channels)}")
    for channel_name, channel_context in sorted(context_store.channels.items()):
        click.echo(f"   {channel_name}:")
        if channel_context.system_prompt:
            click.echo(f"     - system_prompt: {len(channel_context.system_prompt)} characters")
        click.echo(f"     - context: {len(channel_context.context)} entries")
        if channel_context.context:
            for named_context in channel_context.context:
                click.echo(
                    f"       • {named_context.group}/{named_context.name}: {named_context.context.topic}"
                )
        click.echo(f"     - cron_jobs: {len(channel_context.cron_jobs)}")
        if channel_context.cron_jobs:
            for cron_name in channel_context.cron_jobs:
                click.echo(f"       • {cron_name}")

    click.echo()
    click.echo("=" * 80)
    click.echo("✅ Pretty print complete")


@context_store.command()
@click.argument("path_or_org", type=str)
@click.argument("query", type=str)
@click.option(
    "--refresh",
    is_flag=True,
    help="Pull latest changes from git before searching",
)
@click.option(
    "--config-file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help="Optional bot config file for GitHub authentication (for cloning org repos)",
)
def search(path_or_org: str, query: str, refresh: bool, config_file: str | None):
    """Search a context store at the given path or org name.

    This command accepts either:
    - A file path to a local context store repository
    - An org name (will clone dagster-compass/<org> to ~/.compass/repos/<org>)

    Examples:
        compass-dev context-store search /path/to/context-store "python testing"
        compass-dev context-store search prod "python testing" --refresh
        compass-dev context-store search dev "api" --config-file local.csbot.config.yaml
    """
    path = resolve_path_or_org(path_or_org, config_file)
    from csbot.contextengine.context_engine import ContextSearcher

    click.echo(f"🔍 Searching context store at: {path}")
    click.echo(f"📝 Query: {query}")
    click.echo("=" * 80)
    click.echo()

    # Refresh git repository if requested
    if refresh:
        click.echo("🔄 Refreshing git repository...")
        try:
            result = subprocess.run(
                ["git", "-C", str(path), "pull"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                click.echo(f"✅ Git pull successful: {result.stdout.strip()}")
            else:
                click.echo(f"⚠️  Git pull failed: {result.stderr.strip()}", err=True)
                click.echo("Continuing with existing repository state...")
        except subprocess.TimeoutExpired:
            click.echo("⚠️  Git pull timeout after 30 seconds", err=True)
            click.echo("Continuing with existing repository state...")
        except Exception as e:
            click.echo(f"⚠️  Error refreshing git repository: {e}", err=True)
            click.echo("Continuing with existing repository state...")
        click.echo()

    # Load the context store
    try:
        tree = FilesystemFileTree(path)
        context_store = load_context_store(tree)
        click.echo("✅ Successfully loaded context store")
    except Exception as e:
        click.echo(f"❌ Error loading context store: {e}", err=True)
        raise click.Abort()

    # Create searcher and perform search
    try:
        searcher = ContextSearcher(context_store=context_store, channel_name=None)
        results = searcher.search(query)
        click.echo(f"✅ Found {len(results)} results")
    except Exception as e:
        click.echo(f"❌ Error searching: {e}", err=True)
        raise click.Abort()

    # Display results
    click.echo()
    click.echo("📊 Search Results")
    click.echo("-" * 80)

    if not results:
        click.echo("No results found.")
    else:
        for i, (doc_id, context) in enumerate(results, 1):
            click.echo(f"\n[{i}] {doc_id}")
            click.echo(f"    Topic: {context.topic}")
            click.echo(f"    Incorrect Understanding: {context.incorrect_understanding}")
            click.echo(f"    Correct Understanding: {context.correct_understanding}")
            if context.search_keywords:
                click.echo(f"    Keywords: {context.search_keywords}")

    click.echo()
    click.echo("=" * 80)
    click.echo("✅ Search complete")


@context_store.command()
@click.argument(
    "repos_file", type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path)
)
@click.option(
    "--target-dir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=Path.home() / ".compass" / "repos",
    help="Target directory for repositories (default: ~/.compass/repos)",
)
@click.option(
    "--config-file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help="Optional bot config file for GitHub authentication (for cloning missing repos)",
)
@click.option(
    "--skip-clone",
    is_flag=True,
    help="Skip cloning missing repositories (only inspect existing ones)",
)
@click.option(
    "--stop-on-failure",
    is_flag=True,
    help="Stop after the first failure (clone or inspection error)",
)
def inspect_repos(
    repos_file: Path,
    target_dir: Path,
    config_file: str | None,
    skip_clone: bool,
    stop_on_failure: bool,
):
    """Inspect multiple context store repositories from a file.

    This command reads a file containing repository names (one per line, format: owner/repo)
    and for each repository:
    1. Checks if it exists at ~/.compass/repos/<repo_name>
    2. Clones it if it doesn't exist (unless --skip-clone is set)
    3. Runs the inspect command on it

    Example repos file content:
        dagster-compass/dev
        dagster-compass/prod
        my-org/data-context

    Example:
        compass-dev context-store inspect-repos repos.txt
        compass-dev context-store inspect-repos repos.txt --skip-clone
        compass-dev context-store inspect-repos repos.txt --config-file local.csbot.config.yaml
    """
    # Read repos from file
    if not repos_file.exists():
        click.echo(f"❌ File not found: {repos_file}", err=True)
        raise click.Abort()

    repo_names = [
        line.strip()
        for line in repos_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

    if not repo_names:
        click.echo("❌ No repositories found in file", err=True)
        raise click.Abort()

    # Get GitHub authentication if config provided
    github_token = None
    if config_file and not skip_clone:
        try:
            bot_config = load_bot_config(config_file)
            auth_source = bot_config.github.get_auth_source()
            github_token = auth_source.get_token()
        except Exception as e:
            click.echo(f"⚠️  Could not load GitHub token from config: {e}", err=True)
            raise

    click.echo(f"🔍 Inspecting {len(repo_names)} repositories")
    click.echo("=" * 80)
    click.echo()

    successful_inspections = []
    failed_inspections = []
    cloned_repos = []
    skipped_repos = []

    for i, repo_name in enumerate(repo_names, 1):
        # Parse owner/repo format
        if "/" not in repo_name:
            click.echo(
                f"⚠️  [{i}/{len(repo_names)}] Skipping invalid repo format: {repo_name}", err=True
            )
            failed_inspections.append((repo_name, "Invalid format (expected owner/repo)"))
            continue

        # Extract repo name (last part after /)
        repo_short_name = repo_name.split("/")[-1]
        repo_path = target_dir / repo_short_name

        click.echo(f"[{i}/{len(repo_names)}] Processing {repo_name}")
        click.echo("-" * 80)

        # Check if repo exists
        if not repo_path.exists():
            if skip_clone:
                click.echo(
                    f"  ⏭️  Repository not found at {repo_path}, skipping (--skip-clone enabled)"
                )
                skipped_repos.append(repo_name)
                click.echo()
                continue

            # Clone the repository
            click.echo("  📥 Repository not found, cloning...")
            try:
                # Build git clone URL
                if github_token:
                    git_url = f"https://{github_token}@github.com/{repo_name}.git"
                else:
                    git_url = f"git@github.com:{repo_name}.git"

                # Create parent directory
                repo_path.parent.mkdir(parents=True, exist_ok=True)

                # Clone with shallow depth
                result = subprocess.run(
                    ["git", "clone", "--depth", "1", git_url, str(repo_path)],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                if result.returncode == 0:
                    click.echo(f"     ✅ Successfully cloned to {repo_path}")
                    cloned_repos.append(repo_name)
                else:
                    error_msg = result.stderr.strip() or result.stdout.strip()
                    click.echo(f"     ❌ Clone failed: {error_msg}", err=True)
                    failed_inspections.append((repo_name, f"Clone failed: {error_msg}"))
                    if stop_on_failure:
                        click.echo()
                        click.echo("🛑 Stopping due to failure (--stop-on-failure enabled)")
                        break
                    click.echo()
                    continue

            except subprocess.TimeoutExpired:
                click.echo("     ❌ Clone timeout after 60 seconds", err=True)
                failed_inspections.append((repo_name, "Clone timeout"))
                if stop_on_failure:
                    click.echo()
                    click.echo("🛑 Stopping due to failure (--stop-on-failure enabled)")
                    break
                click.echo()
                continue
            except Exception as e:
                click.echo(f"     ❌ Clone error: {e}", err=True)
                failed_inspections.append((repo_name, f"Clone error: {e}"))
                if stop_on_failure:
                    click.echo()
                    click.echo("🛑 Stopping due to failure (--stop-on-failure enabled)")
                    break
                click.echo()
                continue

        # Run inspection
        click.echo("  🔍 Inspecting context store...")
        click.echo()
        try:
            # Use the inspect function logic inline
            tree = FilesystemFileTree(repo_path)
            context_store = load_context_store(tree)

            # Print summary (abbreviated version)
            click.echo(
                f"     Project: {context_store.project.project_name} (v{context_store.project.version})"
            )
            click.echo(f"     Datasets: {len(context_store.datasets)}")
            click.echo(f"     General Context: {len(context_store.general_context)}")
            click.echo(f"     General Cron Jobs: {len(context_store.general_cronjobs)}")
            click.echo(f"     Channels: {len(context_store.channels)}")

            # Run round-trip test
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                reserialized_path = temp_path / "reserialized"
                reserialized_path.mkdir()

                serialize_context_store(context_store, reserialized_path)

                # Quick comparison (just count files)
                # Files to ignore in comparison
                ignored_files = {Path(".gitignore"), Path("README.md")}

                original_files = set()
                for item in repo_path.rglob("*"):
                    if item.is_file() and ".git" not in item.parts:
                        rel_path = item.relative_to(repo_path)
                        # Ignore specific files and any file named .gitkeep
                        if rel_path not in ignored_files and item.name != ".gitkeep":
                            original_files.add(rel_path)

                reserialized_files = set()
                for item in reserialized_path.rglob("*"):
                    if item.is_file():
                        rel_path = item.relative_to(reserialized_path)
                        # Ignore specific files and any file named .gitkeep
                        if rel_path not in ignored_files and item.name != ".gitkeep":
                            reserialized_files.add(rel_path)

                # Check for file structure differences
                only_in_original_set = original_files - reserialized_files
                only_in_reserialized_set = reserialized_files - original_files

                # Check for content differences in common files
                content_diffs = []
                common_files = original_files & reserialized_files
                for file in sorted(common_files):
                    file1_path = repo_path / file
                    file2_path = reserialized_path / file

                    content1 = file1_path.read_text()
                    content2 = file2_path.read_text()

                    if content1 != content2:
                        content_diffs.append(file)

                # Report results
                if not only_in_original_set and not only_in_reserialized_set and not content_diffs:
                    click.echo("     ✅ Round-trip test: PASSED")
                else:
                    click.echo("     ⚠️  Round-trip test: DIFFERENCES FOUND")

                    if only_in_original_set:
                        click.echo(f"        Files only in original ({len(only_in_original_set)}):")
                        for file in sorted(only_in_original_set):
                            click.echo(f"          - {file}")

                    if only_in_reserialized_set:
                        click.echo(
                            f"        Files only in reserialized ({len(only_in_reserialized_set)}):"
                        )
                        for file in sorted(only_in_reserialized_set):
                            click.echo(f"          - {file}")

                    if content_diffs:
                        click.echo(f"        Files with different content ({len(content_diffs)}):")
                        for file in sorted(content_diffs):
                            click.echo(f"          - {file}")

                    # Record as failed inspection due to differences
                    failed_inspections.append((repo_name, "Round-trip test found differences"))

                    if stop_on_failure:
                        click.echo()
                        click.echo(
                            "🛑 Stopping due to round-trip differences (--stop-on-failure enabled)"
                        )
                        break

            successful_inspections.append(repo_name)

        except Exception as e:
            click.echo(f"     ❌ Inspection failed: {e}", err=True)
            failed_inspections.append((repo_name, f"Inspection failed: {e}"))
            if stop_on_failure:
                click.echo()
                click.echo("🛑 Stopping due to failure (--stop-on-failure enabled)")
                break

        click.echo()

    # Final summary
    click.echo("=" * 80)
    click.echo("📊 Final Summary")
    click.echo(f"Total repositories: {len(repo_names)}")
    click.echo(f"✅ Successfully inspected: {len(successful_inspections)}")
    click.echo(f"📥 Cloned during this run: {len(cloned_repos)}")
    click.echo(f"⏭️  Skipped (not found): {len(skipped_repos)}")
    click.echo(f"❌ Failed: {len(failed_inspections)}")

    if successful_inspections:
        click.echo()
        click.echo("Successfully inspected:")
        for repo in successful_inspections:
            click.echo(f"  ✓ {repo}")

    if cloned_repos:
        click.echo()
        click.echo("Cloned during this run:")
        for repo in cloned_repos:
            click.echo(f"  📥 {repo}")

    if skipped_repos:
        click.echo()
        click.echo("Skipped (not found, --skip-clone enabled):")
        for repo in skipped_repos:
            click.echo(f"  ⏭️  {repo}")

    if failed_inspections:
        click.echo()
        click.echo("Failed:")
        for repo, error in failed_inspections:
            click.echo(f"  ✗ {repo}")
            click.echo(f"    {error}")


@context_store.command()
@click.argument("path_or_org", type=str)
@click.option(
    "--refresh",
    is_flag=True,
    help="Pull latest changes from git before listing cron jobs",
)
@click.option(
    "--config-file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help="Optional bot config file for GitHub authentication (for cloning org repos)",
)
def list_cron_jobs(path_or_org: str, refresh: bool, config_file: str | None):
    """List all cron jobs in a context store.

    This command accepts either:
    - A file path to a local context store repository
    - An org name (will clone dagster-compass/<org> to ~/.compass/repos/<org>)

    Examples:
        compass-dev context-store list-cron-jobs /path/to/context-store
        compass-dev context-store list-cron-jobs prod --refresh
        compass-dev context-store list-cron-jobs dev --config-file local.csbot.config.yaml
    """
    path = resolve_path_or_org(path_or_org, config_file)
    # Refresh git repository if requested
    if refresh:
        click.echo("🔄 Refreshing git repository...")
        try:
            result = subprocess.run(
                ["git", "-C", str(path), "pull"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                click.echo(f"✅ Git pull successful: {result.stdout.strip()}")
            else:
                click.echo(f"⚠️  Git pull failed: {result.stderr.strip()}", err=True)
                click.echo("Continuing with existing repository state...")
        except subprocess.TimeoutExpired:
            click.echo("⚠️  Git pull timeout after 30 seconds", err=True)
            click.echo("Continuing with existing repository state...")
        except Exception as e:
            click.echo(f"⚠️  Error refreshing git repository: {e}", err=True)
            click.echo("Continuing with existing repository state...")
        click.echo()

    tree = FilesystemFileTree(Path(path))
    context_store = load_context_store(tree)
    manager = ReadOnlyContextStoreManager(SimpleContextStore(context_store))
    storage = UserCronStorage(
        manager,
        None,
    )

    async def f():
        cron_jobs = await storage.get_cron_jobs()

        if not cron_jobs:
            click.echo("No cron jobs found.")
            return

        click.echo(f"⏰ Found {len(cron_jobs)} cron job(s)")
        click.echo("=" * 80)
        click.echo()

        for job_id, job in sorted(cron_jobs.items()):
            click.echo(f"📌 {job_id}")
            click.echo(f"   Cron Schedule: {job.cron}")

            # Handle potential surrogate characters in thread string
            thread_safe = job.thread.encode("utf-8", errors="replace").decode(
                "utf-8", errors="replace"
            )
            click.echo(f"   Thread: {thread_safe}")

            click.echo("   Question:")
            for line in job.question.split("\n"):
                click.echo(f"     {line}")
            click.echo()

    asyncio.run(f())


@context_store.command()
@click.option(
    "--config-file",
    required=True,
    help="Path to bot configuration YAML file",
)
@click.argument("pr_url", type=str)
def pr_diff(config_file: str, pr_url: str):
    """Compute and pretty print the context store diff for a GitHub PR.

    This command:
    1. Fetches the PR details from GitHub
    2. Extracts the before and after context store states
    3. Computes the diff between them
    4. Pretty prints the differences

    The repo name is automatically extracted from the PR URL.

    Example:
        compass-dev context-store pr-diff \\
            --config-file local.csbot.config.yaml \\
            https://github.com/owner/repo/pull/123
    """
    # Extract repo name from PR URL
    # URL format: https://github.com/owner/repo/pull/123[/files]
    if "github.com" not in pr_url:
        click.echo("❌ Invalid PR URL: must be a GitHub URL", err=True)
        return

    try:
        # Split URL and extract owner/repo
        parts = pr_url.split("github.com/")[1].split("/")
        if len(parts) < 4 or parts[2] != "pull":
            click.echo(
                "❌ Invalid PR URL format: expected https://github.com/owner/repo/pull/123",
                err=True,
            )
            return
        repo_name = f"{parts[0]}/{parts[1]}"
    except (IndexError, ValueError) as e:
        click.echo(f"❌ Failed to parse PR URL: {e}", err=True)
        return

    # Load bot config
    bot_config = load_bot_config(config_file)
    auth_source = bot_config.github.get_auth_source()

    github_config = GithubConfig(
        auth_source=auth_source,
        repo_name=repo_name,
    )

    click.echo(f"🔍 Fetching PR details from: {pr_url}")
    click.echo("=" * 80)
    click.echo()

    # Create temporary directories for before and after states
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        before_path = temp_path / "before"
        after_path = temp_path / "after"
        before_path.mkdir()
        after_path.mkdir()

        # Get base and head commits from GitHub
        g = github_config.auth_source.get_github_client()
        repo = g.get_repo(github_config.repo_name)
        pr_number = int(pr_url.split("/")[-1])
        pr = repo.get_pull(pr_number)

        click.echo(f"📝 PR #{pr_number}: {pr.title}")
        click.echo(f"   Base: {pr.base.ref} ({pr.base.sha[:7]})")
        click.echo(f"   Head: {pr.head.ref} ({pr.head.sha[:7]})")
        click.echo()

        # Clone the repository at base commit
        click.echo("📥 Cloning repository at base commit...")
        try:
            result = subprocess.run(
                [
                    "git",
                    "clone",
                    "--depth",
                    "1",
                    "--branch",
                    pr.base.ref,
                    pr.base.repo.clone_url,
                    str(before_path),
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                click.echo(f"❌ Failed to clone base: {result.stderr}", err=True)
                return
        except Exception as e:
            click.echo(f"❌ Error cloning base: {e}", err=True)
            return

        # Clone the repository at head commit
        click.echo("📥 Cloning repository at head commit...")
        try:
            result = subprocess.run(
                [
                    "git",
                    "clone",
                    "--depth",
                    "1",
                    "--branch",
                    pr.head.ref,
                    pr.head.repo.clone_url,
                    str(after_path),
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                click.echo(f"❌ Failed to clone head: {result.stderr}", err=True)
                return
        except Exception as e:
            click.echo(f"❌ Error cloning head: {e}", err=True)
            return

        click.echo()

        # Load context stores
        try:
            click.echo("📖 Loading base context store...")
            before_tree = FilesystemFileTree(before_path)
            before_store = load_context_store(before_tree)
            click.echo("✅ Base context store loaded")
        except Exception as e:
            click.echo(f"❌ Error loading base context store: {e}", err=True)
            return

        try:
            click.echo("📖 Loading head context store...")
            after_tree = FilesystemFileTree(after_path)
            after_store = load_context_store(after_tree)
            click.echo("✅ Head context store loaded")
        except Exception as e:
            click.echo(f"❌ Error loading head context store: {e}", err=True)
            return

        click.echo()

        # Compute diff
        click.echo("🔄 Computing diff...")
        diff = compute_diff(before_store, after_store)

        if not diff.has_changes():
            click.echo("✅ No changes detected in context store")
            return

        click.echo("✅ Diff computed")
        click.echo()
        click.echo("=" * 80)
        click.echo("📊 Context Store Diff")
        click.echo("=" * 80)
        click.echo()

        # Pretty print the diff
        _print_context_store_diff(diff)


def _print_context_store_diff(diff):
    """Pretty print a ContextStoreDiff."""
    # Project changes
    if diff.project_diff:
        click.echo("🏢 Project Changes:")
        if diff.project_diff.project_name_changed:
            click.echo("   ⚠️  Project name changed")
        if diff.project_diff.version_changed:
            click.echo("   ⚠️  Version changed")
        if diff.project_diff.teams_added:
            click.echo(f"   ➕ Teams added: {', '.join(diff.project_diff.teams_added)}")
        if diff.project_diff.teams_removed:
            click.echo(f"   ➖ Teams removed: {', '.join(diff.project_diff.teams_removed)}")
        if diff.project_diff.teams_modified:
            click.echo(f"   📝 Teams modified: {len(diff.project_diff.teams_modified)}")
            for team_name, (old_members, new_members) in diff.project_diff.teams_modified.items():
                old_set = set(old_members)
                new_set = set(new_members)
                added = new_set - old_set
                removed = old_set - new_set
                if added:
                    click.echo(f"      {team_name} ➕: {', '.join(added)}")
                if removed:
                    click.echo(f"      {team_name} ➖: {', '.join(removed)}")
        click.echo()

    # System prompt changes
    if diff.system_prompt_changed:
        click.echo("📝 System Prompt: Changed")
        click.echo()

    # Dataset changes
    if diff.datasets_added or diff.datasets_removed or diff.datasets_modified:
        click.echo("📊 Dataset Changes:")
        if diff.datasets_added:
            click.echo(f"   ➕ Added ({len(diff.datasets_added)}):")
            for dataset in diff.datasets_added:
                click.echo(f"      {dataset.connection}/{dataset.table_name}")
        if diff.datasets_removed:
            click.echo(f"   ➖ Removed ({len(diff.datasets_removed)}):")
            for dataset in diff.datasets_removed:
                click.echo(f"      {dataset.connection}/{dataset.table_name}")
        if diff.datasets_modified:
            click.echo(f"   📝 Modified ({len(diff.datasets_modified)}):")
            for dataset_diff in diff.datasets_modified:
                click.echo(
                    f"      {dataset_diff.dataset.connection}/{dataset_diff.dataset.table_name}"
                )
        click.echo()

    # General context changes
    if diff.general_context_added or diff.general_context_removed or diff.general_context_modified:
        click.echo("📚 General Context Changes:")
        if diff.general_context_added:
            click.echo(f"   ➕ Added ({len(diff.general_context_added)}):")
            for ctx in diff.general_context_added:
                click.echo(f"      {ctx.group}/{ctx.name}: {ctx.context.topic}")
        if diff.general_context_removed:
            click.echo(f"   ➖ Removed ({len(diff.general_context_removed)}):")
            for ctx in diff.general_context_removed:
                click.echo(f"      {ctx.group}/{ctx.name}: {ctx.context.topic}")
        if diff.general_context_modified:
            click.echo(f"   📝 Modified ({len(diff.general_context_modified)}):")
            for ctx_diff in diff.general_context_modified:
                click.echo(f"      {ctx_diff.group}/{ctx_diff.name}")
                if ctx_diff.topic_changed:
                    click.echo("         Topic changed")
                if ctx_diff.incorrect_understanding_changed:
                    click.echo("         Incorrect understanding changed")
                if ctx_diff.correct_understanding_changed:
                    click.echo("         Correct understanding changed")
                if ctx_diff.search_keywords_changed:
                    click.echo("         Search keywords changed")
        click.echo()

    # General cron jobs changes
    if (
        diff.general_cronjobs_added
        or diff.general_cronjobs_removed
        or diff.general_cronjobs_modified
    ):
        click.echo("⏰ General Cron Jobs Changes:")
        if diff.general_cronjobs_added:
            click.echo(
                f"   ➕ Added ({len(diff.general_cronjobs_added)}): {', '.join(diff.general_cronjobs_added)}"
            )
        if diff.general_cronjobs_removed:
            click.echo(
                f"   ➖ Removed ({len(diff.general_cronjobs_removed)}): {', '.join(diff.general_cronjobs_removed)}"
            )
        if diff.general_cronjobs_modified:
            click.echo(f"   📝 Modified ({len(diff.general_cronjobs_modified)}):")
            for job_diff in diff.general_cronjobs_modified:
                click.echo(f"      {job_diff.name}")
                if job_diff.cron_changed:
                    click.echo("         Cron schedule changed")
                if job_diff.question_changed:
                    click.echo("         Question changed")
                if job_diff.thread_changed:
                    click.echo("         Thread changed")
        click.echo()

    # Channel changes
    if diff.channels_added or diff.channels_removed or diff.channels_modified:
        click.echo("📢 Channel Changes:")
        if diff.channels_added:
            click.echo(
                f"   ➕ Added ({len(diff.channels_added)}): {', '.join(diff.channels_added)}"
            )
        if diff.channels_removed:
            click.echo(
                f"   ➖ Removed ({len(diff.channels_removed)}): {', '.join(diff.channels_removed)}"
            )
        if diff.channels_modified:
            click.echo(f"   📝 Modified ({len(diff.channels_modified)}):")
            for channel_diff in diff.channels_modified:
                click.echo(f"      {channel_diff.channel_name}:")
                if channel_diff.system_prompt_changed:
                    click.echo("         System prompt changed")
                if channel_diff.cron_jobs_added:
                    click.echo(
                        f"         Cron jobs added: {', '.join(channel_diff.cron_jobs_added)}"
                    )
                if channel_diff.cron_jobs_removed:
                    click.echo(
                        f"         Cron jobs removed: {', '.join(channel_diff.cron_jobs_removed)}"
                    )
                if channel_diff.cron_jobs_modified:
                    click.echo(
                        f"         Cron jobs modified: {len(channel_diff.cron_jobs_modified)}"
                    )
                if channel_diff.context_added:
                    click.echo(f"         Context added: {len(channel_diff.context_added)}")
                if channel_diff.context_removed:
                    click.echo(f"         Context removed: {len(channel_diff.context_removed)}")
                if channel_diff.context_modified:
                    click.echo(f"         Context modified: {len(channel_diff.context_modified)}")
        click.echo()

    click.echo("=" * 80)
    click.echo("✅ Diff display complete")
