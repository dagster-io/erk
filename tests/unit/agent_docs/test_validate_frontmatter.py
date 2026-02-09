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


def test_tripwire_with_valid_pattern() -> None:
    data: dict[str, object] = {
        "title": "My Doc",
        "read_when": ["editing code"],
        "tripwires": [
            {
                "action": "using subprocess.run",
                "warning": "Use wrapper functions",
                "pattern": r"subprocess\.run\(",
            }
        ],
    }
    result, errors = validate_agent_doc_frontmatter(data)

    assert result is not None
    assert errors == []
    assert len(result.tripwires) == 1
    assert result.tripwires[0].pattern == r"subprocess\.run\("


def test_tripwire_without_pattern() -> None:
    data: dict[str, object] = {
        "title": "My Doc",
        "read_when": ["editing code"],
        "tripwires": [
            {
                "action": "choosing between exceptions",
                "warning": "Read the guide",
            }
        ],
    }
    result, errors = validate_agent_doc_frontmatter(data)

    assert result is not None
    assert errors == []
    assert len(result.tripwires) == 1
    assert result.tripwires[0].pattern is None


def test_tripwire_with_invalid_pattern() -> None:
    data: dict[str, object] = {
        "title": "My Doc",
        "read_when": ["editing code"],
        "tripwires": [
            {
                "action": "using subprocess.run",
                "warning": "Use wrapper functions",
                "pattern": r"[invalid(regex",
            }
        ],
    }
    result, errors = validate_agent_doc_frontmatter(data)

    assert result is None
    assert len(errors) == 1
    assert "tripwires[0].pattern" in errors[0]
    assert "not a valid regex" in errors[0]


def test_tripwire_with_non_string_pattern() -> None:
    data: dict[str, object] = {
        "title": "My Doc",
        "read_when": ["editing code"],
        "tripwires": [
            {
                "action": "using subprocess.run",
                "warning": "Use wrapper functions",
                "pattern": 42,
            }
        ],
    }
    result, errors = validate_agent_doc_frontmatter(data)

    assert result is None
    assert len(errors) == 1
    assert "tripwires[0].pattern" in errors[0]
    assert "must be a string" in errors[0]
