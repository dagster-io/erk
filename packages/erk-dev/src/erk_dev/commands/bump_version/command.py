"""Bump all package and kit versions to a specified version."""

import re
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


def update_kits_toml(path: Path, new_version: str, dry_run: bool) -> int:
    """Update all kit versions in kits.toml. Returns count of updates."""
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


def validate_changelog_for_release(repo_root: Path, version: str) -> list[str]:
    """Validate changelog is ready for release. Returns list of error messages."""
    # Import here to avoid circular dependency
    from erk_dev.commands.release_check.command import validate_changelog

    changelog_path = repo_root / "CHANGELOG.md"
    if not changelog_path.exists():
        return ["CHANGELOG.md not found"]

    content = changelog_path.read_text(encoding="utf-8")
    issues = validate_changelog(content, for_version=version)

    return [issue.message for issue in issues if issue.level == "error"]


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

    # Validate changelog is ready for this release (fail fast before any changes)
    changelog_errors = validate_changelog_for_release(repo_root, version)
    if changelog_errors:
        click.echo(click.style("Changelog not ready for release:", fg="red"))
        for error in changelog_errors:
            click.echo(click.style(f"  ✗ {error}", fg="red"))
        click.echo(f"\nRun 'erk-dev release-check --version {version}' for details.")
        raise SystemExit(1)

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

    # 3. kits.toml
    click.echo("\nInstalled kit registries:")
    kits_toml = repo_root / ".erk" / "kits.toml"
    if kits_toml.exists():
        count = update_kits_toml(kits_toml, version, dry_run)
        click.echo(f"  .erk/kits.toml: {count} kits")

    # 4. kit-registry.md
    click.echo("\nDocumentation registry:")
    registry = repo_root / ".erk/kits/kit-registry.md"
    if registry.exists():
        count = update_kit_registry_md(registry, version, dry_run)
        click.echo(f"  .erk/kits/kit-registry.md: {count} entries")

    # Changelog was already validated at the start - just confirm it's ready
    click.echo(click.style(f"\nChangelog: ✓ validated for {version}", fg="green"))

    if dry_run:
        click.echo("\n[DRY RUN] No files modified")
    else:
        click.echo("\nDone! Run 'uv sync' to update lockfile.")
