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
    assert result.lifecycle is None
    assert result.promoted_to is None


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


def test_last_audited_rejects_date_only_format() -> None:
    data: dict[str, object] = {
        "title": "My Doc",
        "read_when": ["editing code"],
        "last_audited": "2026-02-08",
    }
    result, errors = validate_agent_doc_frontmatter(data)

    assert result is None
    assert len(errors) == 1
    assert "must match format 'YYYY-MM-DD HH:MM PT'" in errors[0]
    assert "'2026-02-08'" in errors[0]


def test_last_audited_accepts_valid_datetime_format() -> None:
    data: dict[str, object] = {
        "title": "My Doc",
        "read_when": ["editing code"],
        "last_audited": "2026-02-08 14:30 PT",
    }
    result, errors = validate_agent_doc_frontmatter(data)

    assert result is not None
    assert errors == []
    assert result.last_audited == "2026-02-08 14:30 PT"


def test_last_audited_rejects_wrong_timezone() -> None:
    data: dict[str, object] = {
        "title": "My Doc",
        "read_when": ["editing code"],
        "last_audited": "2026-02-08 14:30 EST",
    }
    result, errors = validate_agent_doc_frontmatter(data)

    assert result is None
    assert len(errors) == 1
    assert "must match format 'YYYY-MM-DD HH:MM PT'" in errors[0]


def test_last_audited_rejects_seconds() -> None:
    data: dict[str, object] = {
        "title": "My Doc",
        "read_when": ["editing code"],
        "last_audited": "2026-02-08 14:30:00 PT",
    }
    result, errors = validate_agent_doc_frontmatter(data)

    assert result is None
    assert len(errors) == 1
    assert "must match format 'YYYY-MM-DD HH:MM PT'" in errors[0]


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


# -- lifecycle field --


def test_lifecycle_accepts_raw() -> None:
    data: dict[str, object] = {
        "title": "My Doc",
        "read_when": ["editing code"],
        "lifecycle": "raw",
    }
    result, errors = validate_agent_doc_frontmatter(data)

    assert result is not None
    assert errors == []
    assert result.lifecycle == "raw"


def test_lifecycle_accepts_staged() -> None:
    data: dict[str, object] = {
        "title": "My Doc",
        "read_when": ["editing code"],
        "lifecycle": "staged",
    }
    result, errors = validate_agent_doc_frontmatter(data)

    assert result is not None
    assert errors == []
    assert result.lifecycle == "staged"


def test_lifecycle_accepts_promoted_with_promoted_to() -> None:
    data: dict[str, object] = {
        "title": "My Doc",
        "read_when": ["editing code"],
        "lifecycle": "promoted",
        "promoted_to": "fake-driven-testing",
    }
    result, errors = validate_agent_doc_frontmatter(data)

    assert result is not None
    assert errors == []
    assert result.lifecycle == "promoted"
    assert result.promoted_to == "fake-driven-testing"


def test_lifecycle_rejects_invalid_value() -> None:
    data: dict[str, object] = {
        "title": "My Doc",
        "read_when": ["editing code"],
        "lifecycle": "unknown",
    }
    result, errors = validate_agent_doc_frontmatter(data)

    assert result is None
    assert len(errors) == 1
    assert "'unknown'" in errors[0]


def test_lifecycle_rejects_non_string() -> None:
    data: dict[str, object] = {
        "title": "My Doc",
        "read_when": ["editing code"],
        "lifecycle": 42,
    }
    result, errors = validate_agent_doc_frontmatter(data)

    assert result is None
    assert len(errors) == 1
    assert "Field 'lifecycle' must be a string" in errors[0]


def test_promoted_to_requires_lifecycle_promoted() -> None:
    data: dict[str, object] = {
        "title": "My Doc",
        "read_when": ["editing code"],
        "promoted_to": "some-skill",
    }
    result, errors = validate_agent_doc_frontmatter(data)

    assert result is None
    assert len(errors) == 1
    assert "only valid when lifecycle is 'promoted'" in errors[0]


def test_lifecycle_promoted_requires_promoted_to() -> None:
    data: dict[str, object] = {
        "title": "My Doc",
        "read_when": ["editing code"],
        "lifecycle": "promoted",
    }
    result, errors = validate_agent_doc_frontmatter(data)

    assert result is None
    assert len(errors) == 1
    assert "required when lifecycle is 'promoted'" in errors[0]


def test_promoted_to_rejects_empty_string() -> None:
    data: dict[str, object] = {
        "title": "My Doc",
        "read_when": ["editing code"],
        "lifecycle": "promoted",
        "promoted_to": "",
    }
    result, errors = validate_agent_doc_frontmatter(data)

    assert result is None
    assert "must not be empty" in errors[0]


def test_lifecycle_none_by_default() -> None:
    data: dict[str, object] = {
        "title": "My Doc",
        "read_when": ["editing code"],
    }
    result, errors = validate_agent_doc_frontmatter(data)

    assert result is not None
    assert errors == []
    assert result.lifecycle is None
    assert result.promoted_to is None
