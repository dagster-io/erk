"""Tests for diff extraction operation.

Tests the execute_diff_extraction function that computes local git diff
and writes it to a scratch file for AI analysis.
"""

from pathlib import Path

from erk_shared.context.testing import context_for_test
from erk_shared.gateway.graphite.fake import FakeGraphite
from erk_shared.gateway.gt.events import CompletionEvent, ProgressEvent
from erk_shared.gateway.pr.diff_extraction import (
    execute_diff_extraction,
    filter_diff_excluded_files,
)
from erk_shared.git.fake import FakeGit
from erk_shared.github.fake import FakeGitHub

# --- Tests for filter_diff_excluded_files ---


def test_filter_diff_excluded_files_removes_lock_files() -> None:
    """Test that lock files like uv.lock are filtered out."""
    diff = """\
diff --git a/pyproject.toml b/pyproject.toml
index abc123..def456 100644
--- a/pyproject.toml
+++ b/pyproject.toml
@@ -1,2 +1,3 @@
+dependencies = ["click"]
diff --git a/uv.lock b/uv.lock
index 111111..222222 100644
--- a/uv.lock
+++ b/uv.lock
@@ -1,100 +1,200 @@
+lots of lock content
diff --git a/src/main.py b/src/main.py
index aaa111..bbb222 100644
--- a/src/main.py
+++ b/src/main.py
@@ -1 +1,2 @@
+import click"""

    result = filter_diff_excluded_files(diff)

    # uv.lock should be removed
    assert "uv.lock" not in result
    # Other files should remain
    assert "pyproject.toml" in result
    assert "src/main.py" in result
    assert "+dependencies" in result
    assert "+import click" in result


def test_filter_diff_excluded_files_preserves_other_files() -> None:
    """Test that non-lock files pass through unchanged."""
    diff = """\
diff --git a/README.md b/README.md
index abc123..def456 100644
--- a/README.md
+++ b/README.md
@@ -1 +1,2 @@
+New content
diff --git a/src/app.py b/src/app.py
index 111111..222222 100644
--- a/src/app.py
+++ b/src/app.py
@@ -1 +1,2 @@
+import os"""

    result = filter_diff_excluded_files(diff)

    # Both files should remain
    assert "README.md" in result
    assert "src/app.py" in result
    assert "+New content" in result
    assert "+import os" in result


def test_filter_diff_excluded_files_handles_nested_paths() -> None:
    """Test that lock files in subdirectories are also filtered."""
    diff = """\
diff --git a/packages/frontend/package-lock.json b/packages/frontend/package-lock.json
index abc123..def456 100644
--- a/packages/frontend/package-lock.json
+++ b/packages/frontend/package-lock.json
@@ -1,100 +1,200 @@
+huge lock content
diff --git a/packages/frontend/src/index.ts b/packages/frontend/src/index.ts
index 111111..222222 100644
--- a/packages/frontend/src/index.ts
+++ b/packages/frontend/src/index.ts
@@ -1 +1,2 @@
+console.log("hello")"""

    result = filter_diff_excluded_files(diff)

    # package-lock.json should be removed even in nested path
    assert "package-lock.json" not in result
    # Other files should remain
    assert "index.ts" in result
    assert '+console.log("hello")' in result


def test_filter_diff_excluded_files_handles_all_lock_types() -> None:
    """Test that all supported lock file types are filtered."""
    diff = """\
diff --git a/uv.lock b/uv.lock
+content
diff --git a/package-lock.json b/package-lock.json
+content
diff --git a/yarn.lock b/yarn.lock
+content
diff --git a/pnpm-lock.yaml b/pnpm-lock.yaml
+content
diff --git a/Cargo.lock b/Cargo.lock
+content
diff --git a/poetry.lock b/poetry.lock
+content
diff --git a/Pipfile.lock b/Pipfile.lock
+content
diff --git a/composer.lock b/composer.lock
+content
diff --git a/Gemfile.lock b/Gemfile.lock
+content
diff --git a/real-code.py b/real-code.py
+actual changes"""

    result = filter_diff_excluded_files(diff)

    # All lock files should be removed
    assert "uv.lock" not in result
    assert "package-lock.json" not in result
    assert "yarn.lock" not in result
    assert "pnpm-lock.yaml" not in result
    assert "Cargo.lock" not in result
    assert "poetry.lock" not in result
    assert "Pipfile.lock" not in result
    assert "composer.lock" not in result
    assert "Gemfile.lock" not in result

    # Real code should remain
    assert "real-code.py" in result
    assert "+actual changes" in result


def test_filter_diff_excluded_files_handles_empty_diff() -> None:
    """Test that empty diff returns empty string."""
    assert filter_diff_excluded_files("") == ""


def test_filter_diff_excluded_files_handles_diff_with_only_lock_files() -> None:
    """Test that diff with only lock files returns empty string."""
    diff = """\
diff --git a/uv.lock b/uv.lock
index abc123..def456 100644
--- a/uv.lock
+++ b/uv.lock
@@ -1,100 +1,200 @@
+lots of lock content"""

    result = filter_diff_excluded_files(diff)
    assert result == ""


# --- Tests for execute_diff_extraction ---


def test_execute_diff_extraction_success(tmp_path: Path) -> None:
    """Test successful diff extraction using local git diff."""
    # Create repo root structure
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    scratch_dir = repo_root / ".tmp" / "test-session"
    scratch_dir.mkdir(parents=True)

    local_diff = "diff --git a/file.py b/file.py\n+new line"

    git = FakeGit(
        git_common_dirs={tmp_path: repo_root},
        repository_roots={tmp_path: str(repo_root)},
        trunk_branches={repo_root: "main"},
        diff_to_branch={(tmp_path, "main"): local_diff},
    )

    github = FakeGitHub(
        pr_bases={123: "main"},
    )

    ctx = context_for_test(git=git, github=github, graphite=FakeGraphite(), cwd=tmp_path)

    # Collect events
    events = list(execute_diff_extraction(ctx, tmp_path, pr_number=123, session_id="test-session"))

    # Should have progress events and completion
    progress_events = [e for e in events if isinstance(e, ProgressEvent)]
    completion_events = [e for e in events if isinstance(e, CompletionEvent)]

    assert len(progress_events) >= 2  # "Getting diff..." and "Diff written to..."
    assert len(completion_events) == 1

    # Check result is a Path
    result = completion_events[0].result
    assert isinstance(result, Path)
    assert result.exists()

    # Verify diff content was written
    content = result.read_text(encoding="utf-8")
    assert "diff --git" in content
    assert "+new line" in content


def test_execute_diff_extraction_truncates_large_diff(tmp_path: Path) -> None:
    """Test that large diffs are truncated."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    scratch_dir = repo_root / ".tmp" / "test-session"
    scratch_dir.mkdir(parents=True)

    # Create a very large diff (over 1M chars - the MAX_DIFF_CHARS threshold)
    large_diff = "diff --git a/file.py b/file.py\n" + "+" + "a" * 1_100_000

    git = FakeGit(
        git_common_dirs={tmp_path: repo_root},
        repository_roots={tmp_path: str(repo_root)},
        trunk_branches={repo_root: "main"},
        diff_to_branch={(tmp_path, "main"): large_diff},
    )

    github = FakeGitHub(
        pr_bases={123: "main"},
    )

    ctx = context_for_test(git=git, github=github, graphite=FakeGraphite(), cwd=tmp_path)

    events = list(execute_diff_extraction(ctx, tmp_path, pr_number=123, session_id="test-session"))

    # Should have a warning about truncation
    progress_events = [e for e in events if isinstance(e, ProgressEvent)]
    warning_events = [e for e in progress_events if e.style == "warning"]
    assert len(warning_events) == 1
    assert "truncated" in warning_events[0].message.lower()

    # Result should still be a valid path
    completion_events = [e for e in events if isinstance(e, CompletionEvent)]
    result = completion_events[0].result
    assert isinstance(result, Path)
    assert result.exists()


def test_execute_diff_extraction_progress_messages(tmp_path: Path) -> None:
    """Test that appropriate progress messages are emitted."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    scratch_dir = repo_root / ".tmp" / "test-session"
    scratch_dir.mkdir(parents=True)

    local_diff = "diff content\nline 2\nline 3"

    git = FakeGit(
        git_common_dirs={tmp_path: repo_root},
        repository_roots={tmp_path: str(repo_root)},
        trunk_branches={repo_root: "main"},
        diff_to_branch={(tmp_path, "main"): local_diff},
    )

    github = FakeGitHub(
        pr_bases={123: "main"},
    )

    ctx = context_for_test(git=git, github=github, graphite=FakeGraphite(), cwd=tmp_path)

    events = list(execute_diff_extraction(ctx, tmp_path, pr_number=123, session_id="test-session"))

    progress_events = [e for e in events if isinstance(e, ProgressEvent)]
    messages = [e.message for e in progress_events]

    # Should report getting diff
    assert any("Getting diff" in m for m in messages)
    # Should report diff retrieved with line count
    assert any("3 lines" in m for m in messages)
    # Should report diff written
    assert any("Diff written" in m for m in messages)


def test_execute_diff_extraction_uses_pr_base_branch(tmp_path: Path) -> None:
    """Test that diff uses PR's base branch, not trunk."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    scratch_dir = repo_root / ".tmp" / "test-session"
    scratch_dir.mkdir(parents=True)

    feature_branch_diff = "diff --git a/f.py b/f.py\n+feature branch diff"
    trunk_diff = "diff --git a/f.py b/f.py\n+trunk diff"

    git = FakeGit(
        git_common_dirs={tmp_path: repo_root},
        repository_roots={tmp_path: str(repo_root)},
        trunk_branches={repo_root: "main"},
        diff_to_branch={
            (tmp_path, "feature-base"): feature_branch_diff,
            (tmp_path, "main"): trunk_diff,
        },
    )

    github = FakeGitHub(
        pr_bases={123: "feature-base"},
    )

    ctx = context_for_test(git=git, github=github, graphite=FakeGraphite(), cwd=tmp_path)

    events = list(execute_diff_extraction(ctx, tmp_path, pr_number=123, session_id="test-session"))

    completion_events = [e for e in events if isinstance(e, CompletionEvent)]
    result = completion_events[0].result
    assert isinstance(result, Path)

    content = result.read_text(encoding="utf-8")
    # Should use the PR's base branch (feature-base), not trunk
    assert "feature branch diff" in content
    assert "trunk diff" not in content


def test_execute_diff_extraction_uses_trunk_when_no_pr_base(tmp_path: Path) -> None:
    """Test that diff uses trunk branch when PR base is not available."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    scratch_dir = repo_root / ".tmp" / "test-session"
    scratch_dir.mkdir(parents=True)

    trunk_diff = "diff --git a/f.py b/f.py\n+trunk diff content"

    git = FakeGit(
        git_common_dirs={tmp_path: repo_root},
        repository_roots={tmp_path: str(repo_root)},
        trunk_branches={repo_root: "main"},
        diff_to_branch={(tmp_path, "main"): trunk_diff},
    )

    github = FakeGitHub(
        # No pr_bases configured - get_pr_base_branch returns None
    )

    ctx = context_for_test(git=git, github=github, graphite=FakeGraphite(), cwd=tmp_path)

    events = list(execute_diff_extraction(ctx, tmp_path, pr_number=123, session_id="test-session"))

    completion_events = [e for e in events if isinstance(e, CompletionEvent)]
    result = completion_events[0].result
    assert isinstance(result, Path)

    content = result.read_text(encoding="utf-8")
    # Should fall back to trunk branch
    assert "trunk diff content" in content
