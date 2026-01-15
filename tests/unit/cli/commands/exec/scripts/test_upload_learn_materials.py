"""Unit tests for upload-learn-materials exec script.

Tests uploading preprocessed session files to learn-materials branch
using GitHub Contents API.

Note: Full CLI integration tests are deferred since they require
GitHub repo identity in context. These tests focus on helper functions
and subprocess mocking patterns.
"""

import subprocess
from pathlib import Path
from typing import Any

from erk.cli.commands.exec.scripts.upload_learn_materials import (
    LEARN_MATERIALS_BRANCH,
    LEARN_MATERIALS_DIR,
    UploadedFile,
    _branch_exists,
    _create_branch,
    _get_default_branch,
    _get_existing_file_sha,
    _upload_file,
)

# ============================================================================
# Constants Tests
# ============================================================================


def test_constants() -> None:
    """Test that constants have expected values."""
    assert LEARN_MATERIALS_BRANCH == "learn-materials"
    assert LEARN_MATERIALS_DIR == ".learn-materials"


# ============================================================================
# UploadedFile Dataclass Tests
# ============================================================================


def test_uploaded_file_dataclass() -> None:
    """Test UploadedFile dataclass creation."""
    file = UploadedFile(path=".learn-materials/123/file.xml", url="https://example.com/file.xml")
    assert file.path == ".learn-materials/123/file.xml"
    assert file.url == "https://example.com/file.xml"


def test_uploaded_file_frozen() -> None:
    """Test UploadedFile is frozen (immutable)."""
    file = UploadedFile(path="path", url="url")
    try:
        file.path = "new_path"  # type: ignore[misc]
        raise AssertionError("Expected FrozenInstanceError")
    except AttributeError:
        pass  # Expected


# ============================================================================
# _get_default_branch Tests
# ============================================================================


def test_get_default_branch_detects_main(monkeypatch: Any, tmp_path: Path) -> None:
    """Test _get_default_branch detects main branch."""

    def mock_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if "symbolic-ref" in cmd:
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout="refs/remotes/origin/main\n",
                stderr="",
            )
        return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)

    result = _get_default_branch(tmp_path)
    assert result == "main"


def test_get_default_branch_detects_master_via_fallback(monkeypatch: Any, tmp_path: Path) -> None:
    """Test _get_default_branch detects master branch via fallback."""

    def mock_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if "symbolic-ref" in cmd:
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=1,
                stdout="",
                stderr="fatal: ref refs/remotes/origin/HEAD is not a symbolic ref",
            )
        if "ls-remote" in cmd and "main" in cmd:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")
        if "ls-remote" in cmd and "master" in cmd:
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout="abc123\trefs/heads/master\n",
                stderr="",
            )
        return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)

    result = _get_default_branch(tmp_path)
    assert result == "master"


def test_get_default_branch_fallback_to_main(monkeypatch: Any, tmp_path: Path) -> None:
    """Test _get_default_branch falls back to main when nothing found."""

    def mock_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)

    result = _get_default_branch(tmp_path)
    assert result == "main"


# ============================================================================
# _branch_exists Tests
# ============================================================================


def test_branch_exists_returns_true(monkeypatch: Any) -> None:
    """Test _branch_exists returns True when branch exists."""

    def mock_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)

    result = _branch_exists("owner", "repo")
    assert result is True


def test_branch_exists_returns_false(monkeypatch: Any) -> None:
    """Test _branch_exists returns False when branch doesn't exist."""

    def mock_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)

    result = _branch_exists("owner", "repo")
    assert result is False


# ============================================================================
# _create_branch Tests
# ============================================================================


def test_create_branch_success(monkeypatch: Any) -> None:
    """Test _create_branch returns True on success."""
    call_count = 0

    def mock_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        nonlocal call_count
        call_count += 1
        if call_count == 1:  # Get SHA
            return subprocess.CompletedProcess(
                args=cmd, returncode=0, stdout="abc123def456\n", stderr=""
            )
        else:  # Create ref
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)

    result = _create_branch("owner", "repo", "main")
    assert result is True


def test_create_branch_failure_no_sha(monkeypatch: Any) -> None:
    """Test _create_branch returns False when base SHA lookup fails."""

    def mock_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)

    result = _create_branch("owner", "repo", "main")
    assert result is False


def test_create_branch_failure_empty_sha(monkeypatch: Any) -> None:
    """Test _create_branch returns False when SHA is empty."""

    def mock_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)

    result = _create_branch("owner", "repo", "main")
    assert result is False


def test_create_branch_failure_ref_creation(monkeypatch: Any) -> None:
    """Test _create_branch returns False when ref creation fails."""
    call_count = 0

    def mock_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        nonlocal call_count
        call_count += 1
        if call_count == 1:  # Get SHA succeeds
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="abc123\n", stderr="")
        else:  # Create ref fails
            return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="error")

    monkeypatch.setattr(subprocess, "run", mock_run)

    result = _create_branch("owner", "repo", "main")
    assert result is False


# ============================================================================
# _get_existing_file_sha Tests
# ============================================================================


def test_get_existing_file_sha_found(monkeypatch: Any) -> None:
    """Test _get_existing_file_sha returns SHA when file exists."""

    def mock_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=cmd, returncode=0, stdout="abc123def456\n", stderr=""
        )

    monkeypatch.setattr(subprocess, "run", mock_run)

    result = _get_existing_file_sha("owner", "repo", "path/to/file.xml")
    assert result == "abc123def456"


def test_get_existing_file_sha_not_found(monkeypatch: Any) -> None:
    """Test _get_existing_file_sha returns None when file doesn't exist."""

    def mock_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)

    result = _get_existing_file_sha("owner", "repo", "path/to/file.xml")
    assert result is None


def test_get_existing_file_sha_empty_response(monkeypatch: Any) -> None:
    """Test _get_existing_file_sha returns None when response is empty."""

    def mock_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)

    result = _get_existing_file_sha("owner", "repo", "path/to/file.xml")
    assert result is None


# ============================================================================
# _upload_file Tests
# ============================================================================


def test_upload_file_success(monkeypatch: Any, tmp_path: Path) -> None:
    """Test _upload_file returns UploadedFile on success."""
    # Create test file
    test_file = tmp_path / "test.xml"
    test_file.write_text("<test>content</test>", encoding="utf-8")

    call_count = 0

    def mock_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        nonlocal call_count
        call_count += 1
        if call_count == 1:  # Check existing SHA
            return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="")
        else:  # Upload
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="{}", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)

    result = _upload_file(
        owner="testowner",
        repo="testrepo",
        issue_number=123,
        local_path=test_file,
        dest_filename="test.xml",
    )

    assert isinstance(result, UploadedFile)
    assert result.path == ".learn-materials/123/test.xml"
    assert "testowner/testrepo" in result.url
    assert "learn-materials" in result.url


def test_upload_file_update_existing(monkeypatch: Any, tmp_path: Path) -> None:
    """Test _upload_file includes SHA when updating existing file."""
    test_file = tmp_path / "test.xml"
    test_file.write_text("<test>content</test>", encoding="utf-8")

    upload_cmd: list[str] = []
    call_count = 0

    def mock_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        nonlocal call_count, upload_cmd
        call_count += 1
        if call_count == 1:  # Check existing SHA - file exists
            return subprocess.CompletedProcess(
                args=cmd, returncode=0, stdout="existing_sha_123\n", stderr=""
            )
        else:  # Upload
            upload_cmd = cmd
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="{}", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)

    result = _upload_file(
        owner="testowner",
        repo="testrepo",
        issue_number=123,
        local_path=test_file,
        dest_filename="test.xml",
    )

    assert isinstance(result, UploadedFile)
    # Verify SHA was included in upload command
    assert "sha=existing_sha_123" in " ".join(upload_cmd)


def test_upload_file_not_found() -> None:
    """Test _upload_file returns error when file doesn't exist."""
    result = _upload_file(
        owner="testowner",
        repo="testrepo",
        issue_number=123,
        local_path=Path("/nonexistent/file.xml"),
        dest_filename="file.xml",
    )

    assert isinstance(result, str)
    assert "not found" in result.lower()


def test_upload_file_api_failure(monkeypatch: Any, tmp_path: Path) -> None:
    """Test _upload_file returns error on API failure."""
    test_file = tmp_path / "test.xml"
    test_file.write_text("<test>content</test>", encoding="utf-8")

    call_count = 0

    def mock_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        nonlocal call_count
        call_count += 1
        if call_count == 1:  # Check existing SHA
            return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="")
        else:  # Upload fails
            return subprocess.CompletedProcess(
                args=cmd, returncode=1, stdout="", stderr="API error: rate limited"
            )

    monkeypatch.setattr(subprocess, "run", mock_run)

    result = _upload_file(
        owner="testowner",
        repo="testrepo",
        issue_number=123,
        local_path=test_file,
        dest_filename="test.xml",
    )

    assert isinstance(result, str)
    assert "Failed to upload" in result


def test_upload_file_url_format(monkeypatch: Any, tmp_path: Path) -> None:
    """Test _upload_file generates correct URL format."""
    test_file = tmp_path / "session.xml"
    test_file.write_text("<session/>", encoding="utf-8")

    def mock_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="{}", stderr="")

    monkeypatch.setattr(subprocess, "run", mock_run)

    result = _upload_file(
        owner="myorg",
        repo="myrepo",
        issue_number=456,
        local_path=test_file,
        dest_filename="session.xml",
    )

    assert isinstance(result, UploadedFile)
    expected_url = (
        "https://github.com/myorg/myrepo/blob/learn-materials/.learn-materials/456/session.xml"
    )
    assert result.url == expected_url
