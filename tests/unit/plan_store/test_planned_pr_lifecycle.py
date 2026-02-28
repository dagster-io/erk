"""Tests for draft PR lifecycle build/parse functions."""

from erk_shared.plan_store.planned_pr_lifecycle import (
    _LEGACY_DETAILS_OPEN,
    DETAILS_CLOSE,
    DETAILS_OPEN,
    PLAN_CONTENT_SEPARATOR,
    build_original_plan_section,
    build_plan_stage_body,
    extract_plan_content,
)

# =============================================================================
# build_plan_stage_body
# =============================================================================


def test_build_plan_stage_body() -> None:
    """Stage 1 body contains metadata + details-wrapped plan, no separator."""
    result = build_plan_stage_body("metadata block", "plan content", summary=None)
    assert "metadata block" in result
    assert PLAN_CONTENT_SEPARATOR not in result
    assert DETAILS_OPEN in result
    assert "plan content" in result
    assert DETAILS_CLOSE in result


def test_build_plan_stage_body_structure() -> None:
    """Stage 1 body has correct ordering: details, content, close, metadata."""
    result = build_plan_stage_body("META", "PLAN", summary=None)
    meta_idx = result.index("META")
    open_idx = result.index(DETAILS_OPEN)
    plan_idx = result.index("PLAN")
    close_idx = result.index(DETAILS_CLOSE)
    assert open_idx < plan_idx < close_idx < meta_idx


def test_build_plan_stage_body_with_summary() -> None:
    """Summary appears before the details section when provided."""
    result = build_plan_stage_body("META", "PLAN", summary="This plan does things.")
    assert "This plan does things." in result
    assert DETAILS_OPEN in result
    assert "PLAN" in result
    assert DETAILS_CLOSE in result
    assert "META" in result


def test_build_plan_stage_body_summary_structure() -> None:
    """Summary ordering: summary < details < plan < close < metadata."""
    result = build_plan_stage_body("META", "PLAN", summary="SUMMARY")
    summary_idx = result.index("SUMMARY")
    open_idx = result.index(DETAILS_OPEN)
    plan_idx = result.index("PLAN")
    close_idx = result.index(DETAILS_CLOSE)
    meta_idx = result.index("META")
    assert summary_idx < open_idx < plan_idx < close_idx < meta_idx


# =============================================================================
# extract_plan_content
# =============================================================================


def test_extract_plan_content_from_plan_stage() -> None:
    """Extracts plan content from Stage 1 body (details-wrapped)."""
    body = build_plan_stage_body("metadata block", "plan content here", summary=None)
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
    body = build_plan_stage_body("<!-- metadata -->", plan, summary=None)
    assert extract_plan_content(body) == plan


def test_build_and_extract_roundtrip_with_summary() -> None:
    """Roundtrip works when a summary is present — summary is outside details tags."""
    plan = "# My Plan\n\nStep 1: Do things.\nStep 2: More things."
    body = build_plan_stage_body("<!-- metadata -->", plan, summary="A concise summary.")
    assert extract_plan_content(body) == plan
