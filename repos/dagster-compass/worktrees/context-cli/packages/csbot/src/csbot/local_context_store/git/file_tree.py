"""File tree interface for the context engine.

This module provides a unified interface for reading files and directories from different sources,
primarily Git repositories and the filesystem. The FileTree protocol abstracts these differences
to allow the context engine to work with both Git-backed repositories and local filesystem
directories seamlessly.

GitCommitFileTree uses pygit2, which is a set of Python bindings for libgit2 - a portable, pure C
implementation of the Git core. This provides very fast access to Git repository files without
requiring filesystem checkout operations.

This allows for an extremely fast way to access the context store, which is git-backed.

## Architecture

The module follows a protocol-based design with two main implementations:

1. **GitCommitFileTree**: Uses pygit2 to read from Git tree objects, enabling efficient access
   to repository contents at specific commits without checking out files to disk.

2. **FilesystemFileTree**: Direct filesystem access using pathlib, primarily used for testing
   and scenarios where Git integration isn't available.

## Usage Patterns

FileTree instances are typically obtained through the GithubWorkingDir.latest() context manager:

```python
with github_working_dir.latest() as tree:
    if tree.exists("config.yaml"):
        config_content = tree.read_text("config.yaml")

    for yaml_file in tree.recursive_glob("**/*.yaml"):
        process_file(yaml_file)
```

## Design Considerations

- **Read-Only**: FileTree is designed for read operations only; write operations go through the
  pull request context mechanisms
- **Path Consistency**: All paths use forward slashes and are relative to the repository root
- **Git Behavior**: FilesystemFileTree excludes .git directories to match Git tree behavior
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Protocol

import pygit2

from csbot.local_context_store.git.utils import extract_git_info
from csbot.utils.check_async_context import ensure_not_in_async_context

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

    from csbot.contextengine.contextstore_protocol import GitInfo


class FileTree(Protocol):
    """Protocol for file tree access interfaces."""

    def read_text(self, path: str) -> str:
        """Read a file as text."""
        ...

    def exists(self, path: str) -> bool:
        """Check if a path exists."""
        ...

    def is_file(self, path: str) -> bool:
        """Check if a path is a file."""
        ...

    def is_dir(self, path: str) -> bool:
        """Check if a path is a directory."""
        ...

    def listdir(self, path: str = "") -> list[str]:
        """List contents of a directory."""
        ...

    def glob(self, path: str, pattern: str) -> Generator[str]:
        """Find files matching a pattern in a directory."""
        ...

    def recursive_glob(self, pattern: str) -> Generator[str]:
        """Find files matching a pattern recursively."""
        ...

    def get_git_info(self) -> GitInfo | None:
        """Get git info."""
        ...


class FilesystemFileTree:
    """Filesystem-based implementation of the file tree interface for testing."""

    def __init__(self, root_path: Path):
        self.root_path = root_path

    def read_text(self, path: str) -> str:
        """Read a file from the filesystem as text."""
        ensure_not_in_async_context()
        file_path = self.root_path / path
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        if not file_path.is_file():
            raise IsADirectoryError(f"Path is not a file: {path}")
        return file_path.read_text()

    def exists(self, path: str) -> bool:
        """Check if a path exists in the filesystem."""
        ensure_not_in_async_context()
        return (self.root_path / path).exists()

    def is_file(self, path: str) -> bool:
        """Check if a path is a file."""
        ensure_not_in_async_context()
        return (self.root_path / path).is_file()

    def is_dir(self, path: str) -> bool:
        """Check if a path is a directory."""
        ensure_not_in_async_context()
        return (self.root_path / path).is_dir()

    def listdir(self, path: str = "") -> list[str]:
        """List contents of a directory."""
        ensure_not_in_async_context()
        dir_path = self.root_path / path if path else self.root_path
        if not dir_path.exists():
            raise FileNotFoundError(f"Directory not found: {path}")
        if not dir_path.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {path}")
        # Exclude .git directory to match git tree behavior
        return [item.name for item in dir_path.iterdir() if item.name != ".git"]

    def glob(self, path: str, pattern: str) -> Generator[str]:
        """Find files matching a pattern in a directory."""
        ensure_not_in_async_context()
        dir_path = self.root_path / path if path else self.root_path
        if not dir_path.exists() or not dir_path.is_dir():
            return
        for item in dir_path.glob(pattern):
            # Return full path relative to root, matching GitCommitFileTree behavior
            if path:
                yield f"{path}/{item.name}"
            else:
                yield item.name

    def recursive_glob(self, pattern: str) -> Generator[str]:
        """Find files matching a pattern recursively."""
        ensure_not_in_async_context()
        # Collect all files first, similar to GitCommitFileTree approach
        all_files = []

        def _walk_directory(current_path: Path, relative_path: str = "") -> None:
            """Walk directory recursively, collecting all files."""
            for item in current_path.iterdir():
                if item.name == ".git":
                    continue  # Exclude .git to match git behavior

                item_relative_path = f"{relative_path}/{item.name}" if relative_path else item.name

                if item.is_file():
                    all_files.append(item_relative_path)
                elif item.is_dir():
                    _walk_directory(item, item_relative_path)

        _walk_directory(self.root_path)

        # Now filter using the same pattern matching logic as GitCommitFileTree
        for file_path in all_files:
            if self._matches_glob_pattern(file_path, pattern):
                yield file_path

    def _matches_glob_pattern(self, path: str, pattern: str) -> bool:
        """Custom glob pattern matching to emulate GitCommitFileTree behavior."""
        import fnmatch
        from pathlib import PurePosixPath

        # Handle ** patterns specially
        if "**" in pattern:
            # For ** patterns, use simpler recursive matching
            if pattern.endswith("/**/*"):
                # Pattern like "context/**/*" - match any file under context
                prefix = pattern[:-6]  # Remove "/**/*"
                return path.startswith(prefix + "/") and "/" in path[len(prefix) + 1 :]
            elif "/**/" in pattern:
                # Pattern like "context/**/*.yaml"
                parts = pattern.split("/**/")
                if len(parts) == 2:
                    prefix, suffix = parts
                    return path.startswith(prefix + "/") and fnmatch.fnmatch(
                        path.split("/")[-1], suffix
                    )

        # Use PurePath.match for simple patterns
        return PurePosixPath(path).match(pattern)

    def get_git_info(self) -> GitInfo | None:
        """Get git info."""
        ensure_not_in_async_context()
        return None


class GitCommitFileTree:
    """Wrapper around pygit2.Tree providing Path-like file access interface.

    This class allows you to treat an arbitrary Git commit as a tree of files,
    providing efficient read-only access to the repository state at that specific
    commit without requiring filesystem checkout operations.
    """

    def __init__(self, tree: pygit2.Tree, git_info: GitInfo | None):
        self.tree = tree
        self.git_info = git_info

    def read_text(self, path: str) -> str:
        """Read a file from the tree as text."""
        ensure_not_in_async_context()
        if path not in self.tree:
            raise FileNotFoundError(f"File not found: {path}")

        if path not in self.tree:
            raise FileNotFoundError(f"File not found: {path}")

        entry = self.tree[path]
        if entry.type_str != "blob":
            raise IsADirectoryError(f"Path is not a file: {path}")
        # entry is a TreeEntry pointing to a blob
        blob = entry.peel(pygit2.Blob)
        return blob.data.decode("utf-8")

    def exists(self, path: str) -> bool:
        """Check if a path exists in the tree."""
        ensure_not_in_async_context()
        # Root directory always exists
        if path == "":
            return True
        return path in self.tree

    def is_file(self, path: str) -> bool:
        """Check if a path is a file."""
        ensure_not_in_async_context()
        if path not in self.tree:
            return False
        if path not in self.tree:
            return False
        entry = self.tree[path]
        return entry.type_str == "blob"

    def is_dir(self, path: str) -> bool:
        """Check if a path is a directory."""
        ensure_not_in_async_context()
        # Root directory is always a directory
        if path == "":
            return True
        if path not in self.tree:
            return False
        entry = self.tree[path]
        return entry.type_str == "tree"

    def listdir(self, path: str = "") -> list[str]:
        """List contents of a directory."""
        ensure_not_in_async_context()
        if path == "":
            return [entry.name for entry in self.tree if entry.name is not None]

        if path not in self.tree:
            raise FileNotFoundError(f"Directory not found: {path}")

        entry = self.tree[path]
        if entry.type_str != "tree":
            raise NotADirectoryError(f"Path is not a directory: {path}")
        # Get the subtree object
        subtree = entry.peel(pygit2.Tree)
        return [entry.name for entry in subtree if entry.name is not None]

    def glob(self, path: str, pattern: str) -> Generator[str]:
        """Find files matching a pattern in a directory."""
        ensure_not_in_async_context()
        import fnmatch

        if not self.is_dir(path):
            return
        for name in self.listdir(path):
            if fnmatch.fnmatch(name, pattern):
                yield f"{path}/{name}" if path else name

    def recursive_glob(self, pattern: str) -> Generator[str]:
        """Find files matching a pattern recursively."""
        ensure_not_in_async_context()
        # Collect all files first
        all_files = []

        def _walk_tree(tree: pygit2.Tree, current_path: str = "") -> None:
            for entry in tree:
                if entry.name is None:
                    continue

                entry_path = f"{current_path}/{entry.name}" if current_path else entry.name

                if entry.type_str == "blob":
                    all_files.append(entry_path)
                elif entry.type_str == "tree":
                    subtree = entry.peel(pygit2.Tree)
                    _walk_tree(subtree, entry_path)

        _walk_tree(self.tree)

        # Now filter using PurePath matching (which handles ** correctly for some patterns)
        for file_path in all_files:
            # Try to emulate filesystem glob behavior
            if self._matches_glob_pattern(file_path, pattern):
                yield file_path

    def _matches_glob_pattern(self, path: str, pattern: str) -> bool:
        """Custom glob pattern matching to emulate filesystem behavior."""
        import fnmatch
        from pathlib import PurePosixPath

        # Handle ** patterns specially
        if "**" in pattern:
            # For ** patterns, use simpler recursive matching
            if pattern.endswith("/**/*"):
                # Pattern like "context/**/*" - match any file under context
                prefix = pattern[:-6]  # Remove "/**/*"
                return path.startswith(prefix + "/") and "/" in path[len(prefix) + 1 :]
            elif "/**/" in pattern:
                # Pattern like "context/**/*.yaml"
                parts = pattern.split("/**/")
                if len(parts) == 2:
                    prefix, suffix = parts
                    return path.startswith(prefix + "/") and fnmatch.fnmatch(
                        path.split("/")[-1], suffix
                    )

        # Use PurePath.match for simple patterns
        return PurePosixPath(path).match(pattern)

    def get_git_info(self) -> GitInfo | None:
        """Get git info."""
        ensure_not_in_async_context()
        return self.git_info


@contextmanager
def create_git_commit_file_tree(
    repo_path: Path,
    repository_name: str,
) -> Generator[FileTree]:
    """
    Shared utility for creating GitCommitFileTree from a git repository.

    Args:
        repo_path: Path to the git repository
        repository_name: Name/identifier for the repository

    Yields:
        GitCommitFileTree: A wrapper around pygit2.Tree with Path-like interface
    """
    ensure_not_in_async_context()
    repo = pygit2.Repository(str(repo_path))
    commit_obj = repo[repo.head.target]
    tree = commit_obj.peel(pygit2.Tree)
    git_info = extract_git_info(repo_path, repository_name)
    yield GitCommitFileTree(tree, git_info)
