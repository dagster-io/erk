"""Tests for ScriptDefinition and KitManifest validation."""

from erk.kits.models.kit import ScriptDefinition


def test_validate_valid_definition() -> None:
    """Test validation of a valid script definition."""
    script = ScriptDefinition(
        name="test-command", path="scripts/test-kit/test.py", description="Test script"
    )

    errors = script.validate()
    assert errors == []


def test_validate_valid_definition_with_numbers() -> None:
    """Test validation accepts numbers in name."""
    script = ScriptDefinition(
        name="test-command-123",
        path="scripts/test-kit/test.py",
        description="Test script",
    )

    errors = script.validate()
    assert errors == []


def test_validate_valid_nested_path() -> None:
    """Test validation accepts nested paths."""
    script = ScriptDefinition(
        name="test-command",
        path="scripts/test-kit/subdir/test.py",
        description="Test script",
    )

    errors = script.validate()
    assert errors == []


def test_validate_invalid_name_uppercase() -> None:
    """Test validation rejects uppercase letters in name."""
    script = ScriptDefinition(
        name="Test-Command", path="scripts/test-kit/test.py", description="Test script"
    )

    errors = script.validate()
    assert len(errors) == 1
    assert "must start with lowercase letter" in errors[0]


def test_validate_invalid_name_underscore() -> None:
    """Test validation rejects underscores in name."""
    script = ScriptDefinition(
        name="test_command", path="scripts/test-kit/test.py", description="Test script"
    )

    errors = script.validate()
    assert len(errors) == 1
    assert "must start with lowercase letter" in errors[0]


def test_validate_invalid_name_starts_with_number() -> None:
    """Test validation rejects names starting with numbers."""
    script = ScriptDefinition(
        name="123-test", path="scripts/test-kit/test.py", description="Test script"
    )

    errors = script.validate()
    assert len(errors) == 1
    assert "must start with lowercase letter" in errors[0]


def test_validate_invalid_name_special_chars() -> None:
    """Test validation rejects special characters in name."""
    script = ScriptDefinition(
        name="test@command", path="scripts/test-kit/test.py", description="Test script"
    )

    errors = script.validate()
    assert len(errors) == 1
    assert "must start with lowercase letter" in errors[0]


def test_validate_path_not_python() -> None:
    """Test validation rejects non-.py files."""
    script = ScriptDefinition(
        name="test-command", path="scripts/test-kit/test.txt", description="Test script"
    )

    errors = script.validate()
    assert len(errors) == 1
    assert "must end with .py" in errors[0]


def test_validate_path_no_extension() -> None:
    """Test validation rejects paths without extension."""
    script = ScriptDefinition(
        name="test-command", path="scripts/test-kit/test", description="Test script"
    )

    errors = script.validate()
    assert len(errors) == 1
    assert "must end with .py" in errors[0]


def test_validate_path_traversal() -> None:
    """Test validation rejects directory traversal in path."""
    script = ScriptDefinition(
        name="test-command", path="../scripts/test-kit/test.py", description="Test script"
    )

    errors = script.validate()
    assert len(errors) == 2  # directory traversal + wrong prefix
    assert any("directory traversal" in e for e in errors)


def test_validate_path_traversal_middle() -> None:
    """Test validation rejects directory traversal in middle of path."""
    script = ScriptDefinition(
        name="test-command", path="scripts/../test.py", description="Test script"
    )

    errors = script.validate()
    assert len(errors) == 1
    assert "directory traversal" in errors[0]


def test_validate_empty_description() -> None:
    """Test validation rejects empty description."""
    script = ScriptDefinition(
        name="test-command",
        path="scripts/test-kit/test.py",
        description="",
    )

    errors = script.validate()
    assert len(errors) == 1
    assert "Description cannot be empty" in errors[0]


def test_validate_whitespace_only_description() -> None:
    """Test validation rejects whitespace-only description."""
    script = ScriptDefinition(
        name="test-command",
        path="scripts/test-kit/test.py",
        description="   ",
    )

    errors = script.validate()
    assert len(errors) == 1
    assert "Description cannot be empty" in errors[0]


def test_validate_wrong_directory_prefix() -> None:
    """Test validation rejects paths not starting with scripts/."""
    script = ScriptDefinition(
        name="test-command", path="commands/test.py", description="Test script"
    )

    errors = script.validate()
    assert len(errors) == 1
    assert "must start with 'scripts/'" in errors[0]


def test_validate_multiple_errors() -> None:
    """Test validation returns multiple errors when multiple issues exist."""
    script = ScriptDefinition(name="INVALID_NAME", path="../bad/path.txt", description="")

    errors = script.validate()
    assert len(errors) == 5  # name, path extension, path traversal, wrong prefix, description
    assert any("must start with lowercase letter" in e for e in errors)
    assert any("must end with .py" in e for e in errors)
    assert any("directory traversal" in e for e in errors)
    assert any("must start with 'scripts/'" in e for e in errors)
    assert any("Description cannot be empty" in e for e in errors)
