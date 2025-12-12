"""Check kit integrity by validating @ references."""

from dataclasses import dataclass
from pathlib import Path

import click

from erk.kits.io.at_reference import parse_at_references
from erk.kits.io.manifest import load_kit_manifest
from erk.kits.sources.bundled import BundledKitSource


@dataclass(frozen=True)
class MissingReference:
    """A missing @ reference found in a kit artifact."""

    artifact_path: str
    reference_path: str
    line_number: int


@dataclass(frozen=True)
class KitCheckResult:
    """Result of checking a kit for missing references."""

    kit_name: str
    missing_references: list[MissingReference]

    @property
    def is_valid(self) -> bool:
        """Check if the kit has no missing references."""
        return len(self.missing_references) == 0


def get_kit_artifact_paths(manifest_path: Path) -> set[str]:
    """Get all artifact paths declared in a kit manifest.

    Args:
        manifest_path: Path to kit.yaml

    Returns:
        Set of artifact paths (with .claude/ prefix normalized)
    """
    manifest = load_kit_manifest(manifest_path)

    paths: set[str] = set()
    for artifact_list in manifest.artifacts.values():
        for artifact_rel in artifact_list:
            # Normalize to .claude/ prefix for comparison
            paths.add(f".claude/{artifact_rel}")

    return paths


def check_kit_references(kit_name: str, kit_path: Path) -> KitCheckResult:
    """Check all @ references in a kit's artifacts.

    Parses each artifact file and checks that all @ references point to
    files that are also included in the kit's artifact list.

    Args:
        kit_name: Name of the kit being checked
        kit_path: Path to the kit directory (containing kit.yaml)

    Returns:
        KitCheckResult with any missing references found
    """
    manifest_path = kit_path / "kit.yaml"
    if not manifest_path.exists():
        return KitCheckResult(kit_name=kit_name, missing_references=[])

    manifest = load_kit_manifest(manifest_path)
    kit_artifacts = get_kit_artifact_paths(manifest_path)

    missing: list[MissingReference] = []

    # Check each artifact for @ references
    for artifact_list in manifest.artifacts.values():
        for artifact_rel in artifact_list:
            artifact_path = kit_path / artifact_rel
            if not artifact_path.exists():
                continue

            content = artifact_path.read_text(encoding="utf-8")
            references = parse_at_references(content)

            for ref in references:
                # Check if the referenced file is in the kit's artifacts
                ref_path = ref.file_path

                # Normalize reference path for comparison
                if not ref_path.startswith(".claude/"):
                    ref_path = f".claude/{ref_path}"

                if ref_path not in kit_artifacts:
                    # Also check if the physical file exists in the kit
                    # (for docs that might be bundled but not listed in artifacts)
                    # Handle both absolute (.claude/...) and relative (../../...) paths
                    if ref.file_path.startswith(".."):
                        # Relative path - resolve from artifact location
                        physical_path = (artifact_path.parent / ref.file_path).resolve()
                    else:
                        physical_path = kit_path / ref.file_path.removeprefix(".claude/")

                    if not physical_path.exists():
                        missing.append(
                            MissingReference(
                                artifact_path=f".claude/{artifact_rel}",
                                reference_path=ref.file_path,
                                line_number=ref.line_number,
                            )
                        )

    return KitCheckResult(kit_name=kit_name, missing_references=missing)


@click.command(name="kit-check")
@click.option(
    "--kit",
    "-k",
    "kit_name",
    help="Check only this specific kit (by name)",
)
def kit_check(kit_name: str | None) -> None:
    """Check kit integrity by validating @ references.

    Scans kit artifacts for @ references and verifies that all
    referenced files are also included in the kit's artifacts list.

    This helps prevent broken references when a skill references
    documentation that wasn't included in the kit.

    Examples:

        # Check all bundled kits
        dot-agent dev kit-check

        # Check a specific kit
        dot-agent dev kit-check --kit dignified-python
    """
    bundled_source = BundledKitSource()
    kit_names = bundled_source.list_available()

    if not kit_names:
        click.echo("No bundled kits found")
        return

    if kit_name is not None:
        if kit_name not in kit_names:
            available = ", ".join(sorted(kit_names))
            click.echo(f"Kit '{kit_name}' not found. Available kits: {available}")
            raise SystemExit(1)
        kit_names = [kit_name]

    all_valid = True
    total_missing = 0

    for name in sorted(kit_names):
        kit_path = bundled_source._get_bundled_kit_path(name)
        if kit_path is None:
            continue

        result = check_kit_references(name, kit_path)

        if result.is_valid:
            click.echo(f"  {name}: OK")
        else:
            all_valid = False
            total_missing += len(result.missing_references)
            click.echo(f"  {name}: FAILED")
            for missing in result.missing_references:
                click.echo(
                    f"    {missing.artifact_path}:{missing.line_number} "
                    f"references '{missing.reference_path}' (not in kit)"
                )

    click.echo()
    if all_valid:
        click.echo("All kits passed reference checks")
    else:
        click.echo(f"Found {total_missing} missing reference(s)")
        raise SystemExit(1)
