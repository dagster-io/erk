"""Unit tests for push-session command."""

import json
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.push_session import push_session
from erk_shared.context.context import ErkContext
from erk_shared.gateway.git.fake import FakeGit


def _write_session_file(tmp_path: Path) -> Path:
    """Create a test session JSONL file."""
    session_file = tmp_path / "session.jsonl"
    session_file.write_text('{"type": "test"}\n', encoding="utf-8")
    return session_file


def _make_xml_file(tmpdir: str, prefix: str) -> None:
    """Write a fake XML file to the preprocessing output directory."""
    xml_path = Path(tmpdir) / f"{prefix}.xml"
    xml_path.write_text("<session>test</session>", encoding="utf-8")


def _fake_preprocess_success(prefix: str):
    """Return a subprocess side_effect that fakes successful preprocessing."""

    def fake_preprocess(*args, **kwargs):
        cmd = args[0] if args else kwargs.get("args", [])
        for i, arg in enumerate(cmd):
            if arg == "--output-dir" and i + 1 < len(cmd):
                _make_xml_file(cmd[i + 1], prefix)
                break

        class FakeResult:
            returncode = 0
            stdout = ""
            stderr = ""

        return FakeResult()

    return fake_preprocess


class TestPushSessionPreprocessingFailed:
    """Tests for push-session when preprocessing fails."""

    def test_preprocessing_fails_returns_not_uploaded(self, tmp_path: Path) -> None:
        """When preprocessing returns non-zero exit code, report gracefully."""
        session_file = _write_session_file(tmp_path)
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        fake_git = FakeGit(
            current_branches={repo_root: "plan/my-feature"},
            local_branches={repo_root: []},
        )
        runner = CliRunner()

        with patch("erk.cli.commands.exec.scripts.push_session.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stdout = ""
            mock_run.return_value.stderr = "preprocessing error"

            result = runner.invoke(
                push_session,
                [
                    "--session-file",
                    str(session_file),
                    "--session-id",
                    "test-session-abc",
                    "--stage",
                    "planning",
                    "--source",
                    "local",
                    "--plan-id",
                    "42",
                ],
                obj=ErkContext.for_test(git=fake_git, repo_root=repo_root, cwd=repo_root),
            )

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["uploaded"] is False
        assert output["reason"] == "preprocessing_failed"


class TestPushSessionNewBranch:
    """Tests for push-session when the async-learn branch doesn't exist yet."""

    def test_creates_branch_and_commits_xml(self, tmp_path: Path) -> None:
        """Session branch created from origin/master with XML files and manifest."""
        session_file = _write_session_file(tmp_path)
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        fake_git = FakeGit(
            current_branches={repo_root: "plan/my-feature"},
            local_branches={repo_root: []},
        )
        runner = CliRunner()

        # Mock subprocess.run for preprocess-session only (git show now uses gateway)
        with patch(
            "erk.cli.commands.exec.scripts.push_session.subprocess.run",
            side_effect=_fake_preprocess_success("planning-test-session-abc"),
        ):
            result = runner.invoke(
                push_session,
                [
                    "--session-file",
                    str(session_file),
                    "--session-id",
                    "test-session-abc",
                    "--stage",
                    "planning",
                    "--source",
                    "local",
                    "--plan-id",
                    "42",
                ],
                obj=ErkContext.for_test(git=fake_git, repo_root=repo_root, cwd=repo_root),
            )

        assert result.exit_code == 0, f"Failed: {result.output}"
        output = json.loads(result.output)
        assert output["uploaded"] is True
        assert output["session_branch"] == "async-learn/42"
        assert output["session_id"] == "test-session-abc"
        assert output["plan_id"] == 42
        assert output["stage"] == "planning"
        assert len(output["files"]) == 1
        assert "planning-test-session-abc.xml" in output["files"]

        # Verify branch was created from origin/master (not from existing remote)
        assert any(b == "async-learn/42" for _, b, _, _ in fake_git.created_branches)
        # Verify the branch was created from origin/master
        assert any(
            b == "async-learn/42" and sp == "origin/master"
            for _, b, sp, _ in fake_git.created_branches
        )

        # Verify files committed via plumbing
        assert len(fake_git.branch_commits) == 1
        bc = fake_git.branch_commits[0]
        assert bc.branch == "async-learn/42"
        assert ".erk/sessions/planning-test-session-abc.xml" in bc.files
        assert ".erk/sessions/manifest.json" in bc.files

        # Verify manifest content
        manifest = json.loads(bc.files[".erk/sessions/manifest.json"])
        assert manifest["version"] == 1
        assert manifest["plan_id"] == 42
        assert len(manifest["sessions"]) == 1
        assert manifest["sessions"][0]["session_id"] == "test-session-abc"
        assert manifest["sessions"][0]["stage"] == "planning"
        assert manifest["sessions"][0]["source"] == "local"

        # Verify force push
        assert any(pb.branch == "async-learn/42" and pb.force for pb in fake_git.pushed_branches)


class TestPushSessionAccumulation:
    """Tests for push-session when accumulating on existing branch."""

    def test_accumulates_on_existing_branch(self, tmp_path: Path) -> None:
        """When remote branch exists, fetch it and accumulate sessions."""
        session_file = _write_session_file(tmp_path)
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        existing_manifest = json.dumps(
            {
                "version": 1,
                "plan_id": 42,
                "sessions": [
                    {
                        "session_id": "planning-session-xyz",
                        "stage": "planning",
                        "source": "local",
                        "uploaded_at": "2026-02-28T12:00:00+00:00",
                        "files": ["planning-planning-session-xyz.xml"],
                    }
                ],
            }
        )

        fake_git = FakeGit(
            current_branches={repo_root: "plan/my-feature"},
            local_branches={repo_root: []},
            remote_branches={repo_root: ["origin/async-learn/42"]},
            ref_file_contents={
                (
                    "origin/async-learn/42",
                    ".erk/sessions/manifest.json",
                ): existing_manifest.encode("utf-8"),
            },
        )
        runner = CliRunner()

        with patch(
            "erk.cli.commands.exec.scripts.push_session.subprocess.run",
            side_effect=_fake_preprocess_success("impl-test-impl-session"),
        ):
            result = runner.invoke(
                push_session,
                [
                    "--session-file",
                    str(session_file),
                    "--session-id",
                    "test-impl-session",
                    "--stage",
                    "impl",
                    "--source",
                    "remote",
                    "--plan-id",
                    "42",
                ],
                obj=ErkContext.for_test(git=fake_git, repo_root=repo_root, cwd=repo_root),
            )

        assert result.exit_code == 0, f"Failed: {result.output}"
        output = json.loads(result.output)
        assert output["uploaded"] is True
        assert output["stage"] == "impl"

        # Verify branch was fetched from remote (indicated by creation from origin/async-learn/42)
        assert any(
            b == "async-learn/42" and sp == "origin/async-learn/42"
            for _, b, sp, _ in fake_git.created_branches
        )

        # Verify manifest has both sessions (accumulated)
        bc = fake_git.branch_commits[0]
        manifest = json.loads(bc.files[".erk/sessions/manifest.json"])
        assert len(manifest["sessions"]) == 2
        stages = [s["stage"] for s in manifest["sessions"]]
        assert "planning" in stages
        assert "impl" in stages


class TestPushSessionIdempotency:
    """Tests for push-session idempotency (re-uploading same session)."""

    def test_replaces_existing_session_entry(self, tmp_path: Path) -> None:
        """Re-uploading same session_id replaces the old manifest entry."""
        session_file = _write_session_file(tmp_path)
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        existing_manifest = json.dumps(
            {
                "version": 1,
                "plan_id": 42,
                "sessions": [
                    {
                        "session_id": "same-session",
                        "stage": "impl",
                        "source": "local",
                        "uploaded_at": "2026-02-28T12:00:00+00:00",
                        "files": ["impl-same-session.xml"],
                    }
                ],
            }
        )

        fake_git = FakeGit(
            current_branches={repo_root: "plan/my-feature"},
            local_branches={repo_root: []},
            remote_branches={repo_root: ["origin/async-learn/42"]},
            ref_file_contents={
                (
                    "origin/async-learn/42",
                    ".erk/sessions/manifest.json",
                ): existing_manifest.encode("utf-8"),
            },
        )
        runner = CliRunner()

        with patch(
            "erk.cli.commands.exec.scripts.push_session.subprocess.run",
            side_effect=_fake_preprocess_success("impl-same-session"),
        ):
            result = runner.invoke(
                push_session,
                [
                    "--session-file",
                    str(session_file),
                    "--session-id",
                    "same-session",
                    "--stage",
                    "impl",
                    "--source",
                    "remote",
                    "--plan-id",
                    "42",
                ],
                obj=ErkContext.for_test(git=fake_git, repo_root=repo_root, cwd=repo_root),
            )

        assert result.exit_code == 0, f"Failed: {result.output}"
        output = json.loads(result.output)
        assert output["uploaded"] is True

        # Manifest should have exactly 1 session (replaced, not duplicated)
        bc = fake_git.branch_commits[0]
        manifest = json.loads(bc.files[".erk/sessions/manifest.json"])
        assert len(manifest["sessions"]) == 1
        assert manifest["sessions"][0]["session_id"] == "same-session"
