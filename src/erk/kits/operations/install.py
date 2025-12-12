"""Kit installation operations."""

import os
import shutil
from pathlib import Path

from erk.kits.cli.output import user_output
from erk.kits.hooks.installer import install_hooks
from erk.kits.io.manifest import load_kit_manifest
from erk.kits.models.artifact import ARTIFACT_TARGET_DIRS, ArtifactType
from erk.kits.models.config import InstalledKit
from erk.kits.operations.artifact_operations import ArtifactOperations, create_artifact_operations
from erk.kits.sources.exceptions import ArtifactConflictError
from erk.kits.sources.resolver import ResolvedKit


def _install_skill_two_stage(
    source: Path,
    skill_name: str,
    project_dir: Path,
    operations: ArtifactOperations,
    overwrite: bool,
) -> tuple[str, str]:
    """Install a skill using two-stage installation.

    Stage 1: Install to .erk/skills/{skill-name}/ (copy or symlink depending on mode)
    Stage 2: Create symlink from .claude/skills/{skill-name}/ → .erk/skills/{skill-name}/

    Args:
        source: Source skill directory path
        skill_name: Name of the skill
        project_dir: Project root directory
        operations: Artifact operations strategy (ProdMode or DevMode)
        overwrite: Whether to overwrite existing files

    Returns:
        Tuple of (installed_artifact_path, managed_skill_path) relative to project_dir
    """
    # Stage 1: Install to .erk/skills/{skill-name}/
    erk_skills_dir = project_dir / ".erk" / "skills"
    if not erk_skills_dir.exists():
        erk_skills_dir.mkdir(parents=True)

    erk_skill_path = erk_skills_dir / skill_name

    # Handle conflicts for .erk/skills/{skill-name}
    if erk_skill_path.exists() or erk_skill_path.is_symlink():
        if not overwrite:
            raise ArtifactConflictError(erk_skill_path)
        if erk_skill_path.is_symlink() or erk_skill_path.is_file():
            erk_skill_path.unlink()
        else:
            shutil.rmtree(erk_skill_path)
        user_output(f"  Overwriting: .erk/skills/{skill_name}")

    # Install using strategy (copy in prod mode, symlink in dev mode)
    operations.install_artifact(source, erk_skill_path)

    # Stage 2: Create symlink from .claude/skills/{skill-name}/ → .erk/skills/{skill-name}/
    claude_skills_dir = project_dir / ".claude" / "skills"
    if not claude_skills_dir.exists():
        claude_skills_dir.mkdir(parents=True)

    claude_skill_path = claude_skills_dir / skill_name

    # Handle conflicts for .claude/skills/{skill-name}
    if claude_skill_path.exists() or claude_skill_path.is_symlink():
        if not overwrite:
            raise ArtifactConflictError(claude_skill_path)
        if claude_skill_path.is_symlink() or claude_skill_path.is_file():
            claude_skill_path.unlink()
        else:
            shutil.rmtree(claude_skill_path)
        user_output(f"  Overwriting: .claude/skills/{skill_name}")

    # Always create symlink for stage 2 (relative path from .claude/skills/ to .erk/skills/)
    # Calculate relative path: ../../.erk/skills/{skill-name}
    erk_skill_abs = erk_skill_path.resolve()
    claude_skill_abs = claude_skill_path.parent.resolve() / skill_name
    relative_path = os.path.relpath(erk_skill_abs, claude_skill_abs.parent)
    claude_skill_path.symlink_to(relative_path)

    # Return paths relative to project_dir
    installed_artifact = str(claude_skill_path.relative_to(project_dir))
    managed_skill = str(erk_skill_path.relative_to(project_dir))

    return installed_artifact, managed_skill


def _is_skill_directory(source: Path) -> bool:
    """Check if a source path is a skill directory (not a file)."""
    return source.is_dir()


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
    managed_skills: list[str] = []

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

            # Check if this is a skill directory - use two-stage installation
            if artifact_type == "skill" and _is_skill_directory(source):
                skill_name = source.name
                installed_path, managed_path = _install_skill_two_stage(
                    source=source,
                    skill_name=skill_name,
                    project_dir=project_dir,
                    operations=operations,
                    overwrite=overwrite,
                )
                installed_artifacts.append(installed_path)
                managed_skills.append(managed_path)
                user_output(f"  Installed skill: {skill_name} (managed)")
                continue

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
        managed_skills=managed_skills,
    )
