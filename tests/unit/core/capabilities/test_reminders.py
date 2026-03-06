"""Tests for reminder capabilities and is_reminder_installed detection.

Tests is_reminder_installed helper and ReminderCapability base class behavior.
"""

from pathlib import Path

from erk.core.capabilities.detection import is_reminder_installed
from erk.core.capabilities.registry import get_capability, list_required_capabilities


def _write_state_toml(tmp_path: Path, installed_reminders: list[str]) -> None:
    """Helper to write reminders to state.toml."""
    import tomli_w

    state_path = tmp_path / ".erk" / "state.toml"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with state_path.open("wb") as f:
        tomli_w.dump({"reminders": {"installed": installed_reminders}}, f)


# =============================================================================
# Tests for is_reminder_installed Detection Helper (state.toml)
# =============================================================================


def test_is_reminder_installed_devrun_false_when_not_in_state(tmp_path: Path) -> None:
    """Test devrun reminder returns False when not in state.toml."""
    # No state.toml exists
    assert is_reminder_installed(tmp_path, "devrun") is False


def test_is_reminder_installed_devrun_true_when_in_state(tmp_path: Path) -> None:
    """Test devrun reminder returns True when in state.toml."""
    _write_state_toml(tmp_path, ["devrun"])
    assert is_reminder_installed(tmp_path, "devrun") is True


def test_is_reminder_installed_dignified_python_false_when_not_in_state(
    tmp_path: Path,
) -> None:
    """Test dignified-python reminder returns False when not in state.toml."""
    # No state.toml exists
    assert is_reminder_installed(tmp_path, "dignified-python") is False


def test_is_reminder_installed_dignified_python_true_when_in_state(
    tmp_path: Path,
) -> None:
    """Test dignified-python reminder returns True when in state.toml."""
    _write_state_toml(tmp_path, ["dignified-python"])
    assert is_reminder_installed(tmp_path, "dignified-python") is True


def test_is_reminder_installed_tripwires_false_when_not_in_state(
    tmp_path: Path,
) -> None:
    """Test tripwires reminder returns False when not in state.toml."""
    # No state.toml exists
    assert is_reminder_installed(tmp_path, "tripwires") is False


def test_is_reminder_installed_tripwires_true_when_in_state(
    tmp_path: Path,
) -> None:
    """Test tripwires reminder returns True when in state.toml."""
    _write_state_toml(tmp_path, ["tripwires"])
    assert is_reminder_installed(tmp_path, "tripwires") is True


def test_is_reminder_installed_unknown_reminder_returns_false(tmp_path: Path) -> None:
    """Test unknown reminder name returns False (not in state)."""
    _write_state_toml(tmp_path, ["devrun"])
    assert is_reminder_installed(tmp_path, "unknown-reminder") is False


def test_is_reminder_installed_with_multiple_reminders(tmp_path: Path) -> None:
    """Test detection works when multiple reminders are installed."""
    _write_state_toml(tmp_path, ["devrun", "dignified-python", "tripwires"])
    assert is_reminder_installed(tmp_path, "devrun") is True
    assert is_reminder_installed(tmp_path, "dignified-python") is True
    assert is_reminder_installed(tmp_path, "tripwires") is True
    assert is_reminder_installed(tmp_path, "unknown") is False


# =============================================================================
# Tests for ReminderCapability Base Class
# =============================================================================


def test_reminder_capability_required_is_false() -> None:
    """Test that reminder capabilities have required=False (opt-in)."""
    from erk.capabilities.reminders.devrun import DevrunReminderCapability
    from erk.capabilities.reminders.dignified_python import DignifiedPythonReminderCapability
    from erk.capabilities.reminders.tripwires import TripwiresReminderCapability

    assert DevrunReminderCapability().required is False
    assert DignifiedPythonReminderCapability().required is False
    assert TripwiresReminderCapability().required is False


def test_devrun_reminder_capability_properties() -> None:
    """Test DevrunReminderCapability has correct properties."""
    from erk.capabilities.reminders.devrun import DevrunReminderCapability

    cap = DevrunReminderCapability()
    assert cap.name == "devrun-reminder"
    assert cap.reminder_name == "devrun"
    assert cap.scope == "project"
    assert "devrun" in cap.description.lower()
    assert "state.toml" in cap.installation_check_description


def test_dignified_python_reminder_capability_properties() -> None:
    """Test DignifiedPythonReminderCapability has correct properties."""
    from erk.capabilities.reminders.dignified_python import DignifiedPythonReminderCapability

    cap = DignifiedPythonReminderCapability()
    assert cap.name == "dignified-python-reminder"
    assert cap.reminder_name == "dignified-python"
    assert cap.scope == "project"
    assert "dignified-python" in cap.description.lower()


def test_tripwires_reminder_capability_properties() -> None:
    """Test TripwiresReminderCapability has correct properties."""
    from erk.capabilities.reminders.tripwires import TripwiresReminderCapability

    cap = TripwiresReminderCapability()
    assert cap.name == "tripwires-reminder"
    assert cap.reminder_name == "tripwires"
    assert cap.scope == "project"
    assert "tripwires" in cap.description.lower()


def test_reminder_capability_is_installed_false_when_not_in_state(tmp_path: Path) -> None:
    """Test is_installed returns False when not in state.toml."""
    from erk.capabilities.reminders.devrun import DevrunReminderCapability

    cap = DevrunReminderCapability()
    assert cap.is_installed(tmp_path, backend="claude") is False


def test_reminder_capability_is_installed_true_when_in_state(tmp_path: Path) -> None:
    """Test is_installed returns True when in state.toml."""
    from erk.capabilities.reminders.devrun import DevrunReminderCapability

    _write_state_toml(tmp_path, ["devrun"])

    cap = DevrunReminderCapability()
    assert cap.is_installed(tmp_path, backend="claude") is True


def test_reminder_capability_install_adds_to_state(tmp_path: Path) -> None:
    """Test install adds reminder to state.toml."""
    import tomli

    from erk.capabilities.reminders.devrun import DevrunReminderCapability

    cap = DevrunReminderCapability()
    result = cap.install(tmp_path, backend="claude")

    assert result.success is True
    assert "devrun-reminder" in result.message

    # Verify state.toml was created with reminder
    state_path = tmp_path / ".erk" / "state.toml"
    assert state_path.exists()
    with state_path.open("rb") as f:
        data = tomli.load(f)
    assert "devrun" in data["reminders"]["installed"]


def test_reminder_capability_install_idempotent(tmp_path: Path) -> None:
    """Test install is idempotent when already in state."""
    from erk.capabilities.reminders.devrun import DevrunReminderCapability

    _write_state_toml(tmp_path, ["devrun"])

    cap = DevrunReminderCapability()
    result = cap.install(tmp_path, backend="claude")

    assert result.success is True
    assert "already installed" in result.message


def test_reminder_capability_install_preserves_existing_reminders(tmp_path: Path) -> None:
    """Test install preserves other reminders in state.toml."""
    import tomli

    from erk.capabilities.reminders.tripwires import TripwiresReminderCapability

    _write_state_toml(tmp_path, ["devrun", "dignified-python"])

    cap = TripwiresReminderCapability()
    result = cap.install(tmp_path, backend="claude")

    assert result.success is True

    state_path = tmp_path / ".erk" / "state.toml"
    with state_path.open("rb") as f:
        data = tomli.load(f)
    installed = data["reminders"]["installed"]
    assert "devrun" in installed
    assert "dignified-python" in installed
    assert "tripwires" in installed


def test_reminder_capability_install_preserves_other_sections(tmp_path: Path) -> None:
    """Test install preserves other sections in state.toml."""
    import tomli
    import tomli_w

    from erk.capabilities.reminders.devrun import DevrunReminderCapability

    # Create state.toml with other sections
    state_path = tmp_path / ".erk" / "state.toml"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with state_path.open("wb") as f:
        tomli_w.dump({"artifacts": {"version": "0.1.0"}}, f)

    cap = DevrunReminderCapability()
    cap.install(tmp_path, backend="claude")

    with state_path.open("rb") as f:
        data = tomli.load(f)
    assert "artifacts" in data
    assert data["artifacts"]["version"] == "0.1.0"
    assert "reminders" in data


def test_reminder_capability_artifacts_empty() -> None:
    """Test reminder capabilities have no artifacts (state stored in state.toml)."""
    from erk.capabilities.reminders.devrun import DevrunReminderCapability

    cap = DevrunReminderCapability()
    artifacts = cap.artifacts

    assert len(artifacts) == 0


def test_reminder_capabilities_registered() -> None:
    """Test that reminder capabilities are registered."""
    expected_reminders = [
        "devrun-reminder",
        "dignified-python-reminder",
        "tripwires-reminder",
    ]
    for reminder_name in expected_reminders:
        cap = get_capability(reminder_name)
        assert cap is not None, f"Reminder '{reminder_name}' not registered"
        assert cap.name == reminder_name
        assert cap.required is False


def test_reminder_capabilities_not_in_required_list() -> None:
    """Test that reminder capabilities are NOT in the required list."""
    required_caps = list_required_capabilities()
    required_names = [cap.name for cap in required_caps]

    assert "devrun-reminder" not in required_names
    assert "dignified-python-reminder" not in required_names
    assert "tripwires-reminder" not in required_names
