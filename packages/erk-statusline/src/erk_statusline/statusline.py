#!/usr/bin/env python3
"""
Claude Code status line - robbyrussell theme style.

Matches the robbyrussell Oh My Zsh theme format:
➜  directory (git:branch) ✗

With added Claude-specific info on the right.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import NamedTuple

from erk_statusline.colored_tokens import Color, Token, TokenSeq, context_label

# Cache configuration
CACHE_DIR = Path("/tmp/erk-statusline-cache")
CACHE_TTL_SECONDS = 30


def _get_cache_path(owner: str, repo: str, branch: str) -> Path:
    """Get path to cache file for a specific branch.

    Uses hash of branch name to avoid filesystem issues with special characters.
    """
    branch_hash = hashlib.sha256(branch.encode("utf-8")).hexdigest()[:16]
    return CACHE_DIR / f"{owner}-{repo}-{branch_hash}.json"


def _get_cached_pr_info(owner: str, repo: str, branch: str) -> tuple[int, str] | None:
    """Get cached PR info if valid.

    Returns:
        Tuple of (pr_number, head_sha) if cache is valid, None otherwise.
    """
    cache_path = _get_cache_path(owner, repo, branch)
    if not cache_path.exists():
        return None

    cache_stat = cache_path.stat()
    cache_age = time.time() - cache_stat.st_mtime
    if cache_age > CACHE_TTL_SECONDS:
        return None

    try:
        content = cache_path.read_text(encoding="utf-8")
        data = json.loads(content)
        pr_number = data.get("pr_number")
        head_sha = data.get("head_sha")
        if isinstance(pr_number, int) and isinstance(head_sha, str):
            return (pr_number, head_sha)
    except (json.JSONDecodeError, OSError, KeyError):
        pass

    return None


def _set_cached_pr_info(owner: str, repo: str, branch: str, pr_number: int, head_sha: str) -> None:
    """Cache PR info for a branch."""
    cache_path = _get_cache_path(owner, repo, branch)

    if not CACHE_DIR.exists():
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    cache_data = {"pr_number": pr_number, "head_sha": head_sha}
    cache_path.write_text(json.dumps(cache_data), encoding="utf-8")


class RepoInfo(NamedTuple):
    """Repository and PR information for display."""

    owner: str  # GitHub owner (empty if unavailable)
    repo: str  # Repository name (empty if unavailable)
    pr_number: str  # PR number (empty if no PR)
    pr_url: str  # Graphite URL for PR (empty if no PR)
    pr_state: str  # "published", "draft", "merged", "closed" (empty if no PR)
    has_conflicts: bool  # True if mergeable == "CONFLICTING"


class GitHubData(NamedTuple):
    """Complete GitHub data from GraphQL query."""

    owner: str  # Repository owner
    repo: str  # Repository name
    pr_number: int  # PR number (0 if no PR)
    pr_state: str  # "OPEN", "MERGED", "CLOSED" (empty if no PR)
    is_draft: bool  # True if PR is draft
    mergeable: str  # "MERGEABLE", "CONFLICTING", "UNKNOWN" (empty if no PR)
    check_contexts: list[dict[str, str]]  # List of check contexts from statusCheckRollup


def run_git(cmd: list[str], cwd: str) -> str:
    """Run a git command and return output."""
    try:
        result = subprocess.run(
            ["git"] + cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=2,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        return ""


def get_git_root(cwd: str) -> str:
    """Get git repository root directory.

    Returns:
        Absolute path to git root, or empty string if not in git repo.
    """
    return run_git(["rev-parse", "--show-toplevel"], cwd)


def get_git_status(cwd: str) -> tuple[str, bool]:
    """Get git branch and dirty status.

    Returns:
        (branch_name, is_dirty)
    """
    branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd)
    if not branch:
        return "", False

    status = run_git(["status", "--porcelain"], cwd)
    is_dirty = bool(status)

    return branch, is_dirty


def get_worktree_info(cwd: str) -> tuple[bool, str]:
    """Detect if in a linked worktree and get worktree name.

    Returns:
        (is_linked_worktree, worktree_name)
        - is_linked_worktree: False for main worktree, True for linked worktrees
        - worktree_name: Directory basename of the worktree
    """
    # Get list of all worktrees
    output = run_git(["worktree", "list", "--porcelain"], cwd)
    if not output:
        return False, ""

    # Parse worktree list to find current worktree
    worktrees = []
    current_wt = {}

    for line in output.split("\n"):
        if line.startswith("worktree "):
            if current_wt:
                worktrees.append(current_wt)
            current_wt = {"path": line.split(" ", 1)[1]}
        elif line.startswith("branch "):
            current_wt["branch"] = line.split(" ", 1)[1]

    if current_wt:
        worktrees.append(current_wt)

    # Find which worktree we're in
    git_root = get_git_root(cwd)
    if not git_root:
        return False, ""

    for idx, wt in enumerate(worktrees):
        if wt["path"] == git_root:
            # First worktree is always the main worktree
            is_linked = idx > 0
            wt_name = Path(wt["path"]).name
            return is_linked, wt_name

    return False, ""


def has_plan_file(git_root: str) -> bool:
    """Check if .impl folder exists at git repository root.

    Args:
        git_root: Absolute path to git repository root

    Returns:
        True if .impl folder exists at repo root, False otherwise.
    """
    if not git_root:
        return False

    plan_path = Path(git_root) / ".impl"
    return plan_path.is_dir()


def get_issue_number(git_root: str) -> int | None:
    """Load issue number from .impl/issue.json file.

    Args:
        git_root: Absolute path to git repository root

    Returns:
        Issue number if file exists and is valid, None otherwise.
    """
    if not git_root:
        return None

    issue_file = Path(git_root) / ".impl" / "issue.json"
    if not issue_file.is_file():
        return None

    try:
        with open(issue_file, encoding="utf-8") as f:
            data = json.load(f)
            # Try "issue_number" first (preferred), then fall back to "number"
            issue_number = data.get("issue_number") or data.get("number")
            if isinstance(issue_number, int):
                return issue_number
    except (json.JSONDecodeError, OSError):
        pass

    return None


def get_plan_progress(git_root: str) -> tuple[int, int] | None:
    """Parse .impl/progress.md file to extract step progress.

    Args:
        git_root: Absolute path to git repository root

    Returns:
        Tuple of (completed_steps, total_steps) or None if unavailable.
        Reads YAML frontmatter for completed_steps/total_steps,
        falls back to counting checkboxes if frontmatter missing.
    """
    if not git_root:
        return None

    progress_file = Path(git_root) / ".impl" / "progress.md"
    if not progress_file.is_file():
        return None

    try:
        content = progress_file.read_text(encoding="utf-8")

        # Try to parse YAML frontmatter first
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = parts[1]
                completed = None
                total = None

                for line in frontmatter.split("\n"):
                    line = line.strip()
                    if line.startswith("completed_steps:"):
                        try:
                            completed = int(line.split(":", 1)[1].strip())
                        except (ValueError, IndexError):
                            pass
                    elif line.startswith("total_steps:"):
                        try:
                            total = int(line.split(":", 1)[1].strip())
                        except (ValueError, IndexError):
                            pass

                if completed is not None and total is not None:
                    return (completed, total)

        # Fallback: count checkboxes
        completed = content.count("- [x]")
        total = completed + content.count("- [ ]")

        if total > 0:
            return (completed, total)

    except (OSError, UnicodeDecodeError):
        pass

    return None


def find_new_plan_file(git_root: str) -> str | None:
    """Find plan file with enriched_by_persist_plan frontmatter at git root.

    Args:
        git_root: Absolute path to git repository root

    Returns:
        Filename (basename) of first matching *-impl.md file with
        enriched_by_persist_plan: true in YAML frontmatter, or None if
        no matching file found.
    """
    if not git_root:
        return None

    try:
        git_root_path = Path(git_root)
        if not git_root_path.exists():
            return None

        # Scan for *-impl.md files at repository root
        for plan_file in git_root_path.glob("*-impl.md"):
            if not plan_file.is_file():
                continue

            try:
                content = plan_file.read_text(encoding="utf-8")

                # Parse YAML frontmatter
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        frontmatter = parts[1]

                        # Check for erk_plan: true (new standard) or
                        # enriched_by_persist_plan: true (backward compat)
                        for line in frontmatter.split("\n"):
                            line = line.strip()
                            if line.startswith("erk_plan:") or line.startswith(
                                "enriched_by_persist_plan:"
                            ):
                                value = line.split(":", 1)[1].strip().lower()
                                if value == "true":
                                    return plan_file.name

            except (OSError, UnicodeDecodeError):
                # Skip files that can't be read
                continue

    except (OSError, ValueError):
        pass

    return None


def get_relative_cwd(cwd: str, git_root: str) -> str:
    """Calculate relative path from git root to current directory.

    Returns:
        Relative path from git root, or empty string if at root.
    """
    if not cwd or not git_root:
        return ""

    try:
        cwd_path = Path(cwd).resolve()
        root_path = Path(git_root).resolve()

        if cwd_path == root_path:
            return ""

        rel_path = cwd_path.relative_to(root_path)
        return str(rel_path)
    except (ValueError, OSError):
        return ""


def get_dir_name(cwd: str) -> str:
    """Get just the directory basename."""
    return Path(cwd).name if cwd else ""


def _parse_github_repo_from_remote(cwd: str) -> tuple[str, str] | None:
    """Parse GitHub owner and repo from git remote URL.

    Args:
        cwd: Current working directory

    Returns:
        (owner, repo) tuple, or None if unable to parse.
        Supports both SSH and HTTPS GitHub URLs:
        - git@github.com:owner/repo.git
        - https://github.com/owner/repo.git
    """
    remote_url = run_git(["remote", "get-url", "origin"], cwd)
    if not remote_url:
        return None

    # Remove .git suffix if present
    if remote_url.endswith(".git"):
        remote_url = remote_url[:-4]

    # Parse SSH format: git@github.com:owner/repo
    if remote_url.startswith("git@github.com:"):
        path = remote_url.split("git@github.com:", 1)[1]
        if "/" in path:
            owner, repo = path.split("/", 1)
            return owner, repo

    # Parse HTTPS format: https://github.com/owner/repo
    for prefix in ("https://github.com/", "http://github.com/"):
        if remote_url.startswith(prefix):
            path = remote_url[len(prefix) :]
            if "/" in path:
                owner, repo = path.split("/", 1)
                return owner, repo

    return None


def _fetch_pr_list(
    owner: str, repo: str, branch: str, cwd: str, timeout: float
) -> tuple[int, str, str, bool] | None:
    """Fetch PR list for a branch.

    Returns:
        Tuple of (pr_number, head_sha, pr_state, is_draft) or None if failed.
        pr_number is 0 if no PR exists.
    """
    try:
        result = subprocess.run(
            [
                "gh",
                "api",
                f"repos/{owner}/{repo}/pulls",
                "-X",
                "GET",
                "-f",
                f"head={owner}:{branch}",
                "-f",
                "state=all",
            ],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        if result.returncode != 0:
            return None

        prs = json.loads(result.stdout)

        # No PR for this branch
        if not prs:
            return (0, "", "", False)

        # Take first PR (REST API returns OPEN PRs first with state=all)
        pr = prs[0]
        pr_number = pr.get("number", 0)
        pr_state = pr.get("state", "").upper()  # REST returns lowercase
        is_draft = pr.get("draft", False)
        head_sha = pr.get("head", {}).get("sha", "")

        return (pr_number, head_sha, pr_state, is_draft)

    except (subprocess.TimeoutExpired, subprocess.SubprocessError, json.JSONDecodeError):
        return None


def _fetch_pr_details(owner: str, repo: str, pr_number: int, cwd: str, timeout: float) -> str:
    """Fetch PR details for mergeable status.

    Returns:
        Mergeable status: "MERGEABLE", "CONFLICTING", or "UNKNOWN".
    """
    try:
        result = subprocess.run(
            ["gh", "api", f"repos/{owner}/{repo}/pulls/{pr_number}"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        if result.returncode != 0:
            return "UNKNOWN"

        pr_detail = json.loads(result.stdout)
        mergeable_value = pr_detail.get("mergeable")
        mergeable_state = pr_detail.get("mergeable_state", "")

        # Map REST mergeable fields to GraphQL-style values
        if mergeable_value is True:
            return "MERGEABLE"
        elif mergeable_value is False:
            if mergeable_state == "dirty":
                return "CONFLICTING"
            return "UNKNOWN"
        # mergeable is null (GitHub hasn't computed yet)
        return "UNKNOWN"

    except (subprocess.TimeoutExpired, subprocess.SubprocessError, json.JSONDecodeError):
        return "UNKNOWN"


def _fetch_check_runs(
    owner: str, repo: str, head_sha: str, cwd: str, timeout: float
) -> list[dict[str, str]]:
    """Fetch check runs for a commit.

    Returns:
        List of check context dicts with __typename, conclusion, status, name.
    """
    try:
        result = subprocess.run(
            ["gh", "api", f"repos/{owner}/{repo}/commits/{head_sha}/check-runs"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        if result.returncode != 0:
            return []

        check_runs_data = json.loads(result.stdout)
        raw_runs = check_runs_data.get("check_runs", [])

        check_contexts: list[dict[str, str]] = []
        for run in raw_runs:
            check_contexts.append(
                {
                    "__typename": "CheckRun",
                    "conclusion": (run.get("conclusion") or "").upper(),
                    "status": (run.get("status") or "").upper(),
                    "name": run.get("name", ""),
                }
            )

        return check_contexts

    except (subprocess.TimeoutExpired, subprocess.SubprocessError, json.JSONDecodeError):
        return []


def _fetch_github_data_rest(cwd: str) -> GitHubData | None:
    """Fetch repository, PR, and checks data via REST API.

    Uses caching for PR list and parallelizes PR details + check runs calls.

    Timeout strategy:
    - PR list (cache miss): 1.5s
    - PR details + check runs (parallel): 1.5s each, 2s combined max
    - Total worst case: ~3.5s (cache miss) or ~2s (cache hit)

    Returns:
        GitHubData with all GitHub information, or None if any call fails.
    """
    # Get current branch
    branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd)
    if not branch:
        return None

    # Parse owner/repo from git remote URL
    repo_info = _parse_github_repo_from_remote(cwd)
    if not repo_info:
        return None

    owner, repo = repo_info

    # Try cache first for PR info
    cached = _get_cached_pr_info(owner, repo, branch)
    if cached:
        pr_number, head_sha = cached
        pr_state = "OPEN"  # Cached PRs are always OPEN (we only cache PRs)
        is_draft = False  # Cached: we don't store draft status
    else:
        # Cache miss: fetch PR list (1.5s timeout)
        pr_result = _fetch_pr_list(owner, repo, branch, cwd, 1.5)
        if pr_result is None:
            return None  # API failure

        pr_number, head_sha, pr_state, is_draft = pr_result

        # Cache if we found a PR
        if pr_number > 0:
            _set_cached_pr_info(owner, repo, branch, pr_number, head_sha)

    # No PR for this branch
    if pr_number == 0:
        return GitHubData(
            owner=owner,
            repo=repo,
            pr_number=0,
            pr_state="",
            is_draft=False,
            mergeable="",
            check_contexts=[],
        )

    # Fetch PR details and check runs in parallel (1.5s timeout each, 2s combined)
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            pr_future = executor.submit(_fetch_pr_details, owner, repo, pr_number, cwd, 1.5)
            checks_future = executor.submit(_fetch_check_runs, owner, repo, head_sha, cwd, 1.5)

            # Wait for both with combined timeout
            mergeable = pr_future.result(timeout=2)
            check_contexts = checks_future.result(timeout=2)
    except TimeoutError:
        # If parallel execution times out, use defaults
        mergeable = "UNKNOWN"
        check_contexts = []

    return GitHubData(
        owner=owner,
        repo=repo,
        pr_number=pr_number,
        pr_state=pr_state,
        is_draft=is_draft,
        mergeable=mergeable,
        check_contexts=check_contexts,
    )


def _categorize_check_buckets(check_contexts: list[dict[str, str]]) -> str:
    """Categorize check contexts into bucket status.

    Args:
        check_contexts: List of check context dicts (normalized to GraphQL format)

    Returns:
        "✅" if all checks pass
        "🚫" if any checks fail
        "🔄" if checks are pending/in-progress
        "" (empty string) if no checks
    """
    if not check_contexts:
        return ""

    has_pass = False
    has_fail = False
    has_pending = False

    for context in check_contexts:
        typename = context.get("__typename", "")

        if typename == "CheckRun":
            conclusion = context.get("conclusion", "")
            status = context.get("status", "")

            # Map CheckRun states to buckets
            if conclusion in ("SUCCESS", "NEUTRAL", "SKIPPED"):
                has_pass = True
            elif conclusion in ("FAILURE", "TIMED_OUT", "ACTION_REQUIRED", "CANCELLED"):
                has_fail = True
            elif status in ("IN_PROGRESS", "QUEUED", "PENDING", "WAITING"):
                has_pending = True
            elif conclusion == "" and status in ("COMPLETED",):
                # Completed without conclusion - treat as pending
                has_pending = True

        elif typename == "StatusContext":
            state = context.get("state", "")

            # Map StatusContext states to buckets
            if state == "SUCCESS":
                has_pass = True
            elif state in ("FAILURE", "ERROR"):
                has_fail = True
            elif state in ("PENDING", "EXPECTED"):
                has_pending = True

    # Priority: fail > pending > pass
    if has_fail:
        return "🚫"
    if has_pending:
        return "🔄"
    if has_pass:
        return "✅"

    return ""


def get_checks_status(github_data: GitHubData | None) -> str:
    """Get GitHub checks status from GitHubData.

    Args:
        github_data: GitHub data from GraphQL query, or None if unavailable

    Returns:
        "✅" if all checks pass
        "🚫" if any checks fail
        "🔄" if checks are pending/in-progress
        "" (empty string) if no checks or unavailable
    """
    if not github_data:
        return ""

    return _categorize_check_buckets(github_data.check_contexts)


def get_repo_info(github_data: GitHubData | None) -> RepoInfo:
    """Convert GitHubData to RepoInfo for display.

    Args:
        github_data: GitHub data from GraphQL query, or None if unavailable

    Returns:
        RepoInfo with owner, repo, pr_number, pr_url, pr_state, and has_conflicts.
        All fields empty/False if information unavailable.
    """
    if not github_data:
        return RepoInfo(
            owner="", repo="", pr_number="", pr_url="", pr_state="", has_conflicts=False
        )

    # If no PR, return repo info only
    if github_data.pr_number == 0:
        return RepoInfo(
            owner=github_data.owner,
            repo=github_data.repo,
            pr_number="",
            pr_url="",
            pr_state="",
            has_conflicts=False,
        )

    # Convert PR data to display format
    pr_number = str(github_data.pr_number)
    pr_url = (
        f"https://app.graphite.dev/github/pr/{github_data.owner}/{github_data.repo}/{pr_number}/"
    )

    # Determine PR state based on GitHub fields
    pr_state = ""
    if github_data.is_draft:
        pr_state = "draft"
    elif github_data.pr_state == "OPEN":
        pr_state = "published"
    elif github_data.pr_state == "MERGED":
        pr_state = "merged"
    elif github_data.pr_state == "CLOSED":
        pr_state = "closed"

    # Check for merge conflicts
    has_conflicts = github_data.mergeable == "CONFLICTING"

    return RepoInfo(
        owner=github_data.owner,
        repo=github_data.repo,
        pr_number=pr_number,
        pr_url=pr_url,
        pr_state=pr_state,
        has_conflicts=has_conflicts,
    )


def build_context_labels(
    repo_name: str, is_linked_worktree: bool, worktree_name: str, branch: str, relative_cwd: str
) -> list[TokenSeq]:
    """Build hierarchical context labels.

    Args:
        repo_name: GitHub repository name (empty if not available)
        is_linked_worktree: True if in a linked worktree, False if in main worktree
        worktree_name: Worktree directory name
        branch: Git branch name
        relative_cwd: Relative path from worktree root (empty if at root)

    Returns:
        List of TokenSeq objects following hierarchy:
        (git:repo) [(wt:worktree)] (br:branch) [(cwd:path)]
        When worktree and branch are the same: ({wt, br}:name)
    """
    labels = []

    # Always show git repo name if available
    if repo_name:
        labels.append(context_label(["git"], repo_name, Color.CYAN))

    # Combine worktree and branch if they have the same name
    if is_linked_worktree and worktree_name and branch and worktree_name == branch:
        labels.append(context_label(["wt", "br"], branch, Color.RED))
    else:
        # Show worktree name for linked worktrees, "root" for main worktree
        if is_linked_worktree and worktree_name:
            labels.append(context_label(["wt"], worktree_name, Color.YELLOW))
        else:
            labels.append(context_label(["wt"], "root", Color.YELLOW))

        # Always show branch
        if branch:
            labels.append(context_label(["br"], branch, Color.RED))

    # Show cwd only if not at root
    if relative_cwd:
        labels.append(context_label(["cwd"], relative_cwd, Color.GRAY))

    return labels


def build_plan_label(plan_progress: tuple[int, int] | None) -> Token:
    """Build (.impl) label with progress indicator.

    Args:
        plan_progress: Tuple of (completed_steps, total_steps) or None

    Returns:
        Token with progress indicator:
        - (.impl ⚪ 0/N) for 0% complete
        - (.impl 🟡 X/N) for 1-99% complete
        - (.impl ✅ N/N) for 100% complete
        - (.impl) if no progress data available
    """
    if not plan_progress:
        return Token("(.impl)")

    completed, total = plan_progress

    if total == 0:
        return Token("(.impl)")

    # Calculate progress percentage
    progress_pct = (completed / total) * 100

    # Choose indicator based on progress
    if progress_pct == 0:
        indicator = "⚪"
    elif progress_pct >= 100:
        indicator = "✅"
    else:
        indicator = "🟡"

    return Token(f"(.impl {indicator} {completed}/{total})")


def build_new_plan_label(filename: str) -> Token:
    """Build (🆕:basename) label for new plan file.

    Args:
        filename: Filename like "add-lorem-ipsum-to-readme-impl.md"

    Returns:
        Token with format (🆕:basename) where basename is the filename
        with -impl.md suffix removed.
    """
    # Remove -impl.md suffix
    basename = filename.replace("-impl.md", "")
    return Token(f"(🆕:{basename})")


def build_gh_label(
    repo_info: RepoInfo, github_data: GitHubData | None, issue_number: int | None = None
) -> TokenSeq:
    """Build GitHub PR metadata label.

    Args:
        repo_info: Repository and PR information
        github_data: GitHub data from GraphQL query (for checks status)
        issue_number: Optional issue number from .impl/issue.json

    Returns:
        TokenSeq for the complete GitHub label like:
        (gh:#123 plan:#456 st:👀💥 chks:✅)
    """
    parts = [Token("(gh:")]

    # Add PR number if available (no hyperlink due to Claude Code alignment bug with OSC 8)
    if repo_info.pr_number and repo_info.pr_url:
        parts.append(Token(f"#{repo_info.pr_number}", color=Color.BLUE))

        # Add issue number if available
        if issue_number:
            parts.extend(
                [
                    Token(" plan:"),
                    Token(f"#{issue_number}", color=Color.BLUE),
                ]
            )

        # Build state emoji
        state_emojis = {
            "published": "👀",
            "draft": "🚧",
            "merged": "🎉",
            "closed": "⛔",
        }

        if repo_info.pr_state:
            emoji = state_emojis.get(repo_info.pr_state, "")

            # Add conflicts emoji if applicable
            if repo_info.pr_state in ("published", "draft") and repo_info.has_conflicts:
                emoji += "💥"

            if emoji:
                parts.extend(
                    [
                        Token(" st:"),
                        Token(emoji),
                    ]
                )

        # Get checks status
        checks_status = get_checks_status(github_data)
        if checks_status:
            parts.extend(
                [
                    Token(" chks:"),
                    Token(checks_status),
                ]
            )
    else:
        parts.append(Token("no-pr"))

    parts.append(Token(")"))
    return TokenSeq(tuple(parts))


def main():
    """Main entry point."""
    try:
        data = json.load(sys.stdin)
        cwd = data.get("workspace", {}).get("current_dir", "")

        # Get git status and repo info
        branch = ""
        is_dirty = False
        repo_name = ""
        is_linked_worktree = False
        worktree_name = ""
        relative_cwd = ""
        plan_progress = None
        new_plan_file = None
        git_root = ""
        issue_number = None

        if cwd:
            branch, is_dirty = get_git_status(cwd)
            if branch:
                # Get git root and worktree info
                git_root = get_git_root(cwd)
                if git_root:
                    is_linked_worktree, worktree_name = get_worktree_info(cwd)
                    relative_cwd = get_relative_cwd(cwd, git_root)
                    plan_progress = get_plan_progress(git_root)
                    new_plan_file = find_new_plan_file(git_root)
                    issue_number = get_issue_number(git_root)

        # Get model code
        model = data.get("model", {}).get("display_name", "")
        model_id = data.get("model", {}).get("id", "")
        if "[1m]" in model_id.lower():
            model_code = "S¹ᴹ"
        elif "sonnet" in model.lower():
            model_code = "S"
        elif "opus" in model.lower():
            model_code = "O"
        else:
            model_code = model[:1].upper() if model else "?"

        # Fetch GitHub data via REST API
        github_data = _fetch_github_data_rest(cwd) if cwd else None

        # Get repo info from GitHub data
        repo_info = get_repo_info(github_data)
        if repo_info:
            repo_name = repo_info.repo

        # Build complete statusline as single TokenSeq
        statusline = TokenSeq(
            (
                Token("➜ ", color=Color.GRAY),
                *build_context_labels(
                    repo_name, is_linked_worktree, worktree_name, branch, relative_cwd
                ),
                *(
                    [build_plan_label(plan_progress)]
                    if plan_progress or (git_root and has_plan_file(git_root))
                    else []
                ),
                *([build_new_plan_label(new_plan_file)] if new_plan_file else []),
                *([Token("✗")] if is_dirty else []),
                Token("|"),
                build_gh_label(repo_info, github_data, issue_number),
                TokenSeq((Token("│ ("), Token(model_code), Token(")"))),
            )
        )

        print(statusline.join(" "), end="")

    except Exception as e:
        print(f"➜  error │ {e}", end="")


if __name__ == "__main__":
    main()
