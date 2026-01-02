"""Orchestrator for capturing documentation gaps from implementation sessions.

This module provides the main entry point for the learn feature, coordinating:
1. Reading session data from .impl/local-run-state.json
2. Finding and reading the session JSONL file
3. Converting to XML via batched LLM processing
4. Synthesizing documentation gaps
5. Creating an erk-learn GitHub issue
"""

from pathlib import Path

from erk_shared.github.issues.abc import GitHubIssues
from erk_shared.impl_folder import read_local_run_state
from erk_shared.learn.issue_creation import create_learn_issue
from erk_shared.learn.session_to_xml import session_to_xml
from erk_shared.learn.synthesis import synthesize_session
from erk_shared.learn.types import LearnResult
from erk_shared.prompt_executor.abc import PromptExecutor

# Default batch size for session-to-XML conversion
DEFAULT_BATCH_CHAR_LIMIT = 50_000


def _encode_worktree_path(worktree_path: Path) -> str:
    """Encode worktree path to Claude projects folder name format.

    Claude Code stores session data under ~/.claude/projects/ using
    a path encoding scheme: slashes become dashes, leading slash removed.

    Example:
        /Users/foo/repo -> -Users-foo-repo

    Args:
        worktree_path: Absolute path to worktree

    Returns:
        Encoded folder name
    """
    # Convert path to string and replace / with -
    path_str = str(worktree_path)
    return path_str.replace("/", "-")


def _find_session_file(session_id: str, worktree_path: Path) -> Path | None:
    """Find the session JSONL file for a given session ID.

    Session files are stored under ~/.claude/projects/{encoded-path}/.
    The session file is named {session_id}.jsonl.

    Args:
        session_id: Claude Code session UUID
        worktree_path: Path to the worktree

    Returns:
        Path to session file if found, None otherwise
    """
    encoded_path = _encode_worktree_path(worktree_path)
    claude_projects = Path.home() / ".claude" / "projects"
    project_folder = claude_projects / encoded_path

    if not project_folder.exists():
        return None

    session_file = project_folder / f"{session_id}.jsonl"
    if session_file.exists():
        return session_file

    return None


def capture_for_learn(
    worktree_path: Path,
    branch_name: str,
    pr_number: int,
    github_issues: GitHubIssues,
    prompt_executor: PromptExecutor,
) -> LearnResult | None:
    """Orchestrate learn capture from implementation session.

    This is the main entry point for capturing documentation gaps.
    It reads the implementation session, synthesizes gaps, and creates
    an erk-learn issue.

    Args:
        worktree_path: Path to the worktree directory
        branch_name: Git branch name (for issue context)
        pr_number: PR number that was just merged
        github_issues: GitHubIssues interface for issue creation
        prompt_executor: Executor for LLM calls

    Returns:
        LearnResult if capture was attempted (success or failure),
        None if skipped (no .impl/ folder, no session ID, etc.)
    """
    # Step 1: Check for .impl/ folder
    impl_dir = worktree_path / ".impl"
    if not impl_dir.exists():
        return None

    # Step 2: Read local run state to get session ID
    run_state = read_local_run_state(impl_dir)
    if run_state is None:
        return None

    session_id = run_state.session_id
    if session_id is None:
        return None

    # Step 3: Find and read session file
    session_file = _find_session_file(session_id, worktree_path)
    if session_file is None:
        return LearnResult(
            success=False,
            issue_url=None,
            issue_number=None,
            error=f"Session file not found for session {session_id}",
        )

    session_content = session_file.read_text(encoding="utf-8")
    if not session_content.strip():
        return LearnResult(
            success=False,
            issue_url=None,
            issue_number=None,
            error="Session file is empty",
        )

    # Step 4: Convert to XML
    try:
        session_xml = session_to_xml(
            session_content,
            prompt_executor,
            batch_char_limit=DEFAULT_BATCH_CHAR_LIMIT,
        )
    except RuntimeError as e:
        return LearnResult(
            success=False,
            issue_url=None,
            issue_number=None,
            error=f"Failed to convert session to XML: {e}",
        )

    # Step 5: Synthesize documentation gaps
    synthesis = synthesize_session(
        session_xml,
        branch_name,
        pr_number,
        prompt_executor,
    )

    if synthesis is None:
        return LearnResult(
            success=False,
            issue_url=None,
            issue_number=None,
            error="Failed to synthesize documentation gaps",
        )

    # Step 6: Create erk-learn issue
    return create_learn_issue(
        github_issues=github_issues,
        repo_root=worktree_path,
        branch_name=branch_name,
        pr_number=pr_number,
        session_id=session_id,
        synthesis=synthesis,
    )
