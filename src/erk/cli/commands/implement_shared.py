"""Shared utilities for implement commands.

This module contains the common logic for erk implement - worktree-based implementation.
"""

import re
import shlex
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple, TypeVar

import click

from erk.cli.activation import render_activation_script
from erk.cli.help_formatter import script_option
from erk.core.claude_executor import ClaudeExecutor
from erk.core.context import ErkContext
from erk.core.worktree_utils import compute_relative_path_in_worktree
from erk_shared.issue_workflow import (
    IssueBranchSetup,
    IssueValidationFailed,
    prepare_plan_for_worktree,
)
from erk_shared.naming import (
    sanitize_worktree_name,
    strip_plan_from_filename,
)
from erk_shared.output.output import user_output

# Valid model names and their aliases
_MODEL_ALIASES: dict[str, str] = {
    "h": "haiku",
    "s": "sonnet",
    "o": "opus",
}
_VALID_MODELS = {"haiku", "sonnet", "opus"}

F = TypeVar("F", bound=Callable[..., object])


def implement_common_options(fn: F) -> F:
    """Decorator that applies common options shared between implement commands.

    This decorator applies the following options (in order from top to bottom in help):
    - --dry-run: Print what would be executed without doing it
    - --submit: Automatically run CI validation and submit PR
    - --dangerous: Skip permission prompts
    - --no-interactive: Execute commands via subprocess
    - --script: Output shell script for integration (hidden)
    - --yolo: Equivalent to --dangerous --submit --no-interactive
    - --verbose: Show full Claude Code output
    - -m/--model: Model to use for Claude

    Each command using this decorator must also define its own --force option
    since the behavior differs (worktree deletion vs pool slot unassignment).

    Example:
        @click.command("implement", cls=CommandWithHiddenOptions)
        @click.argument("target")
        @implement_common_options
        @click.option("-f", "--force", ...)  # Command-specific force behavior
        @click.pass_obj
        def implement(ctx, target, dry_run, submit, dangerous, ...):
            ...
    """
    # Apply options in reverse order (Click decorators are applied bottom-up)
    # This results in options appearing in this order in --help
    fn = click.option(
        "-m",
        "--model",
        type=str,
        default=None,
        help="Model to use for Claude (haiku/h, sonnet/s, opus/o)",
    )(fn)
    fn = click.option(
        "--verbose",
        is_flag=True,
        default=False,
        help="Show full Claude Code output (default: filtered)",
    )(fn)
    fn = click.option(
        "--yolo",
        is_flag=True,
        default=False,
        help="Equivalent to --dangerous --submit --no-interactive (full automation)",
    )(fn)
    fn = script_option(fn)
    fn = click.option(
        "--no-interactive",
        is_flag=True,
        default=False,
        help="Execute commands via subprocess without user interaction",
    )(fn)
    fn = click.option(
        "--dangerous",
        is_flag=True,
        default=False,
        help="Skip permission prompts by passing --dangerously-skip-permissions to Claude",
    )(fn)
    fn = click.option(
        "--submit",
        is_flag=True,
        help="Automatically run CI validation and submit PR after implementation",
    )(fn)
    fn = click.option(
        "--dry-run",
        is_flag=True,
        help="Print what would be executed without doing it",
    )(fn)
    return fn


def normalize_model_name(model: str | None) -> str | None:
    """Normalize model name, expanding aliases and validating.

    Args:
        model: User-provided model name or alias (haiku, sonnet, opus, h, s, o, or None)

    Returns:
        Normalized full model name (haiku, sonnet, opus) or None if not provided

    Raises:
        click.ClickException: If model name is invalid
    """
    if model is None:
        return None

    # Expand alias if present
    normalized = _MODEL_ALIASES.get(model.lower(), model.lower())

    if normalized not in _VALID_MODELS:
        valid_options = ", ".join(sorted(_VALID_MODELS | set(_MODEL_ALIASES.keys())))
        raise click.ClickException(f"Invalid model: '{model}'\nValid options: {valid_options}")

    return normalized


def determine_base_branch(ctx: ErkContext, repo_root: Path) -> str:
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


def validate_flags(submit: bool, no_interactive: bool, script: bool) -> None:
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


def build_command_sequence(submit: bool) -> list[str]:
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


def build_claude_args(slash_command: str, dangerous: bool, model: str | None) -> list[str]:
    """Build Claude command argument list for interactive script mode.

    Args:
        slash_command: The slash command to execute
        dangerous: Whether to skip permission prompts
        model: Optional model name (haiku, sonnet, opus) to pass to Claude CLI

    Returns:
        List of command arguments suitable for subprocess
    """
    args = ["claude", "--permission-mode", "acceptEdits"]
    if dangerous:
        args.append("--dangerously-skip-permissions")
    if model is not None:
        args.extend(["--model", model])
    args.append(slash_command)
    return args


def build_claude_command(slash_command: str, dangerous: bool, model: str | None) -> str:
    """Build a Claude CLI invocation for interactive mode.

    Args:
        slash_command: The slash command to execute (e.g., "/erk:plan-implement")
        dangerous: Whether to skip permission prompts
        model: Optional model name (haiku, sonnet, opus) to pass to Claude CLI

    Returns:
        Complete Claude CLI command string
    """
    cmd = "claude --permission-mode acceptEdits"
    if dangerous:
        cmd += " --dangerously-skip-permissions"
    if model is not None:
        cmd += f" --model {model}"
    cmd += f' "{slash_command}"'
    return cmd


def execute_interactive_mode(
    ctx: ErkContext,
    repo_root: Path,
    worktree_path: Path,
    dangerous: bool,
    model: str | None,
    executor: ClaudeExecutor,
) -> None:
    """Execute implementation in interactive mode using executor.

    Args:
        ctx: Erk context for accessing git and current working directory
        repo_root: Path to repository root for listing worktrees
        worktree_path: Path to worktree directory
        dangerous: Whether to skip permission prompts
        model: Optional model name (haiku, sonnet, opus) to pass to Claude CLI
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
            model=model,
        )
    except RuntimeError as e:
        raise click.ClickException(str(e)) from e


def execute_non_interactive_mode(
    *,
    worktree_path: Path,
    commands: list[str],
    dangerous: bool,
    verbose: bool,
    model: str | None,
    executor: ClaudeExecutor,
) -> None:
    """Execute commands via Claude CLI executor with rich output formatting.

    Args:
        worktree_path: Path to worktree directory
        commands: List of slash commands to execute
        dangerous: Whether to skip permission prompts
        verbose: Whether to show raw output (True) or filtered output (False)
        model: Optional model name (haiku, sonnet, opus) to pass to Claude CLI
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
            result = executor.execute_command(
                cmd, worktree_path, dangerous, verbose=True, model=model
            )
        else:
            # Filtered mode - streaming with live print-based feedback
            result = stream_command_with_feedback(
                executor=executor,
                command=cmd,
                worktree_path=worktree_path,
                dangerous=dangerous,
                model=model,
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


def build_activation_script_with_commands(
    worktree_path: Path, commands: list[str], dangerous: bool, model: str | None
) -> str:
    """Build activation script with Claude commands.

    Args:
        worktree_path: Path to worktree
        commands: List of slash commands to include
        dangerous: Whether to skip permission prompts
        model: Optional model name (haiku, sonnet, opus) to pass to Claude CLI

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
        cmd_args = build_claude_args(cmd, dangerous, model)
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


def detect_target_type(target: str) -> TargetInfo:
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


def prepare_plan_source_from_issue(
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

    dry_run_desc = f"Would create worktree from issue #{issue_number}\n  Title: {plan.title}"

    plan_source = PlanSource(
        plan_content=setup.plan_content,
        base_name=setup.worktree_name,
        dry_run_description=dry_run_desc,
    )

    # Check if the branch already exists locally
    local_branches = ctx.git.list_local_branches(repo_root)
    branch_already_exists = setup.branch_name in local_branches

    return IssuePlanSource(
        plan_source=plan_source,
        branch_name=setup.branch_name,
        already_existed=branch_already_exists,
    )


def prepare_plan_source_from_file(ctx: ErkContext, plan_file: Path) -> PlanSource:
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


def output_activation_instructions(
    ctx: ErkContext,
    *,
    wt_path: Path,
    branch: str,
    script: bool,
    submit: bool,
    dangerous: bool,
    model: str | None,
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
        model: Optional model name (haiku, sonnet, opus) to pass to Claude CLI
        target_description: Description of target for user messages
    """
    if script:
        # Build command sequence
        commands = build_command_sequence(submit)

        # Generate activation script with commands
        full_script = build_activation_script_with_commands(wt_path, commands, dangerous, model)

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
            user_output(f"     {build_claude_command('/erk:plan-implement', dangerous, model)}")
            user_output(f"     {build_claude_command('/fast-ci', dangerous, model)}")
            user_output(f"     {build_claude_command('/gt:pr-submit', dangerous, model)}")
        else:
            claude_cmd = build_claude_command("/erk:plan-implement", dangerous, model)
            user_output(f"  2. Run implementation:  {claude_cmd}")
        user_output("\n" + click.style("Shell integration not detected.", fg="yellow"))
        user_output("To activate environment and run commands, use:")
        script_flag = "--submit --script" if submit else "--script"
        user_output(f"  source <(erk implement {target_description} {script_flag})")


@dataclass(frozen=True)
class WorktreeCreationResult:
    """Result of creating a worktree with plan content.

    Attributes:
        worktree_path: Path to the created worktree root
        impl_dir: Path to the .impl/ directory (always at worktree root)
    """

    worktree_path: Path
    impl_dir: Path
