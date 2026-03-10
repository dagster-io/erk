"""Learn plan creation for the land command.

Handles creating erk-learn plans when a PR is landed.
Extracted to avoid circular imports between land_cmd and land_pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import click
from rich.console import Console
from rich.padding import Padding
from rich.table import Table
from rich.text import Text

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
from erk.core.branch_slug_generator import generate_branch_slug
from erk.core.context import ErkContext
from erk_shared.learn.extraction.session_schema import (
    compute_session_provenance,
)
from erk_shared.naming import generate_planned_pr_branch_name
from erk_shared.output.output import user_output
from erk_shared.plan_store.create_plan_draft_pr import create_plan_draft_pr
from erk_shared.plan_store.planned_pr_lifecycle import IMPL_CONTEXT_DIR
from erk_shared.plan_store.types import PlanNotFound
from erk_shared.sessions.discovery import SessionsForPlan, get_readable_sessions
from erk_shared.sessions.manifest import read_session_manifest

if TYPE_CHECKING:
    from pathlib import Path

    from erk.cli.commands.land_pipeline import LandState
    from erk_shared.gateway.git.abc import Git


def _fetch_xmls_from_context_branch(
    git: Git,
    *,
    repo_root: Path,
    pr_id: str,
) -> tuple[dict[str, str], dict | None]:
    """Fetch preprocessed session XMLs from the planned-pr-context branch.

    Remote implementations upload session data to planned-pr-context/{pr_id} branches.
    This function fetches the manifest and downloads each XML file, returning
    them as a dict suitable for embedding in a learn plan PR.

    Args:
        git: Git gateway instance.
        repo_root: Repository root path.
        pr_id: PR identifier string.

    Returns:
        Tuple of (xml_files, manifest). xml_files is empty and manifest is None
        if branch not found or manifest is missing.
    """
    session_branch = f"planned-pr-context/{pr_id}"

    if not git.branch.branch_exists_on_remote(repo_root, "origin", session_branch):
        return {}, None

    git.remote.fetch_branch(repo_root, "origin", session_branch)

    # Read manifest
    manifest = read_session_manifest(git, repo_root=repo_root, session_branch=session_branch)
    if manifest is None:
        return {}, None

    # Download each XML file referenced in manifest
    xml_files: dict[str, str] = {}
    sessions = manifest.get("sessions", [])
    for session_entry in sessions:
        for filename in session_entry.get("files", []):
            file_raw = git.commit.read_file_from_ref(
                repo_root,
                ref=f"origin/{session_branch}",
                file_path=f".erk/sessions/{filename}",
            )
            if file_raw is not None:
                xml_path = f"{IMPL_CONTEXT_DIR}/sessions/{filename}"
                xml_files[xml_path] = file_raw.decode("utf-8")

    return xml_files, manifest


def _extract_session_ids_from_manifest(manifest: dict) -> list[str]:
    """Extract all session IDs from a manifest."""
    return [s.get("session_id", "") for s in manifest.get("sessions", []) if s.get("session_id")]


def _log_session_summary_from_manifest(
    manifest: dict,
    *,
    xml_files: dict[str, str],
    pr_id: str,
) -> None:
    """Print session summary from manifest metadata with per-file sizes."""
    sessions = manifest.get("sessions", [])
    if not sessions:
        return

    table = Table(
        show_header=True,
        show_edge=False,
        box=None,
        padding=(0, 1),
        pad_edge=False,
    )
    table.add_column("Stage", no_wrap=True)
    table.add_column("Session", no_wrap=True)
    table.add_column("Source", no_wrap=True)
    table.add_column("Turns", no_wrap=True)
    table.add_column("Duration", no_wrap=True)
    table.add_column("Size", no_wrap=True)

    for entry in sessions:
        stage = entry.get("stage", "?")
        sid = entry.get("session_id", "?")
        source = entry.get("source", "?")
        turns = str(entry.get("user_turns", "?"))
        duration = entry.get("duration_minutes")
        duration_str = f"{duration} min" if duration is not None else "-"
        raw_kb = entry.get("raw_size_kb")
        xml_kb = entry.get("xml_size_kb")
        if raw_kb is not None and xml_kb is not None:
            size_str = f"{raw_kb:,} KB -> {xml_kb:,} KB"
        else:
            size_str = "-"
        table.add_row(stage, f"{sid[:8]}...", source, turns, duration_str, size_str)

        # Show per-file sizes under each session
        for filename in entry.get("files", []):
            file_size_str = _file_size_from_xml_files(xml_files, filename)
            # Use Rich's Padding for consistent column indentation instead of hardcoded spaces
            text_content = Text(f"{filename}  ({file_size_str})", style="dim")
            padded_content = Padding(text_content, pad=(0, 0, 0, 2))
            table.add_row(padded_content, "", "", "", "", "")

    user_output(
        f"  Manifest: planned-pr-context/{pr_id}"
        f" :: .erk/sessions/manifest.json ({len(sessions)} session(s))"
    )
    console = Console(stderr=True, force_terminal=True)
    console.print(table)


def _file_size_from_xml_files(xml_files: dict[str, str], filename: str) -> str:
    """Compute human-readable size for a manifest filename from xml_files dict."""
    for path, content in xml_files.items():
        if path.endswith(filename):
            return _format_size(len(content.encode("utf-8")))
    return "?"


def _collect_session_material(
    ctx: ErkContext,
    *,
    repo_root: Path,
    pr_id: str,
) -> tuple[list[str], dict[str, str]] | None:
    """Fetch session material from planned-pr-context branch.

    Returns (all_session_ids, xml_files) or None if no material found.
    """
    # Primary path: fetch from planned-pr-context branch
    xml_files, manifest = _fetch_xmls_from_context_branch(ctx.git, repo_root=repo_root, pr_id=pr_id)

    if xml_files:
        if manifest is not None:
            _log_session_summary_from_manifest(manifest, xml_files=xml_files, pr_id=pr_id)
            all_session_ids = _extract_session_ids_from_manifest(manifest)
        else:
            all_session_ids = []
        user_output(
            click.style("\u2713", fg="green")
            + f" Fetched {len(xml_files)} file(s) from planned-pr-context/{pr_id}"
        )
        return all_session_ids, xml_files

    # Deprecated fallback: try local JSONL reprocessing
    sessions = ctx.plan_backend.find_sessions_for_plan(repo_root, pr_id)
    all_session_ids = sessions.all_session_ids()
    xml_files = _log_session_discovery(ctx, sessions=sessions, all_session_ids=all_session_ids)
    if xml_files:
        return all_session_ids, xml_files

    # Nothing found
    if not all_session_ids:
        detail = " (no sessions were tracked for this plan)"
    else:
        detail = " (sessions found but no XML could be extracted)"
    user_output(
        click.style("\u2139", fg="blue")
        + f" Skipping learn plan for #{pr_id}: no session material found"
        + detail
    )
    return None


def _create_learn_pr_core(
    ctx: ErkContext,
    *,
    repo_root: Path,
    pr_id: str,
    merged_pr_number: int,
    cwd: Path,
) -> None:
    """Core implementation for creating a learn PR.

    Collects session material, builds plan content, and creates the draft PR.
    Shared by both the merged-branch and land-pipeline callers.
    """
    # Fetch plan to check labels — skip learn plans (cycle prevention)
    plan_result = ctx.plan_store.get_plan(repo_root, pr_id)
    if isinstance(plan_result, PlanNotFound):
        return
    if "erk-learn" in plan_result.labels:
        return

    # Collect session material (context branch first, local fallback)
    result = _collect_session_material(ctx, repo_root=repo_root, pr_id=pr_id)
    if result is None:
        return
    all_session_ids, xml_files = result

    # Build learn plan body
    session_lines = [f"- `{sid}`" for sid in all_session_ids]
    session_section = "\n".join(session_lines)
    plan_content = (
        f"# Learn: {plan_result.title}\n\n"
        f"Source plan: #{pr_id}\n"
        f"Merged PR: #{merged_pr_number}\n\n"
        f"## Sessions\n\n{session_section}"
    )

    # Generate branch name with LLM slug
    learn_title = f"Learn: {plan_result.title}"
    slug = generate_branch_slug(ctx.prompt_executor, learn_title)
    branch_name = generate_planned_pr_branch_name(slug, ctx.time.now(), objective_id=None)

    # Build deterministic summary
    summary = (
        f'Learn plan for "{plan_result.title}" (PR #{merged_pr_number}). '
        f"Captures implementation insights from {len(all_session_ids)} session(s)."
    )

    # Create the learn plan as a draft PR
    pr_result = create_plan_draft_pr(
        git=ctx.git,
        github=ctx.github,
        github_issues=ctx.issues,
        branch_manager=ctx.branch_manager,
        time=ctx.time,
        repo_root=repo_root,
        cwd=cwd,
        plan_content=plan_content,
        branch_name=branch_name,
        title=learn_title,
        labels=["erk-pr", "erk-learn"],
        source_repo=None,
        objective_id=None,
        created_from_session=None,
        created_from_workflow_run_url=None,
        learned_from_issue=int(pr_id),
        summary=summary,
        extra_files=xml_files or None,
    )

    if pr_result.success:
        user_output(
            click.style("\u2713", fg="green")
            + f" Created learn plan #{pr_result.pr_number} for plan #{pr_id}"
        )
        if pr_result.pr_url:
            user_output(f"  {pr_result.pr_url}")
        else:
            user_output("  (no plan URL available)")
        _log_learn_pr_files(plan_content=plan_content, xml_files=xml_files)
    elif pr_result.error:
        user_output(
            click.style("Warning: ", fg="yellow") + f"Learn plan creation failed: {pr_result.error}"
        )


def _create_learn_pr_for_merged_branch(
    ctx: ErkContext,
    *,
    pr_id: str,
    merged_pr_number: int,
    main_repo_root: Path,
    cwd: Path,
) -> None:
    """Create learn PR for a branch merged outside erk land.

    Thin wrapper around _create_learn_pr_core that extracts params from
    the caller's context.

    Fire-and-forget: raises on error (caller should catch).
    """
    if not _should_create_learn_pr(ctx):
        return

    _create_learn_pr_core(
        ctx,
        repo_root=main_repo_root,
        pr_id=pr_id,
        merged_pr_number=merged_pr_number,
        cwd=cwd,
    )


@dataclass(frozen=True)
class SessionStats:
    """Preprocessing stats for a single session."""

    user_turns: int
    duration_minutes: int | None
    raw_size_kb: int
    xml_size_kb: int
    xml_chunks: tuple[str, ...]


def _compute_session_stats(session_path: Path, *, session_id: str) -> SessionStats | None:
    """Compute preprocessing stats for a session.

    Reads the JSONL, counts user turns, computes duration from timestamps,
    runs the preprocessing compression pipeline, and returns size stats.

    Returns None if preprocessing fails (e.g. corrupt JSONL).
    """
    provenance = compute_session_provenance(session_path)
    if provenance is None:
        return None

    user_turns = provenance.user_turns
    duration_minutes = provenance.duration_minutes

    # Compute raw size: main JSONL + agent logs (includes agent log sizes)
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
        state: LandState with pr_id and merged_pr_number populated
    """
    if state.pr_id is None or state.merged_pr_number is None:
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
    """Log the files committed to the learn plan PR with paths and sizes.

    Only shows plan.md and ref.json here — session XML files are already
    displayed per-session in the manifest summary table.
    """
    files: list[tuple[str, int]] = []

    # plan.md
    plan_bytes = len(plan_content.encode("utf-8"))
    files.append((f"{IMPL_CONTEXT_DIR}/plan.md", plan_bytes))

    # ref.json (always present, small metadata file)
    # Approximate size — exact content constructed by create_plan_draft_pr
    files.append((f"{IMPL_CONTEXT_DIR}/ref.json", 60))

    # Total includes XML files even though we don't list them individually
    xml_bytes = sum(len(content.encode("utf-8")) for content in xml_files.values())
    total_bytes = sum(size for _, size in files) + xml_bytes
    total_files = len(files) + len(xml_files)
    user_output(f"  \U0001f4e6 {total_files} file(s) committed ({_format_size(total_bytes)}):")
    for path, size in files:
        user_output(f"    {path}  ({_format_size(size)})")


def _create_learn_pr_impl(
    ctx: ErkContext,
    *,
    state: LandState,
) -> None:
    """Inner implementation for learn plan creation (raises on error).

    Thin wrapper around _create_learn_pr_core that extracts params from LandState.
    """
    pr_id = state.pr_id
    if pr_id is None:
        return

    if state.merged_pr_number is None:
        return

    if not _should_create_learn_pr(ctx):
        return

    _create_learn_pr_core(
        ctx,
        repo_root=state.main_repo_root,
        pr_id=pr_id,
        merged_pr_number=state.merged_pr_number,
        cwd=state.cwd,
    )
