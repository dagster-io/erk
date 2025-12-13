"""Tests for agent frontmatter validation."""

from pathlib import Path

import yaml


def _get_repo_root() -> Path:
    """Get the repository root from this test file location."""
    # tests/core/foundation/test_agent_frontmatter.py -> repo root
    return Path(__file__).parent.parent.parent.parent


def _parse_frontmatter(content: str) -> dict | None:
    """Parse YAML frontmatter from a markdown file.

    Args:
        content: Full content of the markdown file

    Returns:
        Parsed frontmatter dictionary, or None if not found
    """
    lines = content.split("\n")
    if not lines or lines[0].strip() != "---":
        return None

    # Find the closing ---
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            frontmatter_text = "\n".join(lines[1:i])
            return yaml.safe_load(frontmatter_text)

    return None


def test_all_agents_have_single_line_descriptions() -> None:
    """Verify that all agent descriptions in frontmatter are single-line.

    Multi-line descriptions in YAML frontmatter (using | or >) cause formatting
    issues when displayed in Claude Code's agent listing. Descriptions should be
    concise, single-line strings.
    """
    repo_root = _get_repo_root()
    agents_dir = repo_root / ".claude" / "agents"

    if not agents_dir.exists():
        return  # No agents directory, nothing to test

    # Find all agent .md files
    agent_files = list(agents_dir.rglob("*.md"))

    # Ensure we found at least one (so test doesn't pass vacuously)
    assert len(agent_files) > 0, "Expected to find at least one agent file"

    multiline_descriptions: list[tuple[str, str]] = []

    for agent_file in agent_files:
        content = agent_file.read_text(encoding="utf-8")
        frontmatter = _parse_frontmatter(content)

        if frontmatter is None:
            continue

        description = frontmatter.get("description")
        if description is None:
            continue

        # Check if description contains newlines (multi-line)
        if isinstance(description, str) and "\n" in description:
            relative_path = agent_file.relative_to(repo_root)
            # Get first 50 chars of description for error message
            preview = description[:50].replace("\n", "\\n")
            multiline_descriptions.append((str(relative_path), preview))

    if multiline_descriptions:
        error_lines = [
            f"  - {path}: '{preview}...'" for path, preview in multiline_descriptions
        ]
        error_msg = (
            "Agent descriptions must be single-line. "
            f"Found {len(multiline_descriptions)} agent(s) with multi-line descriptions:\n"
            + "\n".join(error_lines)
        )
        raise AssertionError(error_msg)


def test_all_agents_have_description() -> None:
    """Verify that all agent frontmatter includes a description field.

    The description field is required for agents to display properly in
    Claude Code's agent listing.
    """
    repo_root = _get_repo_root()
    agents_dir = repo_root / ".claude" / "agents"

    if not agents_dir.exists():
        return  # No agents directory, nothing to test

    # Find all agent .md files
    agent_files = list(agents_dir.rglob("*.md"))

    # Ensure we found at least one (so test doesn't pass vacuously)
    assert len(agent_files) > 0, "Expected to find at least one agent file"

    missing_description: list[str] = []

    for agent_file in agent_files:
        content = agent_file.read_text(encoding="utf-8")
        frontmatter = _parse_frontmatter(content)

        if frontmatter is None:
            # No frontmatter is a separate concern
            continue

        if "description" not in frontmatter:
            relative_path = agent_file.relative_to(repo_root)
            missing_description.append(str(relative_path))

    if missing_description:
        error_msg = (
            f"Found {len(missing_description)} agent(s) missing 'description' field:\n"
            + "\n".join(f"  - {path}" for path in missing_description)
        )
        raise AssertionError(error_msg)
