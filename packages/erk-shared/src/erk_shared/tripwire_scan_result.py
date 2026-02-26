"""TypedDict definitions for tripwire-scan JSON output.

These types are the single source of truth for the JSON schema produced by
erk exec tripwire-scan and consumed by the tripwires review definition.
"""

from typing import Literal, TypedDict


class Tier1MatchDict(TypedDict):
    """A single file/line match for a Tier 1 pattern."""

    file: str
    line: int
    text: str


class Tier1ResultDict(TypedDict):
    """Result for a single Tier 1 tripwire pattern."""

    action: str
    pattern: str
    doc_path: str
    matches: list[Tier1MatchDict]


class Tier2EntryDict(TypedDict):
    """Compact Tier 2 entry for LLM evaluation."""

    category: str
    action: str
    doc_path: str
    summary: str


class TripwireScanSuccessDict(TypedDict):
    """Successful result from tripwire-scan command."""

    success: Literal[True]
    tier1_matches: list[Tier1ResultDict]
    tier1_clean: list[Tier1ResultDict]
    tier2_entries: list[Tier2EntryDict]
    categories_loaded: list[str]
    changed_files: list[str]


class TripwireScanErrorDict(TypedDict):
    """Error result from tripwire-scan command."""

    success: Literal[False]
    error: str
    message: str
