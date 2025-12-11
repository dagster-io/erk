"""Migration commands for context store layout versions."""

import shutil

import click
import structlog
import yaml
from csadmin.utils import get_project_path

from csbot.contextengine.loader import load_project_from_path


@click.group()
def migration():
    """Migration commands for context store versions"""
    pass


@migration.command()
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Preview migration changes without executing them",
)
def migrate(dry_run: bool):
    """Migrate context store from V1 (legacy) to V2 (manifest) layout"""
    logger = structlog.get_logger(__name__)

    project_path = get_project_path()
    if project_path is None:
        click.echo(click.style("No contextstore project found", fg="red"))
        return

    project = load_project_from_path(project_path)

    if project.version == 2:
        click.echo(click.style("Project is already version 2 (manifest layout)", fg="yellow"))
        return

    if project.version > 2:
        click.echo(click.style(f"Unsupported project version {project.version}", fg="red"))
        return

    docs_dir = project_path / "docs"
    if not docs_dir.exists():
        click.echo(click.style("No docs directory found", fg="yellow"))
        return

    # Collect migration operations
    migrations = []
    conflicts = []

    for connection_dir in docs_dir.iterdir():
        if not connection_dir.is_dir():
            continue

        connection_name = connection_dir.name

        for md_file in connection_dir.glob("*.md"):
            table_name = md_file.stem
            source_path = md_file
            target_dir = connection_dir / table_name / "context"
            target_path = target_dir / "summary.md"

            # Check for conflicts
            if target_path.exists():
                conflicts.append((source_path, target_path))
                continue

            migrations.append(
                {
                    "source": source_path,
                    "target_dir": target_dir,
                    "target": target_path,
                    "connection": connection_name,
                    "table": table_name,
                }
            )

    if conflicts:
        click.echo(click.style("Migration conflicts detected:", fg="red"))
        for source, target in conflicts:
            click.echo(
                f"  {source.relative_to(project_path)} -> {target.relative_to(project_path)}"
            )
            click.echo(f"    Target already exists: {target}")
        click.echo(click.style("Please resolve conflicts manually before migrating", fg="red"))
        return

    if not migrations:
        click.echo(click.style("No legacy documentation files found to migrate", fg="yellow"))
        return

    # Preview mode
    if dry_run:
        click.echo(click.style("Migration plan (dry run):", fg="cyan"))
        click.echo("Project version: 1 -> 2")
        click.echo(f"Files to migrate: {len(migrations)}")
        for migration in migrations:
            source_rel = migration["source"].relative_to(project_path)
            target_rel = migration["target"].relative_to(project_path)
            click.echo(f"  {source_rel} -> {target_rel}")
        return

    # Execute migration
    click.echo(click.style("Starting migration...", fg="white"))

    try:
        # Create target directories and move files
        for migration in migrations:
            target_dir = migration["target_dir"]
            target_dir.mkdir(parents=True, exist_ok=True)

            shutil.move(str(migration["source"]), str(migration["target"]))
            logger.info(f"Moved {migration['source']} -> {migration['target']}")

        # Update project version
        config_path = project_path / "contextstore_project.yaml"
        with open(config_path) as f:
            config_data = yaml.safe_load(f)

        config_data["version"] = 2

        with open(config_path, "w") as f:
            yaml.dump(config_data, f, default_flow_style=False)

        logger.info("Updated project version to 2")

        click.echo(click.style("✅ Migration completed successfully!", fg="green"))
        click.echo(f"Migrated {len(migrations)} files to manifest layout")
        click.echo("Project version updated to 2")

    except Exception as e:
        click.echo(click.style(f"❌ Migration failed: {e}", fg="red"))
        raise click.Abort()


@migration.command()
def check():
    """Validate context store structure matches declared version"""
    project_path = get_project_path()
    if project_path is None:
        click.echo(click.style("No contextstore project found", fg="red"))
        return

    project = load_project_from_path(project_path)

    docs_dir = project_path / "docs"
    if not docs_dir.exists():
        click.echo(click.style("No docs directory found", fg="yellow"))
        return

    errors = []
    warnings = []

    click.echo(f"Checking project version {project.version} structure...")

    for connection_dir in docs_dir.iterdir():
        if not connection_dir.is_dir():
            continue

        if project.version == 1:
            # Version 1: Should only have .md files directly in connection dir
            for item in connection_dir.iterdir():
                if item.is_file() and item.suffix == ".md":
                    continue  # Valid legacy file
                elif item.is_dir():
                    errors.append(
                        f"Version 1 project should not have subdirectories: {item.relative_to(project_path)}"
                    )
                elif item.is_file():
                    warnings.append(
                        f"Unexpected non-markdown file: {item.relative_to(project_path)}"
                    )

        elif project.version == 2:
            # Version 2: Should only have manifest structure
            for item in connection_dir.iterdir():
                if item.is_file() and item.suffix == ".md":
                    errors.append(
                        f"Version 2 project should not have legacy .md files: {item.relative_to(project_path)}"
                    )
                elif item.is_dir():
                    # Check manifest structure
                    context_dir = item / "context"
                    summary_file = context_dir / "summary.md"

                    if not context_dir.exists():
                        errors.append(
                            f"Missing context directory: {context_dir.relative_to(project_path)}"
                        )
                    elif not summary_file.exists():
                        errors.append(
                            f"Missing summary.md file: {summary_file.relative_to(project_path)}"
                        )
                    else:
                        # Validate summary.md has content
                        try:
                            content = summary_file.read_text()
                            if not content.strip():
                                warnings.append(
                                    f"Empty summary.md file: {summary_file.relative_to(project_path)}"
                                )
                        except Exception as e:
                            errors.append(
                                f"Cannot read summary.md: {summary_file.relative_to(project_path)} - {e}"
                            )
        else:
            errors.append(f"Unsupported project version: {project.version}")

    # Report results
    if errors:
        click.echo(click.style("❌ Structure validation failed:", fg="red"))
        for error in errors:
            click.echo(f"  ERROR: {error}")

    if warnings:
        click.echo(click.style("⚠️  Warnings:", fg="yellow"))
        for warning in warnings:
            click.echo(f"  WARNING: {warning}")

    if not errors and not warnings:
        click.echo(click.style("✅ Structure validation passed", fg="green"))
    elif not errors:
        click.echo(click.style("✅ Structure validation passed with warnings", fg="yellow"))
    else:
        raise click.Abort()
