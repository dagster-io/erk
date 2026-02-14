"""Real AgentDocs implementation using filesystem operations.

Production implementation that reads/writes to docs/learned/ directory
and formats markdown with prettier.
"""

from pathlib import Path

from erk_shared.gateway.agent_docs.abc import AgentDocs
from erk_shared.subprocess_utils import run_subprocess_with_context


class RealAgentDocs(AgentDocs):
    """Production implementation backed by filesystem."""

    def has_docs_dir(self, project_root: Path) -> bool:
        """Check if docs/learned/ directory exists.

        Args:
            project_root: Root of the project

        Returns:
            True if docs/learned/ directory exists
        """
        docs_dir = project_root / "docs" / "learned"
        if not docs_dir.exists():
            return False
        return docs_dir.is_dir()

    def list_files(self, project_root: Path) -> list[str]:
        """List all markdown files in docs/learned/ directory.

        Args:
            project_root: Root of the project

        Returns:
            List of relative paths under docs/learned/ (e.g., "architecture/subprocess-wrappers.md")
        """
        docs_dir = project_root / "docs" / "learned"
        if not docs_dir.exists():
            return []

        # Use rglob to find all .md files recursively
        md_files = docs_dir.rglob("*.md")

        # Convert to relative paths from docs/learned/
        rel_paths = []
        for md_file in md_files:
            rel_path = md_file.relative_to(docs_dir)
            rel_paths.append(str(rel_path))

        return sorted(rel_paths)

    def read_file(self, project_root: Path, rel_path: str) -> str | None:
        """Read a file from docs/learned/ directory.

        Args:
            project_root: Root of the project
            rel_path: Relative path under docs/learned/
                (e.g., "architecture/subprocess-wrappers.md")

        Returns:
            File content, or None if file not found
        """
        file_path = project_root / "docs" / "learned" / rel_path
        if not file_path.exists():
            return None
        return file_path.read_text(encoding="utf-8")

    def write_file(self, project_root: Path, rel_path: str, content: str) -> None:
        """Write a file to docs/learned/ directory.

        Creates parent directories as needed.

        Args:
            project_root: Root of the project
            rel_path: Relative path under docs/learned/
                (e.g., "architecture/subprocess-wrappers.md")
            content: File content to write
        """
        file_path = project_root / "docs" / "learned" / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

    def format_markdown(self, content: str) -> str:
        """Format markdown content with prettier.

        Runs prettier twice to ensure idempotent output. Prettier converts
        underscore emphasis (__text__) to asterisk emphasis on first pass,
        then escapes asterisks on second pass. A single pass causes cycling
        between `erk docs sync` and `make prettier --write`.

        Args:
            content: Raw markdown content

        Returns:
            Formatted markdown content
        """
        # First pass: normalize emphasis markers and basic formatting
        result = run_subprocess_with_context(
            cmd=["prettier", "--stdin-filepath", "temp.md"],
            operation_context="format markdown with prettier (pass 1)",
            input=content,
        )
        # Second pass: escape any asterisks that would be re-interpreted
        result = run_subprocess_with_context(
            cmd=["prettier", "--stdin-filepath", "temp.md"],
            operation_context="format markdown with prettier (pass 2)",
            input=result.stdout,
        )
        return result.stdout
