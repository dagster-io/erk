"""Command to implement features from GitHub issues or plan files.

This unified command provides two modes:
- GitHub issue mode: erk implement 123 or erk implement <URL>
- Plan file mode: erk implement path/to/plan.md

Both modes create a worktree and invoke Claude for implementation.
"""

import re
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

import click
from erk_shared.github.issue_link_branches import DevelopmentBranch
from erk_shared.impl_folder import create_impl_folder, save_issue_reference
from erk_shared.naming import (
    derive_branch_name_from_title,
    ensure_unique_worktree_name_with_date,
    format_branch_timestamp_suffix,
    sanitize_worktree_name,
    strip_plan_from_filename,
)
from erk_shared.output.output import user_output
from erk_shared.plan_store.types import PlanState

from erk.cli.activation import render_activation_script
from erk.cli.commands.completions import complete_plan_files
from erk.cli.commands.wt.create_cmd import add_worktree, run_post_worktree_setup
from erk.cli.config import LoadedConfig
from erk.cli.constants import USE_GITHUB_NATIVE_BRANCH_LINKING
from erk.cli.core import discover_repo_context, worktree_path_for
from erk.core.claude_executor import ClaudeExecutor
from erk.core.context import ErkContext
from erk.core.repo_discovery import ensure_erk_metadata_dir


def _build_claude_command(slash_command: str, dangerous: bool) -> str:
    """Build a Claude CLI invocation for interactive mode.

    Args:
        slash_command: The slash command to execute (e.g., "/erk:plan-implement")
        dangerous: Whether to skip permission prompts

    Returns:
        Complete Claude CLI command string
    """
    cmd = "claude --permission-mode acceptEdits"
    if dangerous:
        cmd += " --dangerously-skip-permissions"
    cmd += f' "{slash_command}"'
    return cmd


def _validate_flags(submit: bool, no_interactive: bool, script: bool) -> None:
    """Validate flag combinations and raise ClickException if invalid.

    Args:
        submit: Whether to auto-submit PR after implementation
        no_interactive: Whether to execute non-interactively
        script: Whether to output shell integration script

    Raises:
        click.ClickException: If flag combination is invalid
    """
    # --submit requires --no-interactive UNLESS using --script mode
    # Script mode generates shell code, so --submit is allowed
    if submit and not no_interactive and not script:
        raise click.ClickException(
            "--submit requires --no-interactive\n"
            "Automated workflows must run non-interactively\n"
            "(or use --script to generate shell integration code)"
        )

    if no_interactive and script:
        raise click.ClickException(
            "--no-interactive and --script are mutually exclusive\n"
            "--script generates shell integration code for manual execution\n"
            "--no-interactive executes commands programmatically"
        )


def _build_command_sequence(submit: bool) -> list[str]:
    """Build list of slash commands to execute.

    Args:
        submit: Whether to include full CI/PR workflow

    Returns:
        List of slash commands to execute in sequence
    """
    commands = ["/erk:plan-implement"]
    if submit:
        commands.extend(["/fast-ci", "/gt:pr-submit"])
    return commands


def _build_claude_args(slash_command: str, dangerous: bool) -> list[str]:
    """Build Claude command argument list for interactive script mode.

    Args:
        slash_command: The slash command to execute
        dangerous: Whether to skip permission prompts

    Returns:
        List of command arguments suitable for subprocess
    """
    args = ["claude", "--permission-mode", "acceptEdits"]
    if dangerous:
        args.append("--dangerously-skip-permissions")
    args.append(slash_command)
    return args


def _execute_interactive_mode(
    worktree_path: Path, dangerous: bool, executor: ClaudeExecutor
) -> None:
    """Execute implementation in interactive mode using executor.

    Args:
        worktree_path: Path to worktree directory
        dangerous: Whether to skip permission prompts
        executor: Claude CLI executor for process replacement

    Raises:
        click.ClickException: If Claude CLI not found

    Note:
        This function never returns in production - the process is replaced by Claude
    """
    # Show message before handing off to executor
    click.echo("Entering interactive implementation mode...", err=True)

    # Delegate to executor (never returns in production)
    try:
        executor.execute_interactive(worktree_path, dangerous)
    except RuntimeError as e:
        raise click.ClickException(str(e)) from e


def _execute_non_interactive_mode(
    worktree_path: Path,
    commands: list[str],
    dangerous: bool,
    verbose: bool,
    executor: ClaudeExecutor,
) -> None:
    """Execute commands via Claude CLI executor with rich output formatting.

    Args:
        worktree_path: Path to worktree directory
        commands: List of slash commands to execute
        dangerous: Whether to skip permission prompts
        verbose: Whether to show raw output (True) or filtered output (False)
        executor: Claude CLI executor for command execution

    Raises:
        click.ClickException: If Claude CLI not found or command fails
    """
    import time

    from rich.console import Console

    from erk.cli.output import format_implement_summary, stream_command_with_feedback
    from erk.core.claude_executor import CommandResult

    # Verify Claude is available
    if not executor.is_claude_available():
        raise click.ClickException(
            "Claude CLI not found\nInstall from: https://claude.com/download"
        )

    console = Console()
    total_start = time.time()
    all_results: list[CommandResult] = []

    for cmd in commands:
        if verbose:
            # Verbose mode - simple output, no spinner
            click.echo(f"Running {cmd}...", err=True)
            result = executor.execute_command(cmd, worktree_path, dangerous, verbose=True)
        else:
            # Filtered mode - streaming with live print-based feedback
            result = stream_command_with_feedback(
                executor=executor,
                command=cmd,
                worktree_path=worktree_path,
                dangerous=dangerous,
                console=console,
            )

        all_results.append(result)

        # Stop on first failure
        if not result.success:
            break

    # Show final summary (unless verbose mode)
    if not verbose:
        total_duration = time.time() - total_start
        summary = format_implement_summary(all_results, total_duration)
        console.print(summary)

    # Raise exception if any command failed
    if not all(r.success for r in all_results):
        raise click.ClickException("One or more commands failed")


def _build_activation_script_with_commands(
    worktree_path: Path, commands: list[str], dangerous: bool
) -> str:
    """Build activation script with Claude commands.

    Args:
        worktree_path: Path to worktree
        commands: List of slash commands to include
        dangerous: Whether to skip permission prompts

    Returns:
        Complete activation script with commands
    """
    # Get base activation script (cd + venv + env)
    script = render_activation_script(
        worktree_path=worktree_path,
        final_message="",  # We'll add commands instead
        comment="implement activation",
    )

    # Add Claude commands
    shell_commands = []
    for cmd in commands:
        cmd_args = _build_claude_args(cmd, dangerous)
        # Build shell command string
        shell_cmd = " ".join(shlex.quote(arg) for arg in cmd_args)
        shell_commands.append(shell_cmd)

    # Chain commands with && so they only run if previous command succeeded
    script += " && \\\n".join(shell_commands) + "\n"

    return script


class TargetInfo(NamedTuple):
    """Information about detected target type.

    Attributes:
        target_type: Type of target - "issue_number", "issue_url", or "file_path"
        issue_number: Extracted issue number for GitHub targets, None for file paths
    """

    target_type: str
    issue_number: str | None


@dataclass(frozen=True)
class PlanSource:
    """Source information for creating a worktree with plan.

    Attributes:
        plan_content: The plan content as a string
        base_name: Base name for generating worktree name
        dry_run_description: Description to show in dry-run mode
    """

    plan_content: str
    base_name: str
    dry_run_description: str


def _detect_target_type(target: str) -> TargetInfo:
    """Detect whether target is an issue number, issue URL, or file path.

    Args:
        target: User-provided target argument

    Returns:
        TargetInfo with target type and extracted issue number (if applicable)
    """
    # Check if starts with # followed by digits (issue number)
    if target.startswith("#") and target[1:].isdigit():
        return TargetInfo(target_type="issue_number", issue_number=target[1:])

    # Check if GitHub issue URL
    github_issue_pattern = r"github\.com/[^/]+/[^/]+/issues/(\d+)"
    match = re.search(github_issue_pattern, target)
    if match:
        issue_number = match.group(1)
        return TargetInfo(target_type="issue_url", issue_number=issue_number)

    # Check if plain digits (issue number without # prefix)
    if target.isdigit():
        return TargetInfo(target_type="issue_number", issue_number=target)

    # Otherwise, treat as file path
    return TargetInfo(target_type="file_path", issue_number=None)


@dataclass(frozen=True)
class IssuePlanSource:
    """Extended plan source with issue-specific metadata.

    Attributes:
        plan_source: The base PlanSource with content and metadata
        branch_name: The linked development branch name from gh issue develop
        already_existed: Whether the branch already existed
    """

    plan_source: PlanSource
    branch_name: str
    already_existed: bool


def _prepare_plan_source_from_issue(
    ctx: ErkContext, repo_root: Path, issue_number: str
) -> IssuePlanSource:
    """Prepare plan source from GitHub issue.

    Uses `gh issue develop` to create a branch linked to the issue,
    which makes the branch appear in the issue sidebar under "Development".

    Args:
        ctx: Erk context
        repo_root: Repository root path
        issue_number: GitHub issue number

    Returns:
        IssuePlanSource with plan content, metadata, and linked branch name

    Raises:
        SystemExit: If issue not found or doesn't have erk-plan label
    """
    # Output fetching diagnostic
    ctx.feedback.info("Fetching issue from GitHub...")

    # Fetch plan from GitHub
    try:
        plan = ctx.plan_store.get_plan(repo_root, issue_number)
    except RuntimeError as e:
        ctx.feedback.error(f"Error: {e}")
        raise SystemExit(1) from e

    # Output issue title
    ctx.feedback.info(f"Issue: {plan.title}")

    # Validate issue has erk-plan label
    if "erk-plan" not in plan.labels:
        user_output(
            click.style("Error: ", fg="red")
            + f"Issue #{issue_number} does not have the 'erk-plan' label.\n"
            + "Only issues tagged with 'erk-plan' can be used for implementation.\n\n"
            + f"To add the label, visit: {plan.url}"
        )
        raise SystemExit(1)

    # Validate issue is open
    if plan.state != PlanState.OPEN:
        user_output(
            click.style("Warning: ", fg="yellow")
            + f"Issue #{issue_number} is {plan.state.value}. "
            + "Proceeding anyway..."
        )

    # Create or derive branch name for the issue
    trunk_branch = ctx.git.get_trunk_branch(repo_root)
    if USE_GITHUB_NATIVE_BRANCH_LINKING:
        # Compute branch name: truncate to 31 chars, then append timestamp suffix
        base_branch_name = sanitize_worktree_name(f"{issue_number}-{plan.title}")
        timestamp_suffix = format_branch_timestamp_suffix(ctx.time.now())
        desired_branch_name = base_branch_name + timestamp_suffix
        # Use GitHub's native branch linking via `gh issue develop`
        dev_branch = ctx.issue_link_branches.create_development_branch(
            repo_root,
            int(issue_number),
            branch_name=desired_branch_name,
            base_branch=trunk_branch,
        )
    else:
        # Traditional branch naming from issue title
        branch_name = derive_branch_name_from_title(plan.title)
        dev_branch = DevelopmentBranch(
            branch_name=branch_name,
            issue_number=int(issue_number),
            already_existed=False,
        )

    if dev_branch.already_existed:
        ctx.feedback.info(f"Using existing linked branch: {dev_branch.branch_name}")
    else:
        ctx.feedback.info(f"Created linked branch: {dev_branch.branch_name}")

    # Use the branch name as the base name for the worktree
    base_name = sanitize_worktree_name(dev_branch.branch_name)

    dry_run_desc = f"Would create worktree from issue #{issue_number}\n  Title: {plan.title}"

    plan_source = PlanSource(
        plan_content=plan.body,
        base_name=base_name,
        dry_run_description=dry_run_desc,
    )

    return IssuePlanSource(
        plan_source=plan_source,
        branch_name=dev_branch.branch_name,
        already_existed=dev_branch.already_existed,
    )


def _prepare_plan_source_from_file(ctx: ErkContext, plan_file: Path) -> PlanSource:
    """Prepare plan source from file.

    Args:
        ctx: Erk context
        plan_file: Path to plan file

    Returns:
        PlanSource with plan content and metadata

    Raises:
        SystemExit: If plan file doesn't exist
    """
    # Validate plan file exists
    if not plan_file.exists():
        ctx.feedback.error(f"Error: Plan file not found: {plan_file}")
        raise SystemExit(1)

    # Output reading diagnostic
    ctx.feedback.info("Reading plan file...")

    # Read plan content
    plan_content = plan_file.read_text(encoding="utf-8")

    # Extract title from plan content for display
    title = plan_file.stem
    for line in plan_content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("#"):
            # Extract title from first heading
            title = stripped.lstrip("#").strip()
            break

    # Output plan title
    ctx.feedback.info(f"Plan: {title}")

    # Derive base name from filename
    plan_stem = plan_file.stem
    cleaned_stem = strip_plan_from_filename(plan_stem)
    base_name = sanitize_worktree_name(cleaned_stem)

    dry_run_desc = (
        f"Would create worktree from plan file: {plan_file}\n"
        f"  Plan file would be deleted: {plan_file}"
    )

    return PlanSource(
        plan_content=plan_content,
        base_name=base_name,
        dry_run_description=dry_run_desc,
    )


def _create_worktree_with_plan_content(
    ctx: ErkContext,
    *,
    plan_source: PlanSource,
    worktree_name: str | None,
    dry_run: bool,
    submit: bool,
    dangerous: bool,
    no_interactive: bool,
    linked_branch_name: str | None = None,
) -> Path | None:
    """Create worktree with plan content.

    Args:
        ctx: Erk context
        plan_source: Plan source with content and metadata
        worktree_name: Optional custom worktree name
        dry_run: Whether to perform dry run
        submit: Whether to auto-submit PR after implementation
        dangerous: Whether to skip permission prompts
        no_interactive: Whether to execute non-interactively
        linked_branch_name: Optional branch name from gh issue develop
                           (when provided, use this branch instead of creating new)

    Returns:
        Path to created worktree, or None if dry-run mode
    """
    # Discover repository context
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)
    repo_root = repo.root

    # Determine branch name and worktree name
    # - linked_branch_name: use the GitHub-linked branch for the worktree
    # - worktree_name: user override for worktree directory name (not branch)
    # - base_name: fallback derived from plan file or issue title
    if linked_branch_name:
        # For issue mode: always use the branch created by gh issue develop
        branch = linked_branch_name
        # But allow --worktree-name to override the directory name
        if worktree_name:
            name = sanitize_worktree_name(worktree_name)
        else:
            name = sanitize_worktree_name(linked_branch_name)
    elif worktree_name:
        name = sanitize_worktree_name(worktree_name)
        branch = name
    else:
        name = ensure_unique_worktree_name_with_date(
            plan_source.base_name, repo.worktrees_dir, ctx.git
        )
        branch = name

    # Calculate worktree path
    wt_path = worktree_path_for(repo.worktrees_dir, name)

    # For linked branches, we use the existing branch; for others, validate it doesn't exist
    trunk_branch = ctx.trunk_branch
    use_existing_branch = linked_branch_name is not None

    if not use_existing_branch:
        # Validate branch doesn't exist (before dry-run output)
        local_branches = ctx.git.list_local_branches(repo_root)
        if branch in local_branches:
            # Different error messages based on whether name was explicitly provided
            if worktree_name:
                # User explicitly provided this name - tell them to choose different one
                ctx.feedback.error(
                    f"Error: Branch '{branch}' already exists.\n"
                    + "Please choose a different name with --worktree-name."
                )
            else:
                # Auto-generated name conflicted - suggest using explicit name
                ctx.feedback.error(
                    f"Error: Branch '{branch}' already exists.\n"
                    + "Cannot create worktree with existing branch name.\n"
                    + "Use --worktree-name to specify a different name."
                )
            raise SystemExit(1)

    # Handle dry-run mode
    if dry_run:
        dry_run_header = click.style("Dry-run mode:", fg="cyan", bold=True)
        user_output(dry_run_header + " No changes will be made\n")

        # Show execution mode
        mode = "non-interactive" if no_interactive else "interactive"
        user_output(f"Execution mode: {mode}\n")

        user_output(f"Would create worktree '{name}'")
        user_output(f"  {plan_source.dry_run_description}")

        # Show command sequence
        commands = _build_command_sequence(submit)
        user_output("\nCommand sequence:")
        for i, cmd in enumerate(commands, 1):
            cmd_args = _build_claude_args(cmd, dangerous)
            user_output(f"  {i}. {' '.join(cmd_args)}")

        return None

    # Create worktree
    ctx.feedback.info(f"Creating worktree '{name}'...")

    # Load local config
    config = (
        ctx.local_config
        if ctx.local_config is not None
        else LoadedConfig(env={}, post_create_commands=[], post_create_shell=None)
    )

    # Output worktree creation diagnostic
    if use_existing_branch:
        ctx.feedback.info(f"Using linked branch '{branch}'...")
    else:
        ctx.feedback.info(f"Creating branch '{branch}' from {trunk_branch}...")

    # Respect global use_graphite config (matching erk create behavior)
    use_graphite = ctx.global_config.use_graphite if ctx.global_config else False

    # Create worktree
    add_worktree(
        ctx,
        repo_root,
        wt_path,
        branch=branch,
        ref=trunk_branch,
        use_existing_branch=use_existing_branch,
        use_graphite=use_graphite,
        skip_remote_check=True,
    )

    ctx.feedback.success(f"✓ Created worktree: {name}")

    # Run post-worktree setup
    run_post_worktree_setup(ctx, config, wt_path, repo_root, name)

    # Create .impl/ folder with plan content
    ctx.feedback.info("Creating .impl/ folder with plan...")
    create_impl_folder(
        worktree_path=wt_path,
        plan_content=plan_source.plan_content,
    )
    ctx.feedback.success("✓ Created .impl/ folder")

    return wt_path


def _output_activation_instructions(
    ctx: ErkContext,
    *,
    wt_path: Path,
    branch: str,
    script: bool,
    submit: bool,
    dangerous: bool,
    target_description: str,
) -> None:
    """Output activation script or manual instructions.

    This is only called when in script mode (for manual shell integration).
    Interactive and non-interactive modes handle execution directly.

    Args:
        ctx: Erk context
        wt_path: Worktree path
        branch: Branch name
        script: Whether to output activation script
        submit: Whether to auto-submit PR after implementation
        dangerous: Whether to skip permission prompts
        target_description: Description of target for user messages
    """
    if script:
        # Build command sequence
        commands = _build_command_sequence(submit)

        # Generate activation script with commands
        full_script = _build_activation_script_with_commands(wt_path, commands, dangerous)

        comment_suffix = "implement, CI, and submit" if submit else "implement"
        result = ctx.script_writer.write_activation_script(
            full_script,
            command_name="implement",
            comment=f"activate {wt_path.name} and {comment_suffix}",
        )

        result.output_for_shell_integration()
    else:
        # Provide manual instructions
        user_output("\n" + click.style("Next steps:", fg="cyan", bold=True))
        user_output(f"  1. Change to worktree:  erk checkout {branch}")
        if submit:
            user_output("  2. Run implementation, CI, and submit PR:")
            user_output(f"     {_build_claude_command('/erk:plan-implement', dangerous)}")
            user_output(f"     {_build_claude_command('/fast-ci', dangerous)}")
            user_output(f"     {_build_claude_command('/gt:pr-submit', dangerous)}")
        else:
            claude_cmd = _build_claude_command("/erk:plan-implement", dangerous)
            user_output(f"  2. Run implementation:  {claude_cmd}")
        user_output("\n" + click.style("Shell integration not detected.", fg="yellow"))
        user_output("To activate environment and run commands, use:")
        script_flag = "--submit --script" if submit else "--script"
        user_output(f"  source <(erk implement {target_description} {script_flag})")


def _implement_from_issue(
    ctx: ErkContext,
    *,
    issue_number: str,
    worktree_name: str | None,
    dry_run: bool,
    submit: bool,
    dangerous: bool,
    script: bool,
    no_interactive: bool,
    verbose: bool,
    executor: ClaudeExecutor,
) -> None:
    """Implement feature from GitHub issue.

    Args:
        ctx: Erk context
        issue_number: GitHub issue number
        worktree_name: Optional custom worktree name
        dry_run: Whether to perform dry run
        submit: Whether to auto-submit PR after implementation
        dangerous: Whether to skip permission prompts
        script: Whether to output activation script
        no_interactive: Whether to execute non-interactively
        verbose: Whether to show raw output or filtered output
        executor: Claude CLI executor for command execution
    """
    # Discover repo context for issue fetch
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)

    # Prepare plan source from issue (creates linked branch via gh issue develop)
    issue_plan_source = _prepare_plan_source_from_issue(ctx, repo.root, issue_number)

    # Create worktree with plan content, using the linked branch name
    wt_path = _create_worktree_with_plan_content(
        ctx,
        plan_source=issue_plan_source.plan_source,
        worktree_name=worktree_name,
        dry_run=dry_run,
        submit=submit,
        dangerous=dangerous,
        no_interactive=no_interactive,
        linked_branch_name=issue_plan_source.branch_name,
    )

    # Early return for dry-run mode
    if wt_path is None:
        return

    # Save issue reference for PR linking (issue-specific)
    ctx.feedback.info("Saving issue reference for PR linking...")
    plan = ctx.plan_store.get_plan(repo.root, issue_number)
    impl_dir = wt_path / ".impl"
    save_issue_reference(impl_dir, int(issue_number), plan.url)

    ctx.feedback.success(f"✓ Saved issue reference: {plan.url}")

    # Execute based on mode
    if script:
        # Script mode - output activation script
        branch = wt_path.name
        target_description = f"#{issue_number}"
        _output_activation_instructions(
            ctx,
            wt_path=wt_path,
            branch=branch,
            script=script,
            submit=submit,
            dangerous=dangerous,
            target_description=target_description,
        )
    elif no_interactive:
        # Non-interactive mode - execute via subprocess
        commands = _build_command_sequence(submit)
        _execute_non_interactive_mode(wt_path, commands, dangerous, verbose, executor)
    else:
        # Interactive mode - hand off to Claude (never returns)
        _execute_interactive_mode(wt_path, dangerous, executor)


def _implement_from_file(
    ctx: ErkContext,
    *,
    plan_file: Path,
    worktree_name: str | None,
    dry_run: bool,
    submit: bool,
    dangerous: bool,
    script: bool,
    no_interactive: bool,
    verbose: bool,
    executor: ClaudeExecutor,
) -> None:
    """Implement feature from plan file.

    Args:
        ctx: Erk context
        plan_file: Path to plan file
        worktree_name: Optional custom worktree name
        dry_run: Whether to perform dry run
        submit: Whether to auto-submit PR after implementation
        dangerous: Whether to skip permission prompts
        script: Whether to output activation script
        no_interactive: Whether to execute non-interactively
        verbose: Whether to show raw output or filtered output
        executor: Claude CLI executor for command execution
    """
    # Prepare plan source from file
    plan_source = _prepare_plan_source_from_file(ctx, plan_file)

    # Create worktree with plan content
    wt_path = _create_worktree_with_plan_content(
        ctx,
        plan_source=plan_source,
        worktree_name=worktree_name,
        dry_run=dry_run,
        submit=submit,
        dangerous=dangerous,
        no_interactive=no_interactive,
    )

    # Early return for dry-run mode
    if wt_path is None:
        return

    # Delete original plan file (move semantics, file-specific)
    ctx.feedback.info(f"Removing original plan file: {plan_file.name}...")
    plan_file.unlink()

    ctx.feedback.success("✓ Moved plan file to worktree")

    # Execute based on mode
    if script:
        # Script mode - output activation script
        branch = wt_path.name
        target_description = str(plan_file)
        _output_activation_instructions(
            ctx,
            wt_path=wt_path,
            branch=branch,
            script=script,
            submit=submit,
            dangerous=dangerous,
            target_description=target_description,
        )
    elif no_interactive:
        # Non-interactive mode - execute via subprocess
        commands = _build_command_sequence(submit)
        _execute_non_interactive_mode(wt_path, commands, dangerous, verbose, executor)
    else:
        # Interactive mode - hand off to Claude (never returns)
        _execute_interactive_mode(wt_path, dangerous, executor)


@click.command("implement")
@click.argument("target", shell_complete=complete_plan_files)
@click.option(
    "--worktree-name",
    type=str,
    default=None,
    help="Override worktree name (optional, auto-generated if not provided)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Print what would be executed without doing it",
)
@click.option(
    "--submit",
    is_flag=True,
    help="Automatically run CI validation and submit PR after implementation",
)
@click.option(
    "--dangerous",
    is_flag=True,
    default=False,
    help="Skip permission prompts by passing --dangerously-skip-permissions to Claude",
)
@click.option(
    "--no-interactive",
    is_flag=True,
    default=False,
    help="Execute commands via subprocess without user interaction",
)
@click.option(
    "--script",
    is_flag=True,
    hidden=True,
    help="Output activation script for shell integration",
)
@click.option(
    "--yolo",
    is_flag=True,
    default=False,
    help="Equivalent to --dangerous --submit --no-interactive (full automation)",
)
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    help="Show full Claude Code output (default: filtered)",
)
@click.pass_obj
def implement(
    ctx: ErkContext,
    target: str,
    worktree_name: str | None,
    dry_run: bool,
    submit: bool,
    dangerous: bool,
    no_interactive: bool,
    script: bool,
    yolo: bool,
    verbose: bool,
) -> None:
    """Create worktree from GitHub issue or plan file and execute implementation.

    By default, runs in interactive mode where you can interact with Claude
    during implementation. Use --no-interactive for automated execution.

    TARGET can be:
    - GitHub issue number (e.g., #123 or 123)
    - GitHub issue URL (e.g., https://github.com/user/repo/issues/123)
    - Path to plan file (e.g., ./my-feature-plan.md)

    Note: Plain numbers (e.g., 809) are always interpreted as GitHub issues.
          For files with numeric names, use ./ prefix (e.g., ./809).

    For GitHub issues, the issue must have the 'erk-plan' label.

    Examples:

    \b
      # Interactive mode (default)
      erk implement 123

    \b
      # Interactive mode, skip permissions
      erk implement 123 --dangerous

    \b
      # Non-interactive mode (automated execution)
      erk implement 123 --no-interactive

    \b
      # Full CI/PR workflow (requires --no-interactive)
      erk implement 123 --no-interactive --submit

    \b
      # YOLO mode - full automation (dangerous + submit + no-interactive)
      erk implement 123 --yolo

    \b
      # Shell integration
      source <(erk implement 123 --script)

    \b
      # From plan file
      erk implement ./my-feature-plan.md
    """
    # Handle --yolo flag (shorthand for dangerous + submit + no-interactive)
    if yolo:
        dangerous = True
        submit = True
        no_interactive = True

    # Validate flag combinations
    _validate_flags(submit, no_interactive, script)

    # Detect target type
    target_info = _detect_target_type(target)

    # Output target detection diagnostic
    if target_info.target_type in ("issue_number", "issue_url"):
        ctx.feedback.info(f"Detected GitHub issue #{target_info.issue_number}")
    elif target_info.target_type == "file_path":
        ctx.feedback.info(f"Detected plan file: {target}")

    if target_info.target_type in ("issue_number", "issue_url"):
        # GitHub issue mode
        if target_info.issue_number is None:
            user_output(
                click.style("Error: ", fg="red") + "Failed to extract issue number from target"
            )
            raise SystemExit(1)

        _implement_from_issue(
            ctx,
            issue_number=target_info.issue_number,
            worktree_name=worktree_name,
            dry_run=dry_run,
            submit=submit,
            dangerous=dangerous,
            script=script,
            no_interactive=no_interactive,
            verbose=verbose,
            executor=ctx.claude_executor,
        )
    else:
        # Plan file mode
        plan_file = Path(target)
        _implement_from_file(
            ctx,
            plan_file=plan_file,
            worktree_name=worktree_name,
            dry_run=dry_run,
            submit=submit,
            dangerous=dangerous,
            script=script,
            no_interactive=no_interactive,
            verbose=verbose,
            executor=ctx.claude_executor,
        )
