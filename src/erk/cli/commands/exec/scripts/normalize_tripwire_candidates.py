"""Normalize agent-produced tripwire candidate JSON before validation.

Usage:
    erk exec normalize-tripwire-candidates --candidates-file <path>

Reads a JSON file produced by the tripwire extraction agent and normalizes
common schema drift patterns in-place:

- Root key: ``tripwire_candidates`` → ``candidates``
- Field mapping: ``description`` → ``warning``, ``title``/``name`` → ``action``
- Extra field stripping: only ``action``, ``warning``, ``target_doc_path`` kept

Exit Codes:
    0: Success (file normalized or already correct)
    1: Error (file not found, unparseable JSON)
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import click

from erk_shared.gateway.github.metadata.tripwire_candidates import (
    InvalidTripwireCandidates,
    validate_candidates_data,
)

CANONICAL_FIELDS = frozenset({"action", "warning", "target_doc_path"})

# Maps drifted root keys to the canonical root key.
ROOT_KEY_ALIASES: dict[str, str] = {
    "tripwire_candidates": "candidates",
}

# Maps drifted candidate field names to canonical field names.
FIELD_ALIASES: dict[str, str] = {
    "description": "warning",
    "title": "action",
    "name": "action",
    "trigger_pattern": "action",
}


@dataclass(frozen=True)
class NormalizeSuccess:
    """Success response for tripwire candidates normalization."""

    success: bool
    normalized: bool
    count: int


@dataclass(frozen=True)
class NormalizeError:
    """Error response for tripwire candidates normalization."""

    success: bool
    error: str


def normalize_candidates_data(data: dict) -> tuple[dict, bool]:
    """Normalize a parsed tripwire candidates dict.

    Returns the normalized dict and whether any changes were made.
    """
    changed = False

    # Root key normalization
    if "candidates" not in data:
        for alias, canonical in ROOT_KEY_ALIASES.items():
            if alias in data:
                data[canonical] = data.pop(alias)
                changed = True
                break

    candidates_raw = data.get("candidates")
    if not isinstance(candidates_raw, list):
        return data, changed

    normalized_candidates: list[dict[str, Any]] = []
    for entry in candidates_raw:
        if not isinstance(entry, dict):
            continue

        normalized_entry: dict[str, Any] = {}

        # Copy canonical fields first
        for field in CANONICAL_FIELDS:
            if field in entry:
                normalized_entry[field] = entry[field]

        # Apply field aliases for missing canonical fields
        for alias, canonical in FIELD_ALIASES.items():
            if canonical not in normalized_entry and alias in entry:
                normalized_entry[canonical] = entry[alias]
                changed = True

        # Detect extra field stripping
        original_keys = set(entry.keys())
        if original_keys != set(normalized_entry.keys()):
            changed = True

        normalized_candidates.append(normalized_entry)

    if normalized_candidates != candidates_raw:
        changed = True

    data["candidates"] = normalized_candidates
    return data, changed


@dataclass(frozen=True)
class UnsalvageableInput:
    """Input too structurally broken for normalization."""

    reason: str


def check_salvageable(data: Any) -> UnsalvageableInput | None:
    """Reject inputs too structurally broken for normalization.

    Returns None if the data is salvageable, or UnsalvageableInput with a reason
    if it cannot be normalized.
    """
    if not isinstance(data, dict):
        return UnsalvageableInput(reason=f"Expected JSON object, got {type(data).__name__}")
    all_candidate_keys = {"candidates"} | set(ROOT_KEY_ALIASES.keys())
    if not any(key in data for key in all_candidate_keys):
        return UnsalvageableInput(
            reason="No 'candidates' key (or known alias) found in JSON object"
        )
    for key in all_candidate_keys:
        if key in data:
            if not isinstance(data[key], list):
                return UnsalvageableInput(reason=f"'{key}' value is not a list")
            break
    return None


@click.command(name="normalize-tripwire-candidates")
@click.option("--candidates-file", required=True, help="Path to tripwire-candidates.json")
def normalize_tripwire_candidates(
    *,
    candidates_file: str,
) -> None:
    """Normalize agent-produced tripwire candidate JSON in-place."""
    path = Path(candidates_file)
    if not path.is_file():
        error_response = NormalizeError(
            success=False, error=f"Candidates file not found: {candidates_file}"
        )
        click.echo(json.dumps(asdict(error_response)), err=True)
        raise SystemExit(1)

    raw = path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        error_response = NormalizeError(success=False, error=f"Invalid JSON: {exc}")
        click.echo(json.dumps(asdict(error_response)), err=True)
        raise SystemExit(1) from None

    unsalvageable = check_salvageable(data)
    if unsalvageable is not None:
        error_response = NormalizeError(success=False, error=unsalvageable.reason)
        click.echo(json.dumps(asdict(error_response)), err=True)
        raise SystemExit(1)

    normalized_data, changed = normalize_candidates_data(data)

    # Post-normalization validation gate
    validation_result = validate_candidates_data(normalized_data)
    if isinstance(validation_result, InvalidTripwireCandidates):
        error_response = NormalizeError(success=False, error=validation_result.message)
        click.echo(json.dumps(asdict(error_response)), err=True)
        raise SystemExit(1)

    if changed:
        path.write_text(json.dumps(normalized_data, indent=2) + "\n", encoding="utf-8")

    candidate_count = len(validation_result.candidates)
    success_response = NormalizeSuccess(success=True, normalized=changed, count=candidate_count)
    click.echo(json.dumps(asdict(success_response)))
