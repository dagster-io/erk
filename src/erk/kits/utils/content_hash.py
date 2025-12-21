"""Content hash utilities for artifact modification detection."""

import hashlib
from pathlib import Path


def compute_content_hash(content: str) -> str:
    """Compute SHA-256 hash of content.

    Args:
        content: Text content to hash

    Returns:
        Hash string in format "sha256:<hex_digest>"
    """
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of file content.

    Args:
        file_path: Path to file

    Returns:
        Hash string in format "sha256:<hex_digest>"
    """
    content = file_path.read_text(encoding="utf-8")
    return compute_content_hash(content)


def is_file_modified(file_path: Path, stored_hash: str) -> bool:
    """Check if file has been modified from its stored hash.

    Args:
        file_path: Path to file to check
        stored_hash: Previously stored hash (e.g., "sha256:abc123...")

    Returns:
        True if file is modified (hash differs), False if unchanged.
        Also returns True if stored_hash is empty (legacy migration).
    """
    # Empty hash means legacy format - treat as modified to trigger reinstall
    if not stored_hash:
        return True

    if not file_path.exists():
        return False  # File doesn't exist, not "modified"

    current_hash = compute_file_hash(file_path)
    return current_hash != stored_hash
