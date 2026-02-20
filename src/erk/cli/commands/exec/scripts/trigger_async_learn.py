"""Trigger async learn workflow for a plan issue.

This exec command orchestrates the full local learn pipeline:
1. Discovers session sources for the plan
2. Preprocesses sessions locally
3. Fetches PR review comments if applicable
4. Uploads materials to a gist
5. Triggers the learn.yml GitHub Actions workflow with the gist URL

Usage:
    erk exec trigger-async-learn <plan_id>

Output:
    JSON with success status and workflow information:
    {"success": true, "plan_id": "123", "workflow_triggered": true,
     "run_id": "12345678", "workflow_url": "https://...", "gist_url": "https://..."}

    On error:
    {"success": false, "error": "message"}

Examples:
    $ erk exec trigger-async-learn 5753
    {"success": true, "plan_id": "5753", "workflow_triggered": true,
     "run_id": "12345678", "workflow_url": "https://github.com/owner/repo/actions/runs/12345678",
     "gist_url": "https://gist.github.com/user/abc123..."}
"""

import json
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import NoReturn

import click

from erk.cli.commands.exec.scripts.download_remote_session import normalize_gist_url
from erk.cli.commands.exec.scripts.get_learn_sessions import _discover_sessions
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
from erk.cli.commands.exec.scripts.upload_learn_materials import (
    combine_learn_material_files,
)
from erk_shared.context.helpers import (
    require_claude_installation,
    require_cwd,
    require_git,
    require_github,
    require_issues,
    require_plan_backend,
    require_repo_root,
)
from erk_shared.gateway.github.abc import GistCreateError
from erk_shared.gateway.github.checks import GitHubChecks
from erk_shared.gateway.github.parsing import construct_workflow_run_url
from erk_shared.gateway.github.types import PRNotFound
from erk_shared.non_ideal_state import GitHubAPIFailed
from erk_shared.plan_store.types import PlanNotFound

LEARN_WORKFLOW = "learn.yml"


@dataclass(frozen=True)
class TriggerSuccess:
    """Success response for trigger-async-learn command when workflow is triggered."""

    success: bool
    plan_id: str
    workflow_triggered: bool
    run_id: str
    workflow_url: str
    gist_url: str


@dataclass(frozen=True)
class PreprocessSuccess:
    """Success response for trigger-async-learn command when --skip-workflow is used."""

    success: bool
    plan_id: str
    workflow_triggered: bool
    gist_url: str


@dataclass(frozen=True)
class TriggerError:
    """Error response for trigger-async-learn command."""

    success: bool
    error: str


def _output_success(plan_id: str, run_id: str, workflow_url: str, gist_url: str) -> None:
    """Output success JSON and exit."""
    result = TriggerSuccess(
        success=True,
        plan_id=plan_id,
        workflow_triggered=True,
        run_id=run_id,
        workflow_url=workflow_url,
        gist_url=gist_url,
    )
    click.echo(json.dumps(asdict(result)))
    raise SystemExit(0)


def _output_preprocess_success(plan_id: str, gist_url: str) -> None:
    """Output preprocess-only success JSON and exit."""
    result = PreprocessSuccess(
        success=True,
        plan_id=plan_id,
        workflow_triggered=False,
        gist_url=gist_url,
    )
    click.echo(json.dumps(asdict(result)))
    raise SystemExit(0)


def _output_error(message: str) -> NoReturn:
    """Output error JSON and exit."""
    result = TriggerError(success=False, error=message)
    click.echo(json.dumps(asdict(result)))
    raise SystemExit(1)


def _preprocess_session_direct(
    *,
    session_path: Path,
    max_tokens: int,
    output_dir: Path,
    prefix: str,
) -> list[Path]:
    """Preprocess a session log file directly using Python functions.

    Replicates the orchestration from the preprocess-session CLI command:
    process log file, apply filters, discover agent logs, generate XML,
    and write output files.

    Args:
        session_path: Path to the session JSONL file
        max_tokens: Maximum tokens per output chunk
        output_dir: Directory to write output files
        prefix: Prefix for output filenames

    Returns:
        List of output file paths (may be empty if session was filtered)
    """
    session_id = session_path.stem

    # Process main session log
    entries, _total_entries, _skipped_entries = process_log_file(
        session_path, session_id=session_id, enable_filtering=True
    )

    # Apply filtering
    if is_empty_session(entries):
        return []
    if is_warmup_session(entries):
        return []

    entries = deduplicate_documentation_blocks(entries)
    entries = truncate_tool_parameters(entries)
    entries = deduplicate_assistant_messages(entries)

    # Track original bytes for compression metrics
    original_bytes = len(session_path.read_text(encoding="utf-8"))

    # Collect all entries with their source labels
    all_entries_with_labels: list[tuple[list[dict], str | None]] = [(entries, None)]

    # Discover and process agent logs
    agent_logs = discover_agent_logs(session_path, session_id)
    for agent_log in agent_logs:
        agent_entries, _agent_total, _agent_skipped = process_log_file(
            agent_log, session_id=session_id, enable_filtering=True
        )

        if is_empty_session(agent_entries):
            continue
        if is_warmup_session(agent_entries):
            continue

        agent_entries = deduplicate_documentation_blocks(agent_entries)
        agent_entries = truncate_tool_parameters(agent_entries)
        agent_entries = deduplicate_assistant_messages(agent_entries)

        original_bytes += len(agent_log.read_text(encoding="utf-8"))
        source_label = f"agent-{agent_log.stem.replace('agent-', '')}"
        all_entries_with_labels.append((agent_entries, source_label))

    # Generate XML sections with splitting
    xml_sections: list[str] = []
    for session_entries, source_label in all_entries_with_labels:
        chunks = split_entries_to_chunks(
            session_entries,
            max_tokens=max_tokens,
            source_label=source_label,
            enable_pruning=True,
        )
        xml_sections.extend(chunks)

    # Log compression metrics
    compressed_size = sum(len(section) for section in xml_sections)
    if original_bytes > 0:
        reduction_pct = ((original_bytes - compressed_size) / original_bytes) * 100
        stats_msg = (
            f"📉 Token reduction: {reduction_pct:.1f}% "
            f"({original_bytes:,} → {compressed_size:,} chars)"
        )
        click.echo(stats_msg, err=True)

    # Write output files
    output_dir.mkdir(parents=True, exist_ok=True)
    filename_session_id = session_path.stem
    output_paths: list[Path] = []

    if len(xml_sections) > 1:
        for i, section in enumerate(xml_sections, start=1):
            file_path = output_dir / f"{prefix}-{filename_session_id}-part{i}.xml"
            file_path.write_text(section, encoding="utf-8")
            output_paths.append(file_path)
    else:
        file_path = output_dir / f"{prefix}-{filename_session_id}.xml"
        file_path.write_text("\n\n".join(xml_sections), encoding="utf-8")
        output_paths.append(file_path)

    return output_paths


def _download_remote_session_for_learn(
    *,
    gist_url: str,
    session_id: str,
    output_dir: Path,
) -> Path | None:
    """Download a remote session JSONL for learn preprocessing.

    Downloads from a gist URL and saves to output_dir with the session_id
    as the filename stem (required by the preprocessing pipeline).

    Args:
        gist_url: Gist URL (webpage or raw) to download from.
        session_id: Session ID used as the output filename stem.
        output_dir: Directory to save the downloaded JSONL file.

    Returns:
        Path to the downloaded file on success, None on failure.
    """
    normalized_url = normalize_gist_url(gist_url)
    try:
        with urllib.request.urlopen(normalized_url) as response:
            content = response.read()
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{session_id}.jsonl"
        output_path.write_bytes(content)
        return output_path
    except urllib.error.URLError as e:
        message = click.style(f"   ⚠️  Failed to download remote session: {e}", fg="yellow")
        click.echo(message, err=True)
        return None


def _get_pr_for_plan_direct(
    *,
    plan_backend,
    github,
    git,
    repo_root: Path,
    plan_id: str,
) -> dict[str, object] | None:
    """Look up the PR associated with a plan using PlanBackend.

    Args:
        plan_backend: PlanBackend for metadata access
        github: GitHub gateway for PR lookups
        git: Git gateway (for branch inference fallback)
        repo_root: Repository root path
        plan_id: Plan identifier

    Returns:
        Dict with pr_number and pr details on success, None on failure
    """
    # Draft-PR: plan_id IS the PR number — look up directly
    if plan_backend.get_provider_name() == "github-draft-pr":
        pr_result = github.get_pr(repo_root, int(plan_id))
        if isinstance(pr_result, PRNotFound):
            return None
        return {
            "success": True,
            "pr_number": pr_result.number,
            "pr": {
                "number": pr_result.number,
                "title": pr_result.title,
                "state": pr_result.state,
                "url": pr_result.url,
                "head_ref_name": pr_result.head_ref_name,
                "base_ref_name": pr_result.base_ref_name,
            },
        }

    branch_name_field = plan_backend.get_metadata_field(repo_root, plan_id, "branch_name")
    if isinstance(branch_name_field, PlanNotFound):
        return None

    branch_name = branch_name_field
    if branch_name is None:
        # Fallback: infer from current git branch
        current_branch = git.branch.get_current_branch(repo_root)
        if current_branch is not None and current_branch.startswith(f"P{plan_id}-"):
            branch_name = current_branch
    if branch_name is None:
        return None

    pr_result = github.get_pr_for_branch(repo_root, branch_name)
    if isinstance(pr_result, PRNotFound):
        return None

    return {
        "success": True,
        "pr_number": pr_result.number,
        "pr": {
            "number": pr_result.number,
            "title": pr_result.title,
            "state": pr_result.state,
            "url": pr_result.url,
            "head_ref_name": pr_result.head_ref_name,
            "base_ref_name": pr_result.base_ref_name,
        },
    }


@click.command(name="trigger-async-learn")
@click.argument("plan_id", type=str)
@click.option(
    "--skip-workflow",
    is_flag=True,
    help="Run preprocessing and upload gist, but skip triggering the learn.yml workflow.",
)
@click.pass_context
def trigger_async_learn(ctx: click.Context, plan_id: str, *, skip_workflow: bool) -> None:
    """Trigger async learn workflow for a plan.

    PLAN_ID is the plan identifier (e.g., issue number) to learn from.

    Orchestrates the full local learn pipeline:
    1. Gets session sources for the plan
    2. Preprocesses sessions locally
    3. Fetches PR review comments if applicable
    4. Uploads materials to a gist
    5. Triggers the learn.yml workflow with the gist URL (unless --skip-workflow)
    """
    # Get required dependencies from context
    if ctx.obj is None:
        _output_error("Context not initialized")
        return

    repo_info = ctx.obj.repo_info
    if repo_info is None:
        _output_error("Not in a GitHub repository")
        return

    repo_root = require_repo_root(ctx)
    cwd = require_cwd(ctx)
    git = require_git(ctx)
    github = require_github(ctx)
    github_issues = require_issues(ctx)
    claude_installation = require_claude_installation(ctx)
    plan_backend = require_plan_backend(ctx)

    # Step 1: Discover session sources for the plan (direct function call)
    message = click.style("📋 Discovering sessions...", fg="cyan")
    click.echo(message, err=True)

    current_branch = git.branch.get_current_branch(repo_root)
    sessions = _discover_sessions(
        plan_backend=plan_backend,
        claude_installation=claude_installation,
        repo_root=repo_root,
        cwd=cwd,
        plan_id=plan_id,
        branch_name=current_branch,
    )

    if not sessions.get("success"):
        _output_error(f"Failed to get session sources: {sessions.get('error', 'unknown error')}")
        return

    session_sources = sessions["session_sources"]

    # Diagnostic: log session source summary
    planning_session_id = sessions.get("planning_session_id")
    planning_count = 0
    for s in session_sources:
        if not isinstance(s, dict):
            continue
        if s.get("session_id") == planning_session_id:
            planning_count += 1

    summary = click.style(
        f"   Found {len(session_sources)} session(s): {planning_count} planning, "
        f"{len(session_sources) - planning_count} impl",
        dim=True,
    )
    click.echo(summary, err=True)

    for source_item in session_sources:
        if not isinstance(source_item, dict):
            continue
        sid = source_item.get("session_id", "unknown")
        source_type = source_item.get("source_type", "unknown")
        if sid == planning_session_id:
            label = "planning"
            emoji = "📝"
        else:
            label = "impl"
            emoji = "🔧"
        session_line = click.style(f"     {emoji} {label}: {sid} ({source_type})", dim=True)
        click.echo(session_line, err=True)

    # Step 2: Create learn materials directory
    learn_dir = repo_root / ".erk" / "scratch" / f"learn-{plan_id}"
    learn_dir.mkdir(parents=True, exist_ok=True)
    dirname = learn_dir.name
    message = click.style(f"📂 Created {dirname}", fg="cyan")
    click.echo(message, err=True)

    # Step 3: Preprocess each session source (local and remote)
    for source_item in session_sources:
        if not isinstance(source_item, dict):
            continue

        source_type = source_item.get("source_type")
        session_id = source_item.get("session_id")
        planning_session_id = sessions["planning_session_id"]
        prefix = "planning" if session_id == planning_session_id else "impl"

        if source_type == "local":
            session_path_str = source_item.get("path")
            if not isinstance(session_path_str, str):
                continue

            message = click.style(f"🔄 Preprocessing {prefix} session...", fg="cyan")
            click.echo(message, err=True)

            session_path = Path(session_path_str)
            if not session_path.exists():
                _output_error(f"Preprocessing {prefix} session failed: Session file not found")

        elif source_type == "remote":
            gist_url = source_item.get("gist_url")
            if not isinstance(gist_url, str) or not isinstance(session_id, str):
                continue

            message = click.style(f"⬇️  Downloading remote {prefix} session...", fg="cyan")
            click.echo(message, err=True)

            downloaded_path = _download_remote_session_for_learn(
                gist_url=gist_url,
                session_id=session_id,
                output_dir=learn_dir / "remote-downloads",
            )
            if downloaded_path is None:
                continue

            message = click.style(f"🔄 Preprocessing remote {prefix} session...", fg="cyan")
            click.echo(message, err=True)
            session_path = downloaded_path

        else:
            continue

        output_paths = _preprocess_session_direct(
            session_path=session_path,
            max_tokens=20000,
            output_dir=learn_dir,
            prefix=prefix,
        )

        if not output_paths:
            message = click.style("   ⏭️  Session filtered (empty/warmup), skipping", dim=True)
            click.echo(message, err=True)
            continue

        # Diagnostic: log output file sizes
        for output_file in output_paths:
            if output_file.exists():
                char_count = len(output_file.read_text(encoding="utf-8"))
                message = click.style(f"   📄 {output_file.name} ({char_count:,} chars)", dim=True)
                click.echo(message, err=True)

    # Step 4: Get PR for plan (if exists) and fetch review comments
    message = click.style("🔍 Getting PR for plan...", fg="cyan")
    click.echo(message, err=True)

    pr_result = _get_pr_for_plan_direct(
        plan_backend=plan_backend,
        github=github,
        git=git,
        repo_root=repo_root,
        plan_id=plan_id,
    )

    if pr_result is None:
        warning = click.style(
            "   ⏭️  Getting PR for plan failed, skipping: No PR found",
            dim=True,
        )
        click.echo(warning, err=True)
    elif pr_result.get("success") and pr_result.get("pr_number"):
        pr_number = pr_result["pr_number"]
        assert isinstance(pr_number, int)

        # Fetch review comments (direct gateway call)
        message = click.style("💬 Fetching review comments...", fg="cyan")
        click.echo(message, err=True)

        threads = github.get_pr_review_threads(repo_root, pr_number, include_resolved=True)
        valid_threads = [t for t in threads if t.id]

        review_data = {
            "success": True,
            "pr_number": pr_number,
            "threads": [
                {
                    "id": t.id,
                    "path": t.path,
                    "line": t.line,
                    "is_outdated": t.is_outdated,
                    "comments": [
                        {
                            "author": c.author,
                            "body": c.body,
                            "created_at": c.created_at,
                        }
                        for c in t.comments
                    ],
                }
                for t in valid_threads
            ],
        }

        review_comments_file = learn_dir / "pr-review-comments.json"
        review_comments_file.write_text(json.dumps(review_data, indent=2), encoding="utf-8")
        message = click.style(f"   📄 Wrote {review_comments_file.name}", dim=True)
        click.echo(message, err=True)

        # Fetch discussion comments (direct gateway call)
        message = click.style("💬 Fetching discussion comments...", fg="cyan")
        click.echo(message, err=True)

        comments_result = GitHubChecks.issue_comments(github_issues, repo_root, pr_number)

        if isinstance(comments_result, GitHubAPIFailed):
            discussion_data: dict[str, object] = {
                "success": False,
                "error": comments_result.message,
            }
        else:
            discussion_data = {
                "success": True,
                "pr_number": pr_number,
                "comments": [
                    {
                        "id": c.id,
                        "author": c.author,
                        "body": c.body,
                        "url": c.url,
                    }
                    for c in comments_result
                ],
            }

        discussion_comments_file = learn_dir / "pr-discussion-comments.json"
        discussion_comments_file.write_text(json.dumps(discussion_data, indent=2), encoding="utf-8")
        message = click.style(f"   📄 Wrote {discussion_comments_file.name}", dim=True)
        click.echo(message, err=True)

    # Step 5: Upload learn materials to gist (direct function calls)
    message = click.style("☁️ Uploading to gist...", fg="cyan")
    click.echo(message, err=True)

    learn_files = sorted(f for f in learn_dir.iterdir() if f.is_file())
    if not learn_files:
        _output_error("No files found in learn directory")
        return

    combined_content = combine_learn_material_files(learn_dir)

    gist_result = github.create_gist(
        filename=f"learn-materials-plan-{plan_id}.txt",
        content=combined_content,
        description=f"Learn materials for plan {plan_id}",
        public=False,
    )

    if isinstance(gist_result, GistCreateError):
        _output_error(f"Failed to upload learn materials: {gist_result.message}")
        return

    gist_url = gist_result.gist_url
    file_count = len(learn_files)
    total_size = len(combined_content)

    url_styled = click.style(f"{gist_url}", fg="blue", underline=True)
    stats_styled = click.style(f"({file_count} file(s), {total_size:,} chars)", dim=True)
    click.echo(f"   🔗 {url_styled} {stats_styled}", err=True)

    # Step 6: Trigger the learn workflow with gist_url (unless --skip-workflow)
    if skip_workflow:
        _output_preprocess_success(plan_id, gist_url)
        return

    workflow_inputs: dict[str, str] = {
        "plan_id": plan_id,
        "gist_url": str(gist_url),
    }

    try:
        run_id = github.trigger_workflow(
            repo_root=repo_root,
            workflow=LEARN_WORKFLOW,
            inputs=workflow_inputs,
            ref="master",
        )
    except RuntimeError as e:
        _output_error(f"Failed to trigger workflow: {e}")
        return

    # Construct the workflow URL
    workflow_url = construct_workflow_run_url(
        owner=repo_info.owner,
        repo=repo_info.name,
        run_id=run_id,
    )

    _output_success(plan_id, run_id, workflow_url, gist_url)
