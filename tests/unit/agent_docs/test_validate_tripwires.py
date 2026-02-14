"""Tests for _validate_tripwires with pattern field."""

from erk.agent_docs.operations import _validate_tripwires


def test_tripwire_without_pattern() -> None:
    data = [{"action": "using os.chdir()", "warning": "Use ctx.cwd instead"}]
    tripwires, errors = _validate_tripwires(data)

    assert errors == []
    assert len(tripwires) == 1
    assert tripwires[0].action == "using os.chdir()"
    assert tripwires[0].warning == "Use ctx.cwd instead"
    assert tripwires[0].pattern is None


def test_tripwire_with_valid_pattern() -> None:
    data = [
        {
            "action": "using bare subprocess.run",
            "warning": "Use wrapper functions",
            "pattern": "subprocess\\.run\\(",
        }
    ]
    tripwires, errors = _validate_tripwires(data)

    assert errors == []
    assert len(tripwires) == 1
    assert tripwires[0].pattern == "subprocess\\.run\\("


def test_tripwire_with_invalid_regex_pattern() -> None:
    data = [
        {
            "action": "some action",
            "warning": "some warning",
            "pattern": "[invalid",
        }
    ]
    tripwires, errors = _validate_tripwires(data)

    assert len(errors) == 1
    assert "not a valid regex" in errors[0]
    assert "tripwires[0].pattern" in errors[0]


def test_tripwire_with_non_string_pattern() -> None:
    data = [
        {
            "action": "some action",
            "warning": "some warning",
            "pattern": 42,
        }
    ]
    tripwires, errors = _validate_tripwires(data)

    assert len(errors) == 1
    assert "must be a string" in errors[0]
    assert "tripwires[0].pattern" in errors[0]


def test_tripwire_with_empty_string_pattern() -> None:
    data = [
        {
            "action": "some action",
            "warning": "some warning",
            "pattern": "",
        }
    ]
    tripwires, errors = _validate_tripwires(data)

    assert len(errors) == 1
    assert "must not be empty" in errors[0]
    assert "tripwires[0].pattern" in errors[0]


def test_multiple_tripwires_mixed_patterns() -> None:
    data = [
        {"action": "action1", "warning": "warning1", "pattern": "os\\.chdir\\("},
        {"action": "action2", "warning": "warning2"},
        {"action": "action3", "warning": "warning3", "pattern": "Path\\.home\\("},
    ]
    tripwires, errors = _validate_tripwires(data)

    assert errors == []
    assert len(tripwires) == 3
    assert tripwires[0].pattern == "os\\.chdir\\("
    assert tripwires[1].pattern is None
    assert tripwires[2].pattern == "Path\\.home\\("


def test_invalid_pattern_does_not_prevent_tripwire_creation() -> None:
    """A tripwire with invalid pattern is still created (pattern set to None)."""
    data = [
        {
            "action": "some action",
            "warning": "some warning",
            "pattern": "[invalid",
        }
    ]
    tripwires, errors = _validate_tripwires(data)

    assert len(errors) == 1
    assert len(tripwires) == 1
    assert tripwires[0].pattern is None
