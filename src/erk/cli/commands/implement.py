"""Command to implement features from GitHub issues or plan files.

This unified command provides two modes:
- GitHub issue mode: erk implement 123 or erk implement <URL>
- Plan file mode: erk implement path/to/plan.md

Both modes create a worktree and invoke Claude for implementation.
"""

import re
import shlex
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

import click

from erk.cli.activation import render_activation_script
from erk.cli.alias import alias
from erk.cli.commands.completions import complete_plan_files
from erk.cli.commands.wt.create_cmd import add_worktree, run_post_worktree_setup
from erk.cli.config import LoadedConfig
from erk.cli.core import discover_repo_context, worktree_path_for
from erk.cli.help_formatter import CommandWithHiddenOptions, script_option
from erk.core.claude_executor import ClaudeExecutor
from erk.core.context import ErkContext
from erk.core.repo_discovery import ensure_erk_metadata_dir
from erk.core.worktree_utils import compute_relative_path_in_worktree
from erk_shared.impl_folder import create_impl_folder, save_issue_reference
from erk_shared.issue_workflow import (
    IssueBranchSetup,
    IssueValidationFailed,
    prepare_plan_for_worktree,
)
from erk_shared.naming import (
    ensure_unique_worktree_name_with_date,
    sanitize_worktree_name,
    strip_plan_from_filename,
)
from erk_shared.output.output import user_output


def _determine_base_branch(ctx: ErkContext, repo_root: Path) -> str:
    """Determine the base branch for new worktree creation.

    When Graphite is enabled and the user is on a non-trunk branch,
    stack on the current branch. Otherwise, use trunk.

    Args:
        ctx: Erk context
        repo_root: Repository root path

    Returns:
        Base branch name to use as ref for worktree creation
    """
    trunk_branch = ctx.git.detect_trunk_branch(repo_root)
    use_graphite = ctx.global_config.use_graphite if ctx.global_config else False

    if not use_graphite:
        return trunk_branch

    current_branch = ctx.git.get_current_branch(ctx.cwd)
    if current_branch and current_branch != trunk_branch:
        return current_branch

    return trunk_branch


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
    ctx: ErkContext,
    repo_root: Path,
    worktree_path: Path,
    dangerous: bool,
    executor: ClaudeExecutor,
) -> None:
    """Execute implementation in interactive mode using executor.

    Args:
        ctx: Erk context for accessing git and current working directory
        repo_root: Path to repository root for listing worktrees
        worktree_path: Path to worktree directory
        dangerous: Whether to skip permission prompts
        executor: Claude CLI executor for process replacement

    Raises:
        click.ClickException: If Claude CLI not found

    Note:
        This function never returns in production - the process is replaced by Claude
    """
    click.echo("Entering interactive implementation mode...", err=True)
    try:
        executor.execute_interactive(
            worktree_path,
            dangerous,
            "/erk:plan-implement",
            compute_relative_path_in_worktree(ctx.git.list_worktrees(repo_root), ctx.cwd),
        )
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
        target_subpath=None,
        post_cd_commands=None,
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


@dataclass(frozen=True)
class ForceDeleteOptions:
    """Options for force-deleting existing worktree/branch.

    Attributes:
        worktree: Whether to delete existing worktree with same name
        branch: Whether to delete existing branch with same name
    """

    worktree: bool = False
    branch: bool = False

    @classmethod
    def from_force_flag(cls, force: bool) -> "ForceDeleteOptions":
        """Create options from --force flag value."""
        return cls(worktree=force, branch=force)

    @property
    def any_enabled(self) -> bool:
        """Return True if any force delete option is enabled."""
        return self.worktree or self.branch


@dataclass(frozen=True)
class WorktreeCreationResult:
    """Result of creating a worktree with plan content.

    Attributes:
        worktree_path: Path to the created worktree root
        impl_dir: Path to the .impl/ directory (always at worktree root)
    """

    worktree_path: Path
    impl_dir: Path


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
        branch_name: The development branch name for this issue
        already_existed: Whether the branch already existed
    """

    plan_source: PlanSource
    branch_name: str
    already_existed: bool


def _prepare_plan_source_from_issue(
    ctx: ErkContext, repo_root: Path, issue_number: str, base_branch: str
) -> IssuePlanSource:
    """Prepare plan source from GitHub issue.

    Creates a branch for the issue and fetches plan content.

    Args:
        ctx: Erk context
        repo_root: Repository root path
        issue_number: GitHub issue number
        base_branch: Base branch for creating the development branch

    Returns:
        IssuePlanSource with plan content, metadata, and branch name

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

    # Prepare and validate using shared helper (returns union type)
    result = prepare_plan_for_worktree(plan, ctx.time.now())

    if isinstance(result, IssueValidationFailed):
        user_output(click.style("Error: ", fg="red") + result.message)
        raise SystemExit(1) from None

    setup: IssueBranchSetup = result
    for warning in setup.warnings:
        user_output(click.style("Warning: ", fg="yellow") + warning)

    # Create branch directly via git
    ctx.git.create_branch(repo_root, setup.branch_name, base_branch)
    ctx.feedback.info(f"Created branch: {setup.branch_name}")

    dry_run_desc = f"Would create worktree from issue #{issue_number}\n  Title: {plan.title}"

    plan_source = PlanSource(
        plan_content=setup.plan_content,
        base_name=setup.worktree_name,
        dry_run_description=dry_run_desc,
    )

    return IssuePlanSource(
        plan_source=plan_source,
        branch_name=setup.branch_name,
        already_existed=False,  # Always new branch since we create it directly
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
        raise SystemExit(1) from None

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


def _show_conflict_error(
    ctx: ErkContext,
    *,
    branch: str,
    wt_path: Path,
    wt_exists: bool,
    branch_exists: bool,
    worktree_name_provided: bool,
) -> None:
    """Show error message when branch or worktree already exists.

    Args:
        ctx: Erk context
        branch: Branch name that conflicts
        wt_path: Worktree path that conflicts
        wt_exists: Whether worktree directory exists
        branch_exists: Whether branch exists
        worktree_name_provided: Whether user explicitly provided --worktree-name

    Raises:
        SystemExit: Always exits with code 1
    """
    # Build error message based on what exists
    if wt_exists and branch_exists:
        conflict_msg = f"Branch '{branch}' and worktree '{wt_path.name}' already exist."
    elif branch_exists:
        conflict_msg = f"Branch '{branch}' already exists."
    else:
        conflict_msg = f"Worktree '{wt_path.name}' already exists."

    # Suggest using --force or --worktree-name
    if worktree_name_provided:
        suggestion = "Use -f to delete the existing resources, or choose a different name."
    else:
        suggestion = (
            "Use -f to delete the existing resources, "
            "or --worktree-name to choose a different name."
        )

    ctx.feedback.error(f"Error: {conflict_msg}\n{suggestion}")
    raise SystemExit(1) from None


def _handle_force_delete(
    ctx: ErkContext,
    *,
    repo_root: Path,
    wt_path: Path,
    branch: str,
    wt_exists: bool,
    branch_exists: bool,
    force_delete: ForceDeleteOptions,
    dry_run: bool,
) -> None:
    """Handle --force flag by prompting for confirmation and deleting existing resources.

    Args:
        ctx: Erk context
        repo_root: Repository root path
        wt_path: Path to existing worktree
        branch: Branch name
        wt_exists: Whether worktree directory exists
        branch_exists: Whether branch exists
        force_delete: Options for which resources to force-delete
        dry_run: Whether in dry-run mode

    Raises:
        SystemExit: If user declines confirmation
    """
    # Build list of what will be deleted
    deletions: list[str] = []
    if wt_exists and force_delete.worktree:
        deletions.append(f"worktree: {click.style(str(wt_path), fg='cyan')}")
    if branch_exists and force_delete.branch:
        deletions.append(f"branch: {click.style(branch, fg='yellow')}")

    if not deletions:
        return

    # Display what will be deleted
    user_output(click.style("⚠️  The following will be deleted:", fg="yellow", bold=True))
    for item in deletions:
        user_output(f"  • {item}")

    # Prompt for confirmation
    if not dry_run:
        prompt_text = click.style("Proceed with deletion?", fg="yellow", bold=True)
        if not click.confirm(f"\n{prompt_text}", default=False, err=True):
            user_output(click.style("⭕ Aborted.", fg="red", bold=True))
            raise SystemExit(1) from None

    # Perform deletions
    if wt_exists and force_delete.worktree:
        if dry_run:
            user_output(f"[DRY RUN] Would delete worktree: {wt_path}")
        else:
            ctx.feedback.info(f"Deleting existing worktree: {wt_path.name}...")
            _delete_worktree_for_force(ctx, repo_root, wt_path)
            ctx.feedback.success(f"✓ Deleted worktree: {wt_path.name}")

    if branch_exists and force_delete.branch:
        if dry_run:
            user_output(f"[DRY RUN] Would delete branch: {branch}")
        else:
            ctx.feedback.info(f"Deleting existing branch: {branch}...")
            _delete_branch_for_force(ctx, repo_root, branch)
            ctx.feedback.success(f"✓ Deleted branch: {branch}")


def _delete_worktree_for_force(ctx: ErkContext, repo_root: Path, wt_path: Path) -> None:
    """Delete a worktree directory for --force flag.

    This reuses patterns from wt/delete_cmd.py for worktree cleanup.
    """
    # Try git worktree remove first
    ctx.git.remove_worktree(repo_root, wt_path, force=True)

    # Manually delete directory if still exists (e.g., if git worktree remove didn't fully clean up)
    if ctx.git.path_exists(wt_path):
        shutil.rmtree(wt_path)

    # Prune worktree metadata
    ctx.git.prune_worktrees(repo_root)


def _delete_branch_for_force(ctx: ErkContext, repo_root: Path, branch: str) -> None:
    """Delete a branch for --force flag.

    Uses force delete (-D) since we've already confirmed with user.
    """
    use_graphite = ctx.global_config.use_graphite if ctx.global_config else False

    if use_graphite:
        ctx.git.delete_branch_with_graphite(repo_root, branch, force=True)
    else:
        ctx.git.delete_branch(repo_root, branch, force=True)


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
    base_branch: str,
    force_delete: ForceDeleteOptions | None = None,
) -> WorktreeCreationResult | None:
    """Create worktree with plan content.

    Args:
        ctx: Erk context
        plan_source: Plan source with content and metadata
        worktree_name: Optional custom worktree name
        dry_run: Whether to perform dry run
        submit: Whether to auto-submit PR after implementation
        dangerous: Whether to skip permission prompts
        no_interactive: Whether to execute non-interactively
        linked_branch_name: Optional branch name for issue-based worktrees
                           (when provided, use this branch instead of creating new)
        base_branch: Base branch to use as ref for worktree creation
        force_delete: Options for force-deleting existing worktree/branch

    Returns:
        WorktreeCreationResult with paths, or None if dry-run mode
    """
    if force_delete is None:
        force_delete = ForceDeleteOptions()
    # Discover repository context
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)
    repo_root = repo.root

    # Determine branch name and worktree name
    # - linked_branch_name: use the issue-linked branch for the worktree
    # - worktree_name: user override for worktree directory name (not branch)
    # - base_name: fallback derived from plan file or issue title
    if linked_branch_name:
        # For issue mode: always use the branch created for this issue
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
    use_existing_branch = linked_branch_name is not None

    if not use_existing_branch:
        # Check for existing worktree and branch
        local_branches = ctx.git.list_local_branches(repo_root)
        branch_exists = branch in local_branches
        wt_exists = ctx.git.path_exists(wt_path)

        # Handle conflicts with --force flag
        if branch_exists or wt_exists:
            if force_delete.any_enabled:
                # Prompt for confirmation and delete what exists
                _handle_force_delete(
                    ctx,
                    repo_root=repo_root,
                    wt_path=wt_path,
                    branch=branch,
                    wt_exists=wt_exists,
                    branch_exists=branch_exists,
                    force_delete=force_delete,
                    dry_run=dry_run,
                )
            else:
                # No --force flag - show error with suggestion
                _show_conflict_error(
                    ctx,
                    branch=branch,
                    wt_path=wt_path,
                    wt_exists=wt_exists,
                    branch_exists=branch_exists,
                    worktree_name_provided=worktree_name is not None,
                )

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
        ctx.feedback.info(f"Using branch '{branch}'...")
    else:
        ctx.feedback.info(f"Creating branch '{branch}' from {base_branch}...")

    # Respect global use_graphite config (matching erk create behavior)
    use_graphite = ctx.global_config.use_graphite if ctx.global_config else False

    # Create worktree
    add_worktree(
        ctx,
        repo_root,
        wt_path,
        branch=branch,
        ref=base_branch,
        use_existing_branch=use_existing_branch,
        use_graphite=use_graphite,
        skip_remote_check=True,
    )

    ctx.feedback.success(f"✓ Created worktree: {name}")

    # Run post-worktree setup
    run_post_worktree_setup(ctx, config, wt_path, repo_root, name)

    # Create .impl/ folder with plan content at worktree root
    # Use overwrite=True since new worktrees created from branches with existing
    # .impl/ folders inherit that folder, and we want to replace it with the new plan
    ctx.feedback.info("Creating .impl/ folder with plan...")
    create_impl_folder(
        worktree_path=wt_path,
        plan_content=plan_source.plan_content,
        prompt_executor=ctx.prompt_executor,
        overwrite=True,
    )
    ctx.feedback.success("✓ Created .impl/ folder")

    return WorktreeCreationResult(
        worktree_path=wt_path,
        impl_dir=wt_path / ".impl",
    )


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
        user_output(f"  1. Change to worktree:  erk br co {branch}")
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

    # Determine base branch (respects worktree stacking)
    base_branch = _determine_base_branch(ctx, repo.root)

    # Prepare plan source from issue (creates branch via git)
    issue_plan_source = _prepare_plan_source_from_issue(
        ctx, repo.root, issue_number, base_branch=base_branch
    )

    # Create worktree with plan content, using the branch name
    result = _create_worktree_with_plan_content(
        ctx,
        plan_source=issue_plan_source.plan_source,
        worktree_name=worktree_name,
        dry_run=dry_run,
        submit=submit,
        dangerous=dangerous,
        no_interactive=no_interactive,
        linked_branch_name=issue_plan_source.branch_name,
        base_branch=base_branch,
    )

    # Early return for dry-run mode
    if result is None:
        return

    wt_path = result.worktree_path

    # Save issue reference for PR linking (issue-specific)
    # Use impl_dir from result to handle monorepo project-root placement
    ctx.feedback.info("Saving issue reference for PR linking...")
    plan = ctx.plan_store.get_plan(repo.root, issue_number)
    save_issue_reference(result.impl_dir, int(issue_number), plan.url, plan.title)

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
        _execute_interactive_mode(ctx, repo.root, wt_path, dangerous, executor)


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
    force_delete: ForceDeleteOptions,
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
        force_delete: Options for force-deleting existing worktree/branch
        executor: Claude CLI executor for command execution
    """
    # Discover repo context
    repo = discover_repo_context(ctx, ctx.cwd)

    # Determine base branch (respects worktree stacking)
    base_branch = _determine_base_branch(ctx, repo.root)

    # Prepare plan source from file
    plan_source = _prepare_plan_source_from_file(ctx, plan_file)

    # Create worktree with plan content
    result = _create_worktree_with_plan_content(
        ctx,
        plan_source=plan_source,
        worktree_name=worktree_name,
        dry_run=dry_run,
        submit=submit,
        dangerous=dangerous,
        no_interactive=no_interactive,
        base_branch=base_branch,
        force_delete=force_delete,
    )

    # Early return for dry-run mode
    if result is None:
        return

    wt_path = result.worktree_path

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
        _execute_interactive_mode(ctx, repo.root, wt_path, dangerous, executor)


@alias("impl")
@click.command("implement", cls=CommandWithHiddenOptions)
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
@script_option
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
@click.option(
    "-f",
    "--force",
    is_flag=True,
    default=False,
    help="Delete existing branch/worktree with same name after confirmation.",
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
    force: bool,
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

    # Create force delete options from --force flag (set at entry point for clarity)
    force_delete = ForceDeleteOptions.from_force_flag(force)

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
            raise SystemExit(1) from None

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
            force_delete=force_delete,
            executor=ctx.claude_executor,
        )
