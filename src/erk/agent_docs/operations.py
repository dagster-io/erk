"""Operations for agent documentation management.

This module provides functionality for validating and syncing agent documentation
files with frontmatter metadata.
"""

import re
from collections.abc import Mapping
from pathlib import Path

import yaml

from erk.agent_docs.models import (
    AgentDocFrontmatter,
    AgentDocValidationResult,
    CategoryInfo,
    CollectedTripwire,
    DocInfo,
    SyncResult,
    Tripwire,
)

AGENT_DOCS_DIR = "docs/learned"
FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)

# Category descriptions for root index generation.
# Format: "Explore when [doing X]. Add docs here for [type of content]."
# To add a new category, add an entry here and run `erk docs sync`.
CATEGORY_DESCRIPTIONS: dict[str, str] = {
    "architecture": (
        "Explore when working on core patterns (dry-run, gateways, subprocess, shell integration). "
        "Add docs here for cross-cutting technical patterns."
    ),
    "cli": (
        "Explore when building CLI commands or output formatting. "
        "Add docs here for Click patterns and terminal UX."
    ),
    "commands": (
        "Explore when creating or optimizing slash commands. "
        "Add docs here for command authoring patterns."
    ),
    "erk": (
        "Explore when working with erk-specific workflows (worktrees, PR sync, Graphite). "
        "Add docs here for erk user-facing features."
    ),
    "hooks": (
        "Explore when creating or debugging hooks. Add docs here for hook development patterns."
    ),
    "planning": (
        "Explore when working with plans, .impl/ folders, or agent delegation. "
        "Add docs here for planning workflow patterns."
    ),
    "reference": (
        "Explore for API/format specifications. "
        "Add docs here for reference material that doesn't fit other categories."
    ),
    "sessions": (
        "Explore when working with session logs or parallel sessions. "
        "Add docs here for session management patterns."
    ),
    "testing": (
        "Explore when writing tests or debugging test infrastructure. "
        "Add docs here for testing patterns specific to erk."
    ),
    "textual": (
        "Explore when working with Textual framework. Add docs here for Textual-specific patterns."
    ),
    "tui": (
        "Explore when working on the erk TUI application. "
        "Add docs here for TUI feature implementation."
    ),
}

# Banner for auto-generated files
GENERATED_FILE_BANNER = """<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->

"""


def parse_frontmatter(content: str) -> tuple[dict[str, object] | None, str | None]:
    """Parse YAML frontmatter from markdown content.

    Args:
        content: The markdown file content.

    Returns:
        Tuple of (parsed_dict, error_message). If parsing succeeds,
        error_message is None. If parsing fails, parsed_dict is None.
    """
    match = FRONTMATTER_PATTERN.match(content)
    if match is None:
        return None, "No frontmatter found"

    frontmatter_text = match.group(1)
    try:
        parsed = yaml.safe_load(frontmatter_text)
        if not isinstance(parsed, dict):
            return None, "Frontmatter is not a valid YAML mapping"
        return parsed, None
    except yaml.YAMLError as e:
        return None, f"Invalid YAML: {e}"


def _validate_tripwires(
    tripwires_data: object,
) -> tuple[list[Tripwire], list[str]]:
    """Validate the tripwires field from frontmatter.

    Args:
        tripwires_data: Raw tripwires data from YAML.

    Returns:
        Tuple of (tripwires, errors). If validation succeeds,
        errors is empty and tripwires contains parsed Tripwire objects.
    """
    errors: list[str] = []
    tripwires: list[Tripwire] = []

    if not isinstance(tripwires_data, list):
        errors.append("Field 'tripwires' must be a list")
        return [], errors

    for i, item in enumerate(tripwires_data):
        if not isinstance(item, dict):
            errors.append(f"Field 'tripwires[{i}]' must be an object")
            continue

        action = item.get("action")
        warning = item.get("warning")

        if not action:
            errors.append(f"Field 'tripwires[{i}].action' is required")
        elif not isinstance(action, str):
            errors.append(f"Field 'tripwires[{i}].action' must be a string")

        if not warning:
            errors.append(f"Field 'tripwires[{i}].warning' is required")
        elif not isinstance(warning, str):
            errors.append(f"Field 'tripwires[{i}].warning' must be a string")

        # Only create Tripwire if both fields are valid strings
        if isinstance(action, str) and action and isinstance(warning, str) and warning:
            tripwires.append(Tripwire(action=action, warning=warning))

    return tripwires, errors


def validate_agent_doc_frontmatter(
    data: Mapping[str, object],
) -> tuple[AgentDocFrontmatter | None, list[str]]:
    """Validate parsed frontmatter against the schema.

    Args:
        data: Parsed YAML dictionary.

    Returns:
        Tuple of (frontmatter, errors). If validation succeeds,
        errors is empty. If validation fails, frontmatter is None.
    """
    errors: list[str] = []

    # Check title
    title = data.get("title")
    if not title:
        errors.append("Missing required field: title")
    elif not isinstance(title, str):
        errors.append("Field 'title' must be a string")

    # Check read_when
    read_when = data.get("read_when")
    if read_when is None:
        errors.append("Missing required field: read_when")
    elif not isinstance(read_when, list):
        errors.append("Field 'read_when' must be a list")
    elif len(read_when) == 0:
        errors.append("Field 'read_when' must not be empty")
    else:
        for i, item in enumerate(read_when):
            if not isinstance(item, str):
                errors.append(f"Field 'read_when[{i}]' must be a string")

    # Check tripwires (optional)
    tripwires: list[Tripwire] = []
    tripwires_data = data.get("tripwires")
    if tripwires_data is not None:
        tripwires, tripwire_errors = _validate_tripwires(tripwires_data)
        errors.extend(tripwire_errors)

    if errors:
        return None, errors

    # At this point, validation has ensured title is str and read_when is list[str]
    assert isinstance(title, str)
    assert isinstance(read_when, list)
    return AgentDocFrontmatter(
        title=title,
        read_when=read_when,
        tripwires=tripwires,
    ), []


def validate_agent_doc_file(file_path: Path, agent_docs_root: Path) -> AgentDocValidationResult:
    """Validate a single agent documentation file.

    Args:
        file_path: Absolute path to the markdown file.
        agent_docs_root: Path to the .erk/docs/agent directory.

    Returns:
        Validation result with any errors found.
    """
    rel_path = str(file_path.relative_to(agent_docs_root))

    if not file_path.exists():
        return AgentDocValidationResult(
            file_path=rel_path,
            frontmatter=None,
            errors=("File does not exist",),
        )

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return AgentDocValidationResult(
            file_path=rel_path,
            frontmatter=None,
            errors=(f"Cannot read file: {e}",),
        )

    parsed, parse_error = parse_frontmatter(content)
    if parse_error is not None:
        return AgentDocValidationResult(
            file_path=rel_path,
            frontmatter=None,
            errors=(parse_error,),
        )

    # parse_error is None means parsed is not None
    assert parsed is not None
    frontmatter, validation_errors = validate_agent_doc_frontmatter(parsed)
    return AgentDocValidationResult(
        file_path=rel_path,
        frontmatter=frontmatter,
        errors=tuple(validation_errors),
    )


def discover_agent_docs(agent_docs_root: Path) -> list[Path]:
    """Discover all markdown files in the agent docs directory.

    Args:
        agent_docs_root: Path to the .erk/docs/agent directory.

    Returns:
        List of paths to markdown files, sorted alphabetically.
    """
    if not agent_docs_root.exists():
        return []

    files: list[Path] = []
    for md_file in agent_docs_root.rglob("*.md"):
        # Skip index files (they are auto-generated)
        if md_file.name == "index.md":
            continue
        files.append(md_file)

    return sorted(files)


def validate_agent_docs(project_root: Path) -> list[AgentDocValidationResult]:
    """Validate all agent documentation files in a project.

    Args:
        project_root: Path to the project root.

    Returns:
        List of validation results for each file.
    """
    agent_docs_root = project_root / AGENT_DOCS_DIR
    if not agent_docs_root.exists():
        return []

    files = discover_agent_docs(agent_docs_root)
    results: list[AgentDocValidationResult] = []

    for file_path in files:
        result = validate_agent_doc_file(file_path, agent_docs_root)
        results.append(result)

    return results


def collect_tripwires(project_root: Path) -> list[CollectedTripwire]:
    """Collect all tripwires from agent documentation frontmatter.

    Args:
        project_root: Path to the project root.

    Returns:
        List of collected tripwires with their source documentation info.
    """
    agent_docs_root = project_root / AGENT_DOCS_DIR
    if not agent_docs_root.exists():
        return []

    files = discover_agent_docs(agent_docs_root)
    tripwires: list[CollectedTripwire] = []

    for file_path in files:
        result = validate_agent_doc_file(file_path, agent_docs_root)
        if not result.is_valid or result.frontmatter is None:
            continue

        rel_path = str(file_path.relative_to(agent_docs_root))

        for tripwire in result.frontmatter.tripwires:
            tripwires.append(
                CollectedTripwire(
                    action=tripwire.action,
                    warning=tripwire.warning,
                    doc_path=rel_path,
                    doc_title=result.frontmatter.title,
                )
            )

    return tripwires


def generate_tripwires_doc(tripwires: list[CollectedTripwire]) -> str:
    """Generate content for the tripwires.md file.

    Args:
        tripwires: List of collected tripwires.

    Returns:
        Generated markdown content for the tripwires reference document.
    """
    # Note: Banner goes AFTER frontmatter so YAML parsing works correctly
    lines = [
        "---",
        "title: Generated Tripwires",
        "read_when:",
        '  - "checking tripwire rules"',
        "---",
        "",
        GENERATED_FILE_BANNER.rstrip(),
        "",
        "# Tripwires",
        "",
        "Action-triggered rules that fire when you're about to perform specific actions.",
        "",
    ]

    if not tripwires:
        lines.append("*No tripwires defined.*")
        lines.append("")
        return "\n".join(lines)

    for tripwire in tripwires:
        # Format: **CRITICAL: Before [action]** → Read [doc-path] first. [warning]
        lines.append(
            f"**CRITICAL: Before {tripwire.action}** → "
            f"Read [{tripwire.doc_title}]({tripwire.doc_path}) first. "
            f"{tripwire.warning}"
        )
        lines.append("")

    return "\n".join(lines)


def collect_valid_docs(project_root: Path) -> tuple[list[DocInfo], list[CategoryInfo], int]:
    """Collect all valid documentation files organized by category.

    Args:
        project_root: Path to the project root.

    Returns:
        Tuple of (uncategorized_docs, categories, invalid_count).
    """
    agent_docs_root = project_root / AGENT_DOCS_DIR
    if not agent_docs_root.exists():
        return [], [], 0

    files = discover_agent_docs(agent_docs_root)
    uncategorized: list[DocInfo] = []
    categories: dict[str, list[DocInfo]] = {}
    invalid_count = 0

    for file_path in files:
        result = validate_agent_doc_file(file_path, agent_docs_root)
        if not result.is_valid or result.frontmatter is None:
            invalid_count += 1
            continue

        rel_path = file_path.relative_to(agent_docs_root)
        doc_info = DocInfo(
            rel_path=str(rel_path),
            frontmatter=result.frontmatter,
        )

        # Check if in subdirectory (category)
        if len(rel_path.parts) > 1:
            category = rel_path.parts[0]
            if category not in categories:
                categories[category] = []
            categories[category].append(doc_info)
        else:
            uncategorized.append(doc_info)

    # Convert to CategoryInfo list
    category_list = [
        CategoryInfo(
            name=name,
            docs=tuple(sorted(docs, key=lambda d: d.rel_path)),
        )
        for name, docs in sorted(categories.items())
    ]

    return sorted(uncategorized, key=lambda d: d.rel_path), category_list, invalid_count


def generate_root_index(
    uncategorized: list[DocInfo],
    categories: list[CategoryInfo],
) -> str:
    """Generate content for the root index.md file.

    Uses bullet list format instead of tables to avoid merge conflicts.
    Each entry is independent - no separator rows that span all entries.

    Args:
        uncategorized: Docs at the root level.
        categories: List of category directories with their docs.

    Returns:
        Generated markdown content.
    """
    lines = [GENERATED_FILE_BANNER.rstrip(), "", "# Agent Documentation", ""]

    if categories:
        lines.append("## Categories")
        lines.append("")
        for category in categories:
            description = CATEGORY_DESCRIPTIONS.get(category.name)
            if description:
                lines.append(f"- [{category.name}/]({category.name}/) — {description}")
            else:
                lines.append(f"- [{category.name}/]({category.name}/)")
        lines.append("")

    if uncategorized:
        lines.append("## Uncategorized")
        lines.append("")
        for doc in uncategorized:
            read_when = ", ".join(doc.frontmatter.read_when)
            lines.append(f"- **[{doc.rel_path}]({doc.rel_path})** — {read_when}")
        lines.append("")

    if not categories and not uncategorized:
        lines.append("*No documentation files found.*")
        lines.append("")

    return "\n".join(lines)


def generate_category_index(category: CategoryInfo) -> str:
    """Generate content for a category's index.md file.

    Uses bullet list format instead of tables to avoid merge conflicts.
    Each entry is independent - no separator rows that span all entries.

    Args:
        category: Category information with docs.

    Returns:
        Generated markdown content.
    """
    # Title case the category name
    title = category.name.replace("-", " ").replace("_", " ").title()

    lines = [GENERATED_FILE_BANNER.rstrip(), "", f"# {title} Documentation", ""]

    for doc in category.docs:
        # Use just the filename for relative links within category
        filename = Path(doc.rel_path).name
        read_when = ", ".join(doc.frontmatter.read_when)
        lines.append(f"- **[{filename}]({filename})** — {read_when}")

    lines.append("")
    return "\n".join(lines)


def _update_index_file(
    index_path: Path,
    content: str,
    created: list[str],
    updated: list[str],
    unchanged: list[str],
    dry_run: bool,
) -> None:
    """Update an index file if content changed.

    Args:
        index_path: Path to the index file.
        content: New content to write.
        created: List to append if file was created.
        updated: List to append if file was updated.
        unchanged: List to append if file was unchanged.
        dry_run: If True, don't actually write.
    """
    rel_path = str(index_path.relative_to(index_path.parent.parent.parent))

    if not index_path.exists():
        if not dry_run:
            index_path.write_text(content, encoding="utf-8")
        created.append(rel_path)
        return

    existing = index_path.read_text(encoding="utf-8")
    if existing == content:
        unchanged.append(rel_path)
        return

    if not dry_run:
        index_path.write_text(content, encoding="utf-8")
    updated.append(rel_path)


def _update_generated_file(
    file_path: Path,
    content: str,
    created: list[str],
    updated: list[str],
    unchanged: list[str],
    dry_run: bool,
    agent_docs_root: Path,
) -> None:
    """Update a generated file if content changed.

    Args:
        file_path: Path to the generated file.
        content: New content to write.
        created: List to append if file was created.
        updated: List to append if file was updated.
        unchanged: List to append if file was unchanged.
        dry_run: If True, don't actually write.
        agent_docs_root: Path to .erk/docs/agent/ for relative path calculation.
    """
    rel_path = str(file_path.relative_to(agent_docs_root.parent.parent))

    if not file_path.exists():
        if not dry_run:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
        created.append(rel_path)
        return

    existing = file_path.read_text(encoding="utf-8")
    if existing == content:
        unchanged.append(rel_path)
        return

    if not dry_run:
        file_path.write_text(content, encoding="utf-8")
    updated.append(rel_path)


def sync_agent_docs(project_root: Path, *, dry_run: bool) -> SyncResult:
    """Sync agent documentation index files from frontmatter.

    Generates index.md files for the root .erk/docs/agent/ directory and
    each subdirectory (category) that contains 2+ docs. Also generates
    the .erk/docs/agent/tripwires.md file from tripwire definitions.

    Args:
        project_root: Path to the project root.
        dry_run: If True, don't write files, just report what would change.

    Returns:
        SyncResult with lists of created, updated, and unchanged files.
    """
    agent_docs_root = project_root / AGENT_DOCS_DIR
    if not agent_docs_root.exists():
        return SyncResult(
            created=(),
            updated=(),
            unchanged=(),
            skipped_invalid=0,
            tripwires_count=0,
        )

    uncategorized, categories, invalid_count = collect_valid_docs(project_root)

    created: list[str] = []
    updated: list[str] = []
    unchanged: list[str] = []

    # Generate root index
    root_index_path = agent_docs_root / "index.md"
    root_content = generate_root_index(uncategorized, categories)
    _update_index_file(root_index_path, root_content, created, updated, unchanged, dry_run)

    # Generate category indexes (only for categories with 2+ docs)
    for category in categories:
        if len(category.docs) < 2:
            continue

        category_index_path = agent_docs_root / category.name / "index.md"
        category_content = generate_category_index(category)
        _update_index_file(
            category_index_path, category_content, created, updated, unchanged, dry_run
        )

    # Collect and generate tripwires
    tripwires = collect_tripwires(project_root)
    tripwires_count = len(tripwires)

    if tripwires:
        tripwires_path = agent_docs_root / "tripwires.md"
        tripwires_content = generate_tripwires_doc(tripwires)
        _update_generated_file(
            tripwires_path,
            tripwires_content,
            created,
            updated,
            unchanged,
            dry_run,
            agent_docs_root,
        )

    return SyncResult(
        created=tuple(created),
        updated=tuple(updated),
        unchanged=tuple(unchanged),
        skipped_invalid=invalid_count,
        tripwires_count=tripwires_count,
    )
