"""Unit tests for FakeErkInstallation.

Layer 1 tests: Verify the fake implementation works correctly.
"""

from erk_shared.gateway.erk_installation.fake import FakeErkInstallation


def test_fake_erk_installation_get_last_seen_version_returns_none_by_default() -> None:
    """Test that get_last_seen_version returns None when not configured."""
    fake = FakeErkInstallation()

    result = fake.get_last_seen_version()

    assert result is None


def test_fake_erk_installation_get_last_seen_version_returns_configured_value() -> None:
    """Test that get_last_seen_version returns the configured version."""
    fake = FakeErkInstallation(last_seen_version="0.2.3")

    result = fake.get_last_seen_version()

    assert result == "0.2.3"


def test_fake_erk_installation_update_last_seen_version_updates_state() -> None:
    """Test that update_last_seen_version updates internal state."""
    fake = FakeErkInstallation()

    fake.update_last_seen_version("0.3.0")

    assert fake.get_last_seen_version() == "0.3.0"


def test_fake_erk_installation_update_tracks_all_updates() -> None:
    """Test that version_updates tracks all update calls."""
    fake = FakeErkInstallation()

    fake.update_last_seen_version("0.2.0")
    fake.update_last_seen_version("0.2.1")
    fake.update_last_seen_version("0.3.0")

    assert fake.version_updates == ["0.2.0", "0.2.1", "0.3.0"]


def test_fake_erk_installation_version_updates_returns_copy() -> None:
    """Test that version_updates returns a copy to prevent mutation."""
    fake = FakeErkInstallation()
    fake.update_last_seen_version("0.2.0")

    updates = fake.version_updates
    updates.append("MUTATED")

    # Original should be unchanged
    assert fake.version_updates == ["0.2.0"]


def test_fake_erk_installation_configured_version_can_be_overwritten() -> None:
    """Test that a configured version can be overwritten by update."""
    fake = FakeErkInstallation(last_seen_version="0.2.0")

    fake.update_last_seen_version("0.3.0")

    assert fake.get_last_seen_version() == "0.3.0"
    assert fake.version_updates == ["0.3.0"]
