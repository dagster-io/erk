"""FileTree Interface Tests.

Tests for file system operations through the FileTree interface,
validating file/directory operations, glob patterns, and error handling.
"""

import pytest


def test_read_text_files(minimal_file_tree_v1):
    """Read configuration and markdown files from the context store."""
    # Read project configuration
    config_content = minimal_file_tree_v1.read_text("contextstore_project.yaml")
    assert "project_name: test/minimal" in config_content

    # Read system prompt
    prompt_content = minimal_file_tree_v1.read_text("system_prompt.md")
    assert len(prompt_content) > 0
    assert "Test system prompt" in prompt_content


def test_file_existence_checks(minimal_file_tree_v1):
    """Test file and directory existence checking."""
    # Test existing files
    assert minimal_file_tree_v1.exists("contextstore_project.yaml") is True
    assert minimal_file_tree_v1.exists("system_prompt.md") is True

    # Test existing directory
    assert minimal_file_tree_v1.exists("context") is True

    # Test non-existent file
    assert minimal_file_tree_v1.exists("nonexistent.txt") is False


def test_directory_operations(minimal_file_tree_v1):
    """Test directory type checking and operations."""
    # Test directory identification
    assert minimal_file_tree_v1.is_dir("context") is True
    assert minimal_file_tree_v1.is_dir("context/org_and_people") is True

    # Test file identification
    assert minimal_file_tree_v1.is_file("contextstore_project.yaml") is True
    assert minimal_file_tree_v1.is_file("context") is False

    # Test non-existent paths
    assert minimal_file_tree_v1.is_dir("nonexistent") is False
    assert minimal_file_tree_v1.is_file("nonexistent.txt") is False


def test_list_directory_contents(minimal_file_tree_v1):
    """Test directory content listing."""
    # List root directory
    root_contents = minimal_file_tree_v1.listdir("")
    expected_items = ["context", "contextstore_project.yaml", "system_prompt.md", "cronjobs"]
    for item in expected_items:
        assert item in root_contents

    # List context directory
    context_contents = minimal_file_tree_v1.listdir("context")
    expected_categories = ["org_and_people", "sales_definitions", "uncategorized"]
    for category in expected_categories:
        assert category in context_contents


def test_glob_pattern_matching(minimal_file_tree_v1):
    """Test glob pattern matching in directories."""
    # Find YAML files in context directory
    yaml_files = list(minimal_file_tree_v1.glob("context/org_and_people", "*.yaml"))
    assert len(yaml_files) > 0
    assert all(path.endswith(".yaml") for path in yaml_files)
    assert all("context/org_and_people" in path for path in yaml_files)


def test_recursive_glob_operations(minimal_file_tree_v1):
    """Test recursive glob pattern matching."""
    # Find all YAML files recursively (this finds files in subdirectories)
    yaml_files = list(minimal_file_tree_v1.recursive_glob("**/*.yaml"))
    assert len(yaml_files) >= 3  # Minimal fixture has 3 context files plus cronjobs
    # Note: contextstore_project.yaml is at root, not in subdirectory, so not in **/*.yaml
    assert any("context/" in path for path in yaml_files)
    assert any("cronjobs/" in path for path in yaml_files)

    # Find context files specifically
    context_files = list(minimal_file_tree_v1.recursive_glob("context/**/*.yaml"))
    assert len(context_files) == 3  # Minimal fixture has 3 context files
    assert all("context/" in path for path in context_files)

    # Test that root files need different pattern
    root_yaml = list(minimal_file_tree_v1.glob("", "*.yaml"))
    assert any("contextstore_project.yaml" in path for path in root_yaml)


def test_path_normalization(minimal_file_tree_v1):
    """Test path handling with various formats."""
    # Test with and without leading/trailing slashes
    assert minimal_file_tree_v1.exists("context") == minimal_file_tree_v1.exists("context/")

    # Test nested paths
    nested_files = list(minimal_file_tree_v1.glob("context/org_and_people", "*.yaml"))
    assert len(nested_files) > 0

    # Verify path format consistency
    for file_path in nested_files:
        assert file_path.startswith("context/org_and_people/")
        assert not file_path.startswith("//")


def test_error_handling(minimal_file_tree_v1):
    """Test error handling for invalid operations."""
    # Reading non-existent file should raise FileNotFoundError
    with pytest.raises(FileNotFoundError):
        minimal_file_tree_v1.read_text("nonexistent.txt")

    # Reading a directory as a file should raise IsADirectoryError
    with pytest.raises(IsADirectoryError):
        minimal_file_tree_v1.read_text("context")

    # Listing non-existent directory should raise FileNotFoundError
    with pytest.raises(FileNotFoundError):
        minimal_file_tree_v1.listdir("nonexistent_directory")

    # Listing a file as directory should raise NotADirectoryError
    with pytest.raises(NotADirectoryError):
        minimal_file_tree_v1.listdir("contextstore_project.yaml")
