"""Validation logic for @ file references.

This module provides filesystem-aware validation for @ references parsed
by the at_reference module. It checks that referenced files exist and
that fragment anchors (if specified) match headings in target files.
"""

import os
import re
from dataclasses import dataclass
from pathlib import Path

from erk.kits.io.at_reference import AtReference, parse_at_references


@dataclass(frozen=True)
class BrokenLink:
    """A broken @ reference.

    Attributes:
        source_file: Path to the file containing the broken reference
        reference: The AtReference that is broken
        resolved_path: The path we attempted to resolve to
        error_type: Type of error ("missing_file" or "missing_fragment")
        error_detail: Additional detail about the error (e.g., fragment name)
    """

    source_file: Path
    reference: AtReference
    resolved_path: Path
    error_type: str
    error_detail: str | None = None


def heading_to_anchor(heading: str) -> str:
    """Convert markdown heading to anchor format (GitHub-style).

    GitHub-style anchor conversion:
    - Remove leading # characters and whitespace
    - Convert to lowercase
    - Replace spaces with hyphens
    - Remove punctuation except hyphens
    - Collapse multiple hyphens

    Args:
        heading: Raw markdown heading text (e.g., "## My Section!")

    Returns:
        Anchor string (e.g., "my-section")
    """
    # Remove leading # characters and whitespace
    text = re.sub(r"^#+\s*", "", heading)

    # Convert to lowercase
    text = text.lower()

    # Replace spaces with hyphens
    text = text.replace(" ", "-")

    # Remove punctuation except hyphens (keep alphanumeric and hyphens)
    text = re.sub(r"[^\w\-]", "", text)

    # Collapse multiple hyphens
    text = re.sub(r"-+", "-", text)

    # Remove leading/trailing hyphens
    text = text.strip("-")

    return text


def _resolve_relative_path_from_symlink(
    file_path_str: str,
    source_file: Path,
) -> Path:
    """Resolve relative @ reference path from source file location.

    When source_file is a symlink, resolves from the symlink's location
    (not the target's location) to match Claude Code's behavior.

    Uses os.path.normpath to normalize .. and . components without
    following symlinks, unlike Path.resolve() which follows them.

    Args:
        file_path_str: The relative path string from the @ reference
        source_file: Path to the source file (may be a symlink)

    Returns:
        Normalized path without following symlinks
    """
    # Get the literal parent path without following symlinks
    parent = source_file.parent

    # Construct the path
    raw_path = parent / file_path_str

    # Normalize .. and . components manually without following symlinks
    # os.path.normpath doesn't follow symlinks, unlike Path.resolve()
    normalized = Path(os.path.normpath(str(raw_path)))

    return normalized


def extract_anchors(file_path: Path) -> set[str]:
    """Extract all heading anchors from a markdown file.

    Reads a markdown file and extracts all headings, converting them
    to GitHub-style anchors.

    Args:
        file_path: Path to the markdown file

    Returns:
        Set of anchor strings found in the file
    """
    if not file_path.exists():
        return set()

    content = file_path.read_text(encoding="utf-8")
    anchors: set[str] = set()

    # Match markdown headings (lines starting with one or more #)
    heading_pattern = re.compile(r"^(#+\s+.+)$", re.MULTILINE)

    for match in heading_pattern.finditer(content):
        heading = match.group(1)
        anchor = heading_to_anchor(heading)
        if anchor:  # Skip empty anchors
            anchors.add(anchor)

    return anchors


def validate_at_reference(
    reference: AtReference, source_file: Path, repo_root: Path
) -> list[BrokenLink]:
    """Validate a single @ reference.

    Validates that:
    1. The referenced file exists
    2. If a fragment is specified, the heading anchor exists in the target file

    Path resolution:
    - Absolute paths (starting with /) are resolved relative to repo root
    - Paths starting with .claude/ or .erk/ are resolved from repo root
    - Other relative paths are resolved relative to the source file's directory
    - Home directory paths (~/) are skipped (not validated)
    - Shell variable paths ($) are skipped (not validated)

    Args:
        reference: The AtReference to validate
        source_file: Path to the file containing the reference
        repo_root: Repository root path for resolving absolute paths

    Returns:
        List of BrokenLink objects (empty if valid, may contain multiple errors)
    """
    broken_links: list[BrokenLink] = []
    file_path_str = reference.file_path

    # Skip home directory paths (caller's responsibility to expand)
    if file_path_str.startswith("~"):
        return []

    # Skip shell variable paths (not supported)
    if "$" in file_path_str:
        return []

    # Resolve the path
    if file_path_str.startswith("/"):
        # Absolute path - relative to repo root
        resolved_path = repo_root / file_path_str.lstrip("/")
    elif file_path_str.startswith(".claude/") or file_path_str.startswith(".erk/"):
        # Repo-relative paths starting with .claude/ or .erk/ are resolved from repo root
        resolved_path = repo_root / file_path_str
    else:
        # Relative path - relative to source file's directory
        # Use symlink-aware resolution to match Claude Code's behavior:
        # When source_file is a symlink, resolve from the symlink's location,
        # not where it points to
        resolved_path = _resolve_relative_path_from_symlink(file_path_str, source_file)

    # Check if file exists
    file_missing = not resolved_path.exists()
    if file_missing:
        broken_links.append(
            BrokenLink(
                source_file=source_file,
                reference=reference,
                resolved_path=resolved_path,
                error_type="missing_file",
                error_detail=None,
            )
        )

    # Check fragment if present (even if file is missing - report both errors)
    if reference.fragment is not None:
        if file_missing:
            # File is missing, so fragment is also broken
            broken_links.append(
                BrokenLink(
                    source_file=source_file,
                    reference=reference,
                    resolved_path=resolved_path,
                    error_type="missing_fragment",
                    error_detail=reference.fragment,
                )
            )
        else:
            # File exists, check if fragment is valid
            anchors = extract_anchors(resolved_path)
            if reference.fragment not in anchors:
                broken_links.append(
                    BrokenLink(
                        source_file=source_file,
                        reference=reference,
                        resolved_path=resolved_path,
                        error_type="missing_fragment",
                        error_detail=reference.fragment,
                    )
                )

    return broken_links


def validate_links_in_file(file_path: Path, repo_root: Path) -> list[BrokenLink]:
    """Validate all @ references in a file.

    Args:
        file_path: Path to the markdown file to validate
        repo_root: Repository root path for resolving absolute paths

    Returns:
        List of BrokenLink objects for all broken references found
    """
    if not file_path.exists():
        return []

    content = file_path.read_text(encoding="utf-8")
    references = parse_at_references(content)
    broken_links: list[BrokenLink] = []

    for reference in references:
        broken_links.extend(validate_at_reference(reference, file_path, repo_root))

    return broken_links
