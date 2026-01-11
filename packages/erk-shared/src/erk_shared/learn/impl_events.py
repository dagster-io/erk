"""Extraction of implementation and learn events from GitHub issue comments.

This module provides functions to extract session IDs from comments that
contain erk metadata blocks for implementation and learn events.
"""

from erk_shared.github.metadata.core import extract_metadata_value


def extract_implementation_sessions(comments: list[str]) -> list[str]:
    """Extract session IDs from implementation event comments.

    Looks for erk:metadata-block:impl-started and erk:metadata-block:impl-ended
    comments and extracts session_id from the YAML content.

    Args:
        comments: List of comment bodies from a plan issue

    Returns:
        List of unique session IDs in order of first occurrence
    """
    session_ids: list[str] = []
    seen: set[str] = set()

    for comment in comments:
        # Check both impl-started and impl-ended blocks
        for block_key in ("impl-started", "impl-ended"):
            session_id = extract_metadata_value(comment, block_key, "session_id")
            if session_id is not None and session_id not in seen:
                session_ids.append(session_id)
                seen.add(session_id)

    return session_ids


def extract_learn_sessions(comments: list[str]) -> list[str]:
    """Extract session IDs from learn event comments.

    Looks for erk:metadata-block:learn-invoked comments and extracts
    session_id from the YAML content.

    Args:
        comments: List of comment bodies from a plan issue

    Returns:
        List of unique session IDs in order of first occurrence
    """
    session_ids: list[str] = []
    seen: set[str] = set()

    for comment in comments:
        session_id = extract_metadata_value(comment, "learn-invoked", "session_id")
        if session_id is not None and session_id not in seen:
            session_ids.append(session_id)
            seen.add(session_id)

    return session_ids
