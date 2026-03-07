"""Tests for erk exec tripwire-scan."""

import json
import subprocess
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.tripwire_scan import (
    AddedLine,
    TripwireEntry,
    _collect_tier2,
    _match_categories,
    _parse_tripwire_file,
    _parse_unified_diff,
    _scan_tier1,
    tripwire_scan,
)
from erk_shared.context.context import ErkContext

# --- Parser tests ---


class TestParseTripwireFile:
    """Test parsing of tripwire markdown files."""

    def test_parses_tier1_entry(self, tmp_path: Path) -> None:
        """Tier 1 entries with [pattern: `regex`] are parsed correctly."""
        content = (
            "# Test Tripwires\n\n"
            "**using bare subprocess.run** [pattern: `subprocess\\.run\\(`] "
            "\u2192 Read [Subprocess Wrappers](subprocess-wrappers.md) first. "
            "Use wrapper functions instead.\n"
        )
        tripwire_file = tmp_path / "tripwires.md"
        tripwire_file.write_text(content, encoding="utf-8")

        entries = _parse_tripwire_file(tripwire_file, "architecture")

        assert len(entries) == 1
        entry = entries[0]
        assert entry.action == "using bare subprocess.run"
        assert entry.pattern == "subprocess\\.run\\("
        assert entry.doc_path == "subprocess-wrappers.md"
        assert entry.summary == "Use wrapper functions instead."
        assert entry.category == "architecture"

    def test_parses_tier2_entry(self, tmp_path: Path) -> None:
        """Tier 2 entries without pattern are parsed correctly."""
        content = (
            "# Test Tripwires\n\n"
            "**adding a new method to Git ABC** "
            "\u2192 Read [Gateway ABC](gateway-abc.md) first. "
            "Must implement in 5 places.\n"
        )
        tripwire_file = tmp_path / "tripwires.md"
        tripwire_file.write_text(content, encoding="utf-8")

        entries = _parse_tripwire_file(tripwire_file, "architecture")

        assert len(entries) == 1
        entry = entries[0]
        assert entry.action == "adding a new method to Git ABC"
        assert entry.pattern is None
        assert entry.doc_path == "gateway-abc.md"
        assert entry.summary == "Must implement in 5 places."

    def test_parses_mixed_entries(self, tmp_path: Path) -> None:
        """File with both Tier 1 and Tier 2 entries."""
        content = (
            "# Tripwires\n\n"
            "**tier1 action** [pattern: `foo\\.bar`] "
            "\u2192 Read [Doc1](doc1.md) first. Summary1\n\n"
            "**tier2 action** "
            "\u2192 Read [Doc2](doc2.md) first. Summary2\n"
        )
        tripwire_file = tmp_path / "tripwires.md"
        tripwire_file.write_text(content, encoding="utf-8")

        entries = _parse_tripwire_file(tripwire_file, "testing")

        assert len(entries) == 2
        assert entries[0].pattern == "foo\\.bar"
        assert entries[1].pattern is None

    def test_skips_non_entry_lines(self, tmp_path: Path) -> None:
        """Lines that don't match the entry pattern are skipped."""
        content = (
            "# Architecture Tripwires\n\n"
            "Rules triggered by matching actions in code.\n\n"
            "Some random text here.\n\n"
            "**valid entry** \u2192 Read [Doc](doc.md) first. Summary\n"
        )
        tripwire_file = tmp_path / "tripwires.md"
        tripwire_file.write_text(content, encoding="utf-8")

        entries = _parse_tripwire_file(tripwire_file, "architecture")

        assert len(entries) == 1

    def test_nonexistent_file_returns_empty(self, tmp_path: Path) -> None:
        """Non-existent file returns empty list."""
        entries = _parse_tripwire_file(tmp_path / "nonexistent.md", "testing")
        assert entries == []


# --- Category matching tests ---


class TestMatchCategories:
    """Test file-path-to-category mapping."""

    def test_architecture_paths(self) -> None:
        files = ["src/erk/gateway/git/real.py"]
        assert "architecture" in _match_categories(files)

    def test_shared_package_paths(self) -> None:
        files = ["packages/erk-shared/src/erk_shared/context/context.py"]
        assert "architecture" in _match_categories(files)

    def test_cli_paths(self) -> None:
        files = ["src/erk/cli/commands/exec/scripts/new_script.py"]
        assert "cli" in _match_categories(files)

    def test_testing_paths(self) -> None:
        files = ["tests/unit/test_something.py"]
        assert "testing" in _match_categories(files)

    def test_ci_paths(self) -> None:
        files = [".github/workflows/ci.yml"]
        assert "ci" in _match_categories(files)

    def test_tui_paths(self) -> None:
        files = ["src/erk/tui/app.py"]
        assert "tui" in _match_categories(files)

    def test_planning_paths(self) -> None:
        files = [".impl/plan.md"]
        assert "planning" in _match_categories(files)

    def test_hooks_paths(self) -> None:
        files = [".claude/hooks/pre-tool-use.py"]
        assert "hooks" in _match_categories(files)

    def test_commands_paths(self) -> None:
        files = [".claude/commands/plan-save.md"]
        assert "commands" in _match_categories(files)

    def test_desktop_dash_paths(self) -> None:
        files = ["desktop-dash/src/main.ts"]
        assert "desktop-dash" in _match_categories(files)

    def test_multiple_categories(self) -> None:
        files = ["src/erk/cli/something.py", "tests/test_something.py"]
        categories = _match_categories(files)
        assert "cli" in categories
        assert "testing" in categories

    def test_no_matching_category(self) -> None:
        files = ["README.md", "pyproject.toml"]
        assert _match_categories(files) == []

    def test_sorted_output(self) -> None:
        files = ["tests/test_x.py", "src/erk/cli/x.py", ".github/ci.yml"]
        categories = _match_categories(files)
        assert categories == sorted(categories)


# --- Tier 1 scanning tests ---


class TestScanTier1:
    """Test mechanical regex matching against diff lines."""

    def test_match_found(self) -> None:
        """Pattern matching a diff line produces a hit."""
        entries = [
            TripwireEntry(
                action="using subprocess.run",
                pattern=r"subprocess\.run\(",
                doc_path="doc.md",
                summary="Use wrappers",
                category="architecture",
            ),
        ]
        added_lines = [
            AddedLine(file="src/foo.py", line=10, text="    result = subprocess.run(['git'])"),
        ]

        matches, clean = _scan_tier1(entries, added_lines)

        assert len(matches) == 1
        assert len(clean) == 0
        assert matches[0]["action"] == "using subprocess.run"
        assert len(matches[0]["matches"]) == 1
        assert matches[0]["matches"][0]["file"] == "src/foo.py"
        assert matches[0]["matches"][0]["line"] == 10

    def test_no_match(self) -> None:
        """Pattern not matching any diff line goes to clean."""
        entries = [
            TripwireEntry(
                action="using subprocess.run",
                pattern=r"subprocess\.run\(",
                doc_path="doc.md",
                summary="Use wrappers",
                category="architecture",
            ),
        ]
        added_lines = [
            AddedLine(file="src/foo.py", line=10, text="    print('hello')"),
        ]

        matches, clean = _scan_tier1(entries, added_lines)

        assert len(matches) == 0
        assert len(clean) == 1

    def test_multiple_matches_same_file(self) -> None:
        """Multiple lines in same file matching same pattern."""
        entries = [
            TripwireEntry(
                action="using os.chdir",
                pattern=r"os\.chdir\(",
                doc_path="doc.md",
                summary="Regenerate context",
                category="architecture",
            ),
        ]
        added_lines = [
            AddedLine(file="src/foo.py", line=10, text="    os.chdir('/tmp')"),
            AddedLine(file="src/foo.py", line=20, text="    os.chdir(new_dir)"),
        ]

        matches, clean = _scan_tier1(entries, added_lines)

        assert len(matches) == 1
        assert len(matches[0]["matches"]) == 2

    def test_tier2_entries_excluded(self) -> None:
        """Tier 2 entries (no pattern) are not scanned."""
        entries = [
            TripwireEntry(
                action="tier2 only",
                pattern=None,
                doc_path="doc.md",
                summary="Summary",
                category="testing",
            ),
        ]
        added_lines = [
            AddedLine(file="src/foo.py", line=10, text="anything"),
        ]

        matches, clean = _scan_tier1(entries, added_lines)

        assert len(matches) == 0
        assert len(clean) == 0

    def test_invalid_regex_skipped(self) -> None:
        """Invalid regex pattern is skipped without error."""
        entries = [
            TripwireEntry(
                action="bad pattern",
                pattern="[invalid",
                doc_path="doc.md",
                summary="Summary",
                category="testing",
            ),
        ]
        added_lines = [
            AddedLine(file="src/foo.py", line=10, text="anything"),
        ]

        matches, clean = _scan_tier1(entries, added_lines)

        assert len(matches) == 0
        assert len(clean) == 0

    def test_match_text_stripped(self) -> None:
        """Matched text has leading/trailing whitespace stripped."""
        entries = [
            TripwireEntry(
                action="test",
                pattern=r"os\.chdir",
                doc_path="doc.md",
                summary="Summary",
                category="arch",
            ),
        ]
        added_lines = [
            AddedLine(file="a.py", line=1, text="    os.chdir(x)   "),
        ]

        matches, _ = _scan_tier1(entries, added_lines)

        assert matches[0]["matches"][0]["text"] == "os.chdir(x)"


# --- Tier 2 collection tests ---


class TestCollectTier2:
    """Test Tier 2 entry collection."""

    def test_collects_tier2_only(self) -> None:
        """Only entries without patterns are collected."""
        entries = [
            TripwireEntry(
                action="tier1",
                pattern=r"regex",
                doc_path="doc1.md",
                summary="S1",
                category="arch",
            ),
            TripwireEntry(
                action="tier2",
                pattern=None,
                doc_path="doc2.md",
                summary="S2",
                category="testing",
            ),
        ]

        tier2 = _collect_tier2(entries)

        assert len(tier2) == 1
        assert tier2[0]["action"] == "tier2"
        assert tier2[0]["category"] == "testing"
        assert tier2[0]["doc_path"] == "doc2.md"
        assert tier2[0]["summary"] == "S2"


# --- Unified diff parsing tests ---


class TestParseUnifiedDiff:
    """Test unified diff parsing for added lines."""

    def test_simple_addition(self) -> None:
        """Single added line is extracted correctly."""
        diff = (
            "diff --git a/foo.py b/foo.py\n"
            "--- a/foo.py\n"
            "+++ b/foo.py\n"
            "@@ -1,3 +1,4 @@\n"
            " existing line\n"
            "+new line\n"
            " another line\n"
        )

        lines = _parse_unified_diff(diff)

        assert len(lines) == 1
        assert lines[0].file == "foo.py"
        assert lines[0].line == 2
        assert lines[0].text == "new line"

    def test_multiple_files(self) -> None:
        """Lines from multiple files are tracked separately."""
        diff = (
            "diff --git a/a.py b/a.py\n"
            "--- a/a.py\n"
            "+++ b/a.py\n"
            "@@ -1,2 +1,3 @@\n"
            " old\n"
            "+added_a\n"
            "diff --git a/b.py b/b.py\n"
            "--- a/b.py\n"
            "+++ b/b.py\n"
            "@@ -5,2 +5,3 @@\n"
            " old\n"
            "+added_b\n"
        )

        lines = _parse_unified_diff(diff)

        assert len(lines) == 2
        assert lines[0].file == "a.py"
        assert lines[0].text == "added_a"
        assert lines[1].file == "b.py"
        assert lines[1].text == "added_b"

    def test_hunk_line_numbers(self) -> None:
        """Line numbers from @@ hunk headers are tracked correctly."""
        diff = (
            "diff --git a/foo.py b/foo.py\n"
            "--- a/foo.py\n"
            "+++ b/foo.py\n"
            "@@ -10,3 +15,4 @@\n"
            " context\n"
            "+added at line 16\n"
            " context\n"
        )

        lines = _parse_unified_diff(diff)

        assert len(lines) == 1
        assert lines[0].line == 16

    def test_removed_lines_ignored(self) -> None:
        """Lines starting with - (removed) are not extracted."""
        diff = (
            "diff --git a/foo.py b/foo.py\n"
            "--- a/foo.py\n"
            "+++ b/foo.py\n"
            "@@ -1,3 +1,3 @@\n"
            " keep\n"
            "-removed\n"
            "+added\n"
        )

        lines = _parse_unified_diff(diff)

        assert len(lines) == 1
        assert lines[0].text == "added"

    def test_empty_diff(self) -> None:
        """Empty diff produces no lines."""
        assert _parse_unified_diff("") == []

    def test_new_file(self) -> None:
        """New file (no --- line) is handled."""
        diff = (
            "diff --git a/new.py b/new.py\n"
            "--- /dev/null\n"
            "+++ b/new.py\n"
            "@@ -0,0 +1,2 @@\n"
            "+line one\n"
            "+line two\n"
        )

        lines = _parse_unified_diff(diff)

        assert len(lines) == 2
        assert lines[0].file == "new.py"
        assert lines[0].line == 1
        assert lines[1].line == 2


# --- CLI integration tests ---


def _create_git_repo(tmp_path: Path) -> Path:
    """Create a minimal git repo with a main branch and initial commit."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Initial commit on main
    (repo / "README.md").write_text("initial", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    return repo


def _create_feature_branch(repo: Path, *, branch_name: str) -> None:
    """Create and switch to a feature branch with a new commit."""
    subprocess.run(
        ["git", "checkout", "-b", branch_name],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def _add_commit(repo: Path, *, filename: str, content: str, message: str) -> None:
    """Add a file and commit it."""
    filepath = repo / filename
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", filename], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", message], cwd=repo, check=True, capture_output=True)


class TestTripwireScanCLI:
    """CLI integration tests using real git repos."""

    def test_scan_with_no_changes(self, tmp_path: Path) -> None:
        """Scan on a branch with no changes from base returns empty results."""
        repo = _create_git_repo(tmp_path)
        _create_feature_branch(repo, branch_name="feature")

        runner = CliRunner()
        ctx = ErkContext.for_test(repo_root=repo)
        result = runner.invoke(tripwire_scan, ["--base", "main"], obj=ctx)

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["success"] is True
        assert output["tier1_matches"] == []
        assert output["tier2_entries"] == []
        assert output["changed_files"] == []

    def test_scan_with_matching_tier1(self, tmp_path: Path) -> None:
        """Scan detects Tier 1 pattern matches in diff."""
        repo = _create_git_repo(tmp_path)

        # Create tripwire file on main
        docs_dir = repo / "docs" / "learned" / "architecture"
        docs_dir.mkdir(parents=True)
        tripwire_content = (
            "# Architecture Tripwires\n\n"
            "**using bare subprocess.run** [pattern: `subprocess\\.run\\(`] "
            "\u2192 Read [Subprocess Wrappers](subprocess-wrappers.md) first. "
            "Use wrappers.\n"
        )
        (docs_dir / "tripwires.md").write_text(tripwire_content, encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add tripwires"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        # Create feature branch with a matching change
        _create_feature_branch(repo, branch_name="feature")
        _add_commit(
            repo,
            filename="src/erk/gateway/git/real.py",
            content="import subprocess\nresult = subprocess.run(['git', 'status'])\n",
            message="Add code with subprocess.run",
        )

        runner = CliRunner()
        ctx = ErkContext.for_test(repo_root=repo)
        result = runner.invoke(tripwire_scan, ["--base", "main"], obj=ctx)

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["success"] is True
        assert len(output["tier1_matches"]) == 1
        assert output["tier1_matches"][0]["pattern"] == "subprocess\\.run\\("
        assert len(output["tier1_matches"][0]["matches"]) >= 1
        assert "architecture" in output["categories_loaded"]

    def test_scan_with_tier2_entries(self, tmp_path: Path) -> None:
        """Scan collects Tier 2 entries for matched categories."""
        repo = _create_git_repo(tmp_path)

        # Create tripwire file on main
        docs_dir = repo / "docs" / "learned" / "testing"
        docs_dir.mkdir(parents=True)
        tripwire_content = (
            "# Testing Tripwires\n\n"
            "**adding monkeypatch to a test** "
            "\u2192 Read [Monkeypatch Guide](monkeypatch.md) first. "
            "Use fakes instead.\n"
        )
        (docs_dir / "tripwires.md").write_text(tripwire_content, encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add tripwires"],
            cwd=repo,
            check=True,
            capture_output=True,
        )

        # Create feature branch with a test file change
        _create_feature_branch(repo, branch_name="feature")
        _add_commit(
            repo,
            filename="tests/test_something.py",
            content="def test_foo():\n    assert True\n",
            message="Add test",
        )

        runner = CliRunner()
        ctx = ErkContext.for_test(repo_root=repo)
        result = runner.invoke(tripwire_scan, ["--base", "main"], obj=ctx)

        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["success"] is True
        assert "testing" in output["categories_loaded"]
        assert len(output["tier2_entries"]) == 1
        assert output["tier2_entries"][0]["action"] == "adding monkeypatch to a test"

    def test_scan_with_invalid_base(self, tmp_path: Path) -> None:
        """Scan with invalid base ref fails gracefully."""
        repo = _create_git_repo(tmp_path)
        _create_feature_branch(repo, branch_name="feature")

        runner = CliRunner()
        ctx = ErkContext.for_test(repo_root=repo)
        result = runner.invoke(tripwire_scan, ["--base", "nonexistent-branch"], obj=ctx)

        assert result.exit_code == 1
        output = json.loads(result.output)
        assert output["success"] is False
        assert output["error"] == "git_error"

    def test_scan_json_structure(self, tmp_path: Path) -> None:
        """Verify the complete JSON output structure."""
        repo = _create_git_repo(tmp_path)
        _create_feature_branch(repo, branch_name="feature")
        _add_commit(
            repo,
            filename="src/erk/cli/new.py",
            content="print('hello')\n",
            message="Add CLI file",
        )

        runner = CliRunner()
        ctx = ErkContext.for_test(repo_root=repo)
        result = runner.invoke(tripwire_scan, ["--base", "main"], obj=ctx)

        assert result.exit_code == 0
        output = json.loads(result.output)

        # Verify all required keys present
        assert "success" in output
        assert "tier1_matches" in output
        assert "tier1_clean" in output
        assert "tier2_entries" in output
        assert "categories_loaded" in output
        assert "changed_files" in output
        assert isinstance(output["tier1_matches"], list)
        assert isinstance(output["tier1_clean"], list)
        assert isinstance(output["tier2_entries"], list)
        assert isinstance(output["categories_loaded"], list)
        assert isinstance(output["changed_files"], list)
