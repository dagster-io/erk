"""Metadata block helpers for tripwire-candidates on learn plan issues.

Provides rendering and extraction of structured tripwire candidate data
stored as metadata block comments on GitHub issues. This replaces the
regex-based extraction from learn plan markdown.
"""

import json
import logging
from dataclasses import dataclass

from erk_shared.gateway.github.metadata.core import (
    find_metadata_block,
    render_metadata_block,
)
from erk_shared.gateway.github.metadata.types import MetadataBlock

logger = logging.getLogger(__name__)

TRIPWIRE_CANDIDATES_KEY = "tripwire-candidates"


@dataclass(frozen=True)
class TripwireCandidate:
    """A tripwire candidate extracted from a learn plan.

    Attributes:
        action: The action pattern to detect (e.g., "writing to /tmp/").
        warning: The warning message to display when action is detected.
        target_doc_path: Relative path to the target doc (e.g., "architecture/foo.md").
    """

    action: str
    warning: str
    target_doc_path: str


def render_tripwire_candidates_comment(candidates: list[TripwireCandidate]) -> str:
    """Format tripwire candidates as a metadata block comment body.

    Creates a metadata block with key "tripwire-candidates" containing
    the candidates as a YAML list.

    Args:
        candidates: List of tripwire candidates to render.

    Returns:
        Rendered metadata block markdown ready to post as a GitHub comment.
    """
    candidates_data = [
        {
            "action": c.action,
            "warning": c.warning,
            "target_doc_path": c.target_doc_path,
        }
        for c in candidates
    ]

    block = MetadataBlock(
        key=TRIPWIRE_CANDIDATES_KEY,
        data={"candidates": candidates_data},
    )
    return render_metadata_block(block)


def extract_tripwire_candidates_from_comments(
    comments: list[str],
) -> list[TripwireCandidate]:
    """Scan issue comments for a tripwire-candidates metadata block.

    Looks through all comments for a metadata block with key
    "tripwire-candidates" and extracts the structured candidate data.

    Args:
        comments: List of issue comment bodies.

    Returns:
        List of TripwireCandidate objects. Empty list if no block found
        or on any parse failure (fail-open).
    """
    for comment_body in comments:
        block = find_metadata_block(comment_body, TRIPWIRE_CANDIDATES_KEY)
        if block is None:
            continue

        candidates_raw = block.data.get("candidates")
        if not isinstance(candidates_raw, list):
            logger.debug("tripwire-candidates block has no valid 'candidates' list")
            return []

        results: list[TripwireCandidate] = []
        for entry in candidates_raw:
            if not isinstance(entry, dict):
                continue
            action = entry.get("action")
            warning = entry.get("warning")
            target_doc_path = entry.get("target_doc_path")
            if (
                not isinstance(action, str)
                or not isinstance(warning, str)
                or not isinstance(target_doc_path, str)
            ):
                continue
            results.append(
                TripwireCandidate(
                    action=action,
                    warning=warning,
                    target_doc_path=target_doc_path,
                )
            )
        return results

    return []


def validate_candidates_json(json_path: str) -> list[TripwireCandidate]:
    """Read and validate a tripwire candidates JSON file.

    Reads JSON from a file path and validates the structure matches
    the expected format: {"candidates": [{"action": ..., "warning": ..., "target_doc_path": ...}]}

    Args:
        json_path: Path to the JSON file.

    Returns:
        List of validated TripwireCandidate objects.

    Raises:
        ValueError: If the file content is invalid or missing required fields.
        FileNotFoundError: If the file does not exist.
    """
    import pathlib

    path = pathlib.Path(json_path)
    if not path.is_file():
        raise FileNotFoundError(f"Candidates file not found: {json_path}")

    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)

    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object, got {type(data).__name__}")

    candidates_raw = data.get("candidates")
    if not isinstance(candidates_raw, list):
        raise ValueError("Missing or invalid 'candidates' list in JSON")

    results: list[TripwireCandidate] = []
    for i, entry in enumerate(candidates_raw):
        if not isinstance(entry, dict):
            raise ValueError(f"Candidate at index {i} is not an object")
        action = entry.get("action")
        warning = entry.get("warning")
        target_doc_path = entry.get("target_doc_path")
        if not isinstance(action, str):
            raise ValueError(f"Candidate at index {i} missing 'action' string")
        if not isinstance(warning, str):
            raise ValueError(f"Candidate at index {i} missing 'warning' string")
        if not isinstance(target_doc_path, str):
            raise ValueError(f"Candidate at index {i} missing 'target_doc_path' string")
        results.append(
            TripwireCandidate(
                action=action,
                warning=warning,
                target_doc_path=target_doc_path,
            )
        )

    return results
