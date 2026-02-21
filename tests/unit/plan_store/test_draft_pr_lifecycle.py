"""Tests for draft PR lifecycle build/parse functions."""

from erk_shared.plan_store.draft_pr_lifecycle import (
    _LEGACY_DETAILS_OPEN,
    DETAILS_CLOSE,
    DETAILS_OPEN,
    PLAN_CONTENT_SEPARATOR,
    build_original_plan_section,
    build_plan_stage_body,
    extract_metadata_prefix,
    extract_plan_content,
)

# =============================================================================
# build_plan_stage_body
# =============================================================================


def test_build_plan_stage_body() -> None:
    """Stage 1 body contains metadata + separator + details-wrapped plan."""
    result = build_plan_stage_body("metadata block", "plan content")
    assert "metadata block" in result
    assert PLAN_CONTENT_SEPARATOR in result
    assert DETAILS_OPEN in result
    assert "plan content" in result
    assert DETAILS_CLOSE in result


def test_build_plan_stage_body_structure() -> None:
    """Stage 1 body has correct ordering: metadata, separator, details, content, close."""
    result = build_plan_stage_body("META", "PLAN")
    meta_idx = result.index("META")
    sep_idx = result.index(PLAN_CONTENT_SEPARATOR)
    open_idx = result.index(DETAILS_OPEN)
    plan_idx = result.index("PLAN")
    close_idx = result.index(DETAILS_CLOSE)
    assert meta_idx < sep_idx < open_idx < plan_idx < close_idx


# =============================================================================
# extract_plan_content
# =============================================================================


def test_extract_plan_content_from_plan_stage() -> None:
    """Extracts plan content from Stage 1 body (details-wrapped)."""
    body = build_plan_stage_body("metadata block", "plan content here")
    assert extract_plan_content(body) == "plan content here"


def test_extract_plan_content_from_implementation_stage() -> None:
    """Extracts plan content from Stage 2 body (AI summary before details)."""
    metadata = "metadata block"
    plan = "original plan"
    ai_summary = "## Summary\n\nThis PR does things."

    body = (
        metadata
        + PLAN_CONTENT_SEPARATOR
        + ai_summary
        + "\n\n"
        + DETAILS_OPEN
        + plan
        + DETAILS_CLOSE
    )
    assert extract_plan_content(body) == plan


def test_extract_plan_content_from_legacy_details_format() -> None:
    """Extracts plan content from old format without <code> tags in summary."""
    body = (
        "metadata block"
        + PLAN_CONTENT_SEPARATOR
        + _LEGACY_DETAILS_OPEN
        + "legacy plan content"
        + DETAILS_CLOSE
    )
    assert extract_plan_content(body) == "legacy plan content"


def test_extract_plan_content_backward_compat() -> None:
    """Falls back to old format (content after separator, no details tags)."""
    body = (
        "<!-- erk:metadata-block:plan-header -->\n"
        "metadata\n"
        "<!-- /erk:metadata-block -->\n\n---\n\n"
        "plan content here"
    )
    assert extract_plan_content(body) == "plan content here"


def test_extract_plan_content_no_separator() -> None:
    """Returns full body when no separator or details tags found."""
    body = "just plain text"
    assert extract_plan_content(body) == "just plain text"


# =============================================================================
# extract_metadata_prefix
# =============================================================================


def test_extract_metadata_prefix() -> None:
    """Extracts metadata block + separator."""
    body = (
        "<!-- erk:metadata-block:plan-header -->\n"
        "metadata\n"
        "<!-- /erk:metadata-block -->\n\n---\n\n"
        "rest of content"
    )
    prefix = extract_metadata_prefix(body)
    assert "<!-- erk:metadata-block:plan-header -->" in prefix
    assert prefix.endswith(PLAN_CONTENT_SEPARATOR)


def test_extract_metadata_prefix_no_separator() -> None:
    """Returns empty string when no separator found."""
    body = "no separator here"
    assert extract_metadata_prefix(body) == ""


def test_extract_metadata_prefix_ignores_footer_separator() -> None:
    """Returns empty when separator exists but no metadata block."""
    body = (
        "## Summary\n\nSome content\n\n"
        "**Remotely executed:** [Run #123](url)\n\n---\n\n"
        "To checkout..."
    )
    assert extract_metadata_prefix(body) == ""


def test_extract_plan_content_ignores_footer_separator() -> None:
    """Returns full body when separator exists but no metadata block."""
    body = (
        "## Summary\n\nSome content\n\n"
        "**Remotely executed:** [Run #123](url)\n\n---\n\n"
        "To checkout..."
    )
    assert extract_plan_content(body) == body


# =============================================================================
# build_original_plan_section
# =============================================================================


def test_build_original_plan_section() -> None:
    """Builds a details section with original-plan summary."""
    result = build_original_plan_section("my plan content")
    assert DETAILS_OPEN in result
    assert "my plan content" in result
    assert DETAILS_CLOSE in result
    assert result.startswith("\n\n")


# =============================================================================
# Roundtrip
# =============================================================================


def test_build_and_extract_roundtrip() -> None:
    """build_plan_stage_body + extract_plan_content roundtrips cleanly."""
    plan = "# My Plan\n\nStep 1: Do things.\nStep 2: More things."
    body = build_plan_stage_body("<!-- metadata -->", plan)
    assert extract_plan_content(body) == plan
