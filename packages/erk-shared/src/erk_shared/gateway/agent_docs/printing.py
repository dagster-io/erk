"""Printing AgentDocs wrapper for verbose output.

Prints mutation operations before delegating to the wrapped implementation.
"""

from pathlib import Path

from erk_shared.gateway.agent_docs.abc import AgentDocs
from erk_shared.printing.base import PrintingBase


class PrintingAgentDocs(PrintingBase, AgentDocs):
    """Wrapper that prints agent docs operations before delegating.

    Read-only methods delegate silently.
    Mutation methods print what's happening, then delegate.
    """

    def has_docs_dir(self, project_root: Path) -> bool:
        return self._wrapped.has_docs_dir(project_root)

    def list_files(self, project_root: Path) -> list[str]:
        return self._wrapped.list_files(project_root)

    def read_file(self, project_root: Path, rel_path: str) -> str | None:
        return self._wrapped.read_file(project_root, rel_path)

    def write_file(self, project_root: Path, rel_path: str, content: str) -> None:
        self._emit(self._format_command(f"write docs/learned/{rel_path}"))
        self._wrapped.write_file(project_root, rel_path, content)

    def format_markdown(self, content: str) -> str:
        return self._wrapped.format_markdown(content)
