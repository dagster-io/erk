"""Tests for validate_agent_doc_frontmatter."""

from erk.agent_docs.operations import validate_agent_doc_frontmatter


def test_valid_frontmatter_without_audit_fields() -> None:
    data: dict[str, object] = {
        "title": "My Doc",
        "read_when": ["editing code"],
    }
    result, errors = validate_agent_doc_frontmatter(data)

    assert result is not None
    assert errors == []
    assert result.last_audited is None
    assert result.audit_result is None


def test_valid_frontmatter_with_audit_fields() -> None:
    data: dict[str, object] = {
        "title": "My Doc",
        "read_when": ["editing code"],
        "last_audited": "2026-02-01 20:34 PT",
        "audit_result": "clean",
    }
    result, errors = validate_agent_doc_frontmatter(data)

    assert result is not None
    assert errors == []
    assert result.last_audited == "2026-02-01 20:34 PT"
    assert result.audit_result == "clean"


def test_audit_result_accepts_edited() -> None:
    data: dict[str, object] = {
        "title": "My Doc",
        "read_when": ["editing code"],
        "audit_result": "edited",
    }
    result, errors = validate_agent_doc_frontmatter(data)

    assert result is not None
    assert errors == []
    assert result.audit_result == "edited"


def test_audit_result_rejects_invalid_value() -> None:
    data: dict[str, object] = {
        "title": "My Doc",
        "read_when": ["editing code"],
        "audit_result": "pending",
    }
    result, errors = validate_agent_doc_frontmatter(data)

    assert result is None
    assert len(errors) == 1
    assert "must be 'clean' or 'edited'" in errors[0]
    assert "'pending'" in errors[0]


def test_audit_result_rejects_non_string() -> None:
    data: dict[str, object] = {
        "title": "My Doc",
        "read_when": ["editing code"],
        "audit_result": 42,
    }
    result, errors = validate_agent_doc_frontmatter(data)

    assert result is None
    assert len(errors) == 1
    assert "Field 'audit_result' must be a string" in errors[0]


def test_last_audited_rejects_non_string() -> None:
    data: dict[str, object] = {
        "title": "My Doc",
        "read_when": ["editing code"],
        "last_audited": 12345,
    }
    result, errors = validate_agent_doc_frontmatter(data)

    assert result is None
    assert len(errors) == 1
    assert "Field 'last_audited' must be a string" in errors[0]


def test_multiple_audit_errors_reported() -> None:
    data: dict[str, object] = {
        "title": "My Doc",
        "read_when": ["editing code"],
        "last_audited": True,
        "audit_result": ["not", "a", "string"],
    }
    result, errors = validate_agent_doc_frontmatter(data)

    assert result is None
    assert len(errors) == 2
