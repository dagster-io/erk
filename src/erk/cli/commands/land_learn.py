"""Learn plan creation for the land command.

Handles creating erk-learn plans when a PR is landed.
Extracted to avoid circular imports between land_cmd and land_pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import click
from rich.console import Console
from rich.table import Table

from erk.cli.commands.exec.scripts.preprocess_session import (
    deduplicate_assistant_messages,
    deduplicate_documentation_blocks,
    discover_agent_logs,
    is_empty_session,
    is_warmup_session,
    process_log_file,
    split_entries_to_chunks,
    truncate_tool_parameters,
)
from erk.core.context import ErkContext
from erk_shared.learn.extraction.session_schema import (
    iter_jsonl_entries,
    parse_session_timestamp,
)
from erk_shared.output.output import user_output
from erk_shared.plan_store.create_plan_draft_pr import create_plan_draft_pr
from erk_shared.plan_store.planned_pr_lifecycle import IMPL_CONTEXT_DIR
from erk_shared.plan_store.types import PlanNotFound
from erk_shared.sessions.discovery import SessionsForPlan, get_readable_sessions

if TYPE_CHECKING:
    from pathlib import Path

    from erk.cli.commands.land_pipeline import LandState


@dataclass(frozen=True)
class SessionStats:
    """Preprocessing stats for a single session."""

    user_turns: int
    duration_minutes: int | None
    raw_size_kb: int
    xml_size_kb: int
    xml_chunks: tuple[str, ...]


def _has_user_text(message_content: str | list) -> bool:
    """Check if message content contains non-empty user text."""
    if isinstance(message_content, list):
        return any(
            isinstance(block, dict)
            and block.get("type") == "text"
            and block.get("text", "").strip()
            for block in message_content
        )
    if isinstance(message_content, str):
        return bool(message_content.strip())
    return False


def _compute_session_stats(session_path: Path, *, session_id: str) -> SessionStats | None:
    """Compute preprocessing stats for a session.

    Reads the JSONL, counts user turns, computes duration from timestamps,
    runs the preprocessing compression pipeline, and returns size stats.

    Returns None if preprocessing fails (e.g. corrupt JSONL).
    """
    if not session_path.exists():
        return None

    # Count user turns and compute duration from raw JSONL
    content = session_path.read_text(encoding="utf-8")
    timestamps: list[float] = []
    user_turns = 0
    for entry in iter_jsonl_entries(content):
        ts = parse_session_timestamp(entry.get("timestamp"))
        if ts is not None:
            timestamps.append(ts)
        if entry.get("type") == "user":
            message_content = entry.get("message", {}).get("content", "")
            if _has_user_text(message_content):
                user_turns += 1

    duration_minutes: int | None = None
    if len(timestamps) >= 2:
        duration_seconds = max(timestamps) - min(timestamps)
        duration_minutes = round(duration_seconds / 60)

    # Compute raw size: main JSONL + agent logs
    raw_bytes = session_path.stat().st_size
    agent_logs = discover_agent_logs(session_path, session_id)
    for agent_log in agent_logs:
        raw_bytes += agent_log.stat().st_size

    # Run preprocessing pipeline to get XML sections
    entries, _total, _skipped = process_log_file(
        session_path, session_id=session_id, enable_filtering=True
    )

    if is_empty_session(entries) or is_warmup_session(entries):
        # Still report stats but XML will be minimal
        return SessionStats(
            user_turns=user_turns,
            duration_minutes=duration_minutes,
            raw_size_kb=raw_bytes // 1024,
            xml_size_kb=0,
            xml_chunks=(),
        )

    entries = deduplicate_documentation_blocks(entries)
    entries = truncate_tool_parameters(entries)
    entries = deduplicate_assistant_messages(entries)

    # Process agent logs through same pipeline
    all_entries_with_labels: list[tuple[list[dict], str | None]] = [(entries, None)]
    for agent_log in agent_logs:
        agent_entries, _at, _as = process_log_file(
            agent_log, session_id=session_id, enable_filtering=True
        )
        if is_empty_session(agent_entries) or is_warmup_session(agent_entries):
            continue
        agent_entries = deduplicate_documentation_blocks(agent_entries)
        agent_entries = truncate_tool_parameters(agent_entries)
        agent_entries = deduplicate_assistant_messages(agent_entries)
        source_label = f"agent-{agent_log.stem.replace('agent-', '')}"
        all_entries_with_labels.append((agent_entries, source_label))

    all_chunks: list[str] = []
    for session_entries, source_label in all_entries_with_labels:
        chunks = split_entries_to_chunks(
            session_entries,
            max_tokens=200_000,
            source_label=source_label,
            enable_pruning=True,
        )
        all_chunks.extend(chunks)

    xml_bytes = sum(len(chunk.encode("utf-8")) for chunk in all_chunks)

    return SessionStats(
        user_turns=user_turns,
        duration_minutes=duration_minutes,
        raw_size_kb=raw_bytes // 1024,
        xml_size_kb=xml_bytes // 1024,
        xml_chunks=tuple(all_chunks),
    )


def _should_create_learn_pr(ctx: ErkContext) -> bool:
    """Check config hierarchy to determine if learn plan should be created on land.

    Checks local_config first (repo or local override), falls back to global_config.
    """
    if ctx.local_config.prompt_learn_on_land is not None:
        return ctx.local_config.prompt_learn_on_land
    if ctx.global_config is not None:
        return ctx.global_config.prompt_learn_on_land
    return True


def _create_learn_pr_with_sessions(
    ctx: ErkContext,
    *,
    state: LandState,
) -> None:
    """Create a learn plan as a draft PR with session info for the landed plan.

    This is a fire-and-forget operation that never blocks landing.
    Creates a draft PR with erk-learn label so the replan flow can pick it up.

    Args:
        ctx: ErkContext
        state: LandState with plan_id and merged_pr_number populated
    """
    if state.plan_id is None or state.merged_pr_number is None:
        return

    try:
        _create_learn_pr_impl(ctx, state=state)
    except Exception as exc:
        user_output(click.style("Warning: ", fg="yellow") + f"Could not create learn plan: {exc}")


def _session_type_prefix(
    sid: str,
    *,
    planning_ids: set[str],
    impl_ids: set[str],
    learn_ids: set[str],
) -> str:
    """Map a session ID to its type prefix string."""
    if sid in planning_ids:
        return "planning"
    if sid in impl_ids:
        return "impl"
    if sid in learn_ids:
        return "learn"
    return "unknown"


def _log_session_discovery(
    ctx: ErkContext,
    *,
    sessions: SessionsForPlan,
    all_session_ids: list[str],
) -> dict[str, str]:
    """Log session discovery summary with per-session type badges and sizes.

    Returns a dict mapping file paths to XML content for all readable sessions.
    Paths follow the convention: {IMPL_CONTEXT_DIR}/sessions/{type}-{session_id}.xml
    (or -part{N}.xml for multi-chunk sessions).
    """
    total = len(all_session_ids)
    if total == 0:
        user_output("  \u26a0\ufe0f  No sessions discovered for this plan")
        return {}

    n_planning = 1 if sessions.planning_session_id else 0
    n_impl = len(sessions.implementation_session_ids)
    n_learn = len(sessions.learn_session_ids)
    parts = f"{n_planning} planning, {n_impl} impl"
    if n_learn:
        parts += f", {n_learn} learn"
    user_output(f"  \U0001f4cb Discovered {total} session(s): {parts}")

    # Build readable lookup for O(1) per-session checks
    readable_map: dict[str, Path] = dict(get_readable_sessions(sessions, ctx.claude_installation))

    # Classify each session and emit a typed line
    planning_ids = {sessions.planning_session_id} if sessions.planning_session_id else set()
    impl_ids = set(sessions.implementation_session_ids)
    learn_ids = set(sessions.learn_session_ids)

    table = Table(
        show_header=False,
        show_edge=False,
        box=None,
        padding=(0, 1),
        pad_edge=False,
    )
    table.add_column("pad", width=5, no_wrap=True)
    table.add_column("emoji", no_wrap=True)
    table.add_column("label", no_wrap=True)
    table.add_column("session", no_wrap=True)
    table.add_column("detail", no_wrap=True)

    xml_files: dict[str, str] = {}

    for sid in all_session_ids:
        if sid in planning_ids:
            emoji, label = "\U0001f4dd", "planning:"
        elif sid in impl_ids:
            emoji, label = "\U0001f527", "impl:"
        elif sid in learn_ids:
            emoji, label = "\U0001f4da", "learn:"
        else:
            emoji, label = "\u2753", "unknown:"

        if sid in readable_map:
            stats = _compute_session_stats(readable_map[sid], session_id=sid)
            if stats is not None:
                duration_part = (
                    f" \u00b7 {stats.duration_minutes} min"
                    if stats.duration_minutes is not None
                    else ""
                )
                detail = (
                    f"[dim]{stats.user_turns} turns{duration_part}"
                    f"  ({stats.raw_size_kb:,} KB \u2192 {stats.xml_size_kb:,} KB)[/dim]"
                )
                # Collect XML chunks for embedding in the learn plan PR
                if stats.xml_chunks:
                    prefix = _session_type_prefix(
                        sid,
                        planning_ids=planning_ids,
                        impl_ids=impl_ids,
                        learn_ids=learn_ids,
                    )
                    if len(stats.xml_chunks) == 1:
                        path = f"{IMPL_CONTEXT_DIR}/sessions/{prefix}-{sid}.xml"
                        xml_files[path] = stats.xml_chunks[0]
                    else:
                        for n, chunk in enumerate(stats.xml_chunks, start=1):
                            path = f"{IMPL_CONTEXT_DIR}/sessions/{prefix}-{sid}-part{n}.xml"
                            xml_files[path] = chunk
            else:
                size_kb = readable_map[sid].stat().st_size // 1024
                detail = f"[dim](local, {size_kb:,} KB)[/dim]"
        else:
            detail = "[dim](not found)[/dim]"

        table.add_row("", emoji, label, f"{sid[:8]}...", detail)

    console = Console(stderr=True, force_terminal=True)
    console.print(table)

    return xml_files


def _format_size(size_bytes: int) -> str:
    """Format byte size as human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    return f"{size_bytes // 1024:,} KB"


def _log_learn_pr_files(
    *,
    plan_content: str,
    xml_files: dict[str, str],
) -> None:
    """Log the files committed to the learn plan PR with paths and sizes."""
    files: list[tuple[str, int]] = []

    # plan.md
    plan_bytes = len(plan_content.encode("utf-8"))
    files.append((f"{IMPL_CONTEXT_DIR}/plan.md", plan_bytes))

    # ref.json (always present, small metadata file)
    # Approximate size — exact content constructed by create_plan_draft_pr
    files.append((f"{IMPL_CONTEXT_DIR}/ref.json", 60))

    # Session XML files
    for path, content in sorted(xml_files.items()):
        file_bytes = len(content.encode("utf-8"))
        files.append((path, file_bytes))

    # Log file inventory
    total_bytes = sum(size for _, size in files)
    user_output(f"  \U0001f4e6 {len(files)} file(s) committed ({_format_size(total_bytes)}):")
    for path, size in files:
        user_output(f"     {path}  ({_format_size(size)})")


def _create_learn_pr_impl(
    ctx: ErkContext,
    *,
    state: LandState,
) -> None:
    """Inner implementation for learn plan creation (raises on error)."""
    plan_id = state.plan_id
    if plan_id is None:
        return

    # Check config
    if not _should_create_learn_pr(ctx):
        return

    # Fetch plan to check labels — skip learn plans (cycle prevention)
    plan_result = ctx.plan_store.get_plan(state.main_repo_root, plan_id)
    if isinstance(plan_result, PlanNotFound):
        return
    if "erk-learn" in plan_result.labels:
        return

    # Discover sessions for the plan
    sessions = ctx.plan_backend.find_sessions_for_plan(state.main_repo_root, plan_id)
    all_session_ids = sessions.all_session_ids()

    # Log session discovery summary and collect XML files for embedding
    xml_files = _log_session_discovery(ctx, sessions=sessions, all_session_ids=all_session_ids)

    # Build learn plan body
    if all_session_ids:
        session_lines = [f"- `{sid}`" for sid in all_session_ids]
    else:
        session_lines = ["- (none)"]
    session_section = "\n".join(session_lines)
    plan_content = (
        f"# Learn: {plan_result.title}\n\n"
        f"Source plan: #{plan_id}\n"
        f"Merged PR: #{state.merged_pr_number}\n\n"
        f"## Sessions\n\n{session_section}"
    )

    # Create the learn plan as a draft PR
    result = create_plan_draft_pr(
        git=ctx.git,
        github=ctx.github,
        github_issues=ctx.issues,
        branch_manager=ctx.branch_manager,
        time=ctx.time,
        repo_root=state.main_repo_root,
        cwd=state.cwd,
        plan_content=plan_content,
        title=f"Learn: {plan_result.title}",
        labels=["erk-pr", "erk-learn"],
        source_repo=None,
        objective_id=None,
        created_from_session=None,
        created_from_workflow_run_url=None,
        learned_from_issue=int(plan_id),
        summary=None,
        extra_files=xml_files or None,
    )

    if result.success:
        user_output(
            click.style("✓", fg="green")
            + f" Created learn plan #{result.plan_number} for plan #{plan_id}"
        )
        if result.plan_url:
            user_output(f"  {result.plan_url}")
        else:
            user_output("  (no plan URL available)")
        _log_learn_pr_files(plan_content=plan_content, xml_files=xml_files)
    elif result.error:
        user_output(
            click.style("Warning: ", fg="yellow") + f"Learn plan creation failed: {result.error}"
        )
