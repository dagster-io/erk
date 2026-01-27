"""Tests for FakeGitConfigOps."""

from pathlib import Path

from erk_shared.gateway.git.config_ops.fake import ConfigSetRecord, FakeGitConfigOps


def test_config_set_records_mutation() -> None:
    """Test that config_set records the operation for assertions."""
    fake = FakeGitConfigOps()
    cwd = Path("/repo")

    fake.config_set(cwd, "user.name", "Test User", scope="local")

    assert len(fake.config_sets) == 1
    record = fake.config_sets[0]
    assert record.cwd == cwd
    assert record.key == "user.name"
    assert record.value == "Test User"
    assert record.scope == "local"


def test_config_set_updates_internal_state() -> None:
    """Test that config_set updates the internal config state."""
    fake = FakeGitConfigOps()
    cwd = Path("/repo")

    fake.config_set(cwd, "user.name", "Test User", scope="local")

    result = fake.get_git_user_name(cwd)
    assert result == "Test User"


def test_get_git_user_name_returns_configured_value() -> None:
    """Test that get_git_user_name returns the configured value."""
    cwd = Path("/repo")
    fake = FakeGitConfigOps(user_names={cwd: "Configured User"})

    result = fake.get_git_user_name(cwd)
    assert result == "Configured User"


def test_get_git_user_name_returns_none_when_not_configured() -> None:
    """Test that get_git_user_name returns None when not configured."""
    fake = FakeGitConfigOps(user_names={})

    result = fake.get_git_user_name(Path("/repo"))
    assert result is None


def test_get_git_user_name_walks_up_to_find_value() -> None:
    """Test that get_git_user_name walks up parent directories."""
    parent = Path("/repo")
    child = Path("/repo/subdir")
    fake = FakeGitConfigOps(user_names={parent: "Parent User"})

    result = fake.get_git_user_name(child)
    assert result == "Parent User"


def test_link_state_updates_internal_state() -> None:
    """Test that link_state method updates the fake's state."""
    fake = FakeGitConfigOps()

    user_names = {Path("/repo"): "Linked User"}
    config_values = {(Path("/repo"), "user.email"): "user@example.com"}

    fake.link_state(user_names=user_names, config_values=config_values)

    assert fake.get_git_user_name(Path("/repo")) == "Linked User"


def test_link_mutation_tracking_shares_list_reference() -> None:
    """Test that link_mutation_tracking shares the list reference."""
    fake = FakeGitConfigOps()
    external_list: list[ConfigSetRecord] = []

    fake.link_mutation_tracking(config_sets=external_list)
    fake.config_set(Path("/repo"), "user.name", "Test", scope="global")

    assert len(external_list) == 1
    assert external_list[0].key == "user.name"
