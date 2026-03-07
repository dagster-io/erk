"""Fake cmux implementation for testing."""

from dataclasses import dataclass

from erk_shared.gateway.cmux.abc import Cmux


@dataclass(frozen=True)
class CreateWorkspaceCall:
    """Record of a create_workspace call for test assertions."""

    command: str


@dataclass(frozen=True)
class RenameWorkspaceCall:
    """Record of a rename_workspace call for test assertions."""

    workspace_ref: str
    new_name: str


class FakeCmux(Cmux):
    """In-memory fake cmux for testing.

    Tracks calls for assertion and supports error injection via constructor.
    """

    def __init__(
        self,
        *,
        workspace_ref: str,
        create_error: str | None = None,
    ) -> None:
        """Create FakeCmux with configurable behavior.

        Args:
            workspace_ref: Value to return from create_workspace.
            create_error: If set, create_workspace raises RuntimeError with this message.
        """
        self._workspace_ref = workspace_ref
        self._create_error = create_error
        self._create_calls: list[CreateWorkspaceCall] = []
        self._rename_calls: list[RenameWorkspaceCall] = []

    @property
    def create_calls(self) -> list[CreateWorkspaceCall]:
        """Get list of create_workspace calls. Returns copy to prevent mutation."""
        return list(self._create_calls)

    @property
    def rename_calls(self) -> list[RenameWorkspaceCall]:
        """Get list of rename_workspace calls. Returns copy to prevent mutation."""
        return list(self._rename_calls)

    def create_workspace(self, *, command: str) -> str:
        """Track the call and return configured workspace ref or raise error."""
        self._create_calls.append(CreateWorkspaceCall(command=command))
        if self._create_error is not None:
            raise RuntimeError(self._create_error)
        return self._workspace_ref

    def rename_workspace(self, *, workspace_ref: str, new_name: str) -> None:
        """Track the rename call."""
        self._rename_calls.append(
            RenameWorkspaceCall(workspace_ref=workspace_ref, new_name=new_name)
        )
