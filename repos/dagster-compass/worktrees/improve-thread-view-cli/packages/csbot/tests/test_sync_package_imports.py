"""Test that only certain files import known sync packages."""

import ast
import os
from pathlib import Path


def find_python_files(root_dir: str) -> list[str]:
    """Find all Python files in the given directory recursively."""
    python_files = []
    for root, dirs, files in os.walk(root_dir):
        # Skip __pycache__ and other common directories to ignore
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]

        for file in files:
            if file.endswith(".py"):
                python_files.append(os.path.join(root, file))

    return python_files


def file_imports(file_path: str, check_modules: list[str]) -> bool:
    """Find all imports from the external github package in a Python file."""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content)

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module in check_modules:
                    return True
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in check_modules:
                        return True

        return False
    except (SyntaxError, UnicodeDecodeError, FileNotFoundError):
        # Skip files that can't be parsed
        return False


class TestGitHubPackageImports:
    """Test that only the allowed file imports from the external github package."""

    def test_only_config_py_imports_from_github_package(self):
        """Ensure only src/csbot/github/config.py imports from the external github package."""
        # Get the project root directory
        project_root = Path(__file__).parent.parent
        src_dir = project_root / "src"

        # Find all Python files in the src directory
        python_files = find_python_files(str(src_dir))

        for file_path in python_files:
            # Convert to relative path for easier reading
            rel_path = os.path.relpath(file_path, str(project_root))

            # Skip the allowed file
            if rel_path == "src/csbot/local_context_store/github/config.py":
                continue

            # Check for github imports
            assert not file_imports(file_path, ["github"]), (
                f"{file_path} should not import from the github package"
            )

    def test_config_py_does_import_from_github_package(self):
        """Ensure that src/csbot/local_context_store/github/config.py actually does import from the github package."""
        project_root = Path(__file__).parent.parent
        config_file = (
            project_root / "src" / "csbot" / "local_context_store" / "github" / "config.py"
        )
        assert file_imports(str(config_file), ["github"]), (
            "src/csbot/local_context_store/github/config.py should import from the github package"
        )
