"""Fake AgentDocs implementation for testing.

FakeAgentDocs is an in-memory implementation backed by a dict[str, str]
mapping relative paths to content. Enables fast and deterministic tests.
"""

from pathlib import Path

from erk_shared.gateway.agent_docs.abc import AgentDocs


class FakeAgentDocs(AgentDocs):
    """In-memory fake implementation backed by dict.

    This class has NO public setup methods. All state is provided via constructor
    or captured during execution.
    """

    def __init__(
        self,
        *,
        files: dict[str, str] | None = None,
        has_docs_dir: bool = True,
    ) -> None:
        """Create FakeAgentDocs with pre-seeded file contents.

        Args:
            files: Dict mapping relative paths to content
                (e.g., {"architecture/foo.md": "# Content"}).
                Defaults to empty dict.
            has_docs_dir: Whether docs/learned/ directory exists. Defaults to True.
        """
        self._files = files if files is not None else {}
        self._has_docs_dir = has_docs_dir
        self._written_files: dict[str, str] = {}

    @property
    def written_files(self) -> dict[str, str]:
        """Get files written via write_file().

        Returns a copy of the dict to prevent external mutation.

        This property is for test assertions only.
        """
        return dict(self._written_files)

    def has_docs_dir(self, project_root: Path) -> bool:
        """Return configured docs_dir existence flag.

        Args:
            project_root: Root of the project (ignored in fake)

        Returns:
            The configured has_docs_dir value
        """
        return self._has_docs_dir

    def list_files(self, project_root: Path) -> list[str]:
        """Return sorted list of relative paths in the fake filesystem.

        Args:
            project_root: Root of the project (ignored in fake)

        Returns:
            Sorted list of relative paths
        """
        return sorted(self._files.keys())

    def read_file(self, project_root: Path, rel_path: str) -> str | None:
        """Read file from fake filesystem.

        Args:
            project_root: Root of the project (ignored in fake)
            rel_path: Relative path under docs/learned/

        Returns:
            File content, or None if not found
        """
        return self._files.get(rel_path)

    def write_file(self, project_root: Path, rel_path: str, content: str) -> None:
        """Write file to fake filesystem and track mutation.

        Args:
            project_root: Root of the project (ignored in fake)
            rel_path: Relative path under docs/learned/
            content: File content to write
        """
        self._files[rel_path] = content
        self._written_files[rel_path] = content

    def format_markdown(self, content: str) -> str:
        """Return content as-is (no-op formatter).

        Args:
            content: Raw markdown content

        Returns:
            Same content unchanged
        """
        return content
