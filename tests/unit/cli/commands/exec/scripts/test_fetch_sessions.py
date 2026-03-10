"""Unit tests for fetch-sessions command."""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.fetch_sessions import fetch_sessions
from erk_shared.context.context import ErkContext
from tests.fakes.gateway.git import FakeGit


class TestFetchSessionsBranchNotFound:
    """Tests for fetch-sessions when the planned-pr-context branch doesn't exist."""

    def test_branch_not_found(self, tmp_path: Path) -> None:
        """Error when planned-pr-context branch doesn't exist on remote."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        output_dir = tmp_path / "learn"
        fake_git = FakeGit(
            current_branches={repo_root: "plan/my-feature"},
            local_branches={repo_root: []},
            remote_branches={repo_root: []},
        )
        runner = CliRunner()

        result = runner.invoke(
            fetch_sessions,
            [
                "--pr-number",
                "42",
                "--output-dir",
                str(output_dir),
            ],
            obj=ErkContext.for_test(git=fake_git, repo_root=repo_root, cwd=repo_root),
        )

        assert result.exit_code == 1
        output = json.loads(result.output)
        assert output["success"] is False
        assert output["error"] == "branch_not_found"


class TestFetchSessionsSuccess:
    """Tests for fetch-sessions when branch and manifest exist."""

    def test_fetches_manifest_and_files(self, tmp_path: Path) -> None:
        """Successfully fetches manifest and XML files from branch."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        output_dir = tmp_path / "learn"

        manifest = {
            "version": 1,
            "pr_number": 42,
            "sessions": [
                {
                    "session_id": "abc-123",
                    "stage": "planning",
                    "source": "local",
                    "uploaded_at": "2026-02-28T12:00:00+00:00",
                    "files": ["planning-abc-123.xml"],
                },
                {
                    "session_id": "def-456",
                    "stage": "impl",
                    "source": "remote",
                    "uploaded_at": "2026-02-28T14:00:00+00:00",
                    "files": ["impl-def-456-part1.xml", "impl-def-456-part2.xml"],
                },
            ],
        }

        xml_content = b"<session>test xml content</session>"

        fake_git = FakeGit(
            current_branches={repo_root: "plan/my-feature"},
            local_branches={repo_root: []},
            remote_branches={repo_root: ["origin/planned-pr-context/42"]},
            ref_file_contents={
                (
                    "origin/planned-pr-context/42",
                    ".erk/sessions/manifest.json",
                ): json.dumps(manifest).encode("utf-8"),
                (
                    "origin/planned-pr-context/42",
                    ".erk/sessions/planning-abc-123.xml",
                ): xml_content,
                (
                    "origin/planned-pr-context/42",
                    ".erk/sessions/impl-def-456-part1.xml",
                ): xml_content,
                (
                    "origin/planned-pr-context/42",
                    ".erk/sessions/impl-def-456-part2.xml",
                ): xml_content,
            },
        )
        runner = CliRunner()

        result = runner.invoke(
            fetch_sessions,
            [
                "--pr-number",
                "42",
                "--output-dir",
                str(output_dir),
            ],
            obj=ErkContext.for_test(git=fake_git, repo_root=repo_root, cwd=repo_root),
        )

        assert result.exit_code == 0, f"Failed: {result.output}"
        output = json.loads(result.output)
        assert output["success"] is True
        assert output["pr_number"] == 42
        assert output["session_branch"] == "planned-pr-context/42"
        assert len(output["files"]) == 3
        assert output["manifest"]["version"] == 1
        assert len(output["manifest"]["sessions"]) == 2

        # Verify output directory was created and files written
        assert output_dir.exists()


class TestFetchSessionsManifestNotFound:
    """Tests for fetch-sessions when branch exists but has no manifest."""

    def test_manifest_not_found(self, tmp_path: Path) -> None:
        """Error when manifest.json not found on branch."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        output_dir = tmp_path / "learn"
        fake_git = FakeGit(
            current_branches={repo_root: "plan/my-feature"},
            local_branches={repo_root: []},
            remote_branches={repo_root: ["origin/planned-pr-context/42"]},
            # No ref_file_contents — manifest doesn't exist
        )
        runner = CliRunner()

        result = runner.invoke(
            fetch_sessions,
            [
                "--pr-number",
                "42",
                "--output-dir",
                str(output_dir),
            ],
            obj=ErkContext.for_test(git=fake_git, repo_root=repo_root, cwd=repo_root),
        )

        assert result.exit_code == 1
        output = json.loads(result.output)
        assert output["success"] is False
        assert output["error"] == "manifest_not_found"
