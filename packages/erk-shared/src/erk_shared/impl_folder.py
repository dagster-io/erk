"""Implementation folder utilities for erk and erk-kits.

This module provides shared utilities for managing .impl/ folder structures:
- plan.md: Immutable implementation plan
- progress.md: Mutable progress tracking with step checkboxes
- issue.json: GitHub issue reference (optional)

These utilities are used by both erk (for local operations) and erk-kits
(for kit CLI commands).
"""

import json
import shutil
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import frontmatter
import yaml

from erk_shared.github.metadata import (
    create_worktree_creation_block,
    render_erk_issue_event,
)
from erk_shared.prompt_executor.abc import PromptExecutor


def create_impl_folder(
    worktree_path: Path,
    plan_content: str,
    prompt_executor: PromptExecutor,
    *,
    overwrite: bool,
) -> Path:
    """Create .impl/ folder with plan.md and progress.md files.

    Args:
        worktree_path: Path to the worktree directory
        plan_content: Content for plan.md file
        prompt_executor: Executor for LLM-based step extraction
        overwrite: If True, remove existing .impl/ folder before creating new one.
                   If False, raise FileExistsError when .impl/ already exists.

    Returns:
        Path to the created .impl/ directory

    Raises:
        FileExistsError: If .impl/ directory already exists and overwrite is False
        RuntimeError: If LLM step extraction fails
    """
    impl_folder = worktree_path / ".impl"

    if impl_folder.exists():
        if overwrite:
            shutil.rmtree(impl_folder)
        else:
            raise FileExistsError(f"Implementation folder already exists at {impl_folder}")

    # Create .impl/ directory
    impl_folder.mkdir(parents=True, exist_ok=False)

    # Write immutable plan.md
    plan_file = impl_folder / "plan.md"
    plan_file.write_text(plan_content, encoding="utf-8")

    # Extract steps using LLM and generate progress.md
    steps = extract_steps_from_plan(plan_content, prompt_executor)
    progress_content = generate_progress_content(steps)

    progress_file = impl_folder / "progress.md"
    progress_file.write_text(progress_content, encoding="utf-8")

    # Verify file integrity after creation
    errors = validate_progress_schema(progress_file)
    if errors:
        # This should never happen if generate_progress_content is correct
        msg = f"Generated invalid progress.md: {'; '.join(errors)}"
        raise ValueError(msg)

    return impl_folder


def get_impl_path(worktree_path: Path, git_ops=None) -> Path | None:
    """Get path to plan.md in .impl/ if it exists.

    Args:
        worktree_path: Path to the worktree directory
        git_ops: Optional Git interface for path checking (uses .exists() if None)

    Returns:
        Path to plan.md if exists, None otherwise
    """
    plan_file = worktree_path / ".impl" / "plan.md"
    path_exists = git_ops.path_exists(plan_file) if git_ops is not None else plan_file.exists()
    if path_exists:
        return plan_file
    return None


def get_progress_path(worktree_path: Path) -> Path | None:
    """Get path to progress.md if it exists.

    Args:
        worktree_path: Path to the worktree directory

    Returns:
        Path to progress.md if exists, None otherwise
    """
    progress_file = worktree_path / ".impl" / "progress.md"
    if progress_file.exists():
        return progress_file
    return None


_STEP_EXTRACTION_PROMPT = (
    "You are a JSON extraction tool. Your ONLY output must be valid JSON.\n\n"
    "CRITICAL: Output ONLY a JSON array. No explanations, no markdown, no preamble.\n\n"
    "Task: Extract implementation steps from the plan below.\n"
    "- Include: Numbered steps, phase headings, implementation tasks\n"
    "- Exclude: Testing strategy, success criteria, prerequisites, documentation\n\n"
    'Output format: ["1. Step one", "2. Step two"]\n'
    "Empty plan: []\n\n"
    "IMPORTANT: Your response must start with [ and end with ] - nothing else.\n\n"
    "Plan:\n{plan_content}"
)


def extract_steps_from_plan(plan_content: str, prompt_executor: PromptExecutor) -> list[str]:
    """Extract implementation steps from plan markdown using LLM.

    Uses Claude Sonnet to semantically understand the plan and extract
    actionable implementation steps.

    Args:
        plan_content: Full plan markdown content
        prompt_executor: Executor for running the extraction prompt

    Returns:
        List of step descriptions with their numbers

    Raises:
        RuntimeError: If LLM execution fails or returns invalid response
    """
    prompt = _STEP_EXTRACTION_PROMPT.format(plan_content=plan_content)
    result = prompt_executor.execute_prompt(prompt, model="sonnet")

    if not result.success:
        msg = f"LLM step extraction failed: {result.error}"
        raise RuntimeError(msg)

    # Parse JSON response
    output = result.output.strip()

    # Handle empty output (LLM may return empty response even on success)
    if not output:
        # LOUD warning to help debug this edge case
        print("=" * 60, file=sys.stderr)
        print("WARNING: LLM returned empty output for step extraction", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        print("Model: sonnet", file=sys.stderr)
        print(f"Prompt length: {len(prompt)} chars", file=sys.stderr)
        print("First 500 chars of prompt:", file=sys.stderr)
        print(prompt[:500], file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        msg = "LLM returned empty output for step extraction (see stderr for details)"
        raise RuntimeError(msg)

    # Handle markdown code blocks (LLM may wrap in ```json ... ```)
    if output.startswith("```"):
        # Remove first and last lines (code block markers)
        lines = output.split("\n")
        output = "\n".join(lines[1:-1])

    try:
        steps = json.loads(output)
    except json.JSONDecodeError as e:
        # LOUD warning and fallback to empty list
        print("=" * 60, file=sys.stderr)
        print("WARNING: LLM returned invalid JSON for step extraction", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        print(f"Error: {e}", file=sys.stderr)
        print(f"Output (first 500 chars): {output[:500]}", file=sys.stderr)
        print("Falling back to empty steps list", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        steps = []

    # Validate response structure
    if not isinstance(steps, list):
        msg = f"LLM returned non-list: {type(steps).__name__}"
        raise RuntimeError(msg)

    # Validate all items are strings
    for i, step in enumerate(steps):
        if not isinstance(step, str):
            msg = f"Step {i} is not a string: {type(step).__name__}"
            raise RuntimeError(msg)

    return steps


def extract_plan_steps(impl_dir: Path, prompt_executor: PromptExecutor) -> list[str]:
    """Extract step descriptions from .impl/plan.md file.

    Args:
        impl_dir: Path to .impl/ directory
        prompt_executor: Executor for LLM-based step extraction

    Returns:
        List of step description strings

    Raises:
        FileNotFoundError: If plan.md doesn't exist
        ValueError: If plan.md contains no steps
        RuntimeError: If LLM step extraction fails
    """
    plan_file = impl_dir / "plan.md"

    if not plan_file.exists():
        msg = f"Plan file not found: {plan_file}"
        raise FileNotFoundError(msg)

    plan_content = plan_file.read_text(encoding="utf-8")
    steps = extract_steps_from_plan(plan_content, prompt_executor)

    if not steps:
        msg = f"No steps found in plan file: {plan_file}"
        raise ValueError(msg)

    return steps


def parse_progress_frontmatter(content: str) -> dict[str, Any] | None:
    """Parse YAML front matter from progress.md content.

    Args:
        content: Full progress.md file content

    Returns:
        Dictionary with 'completed_steps' and 'total_steps', or None if missing/invalid
    """
    # Gracefully handle YAML parsing errors (third-party API exception handling)
    try:
        post = frontmatter.loads(content)
    except yaml.YAMLError:
        return None

    # Check for required fields
    metadata = post.metadata
    if "completed_steps" not in metadata or "total_steps" not in metadata:
        return None

    return metadata


def validate_progress_schema(progress_file: Path) -> list[str]:
    """Validate progress.md schema and structure.

    Validates that progress.md has valid YAML frontmatter with required fields
    and internal consistency.

    Args:
        progress_file: Path to progress.md file

    Returns:
        List of error messages (empty if valid)
    """
    errors: list[str] = []

    if not progress_file.exists():
        return ["progress.md file not found"]

    content = progress_file.read_text(encoding="utf-8")

    # Gracefully handle YAML parsing errors - return as validation error, not exception.
    # Invalid YAML is a validation failure, not a crash condition.
    try:
        post = frontmatter.loads(content)
    except yaml.YAMLError as e:
        return [f"Invalid YAML: {e}"]

    metadata = post.metadata

    # Required fields
    if "steps" not in metadata:
        errors.append("Missing 'steps' field")
    elif not isinstance(metadata["steps"], list):
        errors.append("'steps' must be a list")
    else:
        # Validate step structure
        for i, step in enumerate(metadata["steps"]):
            if not isinstance(step, dict):
                errors.append(f"Step {i + 1} must be an object")
            elif "text" not in step:
                errors.append(f"Step {i + 1} missing 'text' field")
            elif "completed" not in step:
                errors.append(f"Step {i + 1} missing 'completed' field")

    if "total_steps" not in metadata:
        errors.append("Missing 'total_steps' field")

    if "completed_steps" not in metadata:
        errors.append("Missing 'completed_steps' field")

    # Consistency checks (only if no structural errors)
    if not errors and "steps" in metadata:
        steps = metadata["steps"]
        total_steps = metadata["total_steps"]
        completed_steps = metadata["completed_steps"]

        # Type assertions for pyright (narrows types after YAML loading)
        assert isinstance(steps, list)
        assert isinstance(total_steps, int)
        assert isinstance(completed_steps, int)

        if total_steps != len(steps):
            errors.append(f"total_steps ({total_steps}) != len(steps) ({len(steps)})")

        actual_completed = sum(1 for s in steps if s.get("completed"))
        if completed_steps != actual_completed:
            errors.append(
                f"completed_steps ({completed_steps}) != actual count ({actual_completed})"
            )

    return errors


def generate_progress_content(steps: list[str]) -> str:
    """Generate progress.md content with YAML front matter and checkboxes.

    The YAML frontmatter contains the source of truth (steps array with completion status),
    while checkboxes are rendered output for human readability.

    Args:
        steps: List of step descriptions

    Returns:
        Formatted progress markdown with front matter (including steps array) and checkboxes
    """
    # Build steps array for YAML (even if empty)
    steps_yaml = [{"text": step, "completed": False} for step in steps]

    metadata = {
        "completed_steps": 0,
        "total_steps": len(steps),
        "steps": steps_yaml,
    }

    # Build markdown body
    if not steps:
        body = "# Progress Tracking\n\nNo steps detected in plan.\n"
    else:
        body_lines = ["# Progress Tracking\n"]
        for step in steps:
            body_lines.append(f"- [ ] {step}")
        body_lines.append("")  # Trailing newline
        body = "\n".join(body_lines)

    # Use frontmatter.dumps to create the full content
    post = frontmatter.Post(body, **metadata)
    return frontmatter.dumps(post)


@dataclass(frozen=True)
class IssueReference:
    """Reference to a GitHub issue associated with a plan."""

    issue_number: int
    issue_url: str
    created_at: str
    synced_at: str


@dataclass(frozen=True)
class RunInfo:
    """GitHub Actions run information associated with a plan implementation."""

    run_id: str
    run_url: str


@dataclass(frozen=True)
class LocalRunState:
    """Local implementation run state tracked in .impl/local-run-state.json.

    Tracks the last local implementation event with metadata for fast local access
    without requiring GitHub API calls.
    """

    last_event: str  # "started" or "ended"
    timestamp: str  # ISO 8601 UTC timestamp
    session_id: str | None  # Claude Code session ID (optional)
    user: str  # User who ran the implementation


def save_issue_reference(
    impl_dir: Path,
    issue_number: int,
    issue_url: str,
    issue_title: str | None = None,
) -> None:
    """Save GitHub issue reference to .impl/issue.json.

    Args:
        impl_dir: Path to .impl/ directory
        issue_number: GitHub issue number
        issue_url: Full GitHub issue URL
        issue_title: Optional issue title for reference

    Raises:
        FileNotFoundError: If impl_dir doesn't exist
    """
    if not impl_dir.exists():
        msg = f"Implementation directory does not exist: {impl_dir}"
        raise FileNotFoundError(msg)

    issue_file = impl_dir / "issue.json"
    now = datetime.now(UTC).isoformat()

    data: dict[str, str | int] = {
        "issue_number": issue_number,
        "issue_url": issue_url,
        "created_at": now,
        "synced_at": now,
    } | ({"issue_title": issue_title} if issue_title is not None else {})

    issue_file.write_text(json.dumps(data, indent=2), encoding="utf-8")


def read_issue_reference(impl_dir: Path) -> IssueReference | None:
    """Read GitHub issue reference from .impl/issue.json.

    Args:
        impl_dir: Path to .impl/ directory

    Returns:
        IssueReference if file exists and is valid, None otherwise
    """
    issue_file = impl_dir / "issue.json"

    if not issue_file.exists():
        return None

    # Gracefully handle JSON parsing errors (third-party API exception handling)
    try:
        data = json.loads(issue_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        # Could add logging here if needed for debugging:
        # logger.debug(f"Failed to parse issue.json: {e}")
        return None

    # Validate required fields exist
    required_fields = ["issue_number", "issue_url", "created_at", "synced_at"]
    missing_fields = [f for f in required_fields if f not in data]

    if missing_fields:
        # Could add logging here for debugging:
        # logger.debug(f"issue.json missing required fields: {missing_fields}")
        return None

    return IssueReference(
        issue_number=data["issue_number"],
        issue_url=data["issue_url"],
        created_at=data["created_at"],
        synced_at=data["synced_at"],
    )


def has_issue_reference(impl_dir: Path) -> bool:
    """Check if .impl/issue.json exists.

    Args:
        impl_dir: Path to .impl/ directory

    Returns:
        True if issue.json exists, False otherwise
    """
    issue_file = impl_dir / "issue.json"
    return issue_file.exists()


def read_run_info(impl_dir: Path) -> RunInfo | None:
    """Read GitHub Actions run info from .impl/run-info.json.

    Args:
        impl_dir: Path to .impl/ directory

    Returns:
        RunInfo if file exists and is valid, None otherwise
    """
    run_info_file = impl_dir / "run-info.json"

    if not run_info_file.exists():
        return None

    # Gracefully handle JSON parsing errors (third-party API exception handling)
    try:
        data = json.loads(run_info_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None

    # Validate required fields exist
    required_fields = ["run_id", "run_url"]
    missing_fields = [f for f in required_fields if f not in data]

    if missing_fields:
        return None

    return RunInfo(
        run_id=data["run_id"],
        run_url=data["run_url"],
    )


def read_plan_author(impl_dir: Path) -> str | None:
    """Read the plan author from .impl/plan.md metadata.

    Extracts the 'created_by' field from the plan-header metadata block
    embedded in the plan.md file.

    Args:
        impl_dir: Path to .impl/ directory

    Returns:
        The plan author username, or None if not found or file doesn't exist
    """
    plan_file = impl_dir / "plan.md"

    if not plan_file.exists():
        return None

    plan_content = plan_file.read_text(encoding="utf-8")

    # Use existing metadata parsing infrastructure
    from erk_shared.github.metadata import find_metadata_block

    block = find_metadata_block(plan_content, "plan-header")
    if block is None:
        return None

    created_by = block.data.get("created_by")
    if created_by is None or not isinstance(created_by, str):
        return None

    return created_by


def read_last_dispatched_run_id(impl_dir: Path) -> str | None:
    """Read the last dispatched run ID from .impl/plan.md metadata.

    Extracts the 'last_dispatched_run_id' field from the plan-header metadata
    block embedded in the plan.md file.

    Args:
        impl_dir: Path to .impl/ directory

    Returns:
        The workflow run ID, or None if not found, file doesn't exist, or value is null
    """
    plan_file = impl_dir / "plan.md"

    if not plan_file.exists():
        return None

    plan_content = plan_file.read_text(encoding="utf-8")

    # Use existing metadata parsing infrastructure
    from erk_shared.github.metadata import find_metadata_block

    block = find_metadata_block(plan_content, "plan-header")
    if block is None:
        return None

    run_id = block.data.get("last_dispatched_run_id")
    if run_id is None or not isinstance(run_id, str):
        return None

    return run_id


def add_worktree_creation_comment(
    github_issues,
    repo_root: Path,
    issue_number: int,
    worktree_name: str,
    branch_name: str,
) -> None:
    """Add a comment to the GitHub issue documenting worktree creation.

    Args:
        github_issues: GitHubIssues interface for posting comments
        repo_root: Repository root directory
        issue_number: GitHub issue number to comment on
        worktree_name: Name of the created worktree
        branch_name: Git branch name for the worktree

    Raises:
        RuntimeError: If gh CLI fails or issue not found
    """
    timestamp = datetime.now(UTC).isoformat()

    # Create metadata block with issue number
    block = create_worktree_creation_block(
        worktree_name=worktree_name,
        branch_name=branch_name,
        timestamp=timestamp,
        issue_number=issue_number,
    )

    # Format instructions for implementation
    instructions = f"""The worktree is ready for implementation. You can navigate to it using:
```bash
erk br co {branch_name}
```

To implement the plan:
```bash
claude --permission-mode acceptEdits "/erk:plan-implement"
```"""

    # Create comment with consistent format
    comment_body = render_erk_issue_event(
        title=f"✅ Worktree created: **{worktree_name}**",
        metadata=block,
        description=instructions,
    )

    github_issues.add_comment(repo_root, issue_number, comment_body)


def read_local_run_state(impl_dir: Path) -> LocalRunState | None:
    """Read local implementation run state from .impl/local-run-state.json.

    Args:
        impl_dir: Path to .impl/ directory

    Returns:
        LocalRunState if file exists and is valid, None otherwise
    """
    state_file = impl_dir / "local-run-state.json"

    if not state_file.exists():
        return None

    # Gracefully handle JSON parsing errors (third-party API exception handling)
    try:
        data = json.loads(state_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None

    # Validate required fields exist
    required_fields = ["last_event", "timestamp", "user"]
    missing_fields = [f for f in required_fields if f not in data]

    if missing_fields:
        return None

    # Validate last_event value
    if data["last_event"] not in {"started", "ended"}:
        return None

    return LocalRunState(
        last_event=data["last_event"],
        timestamp=data["timestamp"],
        session_id=data.get("session_id"),
        user=data["user"],
    )


def write_local_run_state(
    impl_dir: Path,
    last_event: str,
    timestamp: str,
    user: str,
    session_id: str | None = None,
) -> None:
    """Write local implementation run state to .impl/local-run-state.json.

    Args:
        impl_dir: Path to .impl/ directory
        last_event: Event type ("started" or "ended")
        timestamp: ISO 8601 UTC timestamp
        user: User who ran the implementation
        session_id: Optional Claude Code session ID

    Raises:
        FileNotFoundError: If impl_dir doesn't exist
        ValueError: If last_event is not "started" or "ended"
    """
    if not impl_dir.exists():
        msg = f"Implementation directory does not exist: {impl_dir}"
        raise FileNotFoundError(msg)

    if last_event not in {"started", "ended"}:
        msg = f"Invalid last_event '{last_event}'. Must be 'started' or 'ended'"
        raise ValueError(msg)

    state_file = impl_dir / "local-run-state.json"

    data = {
        "last_event": last_event,
        "timestamp": timestamp,
        "session_id": session_id,
        "user": user,
    }

    state_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
