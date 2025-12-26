"""Check command for validating context store YAML files."""

from dataclasses import dataclass
from pathlib import Path

import click
import yaml
from pydantic import ValidationError

from csadmin.models import ContextStoreProject, ProvidedContext, UserCronJob
from csadmin.utils import get_project_path


@dataclass(frozen=True)
class ValidationError_:
    """Represents a validation error for a file."""

    file_path: Path
    error_type: str  # "parse" or "schema"
    message: str


def _validate_yaml_file(
    file_path: Path,
    model_class: type[ContextStoreProject] | type[ProvidedContext] | type[UserCronJob],
) -> ValidationError_ | None:
    """
    Validate a single YAML file against a Pydantic model.

    Args:
        file_path: Path to the YAML file
        model_class: Pydantic model class to validate against

    Returns:
        ValidationError_ if validation fails, None if valid
    """
    if not file_path.exists():
        return ValidationError_(
            file_path=file_path,
            error_type="parse",
            message="File does not exist",
        )

    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return ValidationError_(
            file_path=file_path,
            error_type="parse",
            message=f"Failed to read file: {e}",
        )

    # Try to parse YAML
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        return ValidationError_(
            file_path=file_path,
            error_type="parse",
            message=f"Invalid YAML syntax: {e}",
        )

    # Try to validate against schema
    try:
        model_class.model_validate(data)
    except ValidationError as e:
        return ValidationError_(
            file_path=file_path,
            error_type="schema",
            message=f"Schema validation failed: {e}",
        )

    return None


def _discover_yaml_files(base_path: Path, pattern: str) -> list[Path]:
    """
    Discover YAML files matching a glob pattern.

    Args:
        base_path: Base directory to search in
        pattern: Glob pattern (e.g., "context/**/*.yaml")

    Returns:
        List of matching file paths
    """
    if not base_path.exists():
        return []

    return sorted(base_path.glob(pattern))


def _validate_project_file(project_root: Path) -> ValidationError_ | None:
    """Validate the main contextstore_project.yaml file."""
    project_file = project_root / "contextstore_project.yaml"
    return _validate_yaml_file(project_file, ContextStoreProject)


def _validate_context_files(project_root: Path) -> list[ValidationError_]:
    """Validate all context YAML files (general and channel-specific)."""
    errors: list[ValidationError_] = []

    # General context files
    context_files = _discover_yaml_files(project_root / "context", "**/*.yaml")
    for file_path in context_files:
        error = _validate_yaml_file(file_path, ProvidedContext)
        if error:
            errors.append(error)

    # Channel-specific context files
    channels_dir = project_root / "channels"
    if channels_dir.exists():
        channel_context_files = _discover_yaml_files(channels_dir, "*/context/**/*.yaml")
        for file_path in channel_context_files:
            error = _validate_yaml_file(file_path, ProvidedContext)
            if error:
                errors.append(error)

    return errors


def _validate_cronjob_files(project_root: Path) -> list[ValidationError_]:
    """Validate all cronjob YAML files (general and channel-specific)."""
    errors: list[ValidationError_] = []

    # General cronjob files
    cronjob_files = _discover_yaml_files(project_root / "cronjobs", "*.yaml")
    for file_path in cronjob_files:
        error = _validate_yaml_file(file_path, UserCronJob)
        if error:
            errors.append(error)

    # Channel-specific cronjob files
    channels_dir = project_root / "channels"
    if channels_dir.exists():
        channel_cronjob_files = _discover_yaml_files(channels_dir, "*/cronjobs/*.yaml")
        for file_path in channel_cronjob_files:
            error = _validate_yaml_file(file_path, UserCronJob)
            if error:
                errors.append(error)

    return errors


def _print_validation_results(
    project_root: Path,
    project_error: ValidationError_ | None,
    context_errors: list[ValidationError_],
    cronjob_errors: list[ValidationError_],
) -> None:
    """Print validation results with color-coded output."""
    all_errors = [e for e in [project_error] + context_errors + cronjob_errors if e]

    if not all_errors:
        click.echo(click.style("✅ All files valid!", fg="green"))
        return

    # Group errors by type
    parse_errors = [e for e in all_errors if e.error_type == "parse"]
    schema_errors = [e for e in all_errors if e.error_type == "schema"]

    # Print parse errors (warnings)
    if parse_errors:
        click.echo(click.style(f"\n⚠️  Parse Errors ({len(parse_errors)}):", fg="yellow"))
        for error in parse_errors:
            rel_path = error.file_path.relative_to(project_root)
            click.echo(click.style(f"  {rel_path}", fg="yellow"))
            click.echo(f"    {error.message}")

    # Print schema errors
    if schema_errors:
        click.echo(click.style(f"\n❌ Schema Validation Errors ({len(schema_errors)}):", fg="red"))
        for error in schema_errors:
            rel_path = error.file_path.relative_to(project_root)
            click.echo(click.style(f"  {rel_path}", fg="red"))
            click.echo(f"    {error.message}")

    # Print summary
    click.echo(
        f"\n{click.style('Summary:', bold=True)} "
        f"{len(parse_errors)} parse errors, "
        f"{len(schema_errors)} schema errors"
    )


@click.command("check")
def check() -> None:
    """
    Validate context store YAML files for parseability and schema compliance.

    Validates:
    - contextstore_project.yaml (project configuration)
    - context/**/*.yaml (learning/feedback contexts)
    - cronjobs/*.yaml (scheduled queries)
    - channels/*/context/**/*.yaml (channel-specific contexts)
    - channels/*/cronjobs/*.yaml (channel-specific cronjobs)
    """
    # Find project root
    project_root = get_project_path()
    if not project_root:
        click.echo(
            click.style(
                "Error: Could not find contextstore_project.yaml in current directory or parents",
                fg="red",
            ),
            err=True,
        )
        raise SystemExit(1)

    click.echo(f"Checking context store at: {project_root}\n")

    # Validate project file
    project_error = _validate_project_file(project_root)

    # Validate context files
    context_errors = _validate_context_files(project_root)

    # Validate cronjob files
    cronjob_errors = _validate_cronjob_files(project_root)

    # Print results
    _print_validation_results(project_root, project_error, context_errors, cronjob_errors)

    # Exit with error code if any validation failed
    if project_error or context_errors or cronjob_errors:
        raise SystemExit(1)
