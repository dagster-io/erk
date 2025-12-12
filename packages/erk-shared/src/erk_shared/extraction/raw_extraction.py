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
from pathlib import Path

from erk_shared.extraction.claude_code_session_store import ClaudeCodeSessionStore
from erk_shared.extraction.llm_distillation import distill_with_haiku
from erk_shared.extraction.session_context import collect_session_context
from erk_shared.extraction.types import RawExtractionResult
from erk_shared.git.abc import Git
from erk_shared.github.issues.abc import GitHubIssues
from erk_shared.github.metadata import render_session_content_blocks
from erk_shared.github.plan_issues import create_plan_issue

# Enable/disable Stage 2 Haiku distillation
# When True: Stage 1 mechanical reduction + Stage 2 Haiku distillation
# When False: Stage 1 only (deterministic, no LLM cost)
USE_LLM_DISTILLATION = False

# Template for raw extraction plan body (branch_name will be interpolated)
RAW_EXTRACTION_BODY_TEMPLATE = """# Extraction Plan: {branch_name}

## Objective

Analyze session context to identify documentation gaps and create documentation improvements.

## Source

- **Branch:** {branch_name}
- **Session IDs:** See plan-header metadata
- **Session Data:** See comments below

## Implementation Steps

### Step 1: Read Session Data

Read and parse the session XML from the issue comments below. The XML contains:
- `<session>` blocks: Individual conversation sessions
- `<user>` and `<assistant>` elements: Conversation turns
- `<tool_use>` and `<tool_result>`: Tool invocations and results

### Step 2: Verify Existing Documentation

Before analyzing gaps, scan the project:
- `.erk/docs/agent/` - Existing agent docs
- `.claude/skills/` - Existing skills
- `.erk/docs/agent/glossary.md` - Terms and definitions

### Step 3: Identify Category A - Learning Gaps

Documentation that would have made the session MORE EFFICIENT. Signals:
- Repeated explanations of the same concept
- Trial-and-error before finding the right approach
- Extensive codebase exploration for core patterns
- User redirecting the agent's approach
- WebSearch/WebFetch for locally-documentable info

### Step 4: Identify Category B - Teaching Gaps

Documentation needed for what was BUILT. Signals:
- New CLI commands (need glossary + routing entries)
- New constants/labels (need glossary entries)
- New patterns established (need agent doc)
- New configuration options
- New ABC/interfaces

### Step 5: Categorize Each Finding

For each finding, determine:
- **Type:** Agent Doc (`.erk/docs/agent/`) or Skill (`.claude/skills/`)
- **Action:** New doc | Update existing | Merge into
- **Priority:** High (significant friction) | Medium | Low

### Step 6: Generate Documentation

For each suggestion:
1. Create the documentation file with draft content
2. Add routing entry to AGENTS.md if applicable
3. Update glossary.md for new terms/commands

### Step 7: Verify Changes

Run `make fast-ci` to validate all changes pass CI.

---

## Output Format

For each documentation item created, report:
- File path created/updated
- Type (Agent Doc, Skill, Glossary, Routing)
- Brief description of what was documented
"""


def get_raw_extraction_body(branch_name: str) -> str:
    """Get the raw extraction plan body with branch name interpolated.

    Args:
        branch_name: The branch name to include in the plan.

    Returns:
        The formatted extraction plan body.
    """
    return RAW_EXTRACTION_BODY_TEMPLATE.format(branch_name=branch_name)


def create_raw_extraction_plan(
    github_issues: GitHubIssues,
    git: Git,
    session_store: ClaudeCodeSessionStore,
    repo_root: Path,
    cwd: Path,
    current_session_id: str | None = None,
    min_size: int = 1024,
) -> RawExtractionResult:
    """Create an extraction plan with raw session context.

    This is the main orchestrator function that:
    1. Collects session context via collect_session_context()
    2. Optionally applies Haiku distillation
    3. Renders via render_session_content_blocks()
    4. Creates GitHub issue
    5. Posts chunked comments
    6. Returns result

    Args:
        github_issues: GitHub issues interface for creating issues and comments
        git: Git interface for branch operations
        session_store: SessionStore for session operations
        repo_root: Path to repository root
        cwd: Current working directory (for project directory lookup)
        current_session_id: Current session ID (None to auto-detect from store)
        min_size: Minimum session size in bytes for selection

    Returns:
        RawExtractionResult with success status and created issue info
    """
    # Get current session ID if not provided
    if current_session_id is None:
        current_session_id = session_store.get_current_session_id()

    # Generate fallback session ID if still None (e.g., running outside Claude session)
    if current_session_id is None:
        current_session_id = f"extraction-{uuid.uuid4().hex[:8]}"

    # Collect session context using shared helper
    session_result = collect_session_context(
        git=git,
        cwd=cwd,
        session_store=session_store,
        current_session_id=current_session_id,
        min_size=min_size,
        limit=20,
    )

    if session_result is None:
        return RawExtractionResult(
            success=False,
            issue_url=None,
            issue_number=None,
            chunks=0,
            sessions_processed=[],
            error="No sessions found or all sessions were empty after preprocessing",
        )

    combined_xml = session_result.combined_xml
    session_ids = session_result.session_ids
    branch_context = session_result.branch_context

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

    # Get raw extraction body (plan content)
    raw_body = get_raw_extraction_body(session_label)

    # Use consolidated create_plan_issue for core workflow
    plan_result = create_plan_issue(
        github_issues=github_issues,
        repo_root=repo_root,
        plan_content=raw_body,
        plan_type="extraction",
        extraction_session_ids=session_ids,
    )

    if not plan_result.success:
        return RawExtractionResult(
            success=False,
            issue_url=plan_result.issue_url,
            issue_number=plan_result.issue_number,
            chunks=0,
            sessions_processed=session_ids,
            error=plan_result.error,
        )

    # At this point, plan_result.success is True so issue_number is guaranteed to be set
    issue_number = plan_result.issue_number
    if issue_number is None:
        # Defensive check - should never happen when success=True
        return RawExtractionResult(
            success=False,
            issue_url=plan_result.issue_url,
            issue_number=None,
            chunks=0,
            sessions_processed=session_ids,
            error="Internal error: issue_number is None after successful creation",
        )

    # Add session XML chunks as additional comments (raw extraction specific)
    try:
        for block in content_blocks:
            github_issues.add_comment(repo_root, issue_number, block)
    except RuntimeError as e:
        return RawExtractionResult(
            success=False,
            issue_url=plan_result.issue_url,
            issue_number=issue_number,
            chunks=0,
            sessions_processed=session_ids,
            error=f"Issue created but failed to add session content: {e}",
        )

    return RawExtractionResult(
        success=True,
        issue_url=plan_result.issue_url,
        issue_number=issue_number,
        chunks=len(content_blocks),
        sessions_processed=session_ids,
        error=None,
    )
