"""Filesystem-based artifact repository implementation."""

from pathlib import Path

from erk.kits.hooks.settings import (
    discover_hooks_with_source,
    extract_hook_id_from_command,
    get_all_hooks,
    load_settings,
)
from erk.kits.io.manifest import load_kit_manifest
from erk.kits.models.artifact import (
    ArtifactLevel,
    ArtifactSource,
    ArtifactType,
    InstalledArtifact,
)
from erk.kits.models.bundled_kit import BundledKitInfo
from erk.kits.models.config import InstalledKit, ProjectConfig
from erk.kits.repositories.artifact_repository import ArtifactRepository
from erk.kits.sources.bundled import BundledKitSource


class FilesystemArtifactRepository(ArtifactRepository):
    """Discovers artifacts from filesystem .claude/ directory."""

    def discover_all_artifacts(
        self, project_dir: Path, config: ProjectConfig
    ) -> list[InstalledArtifact]:
        """Discover all installed artifacts with their metadata.

        Scans the .claude/ directory for all artifacts and enriches them with
        source information (managed, unmanaged, or local).

        Args:
            project_dir: Project root directory
            config: Project configuration from kits.toml

        Returns:
            List of all installed artifacts with metadata
        """
        claude_dir = project_dir / ".claude"
        if not claude_dir.exists():
            return []

        artifacts: list[InstalledArtifact] = []

        # Map of artifact paths to installed kits for tracking managed status
        managed_artifacts: dict[str, InstalledKit] = {}
        for kit in config.kits.values():
            for artifact_path in kit.artifacts:
                managed_artifacts[artifact_path] = kit

        # Scan skills directory
        skills_dir = claude_dir / "skills"
        if skills_dir.exists():
            for skill_dir in skills_dir.iterdir():
                if not skill_dir.is_dir():
                    continue

                skill_file = skill_dir / "SKILL.md"
                if not skill_file.exists():
                    continue

                artifact = self._create_artifact_from_file(
                    skill_file, "skill", skill_dir.name, managed_artifacts, config
                )
                if artifact:
                    artifacts.append(artifact)

        # Scan commands directory
        commands_dir = claude_dir / "commands"
        if commands_dir.exists():
            for item in commands_dir.iterdir():
                if item.is_file() and item.suffix == ".md":
                    # Direct command file: commands/command-name.md
                    name = item.stem
                    artifact = self._create_artifact_from_file(
                        item, "command", name, managed_artifacts, config
                    )
                    if artifact:
                        artifacts.append(artifact)
                elif item.is_dir():
                    # Kit commands directory: commands/kit-name/*.md
                    for cmd_file in item.glob("*.md"):
                        # Format as "kit:command-name"
                        name = f"{item.name}:{cmd_file.stem}"
                        artifact = self._create_artifact_from_file(
                            cmd_file, "command", name, managed_artifacts, config
                        )
                        if artifact:
                            artifacts.append(artifact)

        # Scan agents directory
        agents_dir = claude_dir / "agents"
        if agents_dir.exists():
            for item in agents_dir.iterdir():
                if item.is_file() and item.suffix == ".md":
                    # Direct agent file: agents/agent-name.md
                    name = item.stem
                    artifact = self._create_artifact_from_file(
                        item, "agent", name, managed_artifacts, config
                    )
                    if artifact:
                        artifacts.append(artifact)
                elif item.is_dir():
                    # Kit agents directory: agents/kit-name/*.md
                    for agent_file in item.glob("*.md"):
                        name = agent_file.stem
                        artifact = self._create_artifact_from_file(
                            agent_file, "agent", name, managed_artifacts, config
                        )
                        if artifact:
                            artifacts.append(artifact)

        # Scan docs directory (project-level only)
        docs_dir = claude_dir / "docs"
        if docs_dir.exists():
            # Docs are organized by kit: docs/kit-id/**/*.md
            for kit_dir in docs_dir.iterdir():
                if not kit_dir.is_dir():
                    continue

                kit_id_from_dir = kit_dir.name

                # Recursively find all .md files in kit directory
                for doc_file in kit_dir.rglob("*.md"):
                    # Artifact name is relative path within kit directory
                    relative_to_kit = doc_file.relative_to(kit_dir)
                    display_name = str(relative_to_kit).replace("\\", "/")

                    # Get relative path from .claude/ directory
                    relative_to_claude = doc_file.relative_to(claude_dir)

                    # Determine source based on kit config
                    source = ArtifactSource.LOCAL
                    kit_version = None
                    if kit_id_from_dir in config.kits:
                        # Check if this doc is in the kit's artifact list
                        kit = config.kits[kit_id_from_dir]
                        normalized_relative = str(relative_to_claude).replace("\\", "/")
                        for artifact_path in kit.artifacts:
                            normalized_artifact = artifact_path.replace(".claude/", "").replace(
                                "\\", "/"
                            )
                            if normalized_relative == normalized_artifact:
                                source = ArtifactSource.MANAGED
                                kit_version = kit.version
                                break

                    artifact = InstalledArtifact(
                        artifact_type="doc",
                        artifact_name=display_name,
                        file_path=relative_to_claude,
                        source=source,
                        level=ArtifactLevel.PROJECT,
                        kit_id=kit_id_from_dir,
                        kit_version=kit_version,
                    )
                    artifacts.append(artifact)

        # Scan hooks from settings.json
        settings_path = claude_dir / "settings.json"
        if settings_path.exists():
            settings = load_settings(settings_path)
            hooks = get_all_hooks(settings)

            for _lifecycle, _matcher, entry in hooks:
                # Extract script path from command
                # Command format: "python3 $CLAUDE_PROJECT_DIR/.claude/hooks/kit-id/script.py"
                # We want the relative path: hooks/kit-id/script.py
                command = entry.command

                # Try to extract the script path from the command
                script_path = None
                if ".claude/hooks/" in command:
                    # Extract path after .claude/
                    parts = command.split(".claude/")
                    if len(parts) > 1:
                        # Get the path part and extract just the file path
                        path_part = parts[1].split()[0]  # Take first token
                        script_path = Path(path_part)

                # Determine hook name, source, and metadata
                entry_hook_id = extract_hook_id_from_command(entry.command)
                if entry_hook_id:
                    # Managed hook with hook ID (from erk kit)
                    hook_name = entry_hook_id
                    kit_id = "erk"  # All managed hooks are from erk kit now
                    source = ArtifactSource.LOCAL
                    kit_version = None

                    # If we couldn't extract a path, create a placeholder
                    if not script_path:
                        script_path = Path("hooks") / "erk" / "hook"

                    hook_path_str = str(script_path).replace("\\", "/")

                    # Check if this hook's script is in managed artifacts
                    for artifact_path, kit in managed_artifacts.items():
                        normalized_artifact = artifact_path.replace(".claude/", "").replace(
                            "\\", "/"
                        )
                        matches_path = normalized_artifact == hook_path_str
                        matches_kit = kit.kit_id == "erk"
                        if matches_path or matches_kit:
                            source = ArtifactSource.MANAGED
                            kit_version = kit.version
                            break
                else:
                    # Local hook without kit metadata
                    if script_path:
                        # Use script filename as hook name
                        hook_name = script_path.stem
                    else:
                        # Use command as fallback (truncate if too long)
                        hook_name = command[:50] if len(command) > 50 else command
                        script_path = Path("hooks") / "local-hook"

                    kit_id = None
                    kit_version = None
                    source = ArtifactSource.LOCAL

                artifact = InstalledArtifact(
                    artifact_type="hook",
                    artifact_name=hook_name,
                    file_path=script_path,
                    source=source,
                    level=ArtifactLevel.PROJECT,  # Default level for discover_all_artifacts
                    kit_id=kit_id,
                    kit_version=kit_version,
                )
                artifacts.append(artifact)

        return artifacts

    def _create_artifact_from_file(
        self,
        file_path: Path,
        artifact_type: ArtifactType,
        display_name: str,
        managed_artifacts: dict[str, InstalledKit],
        config: ProjectConfig,
    ) -> InstalledArtifact | None:
        """Create an InstalledArtifact from a file.

        Args:
            file_path: Path to the artifact file
            artifact_type: Type of artifact (skill, command, agent)
            display_name: Display name for the artifact
            managed_artifacts: Map of artifact paths to installed kits
            config: Project configuration

        Returns:
            InstalledArtifact or None if file doesn't exist
        """
        if not file_path.exists():
            return None

        # Get relative path from .claude/ directory
        claude_dir = file_path.parent
        while claude_dir.name != ".claude" and claude_dir.parent != claude_dir:
            claude_dir = claude_dir.parent
        relative_path = file_path.relative_to(claude_dir)

        # Determine source and kit info
        source = ArtifactSource.LOCAL
        kit_id = None
        kit_version = None

        # Check if it's a managed artifact
        # Config paths may include ".claude/" prefix, so check both variations
        for artifact_path, kit in managed_artifacts.items():
            normalized_artifact = artifact_path.replace(".claude/", "").replace("\\", "/")
            normalized_relative = str(relative_path).replace("\\", "/")

            if normalized_relative == normalized_artifact:
                source = ArtifactSource.MANAGED
                kit_id = kit.kit_id
                kit_version = kit.version
                break

        # If not managed, it's a local artifact

        return InstalledArtifact(
            artifact_type=artifact_type,
            artifact_name=display_name,
            file_path=relative_path,
            source=source,
            level=ArtifactLevel.PROJECT,  # Default level for discover_all_artifacts
            kit_id=kit_id,
            kit_version=kit_version,
        )

    def discover_multi_level(
        self, user_path: Path, project_path: Path, project_config: ProjectConfig
    ) -> list[InstalledArtifact]:
        """Discover artifacts from both user and project levels.

        Args:
            user_path: User-level .claude directory (e.g., ~/.claude)
            project_path: Project-level .claude directory (e.g., ./.claude)
            project_config: Project configuration from kits.toml

        Returns:
            List of artifacts from both levels with level annotation
        """
        results: list[InstalledArtifact] = []

        # Discover user-level artifacts
        if user_path.exists():
            user_artifacts = self._discover_at_level(user_path, project_config, ArtifactLevel.USER)
            results.extend(user_artifacts)

        # Discover project-level artifacts
        if project_path.exists():
            project_artifacts = self._discover_at_level(
                project_path, project_config, ArtifactLevel.PROJECT
            )
            results.extend(project_artifacts)

        return results

    def _discover_at_level(
        self, claude_dir: Path, config: ProjectConfig, level: ArtifactLevel
    ) -> list[InstalledArtifact]:
        """Discover artifacts at a specific level (user or project).

        Args:
            claude_dir: .claude directory to scan
            config: Project configuration
            level: Level to annotate artifacts with

        Returns:
            List of artifacts with level annotation
        """
        if not claude_dir.exists():
            return []

        artifacts: list[InstalledArtifact] = []

        # Map of artifact paths to installed kits for tracking managed status
        managed_artifacts: dict[str, InstalledKit] = {}
        for kit in config.kits.values():
            for artifact_path in kit.artifacts:
                managed_artifacts[artifact_path] = kit

        # Scan skills directory
        skills_dir = claude_dir / "skills"
        if skills_dir.exists():
            for skill_dir in skills_dir.iterdir():
                if not skill_dir.is_dir():
                    continue

                skill_file = skill_dir / "SKILL.md"
                if not skill_file.exists():
                    continue

                artifact = self._create_artifact_at_level(
                    skill_file, "skill", skill_dir.name, managed_artifacts, config, level
                )
                if artifact:
                    artifacts.append(artifact)

        # Scan commands directory
        commands_dir = claude_dir / "commands"
        if commands_dir.exists():
            for item in commands_dir.iterdir():
                if item.is_file() and item.suffix == ".md":
                    # Direct command file: commands/command-name.md
                    name = item.stem
                    artifact = self._create_artifact_at_level(
                        item, "command", name, managed_artifacts, config, level
                    )
                    if artifact:
                        artifacts.append(artifact)
                elif item.is_dir():
                    # Kit commands directory: commands/kit-name/*.md
                    for cmd_file in item.glob("*.md"):
                        # Format as "kit:command-name"
                        name = f"{item.name}:{cmd_file.stem}"
                        artifact = self._create_artifact_at_level(
                            cmd_file, "command", name, managed_artifacts, config, level
                        )
                        if artifact:
                            artifacts.append(artifact)

        # Scan agents directory
        agents_dir = claude_dir / "agents"
        if agents_dir.exists():
            for item in agents_dir.iterdir():
                if item.is_file() and item.suffix == ".md":
                    # Direct agent file: agents/agent-name.md
                    name = item.stem
                    artifact = self._create_artifact_at_level(
                        item, "agent", name, managed_artifacts, config, level
                    )
                    if artifact:
                        artifacts.append(artifact)
                elif item.is_dir():
                    # Kit agents directory: agents/kit-name/*.md
                    for agent_file in item.glob("*.md"):
                        name = agent_file.stem
                        artifact = self._create_artifact_at_level(
                            agent_file, "agent", name, managed_artifacts, config, level
                        )
                        if artifact:
                            artifacts.append(artifact)

        # Scan docs directory (project-level only)
        if level == ArtifactLevel.PROJECT:
            docs_dir = claude_dir / "docs"
            if docs_dir.exists():
                # Docs are organized by kit: docs/kit-id/**/*.md
                for kit_dir in docs_dir.iterdir():
                    if not kit_dir.is_dir():
                        continue

                    kit_id_from_dir = kit_dir.name

                    # Recursively find all .md files in kit directory
                    for doc_file in kit_dir.rglob("*.md"):
                        # Artifact name is relative path within kit directory
                        relative_to_kit = doc_file.relative_to(kit_dir)
                        display_name = str(relative_to_kit).replace("\\", "/")

                        # Get relative path from .claude/ directory
                        relative_to_claude = doc_file.relative_to(claude_dir)

                        # Determine source based on kit config
                        source = ArtifactSource.LOCAL
                        kit_version = None
                        if kit_id_from_dir in config.kits:
                            # Check if this doc is in the kit's artifact list
                            kit = config.kits[kit_id_from_dir]
                            normalized_relative = str(relative_to_claude).replace("\\", "/")
                            for artifact_path in kit.artifacts:
                                normalized_artifact = artifact_path.replace(".claude/", "").replace(
                                    "\\", "/"
                                )
                                if normalized_relative == normalized_artifact:
                                    source = ArtifactSource.MANAGED
                                    kit_version = kit.version
                                    break

                        artifact = InstalledArtifact(
                            artifact_type="doc",
                            artifact_name=display_name,
                            file_path=relative_to_claude,
                            source=source,
                            level=level,
                            kit_id=kit_id_from_dir,
                            kit_version=kit_version,
                        )
                        artifacts.append(artifact)

        # Scan hooks with source tracking
        hooks_with_source = discover_hooks_with_source(claude_dir)
        for (_hook_lifecycle, _hook_matcher, entry), settings_source in hooks_with_source:
            # Extract script path from command
            command = entry.command
            script_path = None

            if ".claude/hooks/" in command:
                parts = command.split(".claude/")
                if len(parts) > 1:
                    path_part = parts[1].split()[0]
                    script_path = Path(path_part)

            # Determine hook name, source, and metadata
            entry_hook_id = extract_hook_id_from_command(entry.command)
            if entry_hook_id:
                # Managed hook with hook ID (from erk kit)
                hook_name = entry_hook_id
                kit_id = "erk"  # All managed hooks are from erk kit now
                source = ArtifactSource.LOCAL
                kit_version = None

                if not script_path:
                    script_path = Path("hooks") / "erk" / "hook"

                hook_path_str = str(script_path).replace("\\", "/")

                # Check if this hook's script is in managed artifacts
                for artifact_path, kit in managed_artifacts.items():
                    normalized_artifact = artifact_path.replace(".claude/", "").replace("\\", "/")
                    matches_path = normalized_artifact == hook_path_str
                    matches_kit = kit.kit_id == "erk"
                    if matches_path or matches_kit:
                        source = ArtifactSource.MANAGED
                        kit_version = kit.version
                        break
            else:
                # Local hook without kit metadata
                if script_path:
                    hook_name = script_path.stem
                else:
                    hook_name = command[:50] if len(command) > 50 else command
                    script_path = Path("hooks") / "local-hook"

                kit_id = None
                kit_version = None
                source = ArtifactSource.LOCAL

            artifact = InstalledArtifact(
                artifact_type="hook",
                artifact_name=hook_name,
                file_path=script_path,
                source=source,
                level=level,
                kit_id=kit_id,
                kit_version=kit_version,
                settings_source=settings_source,
            )
            artifacts.append(artifact)

        return artifacts

    def _create_artifact_at_level(
        self,
        file_path: Path,
        artifact_type: ArtifactType,
        display_name: str,
        managed_artifacts: dict[str, InstalledKit],
        config: ProjectConfig,
        level: ArtifactLevel,
    ) -> InstalledArtifact | None:
        """Create an InstalledArtifact at a specific level.

        Args:
            file_path: Path to the artifact file
            artifact_type: Type of artifact (skill, command, agent)
            display_name: Display name for the artifact
            managed_artifacts: Map of artifact paths to installed kits
            config: Project configuration
            level: Installation level (user or project)

        Returns:
            InstalledArtifact or None if file doesn't exist
        """
        if not file_path.exists():
            return None

        # Get relative path from .claude/ directory
        claude_dir = file_path.parent
        while claude_dir.name != ".claude" and claude_dir.parent != claude_dir:
            claude_dir = claude_dir.parent
        relative_path = file_path.relative_to(claude_dir)

        # Determine source and kit info
        source = ArtifactSource.LOCAL
        kit_id = None
        kit_version = None

        # Check if it's a managed artifact
        for artifact_path, kit in managed_artifacts.items():
            normalized_artifact = artifact_path.replace(".claude/", "").replace("\\", "/")
            normalized_relative = str(relative_path).replace("\\", "/")

            if normalized_relative == normalized_artifact:
                source = ArtifactSource.MANAGED
                kit_id = kit.kit_id
                kit_version = kit.version
                break

        return InstalledArtifact(
            artifact_type=artifact_type,
            artifact_name=display_name,
            file_path=relative_path,
            source=source,
            level=level,
            kit_id=kit_id,
            kit_version=kit_version,
        )

    def discover_bundled_kits(
        self, user_path: Path, project_path: Path, project_config: ProjectConfig
    ) -> dict[str, BundledKitInfo]:
        """Discover bundled kits that are installed in project config.

        Only returns bundled kits that are listed in the project's kits.toml
        configuration file. Shows their CLI commands and available docs.

        Args:
            user_path: User-level .claude directory (e.g., ~/.claude)
            project_path: Project-level .claude directory (e.g., ./.claude)
            project_config: Project configuration from kits.toml

        Returns:
            Dict mapping kit_id to BundledKitInfo with CLI commands and available docs
        """
        bundled_kits: dict[str, BundledKitInfo] = {}
        bundled_source = BundledKitSource()

        # Only process kits that are in the project config
        for kit_id, installed_kit in project_config.kits.items():
            # Skip if not a bundled kit
            if not bundled_source.can_resolve(kit_id):
                continue

            # Resolve kit to get manifest path
            resolved_kit = bundled_source.resolve(kit_id)
            manifest_path = resolved_kit.manifest_path

            if not manifest_path.exists():
                continue

            # Load manifest to get CLI commands
            manifest = load_kit_manifest(manifest_path)
            cli_commands = [cmd.name for cmd in manifest.scripts]

            # Scan for available docs in kit's docs directory
            kit_base = manifest_path.parent
            docs_dir = kit_base / "docs"
            available_docs: list[str] = []

            if docs_dir.exists():
                for doc_file in docs_dir.rglob("*.md"):
                    relative_doc = doc_file.relative_to(docs_dir)
                    available_docs.append(str(relative_doc).replace("\\", "/"))

            # All kits in project config are project-level
            bundled_kits[kit_id] = BundledKitInfo(
                kit_id=kit_id,
                version=installed_kit.version,
                cli_commands=cli_commands,
                available_docs=available_docs,
                level="project",
            )

        return bundled_kits
