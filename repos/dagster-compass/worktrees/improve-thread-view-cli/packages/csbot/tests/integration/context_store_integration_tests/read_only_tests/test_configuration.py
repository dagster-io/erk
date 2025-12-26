"""Project Configuration Tests.

Tests for context store project configuration validation,
including schema validation and team structure verification.
"""

import re

import yaml

from csbot.contextengine.contextstore_protocol import ContextStoreProject


def test_load_project_config(minimal_file_tree_v1):
    """Load and validate the project configuration file."""
    config_content = minimal_file_tree_v1.read_text("contextstore_project.yaml")
    config_data = yaml.safe_load(config_content)

    assert config_data["project_name"] == "test/minimal"
    assert "teams" in config_data


def test_teams_structure_validation(minimal_file_tree_v1):
    """Validate the teams structure in the configuration."""
    config_content = minimal_file_tree_v1.read_text("contextstore_project.yaml")
    config_data = yaml.safe_load(config_content)

    teams = config_data["teams"]
    expected_teams = ["exec"]

    # Verify all expected teams are present
    for team in expected_teams:
        assert team in teams

    # Verify teams are lists (even if empty)
    for team_name, members in teams.items():
        assert isinstance(members, list), f"Team {team_name} should be a list"


def test_project_name_format(minimal_file_tree_v1):
    """Validate the project name follows the org/repo pattern."""
    config_content = minimal_file_tree_v1.read_text("contextstore_project.yaml")
    config_data = yaml.safe_load(config_content)

    project_name = config_data["project_name"]

    # Should match pattern org/repo
    pattern = r"^[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+$"
    assert re.match(pattern, project_name), (
        f"Project name '{project_name}' should match pattern {pattern}"
    )

    # Should contain exactly one slash
    assert project_name.count("/") == 1, "Project name should contain exactly one slash"


def test_config_schema_validation(minimal_file_tree_v1):
    """Validate configuration against the ContextStoreProject pydantic model."""
    config_content = minimal_file_tree_v1.read_text("contextstore_project.yaml")
    config_data = yaml.safe_load(config_content)

    # Should be able to create ContextStoreProject instance without errors
    project = ContextStoreProject(**config_data)

    assert project.project_name == "test/minimal"
    assert isinstance(project.teams, dict)


def test_team_member_access(minimal_file_tree_v1):
    """Test team member lookup and access."""
    config_content = minimal_file_tree_v1.read_text("contextstore_project.yaml")
    config_data = yaml.safe_load(config_content)

    teams = config_data["teams"]

    # Verify exec team includes expected member
    assert "exec" in teams
    exec_members = teams["exec"]
    assert "test@example.com" in exec_members[0]

    # Verify email format validation for members
    for team_name, members in teams.items():
        for member in members:
            if member:  # Skip empty strings if any
                assert "@" in member, (
                    f"Team member '{member}' in team '{team_name}' should be an email"
                )


def test_empty_teams_handling(minimal_file_tree_v1):
    """Test handling of empty team lists."""
    config_content = minimal_file_tree_v1.read_text("contextstore_project.yaml")
    config_data = yaml.safe_load(config_content)

    teams = config_data["teams"]

    # For minimal fixture, we have one team with members
    # Update test to verify structure even if no empty teams
    if len(teams) == 0:
        assert False, "Expected at least one team"

    # Verify all teams are valid lists
    for team_name, members in teams.items():
        assert isinstance(members, list)
