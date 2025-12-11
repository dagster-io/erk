"""Naming convention utilities for agent recordings."""

import re
from pathlib import Path


def is_valid_scenario_name(name: str) -> bool:
    """Check if a scenario name follows the naming convention.

    Valid names contain only lowercase letters, numbers, and hyphens.

    Args:
        name: The scenario name to validate

    Returns:
        True if the name is valid, False otherwise

    Examples:
        >>> is_valid_scenario_name("simple-test")
        True
        >>> is_valid_scenario_name("calculator-tool")
        True
        >>> is_valid_scenario_name("simple_text")
        False
        >>> is_valid_scenario_name("Simple-Test")
        False
        >>> is_valid_scenario_name("test@123")
        False
    """
    return bool(re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", name))


def suggest_valid_name(name: str) -> str:
    """Suggest a valid scenario name based on an invalid one.

    Args:
        name: The invalid scenario name

    Returns:
        A suggested valid name

    Examples:
        >>> suggest_valid_name("simple_text")
        'simple-text'
        >>> suggest_valid_name("Simple_Test")
        'simple-test'
        >>> suggest_valid_name("test@123")
        'test-123'
    """
    # Convert to lowercase
    suggested = name.lower()

    # Replace underscores with hyphens
    suggested = suggested.replace("_", "-")

    # Replace any other invalid characters with hyphens
    suggested = re.sub(r"[^a-z0-9-]", "-", suggested)

    # Remove multiple consecutive hyphens
    suggested = re.sub(r"-+", "-", suggested)

    # Remove leading/trailing hyphens
    suggested = suggested.strip("-")

    return suggested


def find_naming_violations(directory: Path) -> list[tuple[Path, str]]:
    """Find JSON files with naming convention violations.

    Args:
        directory: Directory to search for JSON files

    Returns:
        List of (file_path, name) tuples for files with violations
    """
    violations = []

    for json_file in directory.rglob("*.json"):
        if not json_file.name.startswith("_"):  # Skip private files
            name = json_file.name.removesuffix(".json")
            if not is_valid_scenario_name(name):
                violations.append((json_file, name))

    return violations
