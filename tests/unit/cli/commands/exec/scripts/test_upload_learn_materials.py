"""Unit tests for upload-learn-materials exec script.

Tests uploading learn materials directory to GitHub gist with proper error handling.
Uses fakes for fast, reliable testing without subprocess calls.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.upload_learn_materials import upload_learn_materials
from erk_shared.context.context import ErkContext
from erk_shared.github.fake import FakeGitHub

# ============================================================================
# Success Cases (Layer 4: Business Logic over Fakes)
# ============================================================================


def test_upload_learn_materials_success_single_file(tmp_path: Path) -> None:
    """Test successful upload with a single file in learn directory."""
    # Create learn directory with one file
    learn_dir = tmp_path / "learn"
    learn_dir.mkdir()
    (learn_dir / "planning-abc123.xml").write_text("<session>test content</session>")

    fake_github = FakeGitHub()

    runner = CliRunner()
    result = runner.invoke(
        upload_learn_materials,
        ["--learn-dir", str(learn_dir), "--issue", "123"],
        obj=ErkContext.for_test(github=fake_github, cwd=tmp_path, repo_root=tmp_path),
    )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert "gist_url" in output
    assert output["file_count"] == 1

    # Verify gist was created
    assert len(fake_github.created_gists) == 1
    filename, content, description, public = fake_github.created_gists[0]
    assert filename == "learn-materials-plan-123.txt"
    assert "Learn materials for plan #123" in description
    assert public is False
    assert "planning-abc123.xml" in content
    assert "<session>test content</session>" in content


def test_upload_learn_materials_success_multiple_files(tmp_path: Path) -> None:
    """Test successful upload with multiple files in learn directory."""
    # Create learn directory with multiple files
    learn_dir = tmp_path / "learn"
    learn_dir.mkdir()
    (learn_dir / "planning-abc123.xml").write_text("<session>planning data</session>")
    (learn_dir / "impl-def456.xml").write_text("<session>impl data</session>")
    (learn_dir / "pr-comments.json").write_text('{"comments": []}')

    fake_github = FakeGitHub()

    runner = CliRunner()
    result = runner.invoke(
        upload_learn_materials,
        ["--learn-dir", str(learn_dir), "--issue", "456"],
        obj=ErkContext.for_test(github=fake_github, cwd=tmp_path, repo_root=tmp_path),
    )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["file_count"] == 3

    # Verify gist content contains all files with delimiters
    assert len(fake_github.created_gists) == 1
    _, content, _, _ = fake_github.created_gists[0]
    assert "FILE: impl-def456.xml" in content
    assert "FILE: planning-abc123.xml" in content
    assert "FILE: pr-comments.json" in content
    assert "<session>planning data</session>" in content
    assert "<session>impl data</session>" in content
    assert '{"comments": []}' in content


def test_upload_learn_materials_files_are_sorted(tmp_path: Path) -> None:
    """Test that files are sorted alphabetically in the combined content."""
    # Create learn directory with files that would be unsorted
    learn_dir = tmp_path / "learn"
    learn_dir.mkdir()
    (learn_dir / "z-file.txt").write_text("z content")
    (learn_dir / "a-file.txt").write_text("a content")
    (learn_dir / "m-file.txt").write_text("m content")

    fake_github = FakeGitHub()

    runner = CliRunner()
    result = runner.invoke(
        upload_learn_materials,
        ["--learn-dir", str(learn_dir), "--issue", "789"],
        obj=ErkContext.for_test(github=fake_github, cwd=tmp_path, repo_root=tmp_path),
    )

    assert result.exit_code == 0
    _, content, _, _ = fake_github.created_gists[0]

    # Files should appear in alphabetical order
    a_pos = content.find("FILE: a-file.txt")
    m_pos = content.find("FILE: m-file.txt")
    z_pos = content.find("FILE: z-file.txt")
    assert a_pos < m_pos < z_pos


# ============================================================================
# Error Cases (Layer 4: Business Logic over Fakes)
# ============================================================================


def test_upload_learn_materials_fails_empty_directory(tmp_path: Path) -> None:
    """Test error when learn directory is empty."""
    # Create empty learn directory
    learn_dir = tmp_path / "learn"
    learn_dir.mkdir()

    fake_github = FakeGitHub()

    runner = CliRunner()
    result = runner.invoke(
        upload_learn_materials,
        ["--learn-dir", str(learn_dir), "--issue", "123"],
        obj=ErkContext.for_test(github=fake_github, cwd=tmp_path, repo_root=tmp_path),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "No files found" in output["error"]

    # Verify no gist was created
    assert len(fake_github.created_gists) == 0


def test_upload_learn_materials_fails_on_gist_error(tmp_path: Path) -> None:
    """Test error handling when gist creation fails."""
    # Create learn directory with a file
    learn_dir = tmp_path / "learn"
    learn_dir.mkdir()
    (learn_dir / "test.xml").write_text("<session>test</session>")

    # Configure FakeGitHub to return an error
    fake_github = FakeGitHub(gist_create_error="rate limit exceeded")

    runner = CliRunner()
    result = runner.invoke(
        upload_learn_materials,
        ["--learn-dir", str(learn_dir), "--issue", "123"],
        obj=ErkContext.for_test(github=fake_github, cwd=tmp_path, repo_root=tmp_path),
    )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "Failed to create gist" in output["error"]
    assert "rate limit exceeded" in output["error"]


def test_upload_learn_materials_ignores_subdirectories(tmp_path: Path) -> None:
    """Test that subdirectories in learn directory are ignored."""
    # Create learn directory with files and a subdirectory
    learn_dir = tmp_path / "learn"
    learn_dir.mkdir()
    (learn_dir / "file.xml").write_text("<session>data</session>")
    subdir = learn_dir / "subdir"
    subdir.mkdir()
    (subdir / "nested.txt").write_text("nested content")

    fake_github = FakeGitHub()

    runner = CliRunner()
    result = runner.invoke(
        upload_learn_materials,
        ["--learn-dir", str(learn_dir), "--issue", "123"],
        obj=ErkContext.for_test(github=fake_github, cwd=tmp_path, repo_root=tmp_path),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["file_count"] == 1  # Only the file, not the subdirectory

    _, content, _, _ = fake_github.created_gists[0]
    assert "file.xml" in content
    assert "nested.txt" not in content
