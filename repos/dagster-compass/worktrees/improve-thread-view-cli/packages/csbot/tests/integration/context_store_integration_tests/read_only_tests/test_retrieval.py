"""Content Retrieval Tests.

Tests for context file retrieval, validation, and content loading
from the context store fixture.
"""

import re
from datetime import datetime

import yaml


def test_get_all_contexts_by_category(medium_file_tree_v1):
    """Retrieve and count all contexts from each category."""
    categories = ["org_and_people", "sales_definitions", "uncategorized"]

    for category in categories:
        context_files = list(medium_file_tree_v1.glob(f"context/{category}", "*.yaml"))
        assert len(context_files) > 0, f"Expected context files in {category}"

        # Verify all files are in the correct category directory
        for file_path in context_files:
            assert file_path.startswith(f"context/{category}/")
            assert file_path.endswith(".yaml")


def test_context_yaml_structure(file_tree):
    """Validate YAML structure of context files."""
    # Test with a known context file
    org_files = list(file_tree.glob("context/org_and_people", "*.yaml"))
    assert len(org_files) > 0

    # Load first context file and validate structure
    first_file = org_files[0]
    content = file_tree.read_text(first_file)
    context_data = yaml.safe_load(content)

    # Verify required fields
    required_fields = [
        "topic",
        "incorrect_understanding",
        "correct_understanding",
        "search_keywords",
    ]
    for field in required_fields:
        assert field in context_data, f"Field '{field}' missing from {first_file}"
        assert context_data[field] is not None, f"Field '{field}' is null in {first_file}"

    # Verify search_keywords is a list (can be string or list in YAML)
    search_keywords = context_data["search_keywords"]
    assert isinstance(search_keywords, str | list), "search_keywords should be string or list"


def test_retrieve_contexts_by_pattern(file_tree):
    """Test pattern-based context retrieval."""
    # Find contexts from June 2025 (202506*)
    june_contexts = list(file_tree.recursive_glob("context/**/202506*.yaml"))
    assert len(june_contexts) > 0, "Expected contexts from June 2025"

    # Find contexts from July 2025 (202507*)
    july_contexts = list(file_tree.recursive_glob("context/**/202507*.yaml"))
    assert len(july_contexts) > 0, "Expected contexts from July 2025"

    # Find contexts from August 2025 (202508*)
    august_contexts = list(file_tree.recursive_glob("context/**/202508*.yaml"))
    assert len(august_contexts) > 0, "Expected contexts from August 2025"


def test_system_prompt_retrieval(medium_file_tree_v1):
    """Load and validate the system prompt file."""
    prompt_content = medium_file_tree_v1.read_text("system_prompt.md")

    # Should contain meaningful system prompt content
    assert len(prompt_content) > 20, "System prompt should be substantial"
    # Medium fixture has generic test content
    assert "test" in prompt_content.lower() or "prompt" in prompt_content.lower()


def test_category_enumeration(medium_file_tree_v1):
    """Test listing and validation of all available categories."""
    context_dirs = medium_file_tree_v1.listdir("context")

    expected_categories = ["org_and_people", "sales_definitions", "uncategorized"]
    for category in expected_categories:
        assert category in context_dirs, f"Expected category '{category}' not found"

    # Verify each category contains YAML files
    for category in expected_categories:
        yaml_files = list(medium_file_tree_v1.glob(f"context/{category}", "*.yaml"))
        assert len(yaml_files) > 0, f"Category '{category}' should contain YAML files"


def test_file_naming_convention(file_tree):
    """Validate context file naming follows YYYYMMDD_description.yaml pattern."""
    all_context_files = list(file_tree.recursive_glob("context/**/*.yaml"))
    assert len(all_context_files) > 20, "Expected 20+ context files"

    # Pattern: YYYYMMDD_description.yaml
    naming_pattern = re.compile(r"^.*/(20\d{6})_.*\.yaml$")

    valid_files = 0
    for file_path in all_context_files:
        file_path.split("/")[-1]
        match = naming_pattern.match(file_path)
        if match:
            valid_files += 1
            # Extract date portion and validate it's a reasonable date
            date_str = match.group(1)
            try:
                date_obj = datetime.strptime(date_str, "%Y%m%d")
                # Should be a reasonable date (2025 timeframe)
                assert 2025 <= date_obj.year <= 2026, (
                    f"Date {date_str} should be in 2025-2026 range"
                )
            except ValueError:
                assert False, f"Invalid date format in {file_path}"

    assert valid_files > 15, f"Expected most files to follow naming convention, got {valid_files}"


def test_context_content_validation(file_tree):
    """Validate content of each context file for completeness."""
    all_context_files = list(file_tree.recursive_glob("context/**/*.yaml"))

    empty_fields_count = 0
    for file_path in all_context_files:
        content = file_tree.read_text(file_path)
        context_data = yaml.safe_load(content)

        # Check for empty required fields
        required_fields = ["topic", "incorrect_understanding", "correct_understanding"]
        for field in required_fields:
            if field in context_data:
                value = context_data[field]
                if not value or (isinstance(value, str) and value.strip() == ""):
                    empty_fields_count += 1
                    break

    # Allow some empty fields but not too many (data quality check)
    assert empty_fields_count < len(all_context_files) * 0.1, (
        "Too many files with empty required fields"
    )


def test_recursive_context_retrieval(medium_file_tree_v1):
    """Test recursive retrieval of all contexts without duplicates."""
    all_contexts = list(medium_file_tree_v1.recursive_glob("context/**/*.yaml"))

    # Medium fixture has 10 contexts
    assert len(all_contexts) >= 10, f"Expected 10+ contexts, found {len(all_contexts)}"

    # Should not have duplicates
    unique_contexts = set(all_contexts)
    assert len(unique_contexts) == len(all_contexts), "Found duplicate context file paths"

    # All should be under context/ directory
    for context_path in all_contexts:
        assert context_path.startswith("context/"), (
            f"Context file {context_path} not in context/ directory"
        )
