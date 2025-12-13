"""Registry I/O."""

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

import yaml

import erk_kits
from erk.kits.models.config import InstalledKit, ProjectConfig
from erk.kits.models.kit import KitManifest
from erk.kits.models.registry import RegistryEntry


@dataclass(frozen=True)
class DocRegistryEntry:
    """Documentation registry entry with metadata."""

    kit_id: str
    version: str
    source_type: str
    include_path: str


def load_registry() -> list[RegistryEntry]:
    """Load registry.yaml from package data."""
    registry_path = erk_kits.get_registry_path()

    with open(registry_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data or "kits" not in data:
        return []

    return [
        RegistryEntry(
            kit_id=kit["kit_id"],
            source_type=kit["source_type"],
            description=kit["description"],
            version=kit["version"],
        )
        for kit in data["kits"]
    ]


def parse_doc_registry_entries(content: str) -> list[DocRegistryEntry]:
    """Parse documentation registry entries from content.

    Args:
        content: Registry file content

    Returns:
        List of parsed registry entries
    """
    entries = []

    # Pattern matches: <!-- ENTRY_START ... --> \n @path \n <!-- ENTRY_END -->
    pattern = r"<!-- ENTRY_START (.*?) -->\s*\n@(.+?)\s*\n<!-- ENTRY_END -->"

    for match in re.finditer(pattern, content, re.DOTALL):
        # Extract metadata: kit_id="devrun" version="0.1.0" source="bundled"
        metadata_str = match.group(1)
        include_path = match.group(2).strip()

        # Parse key="value" pairs
        metadata = dict(re.findall(r'(\w+)="([^"]+)"', metadata_str))

        # Validate required fields exist
        if "kit_id" not in metadata or "version" not in metadata:
            continue  # Skip malformed entries

        entries.append(
            DocRegistryEntry(
                kit_id=metadata["kit_id"],
                version=metadata["version"],
                source_type=metadata.get("source", "unknown"),
                include_path=include_path,
            )
        )

    return entries


def generate_doc_registry_content(entries: list[DocRegistryEntry]) -> str:
    """Generate registry content from entries.

    Args:
        entries: List of registry entries (will be sorted alphabetically)

    Returns:
        Complete registry markdown content
    """
    # Sort entries alphabetically by kit_id
    sorted_entries = sorted(entries, key=lambda e: e.kit_id)

    # Build registry content
    lines = [
        "# Kit Documentation Registry",
        "",
        "<!-- AUTO-GENERATED: This file is managed by erk kit commands -->",
        "<!-- DO NOT EDIT: Changes will be overwritten. Use 'erk kit install' -->",
        "",
        "<!-- REGISTRY_VERSION: 1 -->",
        "",
        "<!-- BEGIN_ENTRIES -->",
    ]

    for entry in sorted_entries:
        lines.append("")
        lines.append(
            f'<!-- ENTRY_START kit_id="{entry.kit_id}" '
            f'version="{entry.version}" source="{entry.source_type}" -->'
        )
        lines.append(f"@{entry.include_path}")
        lines.append("<!-- ENTRY_END -->")

    lines.append("")
    lines.append("<!-- END_ENTRIES -->")
    lines.append("")

    return "\n".join(lines)


def _validate_registry_entry(entry: str) -> None:
    """Validate registry entry has required fields.

    Required:
    - Header with kit name and version (### kit-name (vX.Y.Z))
    - **Purpose**: line
    - **Usage**: line

    Args:
        entry: Registry entry markdown string

    Raises:
        ValueError: If required fields are missing
    """
    if not re.search(r"^### \S+ \(v\d+\.\d+\.\d+\)$", entry, re.MULTILINE):
        raise ValueError("Registry entry missing required header: ### kit-name (vX.Y.Z)")
    if "**Purpose**:" not in entry:
        raise ValueError("Registry entry missing required field: **Purpose**:")
    if "**Usage**:" not in entry:
        raise ValueError("Registry entry missing required field: **Usage**:")


def generate_registry_entry(
    kit_id: str, version: str, manifest: KitManifest, installed_kit: InstalledKit
) -> str:
    """Generate registry entry markdown from kit manifest.

    Args:
        kit_id: Kit identifier
        version: Kit version
        manifest: Kit manifest data
        installed_kit: Installed kit information

    Returns:
        Formatted markdown string (~15-20 lines)

    Raises:
        ValueError: If required fields are missing from manifest
    """
    # Start with header
    lines = [f"### {kit_id} (v{version})", ""]

    # Add purpose from manifest description
    lines.append(f"**Purpose**: {manifest.description}")
    lines.append("")

    # List artifacts by type
    if manifest.artifacts:
        lines.append("**Artifacts**:")
        for artifact_type, paths in manifest.artifacts.items():
            if paths:
                lines.append(f"- {artifact_type}: {', '.join(paths)}")
        lines.append("")

    # Generate usage example based on artifact types
    lines.append("**Usage**:")
    usage_examples = []

    if "agent" in manifest.artifacts and manifest.artifacts["agent"]:
        agent_name = manifest.artifacts["agent"][0].split("/")[1]  # Extract name from path
        usage_examples.append(f'- Use Task tool with subagent_type="{agent_name}"')

    if "command" in manifest.artifacts and manifest.artifacts["command"]:
        cmd_name = manifest.artifacts["command"][0].split("/")[1]  # Extract name from path
        usage_examples.append(f"- Run `/{cmd_name}` command")

    if "skill" in manifest.artifacts and manifest.artifacts["skill"]:
        skill_name = manifest.artifacts["skill"][0].split("/")[1]  # Extract name from path
        usage_examples.append(f"- Load `{skill_name}` skill")

    # If no usage examples, provide generic guidance based on artifact types
    if not usage_examples:
        if "doc" in manifest.artifacts and manifest.artifacts["doc"]:
            usage_examples.append("- Reference documentation loaded automatically via AGENTS.md")
        else:
            usage_examples.append("- See kit documentation for usage details")

    lines.extend(usage_examples)
    lines.append("")

    entry = "\n".join(lines)

    # Validate before returning
    _validate_registry_entry(entry)

    return entry


def create_kit_registry_file(kit_id: str, entry_content: str, project_dir: Path) -> Path:
    """Create or update registry entry file for a kit.

    Args:
        kit_id: Kit identifier
        entry_content: Registry entry markdown content
        project_dir: Project root directory

    Returns:
        Path to created registry entry file

    Raises:
        IOError: If file cannot be created
    """
    registry_dir = project_dir / ".erk" / "kits" / kit_id

    # Create directory if it doesn't exist
    if not registry_dir.exists():
        registry_dir.mkdir(parents=True, exist_ok=True)

    # Write registry entry file
    registry_file = registry_dir / "registry-entry.md"
    registry_file.write_text(entry_content, encoding="utf-8")

    return registry_file


def add_kit_to_registry(kit_id: str, project_dir: Path, version: str, source_type: str) -> None:
    """Add kit to registry with structured format.

    Args:
        kit_id: Kit identifier
        project_dir: Project root directory
        version: Kit version
        source_type: Source type (bundled, standalone, etc.)

    Raises:
        IOError: If registry file cannot be written
    """
    from erk.kits.io.state import load_project_config

    registry_path = project_dir / ".erk" / "kits" / "kit-registry.md"

    # Create registry file if it doesn't exist
    if not registry_path.exists():
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        # Create empty registry with new format
        content = generate_doc_registry_content([])
        registry_path.write_text(content, encoding="utf-8")

    # Read current content
    content = registry_path.read_text(encoding="utf-8")

    # Check if this is old format (no BEGIN_ENTRIES marker)
    if "<!-- BEGIN_ENTRIES -->" not in content:
        # Migrate to new format by rebuilding from kits.toml
        config = load_project_config(project_dir)
        entries = []
        if config is not None:
            for kit_id_iter, installed_kit in config.kits.items():
                entries.append(
                    DocRegistryEntry(
                        kit_id=kit_id_iter,
                        version=installed_kit.version,
                        source_type=installed_kit.source_type,
                        include_path=f".erk/kits/{kit_id_iter}/registry-entry.md",
                    )
                )
        content = generate_doc_registry_content(entries)
        registry_path.write_text(content, encoding="utf-8")
        # Continue to add the new kit after migration
        # Fall through to parsing and adding logic below

    # Parse existing entries
    entries = parse_doc_registry_entries(content)

    # Check if kit already exists
    if any(e.kit_id == kit_id for e in entries):
        return  # Already present

    # Add new entry
    new_entry = DocRegistryEntry(
        kit_id=kit_id,
        version=version,
        source_type=source_type,
        include_path=f".erk/kits/{kit_id}/registry-entry.md",
    )
    entries.append(new_entry)

    # Regenerate registry (will be sorted alphabetically)
    new_content = generate_doc_registry_content(entries)
    registry_path.write_text(new_content, encoding="utf-8")


def remove_kit_from_registry(kit_id: str, project_dir: Path) -> None:
    """Remove kit from registry and delete its registry files.

    Args:
        kit_id: Kit identifier
        project_dir: Project root directory
    """
    registry_path = project_dir / ".erk" / "kits" / "kit-registry.md"

    # Remove entry from registry if it exists
    if registry_path.exists():
        content = registry_path.read_text(encoding="utf-8")

        # Check if new structured format
        if "<!-- BEGIN_ENTRIES -->" in content:
            # Parse entries and filter out removed kit
            entries = parse_doc_registry_entries(content)
            entries = [e for e in entries if e.kit_id != kit_id]

            # Regenerate registry
            new_content = generate_doc_registry_content(entries)
            registry_path.write_text(new_content, encoding="utf-8")
        else:
            # Old format - simple line removal
            include_line = f"@.erk/kits/{kit_id}/registry-entry.md"
            lines = content.split("\n")
            filtered_lines = []

            for line in lines:
                if line == include_line:
                    # Remove this line and any preceding blank line
                    if filtered_lines and not filtered_lines[-1].strip():
                        filtered_lines.pop()
                    continue
                filtered_lines.append(line)

            registry_path.write_text("\n".join(filtered_lines), encoding="utf-8")

    # Delete kit registry directory
    kit_registry_dir = project_dir / ".erk" / "kits" / kit_id
    if kit_registry_dir.exists():
        shutil.rmtree(kit_registry_dir)


def rebuild_registry(project_dir: Path, config: ProjectConfig) -> None:
    """Rebuild entire registry from installed kits using new structured format.

    Args:
        project_dir: Project root directory
        config: Project configuration with installed kits

    Raises:
        Exception: With list of kits that failed regeneration
    """
    from erk.kits.io.manifest import load_kit_manifest
    from erk.kits.sources.bundled import BundledKitSource
    from erk.kits.sources.resolver import KitResolver
    from erk.kits.sources.standalone import StandalonePackageSource

    registry_path = project_dir / ".erk" / "kits" / "kit-registry.md"

    failures = []
    entries = []

    # Create resolver to locate kit manifests
    sources = [BundledKitSource(), StandalonePackageSource()]
    resolver = KitResolver(sources)

    # Generate registry entry file for each installed kit
    for kit_id, installed_kit in config.kits.items():
        try:
            # Resolve kit to get manifest path
            resolved = resolver.resolve(kit_id)
            if resolved is None:
                failures.append(f"{kit_id}: could not resolve kit")
                continue

            manifest = load_kit_manifest(resolved.manifest_path)

            # Generate and write registry entry file
            entry_content = generate_registry_entry(
                kit_id, installed_kit.version, manifest, installed_kit
            )
            create_kit_registry_file(kit_id, entry_content, project_dir)

            # Add to entries list for main registry
            entries.append(
                DocRegistryEntry(
                    kit_id=kit_id,
                    version=installed_kit.version,
                    source_type=installed_kit.source_type,
                    include_path=f".erk/kits/{kit_id}/registry-entry.md",
                )
            )
        except Exception as e:
            failures.append(f"{kit_id}: {e!s}")

    if failures:
        raise Exception("Failed to regenerate registry for some kits:\n" + "\n".join(failures))

    # Generate new registry file with structured format
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    content = generate_doc_registry_content(entries)
    registry_path.write_text(content, encoding="utf-8")
