"""Raw extraction plan creation orchestrator.

This module provides the main orchestrator for creating raw extraction plans
from Claude Code session logs.

Two-stage preprocessing architecture:
1. Stage 1: Deterministic mechanical reduction (session_preprocessing)
2. Stage 2: Haiku distillation (llm_distillation) - semantic judgment calls

Stage 2 is controlled by USE_LLM_DISTILLATION constant.
"""

import uuid
import warnings
from datetime import UTC, datetime
from pathlib import Path

from erk_shared.extraction.llm_distillation import distill_with_haiku
from erk_shared.extraction.session_discovery import (
    discover_sessions,
    find_project_dir,
    get_branch_context,
    get_current_session_id,
)
from erk_shared.extraction.session_preprocessing import preprocess_session
from erk_shared.extraction.session_selection import auto_select_sessions
from erk_shared.extraction.types import RawExtractionResult
from erk_shared.git.abc import Git
from erk_shared.github.issues.abc import GitHubIssues
from erk_shared.github.metadata import (
    format_plan_header_body,
    render_session_content_blocks,
)

# Enable/disable Stage 2 Haiku distillation
# When True: Stage 1 mechanical reduction + Stage 2 Haiku distillation
# When False: Stage 1 only (deterministic, no LLM cost)
USE_LLM_DISTILLATION = True

# Default issue body content for raw extraction plans
RAW_EXTRACTION_BODY = """# Raw Session Context

This issue contains raw preprocessed session data from the landed PR.

See comments below for session XML content.
"""


def create_raw_extraction_plan(
    github_issues: GitHubIssues,
    git: Git,
    repo_root: Path,
    cwd: Path,
    current_session_id: str | None = None,
    min_size: int = 1024,
) -> RawExtractionResult:
    """Create an extraction plan with raw session context.

    This is the main orchestrator function that:
    1. Discovers sessions via discover_sessions()
    2. Auto-selects via auto_select_sessions()
    3. Preprocesses via preprocess_session()
    4. Renders via render_session_content_blocks()
    5. Creates GitHub issue
    6. Posts chunked comments
    7. Returns result

    Args:
        github_issues: GitHub issues interface for creating issues and comments
        git: Git interface for branch operations
        repo_root: Path to repository root
        cwd: Current working directory (for project directory lookup)
        current_session_id: Current session ID (None to auto-detect from env)
        min_size: Minimum session size in bytes for selection

    Returns:
        RawExtractionResult with success status and created issue info
    """
    # Get current session ID if not provided
    if current_session_id is None:
        current_session_id = get_current_session_id()

    # Generate fallback session ID if still None (e.g., running outside Claude session)
    if current_session_id is None:
        current_session_id = f"extraction-{uuid.uuid4().hex[:8]}"

    # Find project directory
    project_dir = find_project_dir(cwd)
    if project_dir is None:
        return RawExtractionResult(
            success=False,
            issue_url=None,
            issue_number=None,
            chunks=0,
            sessions_processed=[],
            error="Could not find Claude Code project directory",
        )

    # Get branch context
    branch_context = get_branch_context(git, cwd)

    # Discover sessions
    sessions = discover_sessions(
        project_dir=project_dir,
        current_session_id=current_session_id,
        min_size=min_size,
        limit=20,  # Get more to have options for selection
    )

    if not sessions:
        return RawExtractionResult(
            success=False,
            issue_url=None,
            issue_number=None,
            chunks=0,
            sessions_processed=[],
            error="No sessions found in project directory",
        )

    # Auto-select sessions
    selected_sessions = auto_select_sessions(
        sessions=sessions,
        branch_context=branch_context,
        current_session_id=current_session_id,
        min_substantial_size=min_size,
    )

    if not selected_sessions:
        return RawExtractionResult(
            success=False,
            issue_url=None,
            issue_number=None,
            chunks=0,
            sessions_processed=[],
            error="No sessions selected for extraction",
        )

    # Stage 1: Preprocess sessions (deterministic mechanical reduction)
    session_xmls: list[tuple[str, str]] = []  # (session_id, xml)
    for session in selected_sessions:
        xml_content = preprocess_session(
            session_path=session.path,
            session_id=session.session_id,
            include_agents=True,
        )
        if xml_content:  # Skip empty sessions
            session_xmls.append((session.session_id, xml_content))

    if not session_xmls:
        return RawExtractionResult(
            success=False,
            issue_url=None,
            issue_number=None,
            chunks=0,
            sessions_processed=[],
            error="All selected sessions were empty after preprocessing",
        )

    # Combine session XMLs
    if len(session_xmls) == 1:
        combined_xml = session_xmls[0][1]
    else:
        # Multiple sessions - concatenate with headers
        xml_parts = []
        for session_id, xml in session_xmls:
            xml_parts.append(f"<!-- Session: {session_id} -->\n{xml}")
        combined_xml = "\n\n".join(xml_parts)

    # Stage 2: Haiku distillation (if enabled)
    if USE_LLM_DISTILLATION:
        try:
            combined_xml = distill_with_haiku(
                combined_xml,
                session_id=current_session_id,
                repo_root=repo_root,
            )
        except RuntimeError as e:
            # Distillation failed - fall back to Stage 1 output
            warnings.warn(
                f"Haiku distillation failed, using Stage 1 output: {e}",
                RuntimeWarning,
                stacklevel=2,
            )
            # Continue with mechanically reduced content

    # Render session content blocks (handles chunking)
    session_label = branch_context.current_branch or "session"
    extraction_hints = ["Session data for future documentation extraction"]
    content_blocks = render_session_content_blocks(
        content=combined_xml,
        session_label=session_label,
        extraction_hints=extraction_hints,
    )

    # Get GitHub username
    username = github_issues.get_current_username()
    if username is None:
        return RawExtractionResult(
            success=False,
            issue_url=None,
            issue_number=None,
            chunks=0,
            sessions_processed=[s for s, _ in session_xmls],
            error="Could not get GitHub username (gh CLI not authenticated?)",
        )

    # Prepare issue body with metadata
    created_at = datetime.now(UTC).isoformat()
    session_ids = [s for s, _ in session_xmls]

    formatted_body = format_plan_header_body(
        created_at=created_at,
        created_by=username,
        plan_type="extraction",
        source_plan_issues=[],  # No source issues for raw extraction
        extraction_session_ids=session_ids,
    )

    # Append the raw extraction body
    issue_body = f"{formatted_body}\n\n{RAW_EXTRACTION_BODY}"

    # Ensure labels exist
    labels = ["erk-plan", "erk-extraction"]
    try:
        github_issues.ensure_label_exists(
            repo_root=repo_root,
            label="erk-plan",
            description="Implementation plan for manual execution",
            color="0E8A16",
        )
        github_issues.ensure_label_exists(
            repo_root=repo_root,
            label="erk-extraction",
            description="Documentation extraction plan",
            color="D93F0B",
        )
    except RuntimeError as e:
        return RawExtractionResult(
            success=False,
            issue_url=None,
            issue_number=None,
            chunks=0,
            sessions_processed=session_ids,
            error=f"Failed to ensure labels exist: {e}",
        )

    # Create issue
    title = f"Raw Session Context: {session_label} [erk-extraction]"
    try:
        result = github_issues.create_issue(repo_root, title, issue_body, labels=labels)
    except RuntimeError as e:
        return RawExtractionResult(
            success=False,
            issue_url=None,
            issue_number=None,
            chunks=0,
            sessions_processed=session_ids,
            error=f"Failed to create GitHub issue: {e}",
        )

    # Post session content as comments (may be chunked)
    try:
        for block in content_blocks:
            github_issues.add_comment(repo_root, result.number, block)
    except RuntimeError as e:
        return RawExtractionResult(
            success=False,
            issue_url=result.url,
            issue_number=result.number,
            chunks=0,
            sessions_processed=session_ids,
            error=f"Issue created but failed to add session content: {e}",
        )

    return RawExtractionResult(
        success=True,
        issue_url=result.url,
        issue_number=result.number,
        chunks=len(content_blocks),
        sessions_processed=session_ids,
        error=None,
    )
