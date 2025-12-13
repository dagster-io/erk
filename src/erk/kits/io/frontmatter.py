"""Minimal frontmatter parsing for user metadata."""

import re
from dataclasses import dataclass

import yaml

FRONTMATTER_PATTERN = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


@dataclass(frozen=True)
class ArtifactFrontmatter:
    """Parsed frontmatter from an artifact file.

    Attributes:
        name: Artifact name (optional)
        description: Artifact description (optional)
        kit: Kit this artifact belongs to, or None for local-only artifacts
        raw: The full raw frontmatter dictionary for access to other fields

    Note:
        The kit field is read from the `erk.kit` namespace in frontmatter to avoid
        polluting the top-level namespace which may be used by Claude's skill system.
    """

    name: str | None
    description: str | None
    kit: str | None
    raw: dict


def parse_artifact_frontmatter(content: str) -> ArtifactFrontmatter | None:
    """Extract frontmatter metadata from an artifact file.

    Parses frontmatter and extracts known fields like name, description, kit.

    Args:
        content: Markdown content with potential frontmatter

    Returns:
        ArtifactFrontmatter if frontmatter exists, None otherwise
    """
    match = FRONTMATTER_PATTERN.search(content)
    if not match:
        return None

    yaml_content = match.group(1)
    data = yaml.safe_load(yaml_content)

    if data is None:
        return None

    # Remove internal metadata if present (legacy artifacts)
    if "__dot_agent" in data:
        del data["__dot_agent"]

    # Extract kit from erk namespace
    erk_data = data.get("erk", {})
    kit = erk_data.get("kit") if isinstance(erk_data, dict) else None

    return ArtifactFrontmatter(
        name=data.get("name"),
        description=data.get("description"),
        kit=kit,
        raw=data,
    )


def parse_user_metadata(content: str) -> dict | None:
    """Extract user-facing metadata from frontmatter.

    Only reads metadata like name, description, etc.

    Args:
        content: Markdown content with potential frontmatter

    Returns:
        Dictionary of user metadata or None if no frontmatter
    """
    match = FRONTMATTER_PATTERN.search(content)
    if not match:
        return None

    yaml_content = match.group(1)
    data = yaml.safe_load(yaml_content)

    # Remove internal metadata if present (legacy artifacts)
    if data and "__dot_agent" in data:
        del data["__dot_agent"]

    return data


def add_kit_to_frontmatter(content: str, kit_name: str) -> str:
    """Add or update kit field in artifact frontmatter.

    The kit field is placed under the `erk:` namespace to avoid polluting
    the top-level namespace which may be used by Claude's skill system.

    Args:
        content: Markdown content with potential frontmatter
        kit_name: Kit name to add to frontmatter

    Returns:
        Updated content with kit field in frontmatter under erk namespace
    """
    match = FRONTMATTER_PATTERN.search(content)

    if not match:
        # No frontmatter - create new frontmatter with kit field under erk namespace
        return f"---\nerk:\n  kit: {kit_name}\n---\n\n{content}"

    yaml_content = match.group(1)
    data = yaml.safe_load(yaml_content) or {}

    # Add/update kit field under erk namespace
    if "erk" not in data or not isinstance(data["erk"], dict):
        data["erk"] = {}
    data["erk"]["kit"] = kit_name

    # Reconstruct frontmatter with consistent ordering
    # Put name first, then description, then erk namespace, then rest
    ordered_data: dict = {}
    if "name" in data:
        ordered_data["name"] = data["name"]
    if "description" in data:
        ordered_data["description"] = data["description"]
    if "erk" in data:
        ordered_data["erk"] = data["erk"]
    for key, value in data.items():
        if key not in ordered_data:
            ordered_data[key] = value

    new_frontmatter = yaml.dump(
        ordered_data, default_flow_style=False, allow_unicode=True, sort_keys=False
    )
    rest_of_content = content[match.end() :]

    return f"---\n{new_frontmatter}---\n{rest_of_content}"
