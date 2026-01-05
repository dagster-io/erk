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
import logging
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import NamedTuple

from erk_statusline.colored_tokens import Color, Token, TokenSeq, context_label
from erk_statusline.context import StatuslineContext

# Cache configuration
CACHE_DIR = Path("/tmp/erk-statusline-cache")
CACHE_TTL_SECONDS = 30

# Logging setup - file-based to avoid polluting stderr (which breaks status line)
# Logs go to ~/.erk/logs/statusline/<session-id>.log for per-session isolation
_logger = logging.getLogger("erk_statusline")
_logger.setLevel(logging.DEBUG)
_logging_initialized = False


def _setup_logging(session_id: str) -> None:
    """Setup logging for a specific session. Called once per session."""
    global _logging_initialized
    if _logging_initialized:
        return

    log_dir = Path.home() / ".erk" / "logs" / "statusline"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{session_id}.log"
    handler = logging.FileHandler(log_file)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    _logger.addHandler(handler)
    _logging_initialized = True


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
        _logger.debug("Cache miss: %s/%s branch=%s (no cache file)", owner, repo, branch)
        return None

    cache_stat = cache_path.stat()
    cache_age = time.time() - cache_stat.st_mtime
    if cache_age > CACHE_TTL_SECONDS:
        _logger.debug(
            "Cache miss: %s/%s branch=%s (expired, age=%.1fs)", owner, repo, branch, cache_age
        )
        return None

    try:
        content = cache_path.read_text(encoding="utf-8")
        data = json.loads(content)
        pr_number = data.get("pr_number")
        head_sha = data.get("head_sha")
        if isinstance(pr_number, int) and isinstance(head_sha, str):
            _logger.debug(
                "Cache hit: %s/%s branch=%s -> pr=%d sha=%s",
                owner,
                repo,
                branch,
                pr_number,
                head_sha[:7],
            )
            return (pr_number, head_sha)
    except (json.JSONDecodeError, OSError, KeyError):
        _logger.debug("Cache miss: %s/%s branch=%s (parse error)", owner, repo, branch)

    return None


def _set_cached_pr_info(owner: str, repo: str, branch: str, pr_number: int, head_sha: str) -> None:
    """Cache PR info for a branch."""
    cache_path = _get_cache_path(owner, repo, branch)

    if not CACHE_DIR.exists():
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    cache_data = {"pr_number": pr_number, "head_sha": head_sha}
    cache_path.write_text(json.dumps(cache_data), encoding="utf-8")
    _logger.debug(
        "Cache write: %s/%s branch=%s -> pr=%d sha=%s",
        owner,
        repo,
        branch,
        pr_number,
        head_sha[:7],
    )


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


def get_git_root_via_gateway(ctx: StatuslineContext) -> Path | None:
    """Get git repository root directory using gateway.

    Args:
        ctx: StatuslineContext with git gateway

    Returns:
        Path to git root, or None if not in git repo.
    """
    try:
        return ctx.git.get_repository_root(ctx.cwd)
    except (ValueError, OSError):
        return None


def get_git_status_via_gateway(ctx: StatuslineContext) -> tuple[str, bool]:
    """Get git branch and dirty status using gateway.

    Args:
        ctx: StatuslineContext with git gateway

    Returns:
        (branch_name, is_dirty)
    """
    branch = ctx.git.get_current_branch(ctx.cwd)
    if branch is None:
        return "", False

    is_dirty = ctx.git.has_uncommitted_changes(ctx.cwd)
    return branch, is_dirty


def get_worktree_info_via_gateway(ctx: StatuslineContext, repo_root: Path) -> tuple[bool, str]:
    """Detect if in a linked worktree and get worktree name using gateway.

    Args:
        ctx: StatuslineContext with git gateway
        repo_root: Repository root path

    Returns:
        (is_linked_worktree, worktree_name)
        - is_linked_worktree: False for root worktree, True for linked worktrees
        - worktree_name: Directory basename of the worktree
    """
    worktrees = ctx.git.list_worktrees(repo_root)
    if not worktrees:
        return False, ""

    # Find which worktree we're in
    for wt in worktrees:
        if wt.path == repo_root:
            # Use is_root flag from WorktreeInfo
            is_linked = not wt.is_root
            wt_name = wt.path.name
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


def _parse_github_repo_from_url(remote_url: str) -> tuple[str, str] | None:
    """Parse GitHub owner and repo from a remote URL string.

    Args:
        remote_url: Git remote URL string

    Returns:
        (owner, repo) tuple, or None if unable to parse.
        Supports both SSH and HTTPS GitHub URLs:
        - git@github.com:owner/repo.git
        - https://github.com/owner/repo.git
    """
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


def get_github_repo_via_gateway(ctx: StatuslineContext, repo_root: Path) -> tuple[str, str] | None:
    """Get GitHub owner and repo using gateway.

    Args:
        ctx: StatuslineContext with git gateway
        repo_root: Repository root path

    Returns:
        (owner, repo) tuple, or None if unable to parse.
    """
    try:
        remote_url = ctx.git.get_remote_url(repo_root, "origin")
        return _parse_github_repo_from_url(remote_url)
    except ValueError:
        return None


def get_pr_info_via_branch_manager(
    ctx: StatuslineContext, repo_root: Path, branch: str
) -> tuple[int, str, bool] | None:
    """Get PR info via BranchManager.

    Uses BranchManager abstraction which automatically selects between
    Graphite cache (fast, local) or GitHub API (slower, network) based
    on whether Graphite is enabled.

    Args:
        ctx: StatuslineContext with branch_manager
        repo_root: Repository root path
        branch: Current branch name

    Returns:
        Tuple of (pr_number, pr_state, is_draft) or None if no PR found.
        pr_state is one of "OPEN", "MERGED", "CLOSED".
    """
    pr_info = ctx.branch_manager.get_pr_for_branch(repo_root, branch)
    if pr_info is None:
        return None

    return (pr_info.number, pr_info.state, pr_info.is_draft)


class PRDetailsResult(NamedTuple):
    """Result from fetching PR details."""

    mergeable: str  # "MERGEABLE", "CONFLICTING", or "UNKNOWN"
    head_sha: str  # Commit SHA of the PR head (empty string on error)


def _fetch_pr_details(
    owner: str, repo: str, pr_number: int, cwd: str, timeout: float
) -> PRDetailsResult:
    """Fetch PR details for mergeable status and head SHA.

    Returns:
        PRDetailsResult with mergeable status and head SHA.
    """
    _logger.debug("Fetching PR details: %s/%s #%d", owner, repo, pr_number)
    start_time = time.time()
    try:
        result = subprocess.run(
            ["gh", "api", f"repos/{owner}/{repo}/pulls/{pr_number}"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        elapsed = time.time() - start_time
        if result.returncode != 0:
            _logger.debug(
                "PR details fetch failed: %s/%s #%d returncode=%d in %.2fs",
                owner,
                repo,
                pr_number,
                result.returncode,
                elapsed,
            )
            return PRDetailsResult(mergeable="UNKNOWN", head_sha="")

        pr_detail = json.loads(result.stdout)
        mergeable_value = pr_detail.get("mergeable")
        mergeable_state = pr_detail.get("mergeable_state", "")

        # Extract head SHA from PR response
        head_sha = ""
        head_info = pr_detail.get("head")
        if isinstance(head_info, dict):
            sha = head_info.get("sha")
            if isinstance(sha, str):
                head_sha = sha

        # Map REST mergeable fields to GraphQL-style values
        if mergeable_value is True:
            status = "MERGEABLE"
        elif mergeable_value is False:
            status = "CONFLICTING" if mergeable_state == "dirty" else "UNKNOWN"
        else:
            # mergeable is null (GitHub hasn't computed yet)
            status = "UNKNOWN"

        _logger.debug(
            "PR details fetched: %s/%s #%d in %.2fs -> %s sha=%s",
            owner,
            repo,
            pr_number,
            elapsed,
            status,
            head_sha[:7] if head_sha else "",
        )
        return PRDetailsResult(mergeable=status, head_sha=head_sha)

    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        _logger.debug("PR details timeout: %s/%s #%d after %.2fs", owner, repo, pr_number, elapsed)
        return PRDetailsResult(mergeable="UNKNOWN", head_sha="")
    except (subprocess.SubprocessError, json.JSONDecodeError) as e:
        elapsed = time.time() - start_time
        _logger.debug(
            "PR details error: %s/%s #%d in %.2fs - %s", owner, repo, pr_number, elapsed, e
        )
        return PRDetailsResult(mergeable="UNKNOWN", head_sha="")


def _fetch_check_runs(
    owner: str, repo: str, ref: str, cwd: str, timeout: float
) -> list[dict[str, str]]:
    """Fetch check runs for a git ref.

    Args:
        owner: Repository owner
        repo: Repository name
        ref: Git ref - can be a SHA, branch name, or tag name.
             Using branch name resolves to GitHub's HEAD for that branch,
             avoiding issues when local branch differs from remote.
        cwd: Working directory for subprocess
        timeout: Timeout in seconds

    Returns:
        List of check context dicts with __typename, conclusion, status, name.
    """
    ref_display = ref[:20] + "..." if len(ref) > 20 else ref
    _logger.debug("Fetching check runs: %s/%s ref=%s", owner, repo, ref_display)
    start_time = time.time()
    try:
        result = subprocess.run(
            ["gh", "api", f"repos/{owner}/{repo}/commits/{ref}/check-runs"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        elapsed = time.time() - start_time
        if result.returncode != 0:
            _logger.debug(
                "Check runs fetch failed: %s/%s ref=%s returncode=%d in %.2fs",
                owner,
                repo,
                ref_display,
                result.returncode,
                elapsed,
            )
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

        _logger.debug(
            "Check runs fetched: %s/%s ref=%s in %.2fs -> %d checks",
            owner,
            repo,
            ref_display,
            elapsed,
            len(check_contexts),
        )
        return check_contexts

    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        _logger.debug(
            "Check runs timeout: %s/%s ref=%s after %.2fs",
            owner,
            repo,
            ref_display,
            elapsed,
        )
        return []
    except (subprocess.SubprocessError, json.JSONDecodeError) as e:
        elapsed = time.time() - start_time
        _logger.debug(
            "Check runs error: %s/%s ref=%s in %.2fs - %s",
            owner,
            repo,
            ref_display,
            elapsed,
            e,
        )
        return []


def fetch_github_data_via_gateway(
    ctx: StatuslineContext, repo_root: Path, branch: str
) -> GitHubData | None:
    """Fetch GitHub data using gateways for PR info, with REST for checks/mergeable.

    Uses Graphite cache for fast PR info, then fetches check runs and mergeable
    status from GitHub API (not in Graphite cache).

    Args:
        ctx: StatuslineContext with gateways
        repo_root: Repository root path
        branch: Current branch name

    Returns:
        GitHubData with PR info and checks, or None if unable to fetch.
    """
    _logger.debug("Fetching GitHub data for branch=%s", branch)
    start_time = time.time()

    # Get owner/repo from git remote
    repo_info = get_github_repo_via_gateway(ctx, repo_root)
    if repo_info is None:
        _logger.debug("GitHub data fetch: no repo info found")
        return None
    owner, repo = repo_info

    # Get PR info via BranchManager (Graphite cache or GitHub API)
    pr_info = get_pr_info_via_branch_manager(ctx, repo_root, branch)

    if pr_info is None:
        # No PR for this branch
        _logger.debug("GitHub data fetch: no PR for branch=%s", branch)
        return GitHubData(
            owner=owner,
            repo=repo,
            pr_number=0,
            pr_state="",
            is_draft=False,
            mergeable="",
            check_contexts=[],
        )

    pr_number, pr_state, is_draft = pr_info
    _logger.debug(
        "GitHub data fetch: found PR #%d state=%s draft=%s", pr_number, pr_state, is_draft
    )

    # Fetch PR details and check runs in parallel
    # Note: check runs uses branch name (not local SHA) which resolves to GitHub's HEAD,
    # avoiding issues when local branch differs from remote (e.g., after Graphite squash)
    cwd = str(ctx.cwd)
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            pr_future = executor.submit(_fetch_pr_details, owner, repo, pr_number, cwd, 1.5)
            checks_future = executor.submit(_fetch_check_runs, owner, repo, branch, cwd, 1.5)

            # Wait for both with combined timeout
            pr_details = pr_future.result(timeout=2)
            check_contexts = checks_future.result(timeout=2)
        mergeable = pr_details.mergeable
    except TimeoutError:
        # If parallel execution times out, use defaults
        parallel_elapsed = time.time() - start_time
        _logger.debug("GitHub data fetch: ThreadPoolExecutor timeout after %.2fs", parallel_elapsed)
        mergeable = "UNKNOWN"
        check_contexts = []

    elapsed = time.time() - start_time
    _logger.debug(
        "GitHub data fetch complete: branch=%s pr=%d mergeable=%s checks=%d in %.2fs",
        branch,
        pr_number,
        mergeable,
        len(check_contexts),
        elapsed,
    )

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


def build_plan_label() -> Token:
    """Build (.impl) label.

    Returns:
        Token with (.impl) indicator.
    """
    return Token("(.impl)")


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
    from erk_statusline.context import create_context

    try:
        data = json.load(sys.stdin)
        cwd = data.get("workspace", {}).get("current_dir", "")

        # Setup logging with session ID
        session_id = data.get("session_id", "unknown")
        _setup_logging(session_id)
        _logger.debug("Statusline invoked: session=%s cwd=%s", session_id, cwd)

        # Get git status and repo info
        branch = ""
        is_dirty = False
        repo_name = ""
        is_linked_worktree = False
        worktree_name = ""
        relative_cwd = ""
        new_plan_file = None
        git_root = ""
        issue_number = None
        github_data = None

        if cwd:
            # Create context with real gateways
            ctx = create_context(cwd)

            branch, is_dirty = get_git_status_via_gateway(ctx)
            if branch:
                # Get git root and worktree info using gateways
                repo_root = get_git_root_via_gateway(ctx)
                if repo_root is not None:
                    git_root = str(repo_root)
                    is_linked_worktree, worktree_name = get_worktree_info_via_gateway(
                        ctx, repo_root
                    )
                    relative_cwd = get_relative_cwd(cwd, git_root)
                    new_plan_file = find_new_plan_file(git_root)
                    issue_number = get_issue_number(git_root)
                    # Fetch GitHub data using gateway for Graphite PR cache
                    github_data = fetch_github_data_via_gateway(ctx, repo_root, branch)

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

        # Get repo info from GitHub data
        repo_info = get_repo_info(github_data)
        if repo_info:
            repo_name = repo_info.repo

        # Log final checks status for debugging
        checks_status = get_checks_status(github_data)
        _logger.debug(
            "Final result: branch=%s pr=%s checks=%s",
            branch,
            repo_info.pr_number if repo_info else "",
            checks_status if checks_status else "(empty)",
        )

        # Build complete statusline as single TokenSeq
        statusline = TokenSeq(
            (
                Token("➜ ", color=Color.GRAY),
                *build_context_labels(
                    repo_name, is_linked_worktree, worktree_name, branch, relative_cwd
                ),
                *([build_plan_label()] if git_root and has_plan_file(git_root) else []),
                *([build_new_plan_label(new_plan_file)] if new_plan_file else []),
                *([Token("✗")] if is_dirty else []),
                Token("|"),
                build_gh_label(repo_info, github_data, issue_number),
                TokenSeq((Token("│ ("), Token(model_code), Token(")"))),
            )
        )

        print(statusline.join(" "), end="")

    except Exception as e:
        _logger.exception("Statusline error: %s", e)
        print(f"➜  error │ {e}", end="")


if __name__ == "__main__":
    main()
