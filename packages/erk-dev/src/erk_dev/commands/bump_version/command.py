"""Bump all package and kit versions to a specified version."""

import re
from datetime import datetime
from pathlib import Path

import click


def get_current_version(repo_root: Path) -> str | None:
    """Get current version from root pyproject.toml."""
    pyproject = repo_root / "pyproject.toml"
    if not pyproject.exists():
        return None
    content = pyproject.read_text(encoding="utf-8")
    match = re.search(r'version\s*=\s*"([^"]+)"', content)
    if match is None:
        return None
    return match.group(1)


def increment_patch(version: str) -> str:
    """Increment patch version: N.M.P -> N.M.P+1."""
    parts = version.split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid semver: {version}")
    major, minor, patch = parts
    return f"{major}.{minor}.{int(patch) + 1}"


def find_repo_root(start: Path) -> Path | None:
    """Walk up to find repo root (contains pyproject.toml with [tool.uv.workspace])."""
    current = start
    while current != current.parent:
        pyproject = current / "pyproject.toml"
        if pyproject.exists():
            content = pyproject.read_text(encoding="utf-8")
            if "[tool.uv.workspace]" in content:
                return current
        current = current.parent
    return None


def update_toml_version(path: Path, new_version: str, dry_run: bool) -> tuple[bool, str | None]:
    """Update version = "X.Y.Z" in TOML file. Returns (success, old_version).

    Only matches 'version' at start of line to avoid matching 'target-version' etc.
    """
    content = path.read_text(encoding="utf-8")
    # Use ^ with MULTILINE to match 'version' at start of line only
    pattern = r'^(version\s*=\s*")([^"]+)(")'

    match = re.search(pattern, content, re.MULTILINE)
    if match is None:
        return False, None

    old_version = match.group(2)
    new_content = re.sub(pattern, rf"\g<1>{new_version}\3", content, count=1, flags=re.MULTILINE)

    if not dry_run:
        path.write_text(new_content, encoding="utf-8")
    return True, old_version


def update_yaml_version(path: Path, new_version: str, dry_run: bool) -> tuple[bool, str | None]:
    """Update version: X.Y.Z in YAML file. Returns (success, old_version)."""
    content = path.read_text(encoding="utf-8")
    pattern = r"(version:\s*)([^\n]+)"

    match = re.search(pattern, content)
    if match is None:
        return False, None

    old_version = match.group(2).strip()
    new_content = re.sub(pattern, rf"\g<1>{new_version}", content, count=1)

    if not dry_run:
        path.write_text(new_content, encoding="utf-8")
    return True, old_version


def update_dot_agent_toml(path: Path, new_version: str, dry_run: bool) -> int:
    """Update all kit versions in dot-agent.toml. Returns count of updates."""
    content = path.read_text(encoding="utf-8")
    # Match version = "X.Y.Z" lines (semver pattern in kit sections)
    pattern = r'(version\s*=\s*")([^"]+)(")'

    # Replace all semver versions (X.Y.Z pattern)
    lines = content.split("\n")
    updated = 0
    new_lines = []
    for line in lines:
        if re.match(r'\s*version\s*=\s*"[0-9]+\.[0-9]+', line):
            new_line = re.sub(pattern, rf"\g<1>{new_version}\3", line)
            new_lines.append(new_line)
            updated += 1
        else:
            new_lines.append(line)

    if not dry_run and updated > 0:
        path.write_text("\n".join(new_lines), encoding="utf-8")
    return updated


def update_kit_registry_md(path: Path, new_version: str, dry_run: bool) -> int:
    """Update versions in kit-registry.md HTML comments. Returns count."""
    content = path.read_text(encoding="utf-8")
    pattern = r'(<!-- ENTRY_START kit_id="[^"]+" version=")([^"]+)(" source="[^"]+" -->)'

    count = len(re.findall(pattern, content))
    if count == 0:
        return 0

    new_content = re.sub(pattern, rf"\g<1>{new_version}\3", content)

    if not dry_run:
        path.write_text(new_content, encoding="utf-8")
    return count


def update_changelog_header(path: Path, new_version: str, dry_run: bool) -> bool:
    """Update CHANGELOG.md to move [Unreleased] content to new version section.

    Transforms:
        ## [Unreleased]
        <content>
        ## [X.Y.Z] - YYYY-MM-DD

    Into:
        ## [Unreleased]
        ## [NEW_VERSION] - YYYY-MM-DD
        <content>
        ## [X.Y.Z] - YYYY-MM-DD

    Returns True if updated, False if changelog not found or no unreleased section.
    """
    if not path.exists():
        return False

    content = path.read_text(encoding="utf-8")

    # Check if [Unreleased] section exists
    if "## [Unreleased]" not in content:
        return False

    # Get today's date in YYYY-MM-DD format
    today = datetime.now().strftime("%Y-%m-%d")

    # Pattern to match [Unreleased] section followed by content until next ## section
    # This regex captures:
    # 1. The [Unreleased] header
    # 2. The content between [Unreleased] and the next version header
    pattern = r"(## \[Unreleased\])\n(.*?)(## \[\d)"

    match = re.search(pattern, content, re.DOTALL)
    if match is None:
        # No version section after [Unreleased], handle edge case
        # Look for [Unreleased] at end of file
        simple_pattern = r"(## \[Unreleased\])\n(.*?)$"
        match = re.search(simple_pattern, content, re.DOTALL)
        if match is None:
            return False

        unreleased_content = match.group(2).strip()
        if not unreleased_content:
            # No content in unreleased section
            return False

        # Replace [Unreleased]\n<content> with [Unreleased]\n\n## [VERSION] - DATE\n<content>
        new_section = f"## [Unreleased]\n\n## [{new_version}] - {today}\n\n{unreleased_content}\n"
        new_content = re.sub(simple_pattern, new_section, content, flags=re.DOTALL)
    else:
        unreleased_content = match.group(2).strip()
        next_version_start = match.group(3)

        if not unreleased_content:
            # Empty unreleased section - just add the new version header
            new_section = f"## [Unreleased]\n\n## [{new_version}] - {today}\n\n{next_version_start}"
        else:
            # Move unreleased content under new version header
            new_section = (
                f"## [Unreleased]\n\n## [{new_version}] - {today}\n\n"
                f"{unreleased_content}\n\n{next_version_start}"
            )

        new_content = re.sub(pattern, new_section, content, flags=re.DOTALL)

    if not dry_run:
        path.write_text(new_content, encoding="utf-8")
    return True


@click.command("bump-version")
@click.argument("version", required=False, default=None)
@click.option("--dry-run", is_flag=True, help="Show what would change without modifying files")
def bump_version_command(version: str | None, dry_run: bool) -> None:
    """Bump all package and kit versions to VERSION.

    VERSION should be in semver format (e.g., 0.2.1, 1.0.0).
    If not provided, increments the patch version (e.g., 4.2.1 -> 4.2.2).
    """
    repo_root = find_repo_root(Path.cwd())
    if repo_root is None:
        raise click.ClickException("Could not find repository root")

    # Auto-detect and increment if version not provided
    if version is None:
        current = get_current_version(repo_root)
        if current is None:
            raise click.ClickException("Could not detect current version from pyproject.toml")
        version = increment_patch(current)
        click.echo(f"Auto-bumping: {current} -> {version}")
    elif not re.match(r"^\d+\.\d+\.\d+$", version):
        raise click.ClickException(f"Invalid version format: {version}. Expected X.Y.Z")

    if dry_run:
        click.echo("[DRY RUN] Would update:")
    else:
        click.echo(f"Bumping versions to {version}")

    # 1. pyproject.toml files
    click.echo("\nPython packages:")
    for rel_path in [
        "pyproject.toml",
        "packages/erk-dev/pyproject.toml",
        "packages/erk-shared/pyproject.toml",
        "packages/erk-kits/pyproject.toml",
    ]:
        path = repo_root / rel_path
        if path.exists():
            ok, old = update_toml_version(path, version, dry_run)
            status = f"{old} -> {version}" if ok else "not found"
            click.echo(f"  {rel_path}: {status}")

    # 2. kit.yaml files
    click.echo("\nBundled kits:")
    kits_dir = repo_root / "packages/erk-kits/src/erk_kits/data/kits"
    if kits_dir.exists():
        for kit_yaml in sorted(kits_dir.glob("*/kit.yaml")):
            ok, old = update_yaml_version(kit_yaml, version, dry_run)
            status = f"{old} -> {version}" if ok else "not found"
            click.echo(f"  {kit_yaml.parent.name}: {status}")

    # 3. dot-agent.toml files
    click.echo("\nInstalled kit registries:")
    for rel_path in ["dot-agent.toml", ".erk/dot-agent.toml"]:
        path = repo_root / rel_path
        if path.exists():
            count = update_dot_agent_toml(path, version, dry_run)
            click.echo(f"  {rel_path}: {count} kits")

    # 4. kit-registry.md
    click.echo("\nDocumentation registry:")
    registry = repo_root / ".erk/kits/kit-registry.md"
    if registry.exists():
        count = update_kit_registry_md(registry, version, dry_run)
        click.echo(f"  .erk/kits/kit-registry.md: {count} entries")

    # 5. CHANGELOG.md
    click.echo("\nChangelog:")
    changelog = repo_root / "CHANGELOG.md"
    if changelog.exists():
        updated = update_changelog_header(changelog, version, dry_run)
        if updated:
            click.echo(f"  CHANGELOG.md: [Unreleased] -> [{version}]")
        else:
            click.echo("  CHANGELOG.md: no unreleased content")
    else:
        click.echo("  CHANGELOG.md: not found")

    if dry_run:
        click.echo("\n[DRY RUN] No files modified")
    else:
        click.echo("\nDone! Run 'uv sync' to update lockfile.")
