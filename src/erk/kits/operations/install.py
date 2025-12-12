"""Kit installation operations."""

import shutil
from pathlib import Path

from erk.kits.cli.output import user_output
from erk.kits.hooks.installer import install_hooks
from erk.kits.io.manifest import load_kit_manifest
from erk.kits.models.artifact import ARTIFACT_TARGET_DIRS, ArtifactType
from erk.kits.models.config import InstalledKit
from erk.kits.operations.artifact_operations import create_artifact_operations
from erk.kits.sources.exceptions import ArtifactConflictError
from erk.kits.sources.resolver import ResolvedKit


def install_kit(
    resolved: ResolvedKit,
    project_dir: Path,
    overwrite: bool = False,
    filtered_artifacts: dict[str, list[str]] | None = None,
) -> InstalledKit:
    """Install a kit to the project.

    Args:
        resolved: Resolved kit to install
        project_dir: Directory to install to
        overwrite: Whether to overwrite existing files
        filtered_artifacts: Optional filtered artifacts dict (type -> paths).
                          If None, installs all artifacts from manifest.
    """
    manifest = load_kit_manifest(resolved.manifest_path)

    installed_artifacts: list[str] = []

    # Create appropriate installation strategy
    operations = create_artifact_operations(project_dir, resolved)

    # Use filtered artifacts if provided, otherwise use all from manifest
    artifacts_to_install = (
        filtered_artifacts if filtered_artifacts is not None else manifest.artifacts
    )

    # Process each artifact type
    for artifact_type_str, paths in artifacts_to_install.items():
        # Get base directory for this artifact type (default to .claude for unknown types)
        artifact_type: ArtifactType = artifact_type_str  # type: ignore[assignment]
        base_dir_name = ARTIFACT_TARGET_DIRS.get(artifact_type, ".claude")
        base_dir = project_dir / base_dir_name

        # Ensure base directory exists
        if not base_dir.exists():
            base_dir.mkdir(parents=True)

        # Map artifact type to subdirectory (e.g., agents, commands, skills, workflows)
        # Doc type skips plural suffix since target dir (.erk/docs/kits) is complete
        if artifact_type == "doc":
            target_dir = base_dir
        else:
            target_dir = base_dir / f"{artifact_type}s"
        if not target_dir.exists():
            target_dir.mkdir(parents=True)

        for artifact_path in paths:
            # Read source artifact
            source = resolved.artifacts_base / artifact_path
            if not source.exists():
                continue

            # Determine target path - preserve nested directory structure
            # Artifact paths are like "agents/test.md" or "agents/subdir/test.md"
            # We need to strip the type prefix to avoid duplication
            artifact_rel_path = Path(artifact_path)
            type_prefix = f"{artifact_type}s"

            if artifact_rel_path.parts[0] == type_prefix:
                # Strip the type prefix (e.g., "agents/") and keep the rest
                relative_parts = artifact_rel_path.parts[1:]
                if relative_parts:
                    target = target_dir / Path(*relative_parts)
                else:
                    target = target_dir / artifact_rel_path.name
            else:
                # Fallback: use the whole path if prefix doesn't match
                target = target_dir / artifact_rel_path

            # Handle conflicts (check is_symlink too for broken symlinks)
            if target.exists() or target.is_symlink():
                if not overwrite:
                    raise ArtifactConflictError(target)
                # Remove existing file/symlink
                if target.is_symlink() or target.is_file():
                    target.unlink()
                else:
                    # Handle directory removal if needed
                    shutil.rmtree(target)
                user_output(f"  Overwriting: {target.name}")

            # Install artifact using strategy
            mode_indicator = operations.install_artifact(source, target)

            # Log installation with namespace visibility
            relative_path = target.relative_to(base_dir)
            user_output(f"  Installed {artifact_type}: {relative_path}{mode_indicator}")

            # Track installation
            installed_artifacts.append(str(target.relative_to(project_dir)))

    # Install hooks if manifest has them
    if manifest.hooks:
        install_hooks(
            kit_id=manifest.name,
            hooks=manifest.hooks,
            project_root=project_dir,
        )

    return InstalledKit(
        kit_id=manifest.name,
        source_type=resolved.source_type,
        version=manifest.version,
        artifacts=installed_artifacts,
        hooks=manifest.hooks if manifest.hooks else [],
    )
