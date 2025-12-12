"""Minimal frontmatter parsing for user metadata."""

import re

import yaml

FRONTMATTER_PATTERN = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


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
