"""Dry-run AgentDocs implementation.

Delegates read-only methods to wrapped, no-ops mutations.
"""

from pathlib import Path

from erk_shared.gateway.agent_docs.abc import AgentDocs
from erk_shared.output.output import user_output


class DryRunAgentDocs(AgentDocs):
    """No-op wrapper that prevents writes in dry-run mode.

    Read-only methods delegate to the wrapped implementation.
    Mutation methods (write_file) are no-ops that log what would happen.
    """

    def __init__(self, wrapped: AgentDocs) -> None:
        self._wrapped = wrapped

    def has_docs_dir(self, project_root: Path) -> bool:
        return self._wrapped.has_docs_dir(project_root)

    def list_files(self, project_root: Path) -> list[str]:
        return self._wrapped.list_files(project_root)

    def read_file(self, project_root: Path, rel_path: str) -> str | None:
        return self._wrapped.read_file(project_root, rel_path)

    def write_file(self, project_root: Path, rel_path: str, content: str) -> None:
        user_output(f"[DRY RUN] Would write docs/learned/{rel_path}")

    def format_markdown(self, content: str) -> str:
        return self._wrapped.format_markdown(content)
