import os
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _clear_claudecode_env() -> Iterator[None]:
    """Clear CLAUDECODE env var so the SDK can spawn a nested Claude Code process."""
    old_value = os.environ.pop("CLAUDECODE", None)
    yield
    if old_value is not None:
        os.environ["CLAUDECODE"] = old_value


@pytest.fixture
def temp_python_repo(tmp_path: Path) -> Path:
    """Create a temporary git repo with a simple Python module."""
    repo = tmp_path / "test-repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"], cwd=repo, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"], cwd=repo, check=True, capture_output=True
    )
    (repo / "main.py").write_text(
        "# Main module\n\ndef greet(name: str) -> str:\n    return f'Hi {name}'\n"
    )
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"], cwd=repo, check=True, capture_output=True
    )
    return repo
