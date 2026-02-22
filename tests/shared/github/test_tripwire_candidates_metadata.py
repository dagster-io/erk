"""Tests for tripwire candidates metadata block rendering and extraction."""

from pathlib import Path

from erk_shared.gateway.github.metadata.core import render_metadata_block
from erk_shared.gateway.github.metadata.tripwire_candidates import (
    InvalidTripwireCandidates,
    TripwireCandidate,
    ValidTripwireCandidates,
    extract_tripwire_candidates_from_comments,
    render_tripwire_candidates_comment,
    validate_candidates_data,
    validate_candidates_json,
)
from erk_shared.gateway.github.metadata.types import MetadataBlock


def test_render_and_extract_roundtrip() -> None:
    """Render candidates to a comment, then extract them back."""
    candidates = [
        TripwireCandidate(
            action="calling foo() directly",
            warning="Use foo_wrapper() instead.",
            target_doc_path="architecture/foo.md",
        ),
        TripwireCandidate(
            action="using bar without context",
            warning="Pass ctx to bar().",
            target_doc_path="cli/bar.md",
        ),
    ]

    comment_body = render_tripwire_candidates_comment(candidates)
    extracted = extract_tripwire_candidates_from_comments([comment_body])

    assert len(extracted) == 2
    assert extracted[0] == candidates[0]
    assert extracted[1] == candidates[1]


def test_extract_from_multiple_comments() -> None:
    """Find tripwire-candidates block among multiple comments."""
    candidates = [
        TripwireCandidate(
            action="using print()",
            warning="Use user_output() instead.",
            target_doc_path="cli/output-styling.md",
        ),
    ]

    comment_body = render_tripwire_candidates_comment(candidates)
    comments = [
        "This is a regular comment.",
        "Another unrelated comment with some markdown.",
        comment_body,
        "A comment after the metadata.",
    ]

    extracted = extract_tripwire_candidates_from_comments(comments)
    assert len(extracted) == 1
    assert extracted[0].action == "using print()"


def test_extract_from_empty_comments() -> None:
    """Return empty list when no comments exist."""
    assert extract_tripwire_candidates_from_comments([]) == []


def test_extract_from_comments_without_metadata() -> None:
    """Return empty list when no comment has the metadata block."""
    comments = [
        "Regular comment",
        "Another comment",
    ]
    assert extract_tripwire_candidates_from_comments(comments) == []


def test_render_empty_candidates() -> None:
    """Render with empty candidates list produces valid metadata block."""
    comment_body = render_tripwire_candidates_comment([])
    extracted = extract_tripwire_candidates_from_comments([comment_body])
    assert extracted == []


def test_extract_skips_invalid_entries() -> None:
    """Entries missing required fields are skipped."""
    block = MetadataBlock(
        key="tripwire-candidates",
        data={
            "candidates": [
                {
                    "action": "valid action",
                    "warning": "valid warning",
                    "target_doc_path": "foo.md",
                },
                {"action": "missing warning"},
                {"warning": "missing action"},
                {"action": "missing path", "warning": "has warning"},
                "not a dict",
            ]
        },
    )
    comment_body = render_metadata_block(block)
    extracted = extract_tripwire_candidates_from_comments([comment_body])

    assert len(extracted) == 1
    assert extracted[0].action == "valid action"


def test_validate_candidates_json(tmp_path: Path) -> None:
    """Validate a well-formed candidates JSON file."""
    json_content = (
        '{"candidates": [{"action": "doing X", "warning": "Do Y.", "target_doc_path": "foo.md"}]}'
    )
    json_file = tmp_path / "candidates.json"
    json_file.write_text(json_content, encoding="utf-8")

    result = validate_candidates_json(str(json_file))
    assert isinstance(result, ValidTripwireCandidates)
    assert len(result.candidates) == 1
    assert result.candidates[0].action == "doing X"
    assert result.candidates[0].warning == "Do Y."
    assert result.candidates[0].target_doc_path == "foo.md"


def test_validate_candidates_json_missing_file() -> None:
    """Return InvalidTripwireCandidates for missing file."""
    result = validate_candidates_json("/nonexistent/path.json")
    assert isinstance(result, InvalidTripwireCandidates)
    assert "not found" in result.reason


def test_validate_candidates_json_invalid_structure(tmp_path: Path) -> None:
    """Return InvalidTripwireCandidates for invalid JSON structure."""
    json_file = tmp_path / "bad.json"
    json_file.write_text(
        '{"candidates": [{"action": "no warning or path"}]}',
        encoding="utf-8",
    )

    result = validate_candidates_json(str(json_file))
    assert isinstance(result, InvalidTripwireCandidates)
    assert "missing 'warning' string" in result.reason


def test_validate_candidates_json_not_object(tmp_path: Path) -> None:
    """Return InvalidTripwireCandidates when JSON root is not an object."""
    json_file = tmp_path / "array.json"
    json_file.write_text("[1, 2, 3]", encoding="utf-8")

    result = validate_candidates_json(str(json_file))
    assert isinstance(result, InvalidTripwireCandidates)
    assert "Expected JSON object" in result.reason


def test_validate_candidates_json_empty_candidates(tmp_path: Path) -> None:
    """Empty candidates list is valid."""
    json_file = tmp_path / "empty.json"
    json_file.write_text('{"candidates": []}', encoding="utf-8")

    result = validate_candidates_json(str(json_file))
    assert isinstance(result, ValidTripwireCandidates)
    assert result.candidates == []


def test_validate_candidates_data_with_dict() -> None:
    """Validate candidates from a dict directly."""
    data = {
        "candidates": [
            {
                "action": "doing X",
                "warning": "Do Y.",
                "target_doc_path": "foo.md",
            },
            {
                "action": "doing A",
                "warning": "Do B.",
                "target_doc_path": "bar.md",
            },
        ]
    }

    result = validate_candidates_data(data)
    assert isinstance(result, ValidTripwireCandidates)
    assert len(result.candidates) == 2
    assert result.candidates[0] == TripwireCandidate(
        action="doing X", warning="Do Y.", target_doc_path="foo.md"
    )
    assert result.candidates[1] == TripwireCandidate(
        action="doing A", warning="Do B.", target_doc_path="bar.md"
    )


def test_invalid_tripwire_candidates_message_includes_schema() -> None:
    """InvalidTripwireCandidates.message includes schema, rules, and examples."""
    invalid = InvalidTripwireCandidates(
        raw_data={"candidates": [{"action": "no warning"}]},
        reason="Candidate at index 0 missing 'warning' string",
    )
    message = invalid.message
    assert "Expected schema" in message
    assert "action" in message and "warning" in message and "target_doc_path" in message
    assert "Root must be a JSON object" in message
    assert "Valid example" in message
    assert "Invalid example" in message


def test_invalid_tripwire_candidates_error_type() -> None:
    """InvalidTripwireCandidates.error_type is 'invalid-tripwire-candidates'."""
    invalid = InvalidTripwireCandidates(raw_data=None, reason="test")
    assert invalid.error_type == "invalid-tripwire-candidates"
