"""Tests for erk.core.codespace service module.

These tests verify the Codespace ABC behavior using FakeCodespace.
The FakeCodespace implementation provides a testable version of the
codespace operations without subprocess calls.
"""

from erk.core.codespace import CodespaceInfo, FakeCodespace


def test_get_repo_name_returns_configured_value() -> None:
    """Test that get_repo_name returns the pre-configured repo name."""
    fake = FakeCodespace(repo_name="myorg/myrepo")

    result = fake.get_repo_name()

    assert result == "myorg/myrepo"


def test_get_current_branch_returns_configured_value() -> None:
    """Test that get_current_branch returns the pre-configured branch."""
    fake = FakeCodespace(current_branch="feature-branch")

    result = fake.get_current_branch()

    assert result == "feature-branch"


def test_find_existing_codespace_returns_matching_codespace() -> None:
    """Test finding an existing codespace that matches repo and branch."""
    fake = FakeCodespace(
        existing_codespaces=[
            CodespaceInfo(
                name="my-codespace",
                state="Available",
                repository="owner/repo",
                branch="main",
            )
        ]
    )

    result = fake.find_existing_codespace("owner/repo", "main")

    assert result == "my-codespace"


def test_find_existing_codespace_returns_none_when_no_match() -> None:
    """Test returns None when no matching codespace found."""
    fake = FakeCodespace(
        existing_codespaces=[
            CodespaceInfo(
                name="other-codespace",
                state="Available",
                repository="other/repo",
                branch="main",
            )
        ]
    )

    result = fake.find_existing_codespace("owner/repo", "main")

    assert result is None


def test_find_existing_codespace_returns_none_when_state_not_available() -> None:
    """Test returns None when codespace exists but not available."""
    fake = FakeCodespace(
        existing_codespaces=[
            CodespaceInfo(
                name="my-codespace",
                state="Shutdown",
                repository="owner/repo",
                branch="main",
            )
        ]
    )

    result = fake.find_existing_codespace("owner/repo", "main")

    assert result is None


def test_find_existing_codespace_returns_none_when_branch_mismatch() -> None:
    """Test returns None when branch doesn't match."""
    fake = FakeCodespace(
        existing_codespaces=[
            CodespaceInfo(
                name="my-codespace",
                state="Available",
                repository="owner/repo",
                branch="other-branch",
            )
        ]
    )

    result = fake.find_existing_codespace("owner/repo", "main")

    assert result is None


def test_create_codespace_returns_configured_name() -> None:
    """Test that create_codespace returns the pre-configured name."""
    fake = FakeCodespace(created_codespace_name="new-codespace-123")

    result = fake.create_codespace("owner/repo", "main")

    assert result == "new-codespace-123"


def test_create_codespace_tracks_creation() -> None:
    """Test that create_codespace records the creation request."""
    fake = FakeCodespace()

    fake.create_codespace("owner/repo", "feature-branch")

    assert len(fake.created_codespaces) == 1
    assert fake.created_codespaces[0] == ("owner/repo", "feature-branch")


def test_wait_for_codespace_tracks_wait_call() -> None:
    """Test that wait_for_codespace records the codespace waited for."""
    fake = FakeCodespace()

    fake.wait_for_codespace("my-codespace")

    assert "my-codespace" in fake.waited_for


def test_is_claude_available_returns_configured_value() -> None:
    """Test that is_claude_available returns configured availability."""
    fake_available = FakeCodespace(claude_available=True)
    fake_unavailable = FakeCodespace(claude_available=False)

    assert fake_available.is_claude_available() is True
    assert fake_unavailable.is_claude_available() is False


def test_exec_ssh_with_claude_tracks_command() -> None:
    """Test that exec_ssh_with_claude records the SSH command."""
    fake = FakeCodespace()

    fake.exec_ssh_with_claude("my-codespace", "/erk:craft-plan")

    assert len(fake.ssh_commands) == 1
    assert fake.ssh_commands[0] == ("my-codespace", "/erk:craft-plan")


def test_exec_claude_local_tracks_command() -> None:
    """Test that exec_claude_local records the local command."""
    fake = FakeCodespace()

    fake.exec_claude_local("/erk:craft-plan add auth")

    assert len(fake.local_commands) == 1
    assert fake.local_commands[0] == "/erk:craft-plan add auth"


def test_get_or_create_codespace_returns_existing() -> None:
    """Test that get_or_create_codespace returns existing codespace."""
    fake = FakeCodespace(
        existing_codespaces=[
            CodespaceInfo(
                name="existing-cs",
                state="Available",
                repository="owner/repo",
                branch="main",
            )
        ]
    )

    result = fake.get_or_create_codespace("owner/repo", "main")

    assert result == "existing-cs"
    # Should not have created a new one
    assert len(fake.created_codespaces) == 0


def test_get_or_create_codespace_creates_when_none_exists() -> None:
    """Test that get_or_create_codespace creates when no match exists."""
    fake = FakeCodespace(
        existing_codespaces=[],
        created_codespace_name="new-cs",
    )

    result = fake.get_or_create_codespace("owner/repo", "main")

    assert result == "new-cs"
    # Should have created a new one
    assert len(fake.created_codespaces) == 1
    assert fake.created_codespaces[0] == ("owner/repo", "main")
    # Should have waited for it
    assert "new-cs" in fake.waited_for


def test_run_local_planning_with_description() -> None:
    """Test that run_local_planning includes description in command."""
    fake = FakeCodespace()

    fake.run_local_planning("add user auth")

    assert len(fake.local_commands) == 1
    assert fake.local_commands[0] == "/erk:craft-plan add user auth"


def test_run_local_planning_without_description() -> None:
    """Test that run_local_planning works without description."""
    fake = FakeCodespace()

    fake.run_local_planning("")

    assert len(fake.local_commands) == 1
    assert fake.local_commands[0] == "/erk:craft-plan"


def test_run_remote_planning_orchestrates_full_workflow() -> None:
    """Test that run_remote_planning performs full workflow."""
    fake = FakeCodespace(
        repo_name="myorg/myrepo",
        current_branch="feature-x",
        existing_codespaces=[],
        created_codespace_name="new-cs",
    )

    fake.run_remote_planning("implement feature")

    # Should have created a codespace
    assert len(fake.created_codespaces) == 1
    assert fake.created_codespaces[0] == ("myorg/myrepo", "feature-x")
    # Should have waited for it
    assert "new-cs" in fake.waited_for
    # Should have SSH'd with the command
    assert len(fake.ssh_commands) == 1
    assert fake.ssh_commands[0] == ("new-cs", "/erk:craft-plan implement feature")


def test_run_remote_planning_reuses_existing_codespace() -> None:
    """Test that run_remote_planning reuses existing codespace."""
    fake = FakeCodespace(
        repo_name="owner/repo",
        current_branch="main",
        existing_codespaces=[
            CodespaceInfo(
                name="existing-cs",
                state="Available",
                repository="owner/repo",
                branch="main",
            )
        ],
    )

    fake.run_remote_planning("")

    # Should NOT have created a new codespace
    assert len(fake.created_codespaces) == 0
    # Should have SSH'd to the existing one
    assert len(fake.ssh_commands) == 1
    assert fake.ssh_commands[0] == ("existing-cs", "/erk:craft-plan")
