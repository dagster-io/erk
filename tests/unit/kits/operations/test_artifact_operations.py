"""Tests for artifact operations, especially source directory protection."""

from pathlib import Path

from erk.kits.operations.artifact_operations import (
    PROTECTED_SOURCE_DIRS,
    ProdOperations,
    _is_protected_source_path,
)


class TestIsProtectedSourcePath:
    """Tests for protected source path detection."""

    def test_claude_commands_protected(self) -> None:
        assert _is_protected_source_path(".claude/commands/erk/foo.md") is True

    def test_claude_agents_protected(self) -> None:
        assert _is_protected_source_path(".claude/agents/erk/bar.md") is True

    def test_claude_skills_protected(self) -> None:
        assert _is_protected_source_path(".claude/skills/erk/skill.md") is True

    def test_claude_hooks_protected(self) -> None:
        assert _is_protected_source_path(".claude/hooks/erk/hook.md") is True

    def test_claude_dir_itself_protected(self) -> None:
        assert _is_protected_source_path(".claude") is True

    def test_erk_docs_protected(self) -> None:
        assert _is_protected_source_path(".erk/docs/kits/erk/baz.md") is True

    def test_erk_docs_agent_protected(self) -> None:
        assert _is_protected_source_path(".erk/docs/agent/guide.md") is True

    def test_erk_docs_dir_itself_protected(self) -> None:
        assert _is_protected_source_path(".erk/docs") is True

    def test_github_workflows_protected(self) -> None:
        assert _is_protected_source_path(".github/workflows/ci.yml") is True

    def test_github_workflows_dir_itself_protected(self) -> None:
        assert _is_protected_source_path(".github/workflows") is True

    def test_kit_package_not_protected(self) -> None:
        """Kit package output directories are NOT protected."""
        assert _is_protected_source_path("packages/erk-kits/data/foo.md") is False

    def test_erk_kits_registry_not_protected(self) -> None:
        """.erk/kits/ (registry) is NOT protected - only .erk/docs/."""
        assert _is_protected_source_path(".erk/kits/erk/registry-entry.md") is False

    def test_github_not_protected_except_workflows(self) -> None:
        """.github/ itself is not protected, only .github/workflows/."""
        assert _is_protected_source_path(".github/ISSUE_TEMPLATE.md") is False

    def test_regular_path_not_protected(self) -> None:
        assert _is_protected_source_path("src/erk/foo.py") is False

    def test_protected_dirs_constant_contains_expected(self) -> None:
        """Verify the constant contains the expected directories."""
        assert ".claude" in PROTECTED_SOURCE_DIRS
        assert ".erk/docs" in PROTECTED_SOURCE_DIRS
        assert ".github/workflows" in PROTECTED_SOURCE_DIRS


class TestRemoveArtifactsProtection:
    """Tests for remove_artifacts() source protection."""

    def test_skips_protected_claude_files(self, tmp_path: Path) -> None:
        """Protected .claude/ files should be skipped, not deleted."""
        # Create a protected file
        claude_dir = tmp_path / ".claude" / "commands" / "erk"
        claude_dir.mkdir(parents=True)
        protected_file = claude_dir / "command.md"
        protected_file.write_text("source content", encoding="utf-8")

        ops = ProdOperations()
        skipped = ops.remove_artifacts(
            [".claude/commands/erk/command.md"],
            tmp_path,
        )

        # File should still exist
        assert protected_file.exists()
        assert ".claude/commands/erk/command.md" in skipped

    def test_skips_protected_erk_docs_files(self, tmp_path: Path) -> None:
        """Protected .erk/docs/ files should be skipped."""
        docs_dir = tmp_path / ".erk" / "docs" / "kits" / "erk"
        docs_dir.mkdir(parents=True)
        protected_file = docs_dir / "guide.md"
        protected_file.write_text("documentation content", encoding="utf-8")

        ops = ProdOperations()
        skipped = ops.remove_artifacts(
            [".erk/docs/kits/erk/guide.md"],
            tmp_path,
        )

        assert protected_file.exists()
        assert ".erk/docs/kits/erk/guide.md" in skipped

    def test_skips_protected_github_workflows_files(self, tmp_path: Path) -> None:
        """Protected .github/workflows/ files should be skipped."""
        workflows_dir = tmp_path / ".github" / "workflows"
        workflows_dir.mkdir(parents=True)
        protected_file = workflows_dir / "ci.yml"
        protected_file.write_text("workflow content", encoding="utf-8")

        ops = ProdOperations()
        skipped = ops.remove_artifacts(
            [".github/workflows/ci.yml"],
            tmp_path,
        )

        assert protected_file.exists()
        assert ".github/workflows/ci.yml" in skipped

    def test_removes_unprotected_files(self, tmp_path: Path) -> None:
        """Unprotected files should be removed normally."""
        # Create an unprotected file
        pkg_dir = tmp_path / "packages" / "output"
        pkg_dir.mkdir(parents=True)
        unprotected_file = pkg_dir / "artifact.md"
        unprotected_file.write_text("build output", encoding="utf-8")

        ops = ProdOperations()
        skipped = ops.remove_artifacts(
            ["packages/output/artifact.md"],
            tmp_path,
        )

        # File should be removed
        assert not unprotected_file.exists()
        assert skipped == []

    def test_mixed_protected_and_unprotected(self, tmp_path: Path) -> None:
        """Mixed list: protected skipped, unprotected removed."""
        # Create protected file
        claude_dir = tmp_path / ".claude" / "commands"
        claude_dir.mkdir(parents=True)
        protected_file = claude_dir / "foo.md"
        protected_file.write_text("protected", encoding="utf-8")

        # Create unprotected file
        output_dir = tmp_path / "output"
        output_dir.mkdir(parents=True)
        unprotected_file = output_dir / "bar.md"
        unprotected_file.write_text("unprotected", encoding="utf-8")

        ops = ProdOperations()
        skipped = ops.remove_artifacts(
            [".claude/commands/foo.md", "output/bar.md"],
            tmp_path,
        )

        # Protected still exists, unprotected removed
        assert protected_file.exists()
        assert not unprotected_file.exists()
        assert ".claude/commands/foo.md" in skipped
        assert "output/bar.md" not in skipped

    def test_nonexistent_paths_skipped(self, tmp_path: Path) -> None:
        """Non-existent paths should be skipped."""
        ops = ProdOperations()
        skipped = ops.remove_artifacts(
            ["nonexistent/path.md"],
            tmp_path,
        )

        assert "nonexistent/path.md" in skipped

    def test_removes_unprotected_directory(self, tmp_path: Path) -> None:
        """Unprotected directories should be removed recursively."""
        # Create an unprotected directory with files
        pkg_dir = tmp_path / "packages" / "kit" / "data"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "file1.md").write_text("content1", encoding="utf-8")
        (pkg_dir / "file2.md").write_text("content2", encoding="utf-8")

        ops = ProdOperations()
        skipped = ops.remove_artifacts(
            ["packages/kit/data"],
            tmp_path,
        )

        assert not pkg_dir.exists()
        assert skipped == []
