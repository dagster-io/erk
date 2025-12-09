"""Unit tests for extract_session_from_issue kit CLI command.

Tests extracting session XML content from GitHub issue comments.
Uses FakeGitHubIssues for fast, reliable testing.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from click.testing import CliRunner
from erk_shared.git.fake import FakeGit
from erk_shared.github.issues import FakeGitHubIssues
from erk_shared.github.issues.types import IssueInfo
from erk_shared.github.metadata import render_session_content_block

from dot_agent_kit.context import DotAgentContext
from dot_agent_kit.data.kits.erk.scripts.erk.extract_session_from_issue import (
    extract_session_from_issue,
)


def make_issue_info(number: int) -> IssueInfo:
    """Create test IssueInfo with given number."""
    now = datetime.now(UTC)
    return IssueInfo(
        number=number,
        title=f"Test Issue #{number}",
        body="Test issue body",
        state="OPEN",
        url=f"https://github.com/test-owner/test-repo/issues/{number}",
        labels=["raw-extraction"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="test-user",
    )


# ============================================================================
# Success Cases (Layer 4: Business Logic over Fakes)
# ============================================================================


def test_extract_session_single_comment(tmp_path: Path) -> None:
    """Test extracting session content from a single comment."""
    session_xml = '<session session_id="abc123"><message>Hello world</message></session>'
    session_block = render_session_content_block(session_xml, session_label="test-session")

    fake_gh = FakeGitHubIssues(
        issues={100: make_issue_info(100)},
        comments={100: [session_block]},
    )
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        # Create .erk directory for scratch files
        (cwd / ".erk" / "scratch").mkdir(parents=True)

        result = runner.invoke(
            extract_session_from_issue,
            ["100"],
            obj=DotAgentContext.for_test(
                github_issues=fake_gh, git=fake_git, repo_root=cwd, cwd=cwd
            ),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 100
    assert "session_file" in output
    assert "abc123" in output["session_ids"]


def test_extract_session_multiple_chunks(tmp_path: Path) -> None:
    """Test extracting and combining multiple chunked session comments."""
    chunk1 = render_session_content_block(
        '<session session_id="chunk1">Part 1</session>',
        chunk_number=1,
        total_chunks=2,
    )
    chunk2 = render_session_content_block(
        '<session session_id="chunk2">Part 2</session>',
        chunk_number=2,
        total_chunks=2,
    )

    fake_gh = FakeGitHubIssues(
        issues={200: make_issue_info(200)},
        comments={200: [chunk2, chunk1]},  # Out of order to test sorting
    )
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        (cwd / ".erk" / "scratch").mkdir(parents=True)

        result = runner.invoke(
            extract_session_from_issue,
            ["200"],
            obj=DotAgentContext.for_test(
                github_issues=fake_gh, git=fake_git, repo_root=cwd, cwd=cwd
            ),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert "chunk1" in output["session_ids"]
    assert "chunk2" in output["session_ids"]


def test_extract_session_with_explicit_output_path(tmp_path: Path) -> None:
    """Test extracting session to an explicit output path."""
    session_xml = '<session session_id="explicit123"><data>Test</data></session>'
    session_block = render_session_content_block(session_xml)

    fake_gh = FakeGitHubIssues(
        issues={300: make_issue_info(300)},
        comments={300: [session_block]},
    )
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        output_path = cwd / "custom-output" / "session.xml"

        result = runner.invoke(
            extract_session_from_issue,
            ["300", "--output", str(output_path)],
            obj=DotAgentContext.for_test(
                github_issues=fake_gh, git=fake_git, repo_root=cwd, cwd=cwd
            ),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["session_file"] == str(output_path)

    # Verify file was created with correct content
    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert "explicit123" in content


def test_extract_session_with_session_id(tmp_path: Path) -> None:
    """Test extracting session with provided session-id for scratch directory."""
    session_xml = '<session session_id="withid123"><data>Test</data></session>'
    session_block = render_session_content_block(session_xml)

    fake_gh = FakeGitHubIssues(
        issues={400: make_issue_info(400)},
        comments={400: [session_block]},
    )
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        (cwd / ".erk" / "scratch").mkdir(parents=True)

        result = runner.invoke(
            extract_session_from_issue,
            ["400", "--session-id", "custom-session-id"],
            obj=DotAgentContext.for_test(
                github_issues=fake_gh, git=fake_git, repo_root=cwd, cwd=cwd
            ),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    # Session file should be in custom session directory
    assert "custom-session-id" in output["session_file"]


def test_extract_session_mixed_comments(tmp_path: Path) -> None:
    """Test extracting session from comments mixed with regular comments."""
    session_block = render_session_content_block(
        '<session session_id="mixed123"><data>Real session</data></session>'
    )

    fake_gh = FakeGitHubIssues(
        issues={500: make_issue_info(500)},
        comments={
            500: [
                "Just a regular comment",
                session_block,
                "Another regular comment",
                "Status update: everything looks good!",
            ]
        },
    )
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        (cwd / ".erk" / "scratch").mkdir(parents=True)

        result = runner.invoke(
            extract_session_from_issue,
            ["500"],
            obj=DotAgentContext.for_test(
                github_issues=fake_gh, git=fake_git, repo_root=cwd, cwd=cwd
            ),
        )

    assert result.exit_code == 0, result.output
    output = json.loads(result.output)
    assert output["success"] is True
    assert "mixed123" in output["session_ids"]


# ============================================================================
# Error Cases (Layer 4: Business Logic over Fakes)
# ============================================================================


def test_extract_session_no_content_found(tmp_path: Path) -> None:
    """Test error when no session content blocks are found."""
    fake_gh = FakeGitHubIssues(
        issues={600: make_issue_info(600)},
        comments={600: ["Regular comment 1", "Regular comment 2"]},
    )
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            extract_session_from_issue,
            ["600"],
            obj=DotAgentContext.for_test(
                github_issues=fake_gh, git=fake_git, repo_root=cwd, cwd=cwd
            ),
        )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "No session content found" in output["error"]
    assert output["issue_number"] == 600


def test_extract_session_no_comments(tmp_path: Path) -> None:
    """Test error when issue has no comments."""
    fake_gh = FakeGitHubIssues(
        issues={700: make_issue_info(700)},
        comments={700: []},
    )
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            extract_session_from_issue,
            ["700"],
            obj=DotAgentContext.for_test(
                github_issues=fake_gh, git=fake_git, repo_root=cwd, cwd=cwd
            ),
        )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "No session content found" in output["error"]


# ============================================================================
# JSON Output Structure Tests
# ============================================================================


def test_json_output_structure_success(tmp_path: Path) -> None:
    """Test JSON output structure on success."""
    session_xml = '<session session_id="struct123"><data>Test</data></session>'
    session_block = render_session_content_block(session_xml)

    fake_gh = FakeGitHubIssues(
        issues={800: make_issue_info(800)},
        comments={800: [session_block]},
    )
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        (cwd / ".erk" / "scratch").mkdir(parents=True)

        result = runner.invoke(
            extract_session_from_issue,
            ["800"],
            obj=DotAgentContext.for_test(
                github_issues=fake_gh, git=fake_git, repo_root=cwd, cwd=cwd
            ),
        )

    assert result.exit_code == 0
    output = json.loads(result.output)

    # Verify required keys
    assert "success" in output
    assert "issue_number" in output
    assert "session_file" in output
    assert "session_ids" in output
    assert "chunk_count" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["issue_number"], int)
    assert isinstance(output["session_file"], str)
    assert isinstance(output["session_ids"], list)
    assert isinstance(output["chunk_count"], int)


def test_json_output_structure_error(tmp_path: Path) -> None:
    """Test JSON output structure on error."""
    fake_gh = FakeGitHubIssues(
        issues={900: make_issue_info(900)},
        comments={900: ["No session content here"]},
    )
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            extract_session_from_issue,
            ["900"],
            obj=DotAgentContext.for_test(
                github_issues=fake_gh, git=fake_git, repo_root=cwd, cwd=cwd
            ),
        )

    assert result.exit_code == 1
    output = json.loads(result.output)

    # Verify required keys for error
    assert "success" in output
    assert "error" in output
    assert "issue_number" in output

    # Verify types
    assert isinstance(output["success"], bool)
    assert isinstance(output["error"], str)
    assert output["success"] is False


# ============================================================================
# --stdout Flag Tests
# ============================================================================


def test_stdout_outputs_xml_to_stdout(tmp_path: Path) -> None:
    """Test --stdout outputs session XML to stdout."""
    session_xml = '<session session_id="stdout123"><message>Hello world</message></session>'
    session_block = render_session_content_block(session_xml, session_label="test-session")

    fake_gh = FakeGitHubIssues(
        issues={1000: make_issue_info(1000)},
        comments={1000: [session_block]},
    )
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            extract_session_from_issue,
            ["1000", "--stdout"],
            obj=DotAgentContext.for_test(
                github_issues=fake_gh, git=fake_git, repo_root=cwd, cwd=cwd
            ),
        )

    assert result.exit_code == 0, result.output
    # stdout contains the XML (Click 8.2+ separates stdout/stderr automatically)
    assert "<session session_id=" in result.stdout
    assert "stdout123" in result.stdout


def test_stdout_outputs_metadata_to_stderr(tmp_path: Path) -> None:
    """Test --stdout outputs metadata JSON to stderr."""
    session_xml = '<session session_id="stderr456"><data>Test</data></session>'
    session_block = render_session_content_block(session_xml)

    fake_gh = FakeGitHubIssues(
        issues={1100: make_issue_info(1100)},
        comments={1100: [session_block]},
    )
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()

        result = runner.invoke(
            extract_session_from_issue,
            ["1100", "--stdout"],
            obj=DotAgentContext.for_test(
                github_issues=fake_gh, git=fake_git, repo_root=cwd, cwd=cwd
            ),
        )

    assert result.exit_code == 0
    # Click 8.2+ separates stdout/stderr - verify metadata JSON is in stderr
    stderr_output = json.loads(result.stderr)
    assert stderr_output["success"] is True
    assert stderr_output["issue_number"] == 1100
    assert "stderr456" in stderr_output["session_ids"]
    assert stderr_output["chunk_count"] >= 1


def test_stdout_does_not_write_file(tmp_path: Path) -> None:
    """Test --stdout doesn't create any files."""
    session_xml = '<session session_id="nofile789"><data>Test</data></session>'
    session_block = render_session_content_block(session_xml)

    fake_gh = FakeGitHubIssues(
        issues={1200: make_issue_info(1200)},
        comments={1200: [session_block]},
    )
    fake_git = FakeGit()
    runner = CliRunner()

    with runner.isolated_filesystem(temp_dir=tmp_path):
        cwd = Path.cwd()
        scratch_dir = cwd / ".erk" / "scratch"
        scratch_dir.mkdir(parents=True)

        result = runner.invoke(
            extract_session_from_issue,
            ["1200", "--stdout"],
            obj=DotAgentContext.for_test(
                github_issues=fake_gh, git=fake_git, repo_root=cwd, cwd=cwd
            ),
        )

        # Verify no XML files were created in scratch directory
        xml_files = list(scratch_dir.rglob("*.xml"))
        assert xml_files == []

    assert result.exit_code == 0
