"""Upload current implementation session for async learn.

Reads plan reference from .erk/impl-context/, captures session info, and delegates
to push-session for preprocessed XML upload with branch accumulation.

Usage:
    erk exec upload-impl-session --session-id <id>

Output:
    JSON with upload result:
    {"uploaded": true, "plan_id": 2521}
    {"uploaded": false, "reason": "no_plan_tracking"}
    {"uploaded": false, "reason": "no_session_found"}

Exit Codes:
    0: Always (non-critical operation, graceful degradation)

Examples:
    $ erk exec upload-impl-session --session-id abc-123
    {"uploaded": true, "plan_id": 2521}
"""

import json
import subprocess
from pathlib import Path

import click

from erk.cli.commands.exec.scripts.capture_session_info import capture_session
from erk_shared.context.helpers import (
    require_claude_installation,
    require_cwd,
    require_git,
    require_repo_root,
)
from erk_shared.impl_folder import read_plan_ref, resolve_impl_dir


def _output_not_uploaded(reason: str) -> None:
    """Output a not-uploaded result and return."""
    click.echo(json.dumps({"uploaded": False, "reason": reason}))


@click.command(name="upload-impl-session")
@click.option(
    "--session-id",
    required=True,
    help="Claude session ID to upload",
)
@click.pass_context
def upload_impl_session(ctx: click.Context, session_id: str) -> None:
    """Upload current implementation session for async learn.

    Reads plan reference from .erk/impl-context/ to get the plan_id, captures
    session info from Claude installation, and delegates to push-session
    for preprocessed XML upload with branch accumulation.

    Always exits with code 0 (non-critical operation).
    """
    cwd = require_cwd(ctx)
    git = require_git(ctx)
    branch_name = git.branch.get_current_branch(cwd)

    # Read plan reference from resolved impl directory
    impl_dir = resolve_impl_dir(cwd, branch_name=branch_name)
    if impl_dir is None:
        _output_not_uploaded("no_impl_folder")
        return

    plan_ref = read_plan_ref(impl_dir)
    if plan_ref is None:
        _output_not_uploaded("no_plan_tracking")
        return

    if not plan_ref.plan_id.isdigit():
        _output_not_uploaded("non_numeric_plan_id")
        return

    plan_id = int(plan_ref.plan_id)

    # Capture session info
    installation = require_claude_installation(ctx)

    session_result = capture_session(cwd, installation)
    if session_result is None:
        _output_not_uploaded("no_session_found")
        return

    _session_id_from_file, session_file_str = session_result
    session_file = Path(session_file_str)
    if not session_file.exists():
        _output_not_uploaded("session_file_missing")
        return

    # Delegate to push-session for preprocessed upload with accumulation
    repo_root = require_repo_root(ctx)
    result = subprocess.run(
        [
            "erk",
            "exec",
            "push-session",
            "--session-file",
            str(session_file),
            "--session-id",
            session_id,
            "--stage",
            "impl",
            "--source",
            "local",
            "--plan-id",
            str(plan_id),
        ],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )

    if result.returncode == 0 and result.stdout.strip():
        push_output = json.loads(result.stdout.strip())
        if push_output.get("uploaded"):
            click.echo(json.dumps({"uploaded": True, "plan_id": plan_id}))
            return

    # push-session failed or returned not-uploaded — report gracefully
    click.echo(json.dumps({"uploaded": False, "reason": "push_session_failed"}))
