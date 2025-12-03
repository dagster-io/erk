"""Operations for agent documentation management.

This module provides functionality for validating and syncing agent documentation
files with frontmatter metadata.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import yaml

from dot_agent_kit.models.agent_doc import AgentDocFrontmatter, AgentDocValidationResult

AGENT_DOCS_DIR = "docs/agent"
FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)


def parse_frontmatter(content: str) -> tuple[dict[str, object] | None, str | None]:
    """Parse YAML frontmatter from markdown content.

    Args:
        content: The markdown file content.

    Returns:
        Tuple of (parsed_dict, error_message). If parsing succeeds,
        error_message is None. If parsing fails, parsed_dict is None.
    """
    match = FRONTMATTER_PATTERN.match(content)
    if not match:
        return None, "No frontmatter found"

    frontmatter_text = match.group(1)
    try:
        parsed = yaml.safe_load(frontmatter_text)
        if not isinstance(parsed, dict):
            return None, "Frontmatter is not a valid YAML mapping"
        return parsed, None
    except yaml.YAMLError as e:
        return None, f"Invalid YAML: {e}"


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

    if errors:
        return None, errors

    # At this point, validation has ensured title is str and read_when is list[str]
    assert isinstance(title, str)
    assert isinstance(read_when, list)
    return AgentDocFrontmatter(
        title=title,
        read_when=read_when,
    ), []


def validate_agent_doc_file(file_path: Path, agent_docs_root: Path) -> AgentDocValidationResult:
    """Validate a single agent documentation file.

    Args:
        file_path: Absolute path to the markdown file.
        agent_docs_root: Path to the docs/agent directory.

    Returns:
        Validation result with any errors found.
    """
    rel_path = str(file_path.relative_to(agent_docs_root))

    if not file_path.exists():
        return AgentDocValidationResult(
            file_path=rel_path,
            frontmatter=None,
            errors=["File does not exist"],
        )

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return AgentDocValidationResult(
            file_path=rel_path,
            frontmatter=None,
            errors=[f"Cannot read file: {e}"],
        )

    parsed, parse_error = parse_frontmatter(content)
    if parse_error:
        return AgentDocValidationResult(
            file_path=rel_path,
            frontmatter=None,
            errors=[parse_error],
        )

    # parse_error is None means parsed is not None
    assert parsed is not None
    frontmatter, validation_errors = validate_agent_doc_frontmatter(parsed)
    return AgentDocValidationResult(
        file_path=rel_path,
        frontmatter=frontmatter,
        errors=validation_errors,
    )


def discover_agent_docs(agent_docs_root: Path) -> list[Path]:
    """Discover all markdown files in the agent docs directory.

    Args:
        agent_docs_root: Path to the docs/agent directory.

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


@dataclass(frozen=True)
class DocInfo:
    """Information about a documentation file.

    Attributes:
        rel_path: Relative path from docs/agent/.
        frontmatter: Parsed frontmatter.
    """

    rel_path: str
    frontmatter: AgentDocFrontmatter


@dataclass(frozen=True)
class CategoryInfo:
    """Information about a documentation category (subdirectory).

    Attributes:
        name: Category directory name.
        docs: List of documents in this category.
    """

    name: str
    docs: list[DocInfo]


@dataclass(frozen=True)
class SyncResult:
    """Result of syncing agent documentation indexes.

    Attributes:
        created: List of index files that were created.
        updated: List of index files that were updated.
        unchanged: List of index files that didn't need changes.
        skipped_invalid: Number of docs skipped due to invalid frontmatter.
    """

    created: list[str]
    updated: list[str]
    unchanged: list[str]
    skipped_invalid: int


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
        CategoryInfo(name=name, docs=sorted(docs, key=lambda d: d.rel_path))
        for name, docs in sorted(categories.items())
    ]

    return sorted(uncategorized, key=lambda d: d.rel_path), category_list, invalid_count


def generate_root_index(
    uncategorized: list[DocInfo],
    categories: list[CategoryInfo],
) -> str:
    """Generate content for the root index.md file.

    Args:
        uncategorized: Docs at the root level.
        categories: List of category directories with their docs.

    Returns:
        Generated markdown content.
    """
    lines = ["# Agent Documentation", ""]

    if categories:
        lines.append("## Categories")
        lines.append("")
        lines.append("| Category | Documents |")
        lines.append("|----------|-----------|")
        for category in categories:
            doc_names = ", ".join(Path(d.rel_path).stem for d in category.docs)
            lines.append(f"| [{category.name}/]({category.name}/) | {doc_names} |")
        lines.append("")

    if uncategorized:
        lines.append("## Uncategorized")
        lines.append("")
        lines.append("| Document | Read when... |")
        lines.append("|----------|--------------|")
        for doc in uncategorized:
            read_when = ", ".join(doc.frontmatter.read_when)
            lines.append(f"| [{doc.rel_path}]({doc.rel_path}) | {read_when} |")
        lines.append("")

    if not categories and not uncategorized:
        lines.append("*No documentation files found.*")
        lines.append("")

    return "\n".join(lines)


def generate_category_index(category: CategoryInfo) -> str:
    """Generate content for a category's index.md file.

    Args:
        category: Category information with docs.

    Returns:
        Generated markdown content.
    """
    # Title case the category name
    title = category.name.replace("-", " ").replace("_", " ").title()

    lines = [f"# {title} Documentation", ""]
    lines.append("| Document | Read when... |")
    lines.append("|----------|--------------|")

    for doc in category.docs:
        # Use just the filename for relative links within category
        filename = Path(doc.rel_path).name
        read_when = ", ".join(doc.frontmatter.read_when)
        lines.append(f"| [{filename}]({filename}) | {read_when} |")

    lines.append("")
    return "\n".join(lines)


def sync_agent_docs(project_root: Path, *, dry_run: bool = False) -> SyncResult:
    """Sync agent documentation index files from frontmatter.

    Generates index.md files for the root docs/agent/ directory and
    each subdirectory (category) that contains 2+ docs.

    Args:
        project_root: Path to the project root.
        dry_run: If True, don't write files, just report what would change.

    Returns:
        SyncResult with lists of created, updated, and unchanged files.
    """
    agent_docs_root = project_root / AGENT_DOCS_DIR
    if not agent_docs_root.exists():
        return SyncResult(created=[], updated=[], unchanged=[], skipped_invalid=0)

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

    return SyncResult(
        created=created,
        updated=updated,
        unchanged=unchanged,
        skipped_invalid=invalid_count,
    )


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
