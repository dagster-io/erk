"""Command to implement features from plans or plan files.

This command runs implementation in the current directory using Claude.
It creates an impl folder (under .erk/impl-context/<branch>/) with the plan
content and invokes Claude for execution.

Usage:
- Plan number mode: erk implement 123 or erk implement <URL>
- Plan file mode: erk implement path/to/plan.md
- Auto-detect mode: erk implement (on plan branch with plan-ref.json)
"""

from pathlib import Path

import click

from erk.cli.alias import alias
from erk.cli.commands.completions import complete_plan_files
from erk.cli.commands.implement_shared import (
    PlanSource,
    build_claude_args,
    build_command_sequence,
    detect_target_type,
    execute_interactive_mode,
    execute_non_interactive_mode,
    extract_plan_from_current_branch,
    implement_common_options,
    normalize_model_name,
    output_activation_instructions,
    prepare_plan_source_from_file,
    validate_flags,
)
from erk.cli.core import discover_repo_context
from erk.cli.ensure import Ensure
from erk.cli.help_formatter import CommandWithHiddenOptions
from erk.core.context import ErkContext
from erk.core.prompt_executor import PromptExecutor
from erk.core.repo_discovery import ensure_erk_metadata_dir
from erk_shared.context.types import RepoContext
from erk_shared.impl_folder import create_impl_folder, get_impl_dir, resolve_impl_dir, save_plan_ref
from erk_shared.output.output import user_output
from erk_shared.plan_store.types import PlanNotFound


def _execute(
    ctx: ErkContext,
    *,
    repo: RepoContext,
    submit: bool,
    dangerous: bool,
    script: bool,
    no_interactive: bool,
    verbose: bool,
    model: str | None,
    executor: PromptExecutor,
) -> None:
    """Execute implementation in current directory (impl-context must already exist).

    Callers must handle dry-run before calling this function.

    Args:
        ctx: Erk context
        repo: RepoContext from discover_repo_context
        submit: Whether to auto-submit PR after implementation
        dangerous: Whether to skip permission prompts
        script: Whether to output activation script
        no_interactive: Whether to execute non-interactively
        verbose: Whether to show raw output or filtered output
        model: Optional model name (haiku, sonnet, opus) to pass to Claude CLI
        executor: Prompt executor for command execution
    """
    branch = ctx.git.branch.get_current_branch(ctx.cwd) or "current"

    if script:
        output_activation_instructions(
            ctx,
            wt_path=ctx.cwd,
            branch=branch,
            script=script,
            submit=submit,
            dangerous=dangerous,
            model=model,
            target_description="impl-context",
        )
    elif no_interactive:
        commands = build_command_sequence(submit)
        execute_non_interactive_mode(
            worktree_path=ctx.cwd,
            commands=commands,
            dangerous=dangerous,
            verbose=verbose,
            model=model,
            executor=executor,
        )
    else:
        execute_interactive_mode(
            ctx,
            repo_root=repo.root,
            worktree_path=ctx.cwd,
            dangerous=dangerous,
            model=model,
            executor=executor,
        )


def _show_dry_run_output(
    *,
    cwd: Path,
    plan_source: PlanSource,
    submit: bool,
    dangerous: bool,
    no_interactive: bool,
    model: str | None,
) -> None:
    """Show dry-run output for implementation."""
    dry_run_header = click.style("Dry-run mode:", fg="cyan", bold=True)
    user_output(dry_run_header + " No changes will be made\n")

    # Show execution mode
    mode = "non-interactive" if no_interactive else "interactive"
    user_output(f"Execution mode: {mode}\n")

    user_output(f"Would run in current directory: {cwd}")
    user_output(f"  {plan_source.dry_run_description}")

    # Show command sequence
    commands = build_command_sequence(submit)
    user_output("\nCommand sequence:")
    for i, cmd in enumerate(commands, 1):
        cmd_args = build_claude_args(cmd, dangerous, model)
        user_output(f"  {i}. {' '.join(cmd_args)}")


def _implement_from_issue(
    ctx: ErkContext,
    *,
    plan_number: str,
    dry_run: bool,
    submit: bool,
    dangerous: bool,
    script: bool,
    no_interactive: bool,
    verbose: bool,
    model: str | None,
    executor: PromptExecutor,
) -> None:
    """Implement feature from plan in current directory.

    Args:
        ctx: Erk context
        plan_number: GitHub plan number
        dry_run: Whether to perform dry run
        submit: Whether to auto-submit PR after implementation
        dangerous: Whether to skip permission prompts
        script: Whether to output activation script
        no_interactive: Whether to execute non-interactively
        verbose: Whether to show raw output or filtered output
        model: Optional model name (haiku, sonnet, opus) to pass to Claude CLI
        executor: Prompt executor for command execution
    """
    # Discover repo context for plan fetch
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)

    # Fetch plan from GitHub
    ctx.console.info("Fetching plan from GitHub...")
    result = ctx.plan_store.get_plan(repo.root, plan_number)
    if isinstance(result, PlanNotFound):
        user_output(click.style("Error: ", fg="red") + f"Plan #{plan_number} not found")
        raise SystemExit(1)
    plan = result

    # Validate erk-pr title prefix
    if not plan.title.startswith("[erk-pr]"):
        user_output(
            click.style("Error: ", fg="red")
            + f"Plan #{plan_number} does not have the '[erk-pr]' title prefix.\n"
            "Create a plan using 'erk pr create' to ensure correct formatting."
        )
        raise SystemExit(1) from None

    ctx.console.info(f"Plan: {plan.title}")

    # Create dry-run description
    dry_run_desc = f"Would create impl folder from plan #{plan_number}\n  Title: {plan.title}"
    plan_source = PlanSource(
        plan_content=plan.body,
        base_name=plan.title,
        dry_run_description=dry_run_desc,
    )

    # Handle dry-run mode
    if dry_run:
        _show_dry_run_output(
            cwd=ctx.cwd,
            plan_source=plan_source,
            submit=submit,
            dangerous=dangerous,
            no_interactive=no_interactive,
            model=model,
        )
        return

    # Get current branch for impl directory scoping
    branch = ctx.git.branch.get_current_branch(ctx.cwd)

    # Create impl folder in current directory
    ctx.console.info("Creating impl folder with plan...")
    create_impl_folder(
        worktree_path=ctx.cwd,
        plan_content=plan.body,
        branch_name=branch or "current",
        overwrite=True,
    )
    ctx.console.success("✓ Created impl folder")

    # Save plan reference for PR linking
    ctx.console.info("Saving plan reference for PR linking...")
    impl_dir = get_impl_dir(ctx.cwd, branch_name=branch or "current")
    provider_name = ctx.plan_store.get_provider_name()
    save_plan_ref(
        impl_dir,
        provider=provider_name,
        plan_id=str(plan_number),
        url=plan.url,
        labels=(),
        objective_id=plan.objective_id,
        node_ids=None,
    )
    ctx.console.success(f"✓ Saved plan reference: {plan.url}")

    _execute(
        ctx,
        repo=repo,
        submit=submit,
        dangerous=dangerous,
        script=script,
        no_interactive=no_interactive,
        verbose=verbose,
        model=model,
        executor=executor,
    )


def _implement_from_file(
    ctx: ErkContext,
    *,
    plan_file: Path,
    dry_run: bool,
    submit: bool,
    dangerous: bool,
    script: bool,
    no_interactive: bool,
    verbose: bool,
    model: str | None,
    executor: PromptExecutor,
) -> None:
    """Implement feature from plan file in current directory.

    Does NOT delete the original plan file.

    Args:
        ctx: Erk context
        plan_file: Path to plan file
        dry_run: Whether to perform dry run
        submit: Whether to auto-submit PR after implementation
        dangerous: Whether to skip permission prompts
        script: Whether to output activation script
        no_interactive: Whether to execute non-interactively
        verbose: Whether to show raw output or filtered output
        model: Optional model name (haiku, sonnet, opus) to pass to Claude CLI
        executor: Prompt executor for command execution
    """
    # Discover repo context
    repo = discover_repo_context(ctx, ctx.cwd)

    # Prepare plan source from file
    plan_source = prepare_plan_source_from_file(ctx, plan_file)

    # Handle dry-run mode
    if dry_run:
        _show_dry_run_output(
            cwd=ctx.cwd,
            plan_source=plan_source,
            submit=submit,
            dangerous=dangerous,
            no_interactive=no_interactive,
            model=model,
        )
        return

    # Get current branch for impl directory scoping
    branch = ctx.git.branch.get_current_branch(ctx.cwd)

    # Create impl folder in current directory
    ctx.console.info("Creating impl folder with plan...")
    create_impl_folder(
        worktree_path=ctx.cwd,
        plan_content=plan_source.plan_content,
        branch_name=branch or "current",
        overwrite=True,
    )
    ctx.console.success("✓ Created impl folder")

    # NOTE: We do NOT delete the original plan file. The user may want to
    # reference it or use it again.

    _execute(
        ctx,
        repo=repo,
        submit=submit,
        dangerous=dangerous,
        script=script,
        no_interactive=no_interactive,
        verbose=verbose,
        model=model,
        executor=executor,
    )


@alias("impl")
@click.command("implement", cls=CommandWithHiddenOptions)
@click.argument("target", required=False, shell_complete=complete_plan_files)
@implement_common_options
@click.pass_obj
def implement(
    ctx: ErkContext,
    *,
    target: str | None,
    dry_run: bool,
    submit: bool,
    dangerous: bool,
    safe: bool,
    no_interactive: bool,
    script: bool,
    yolo: bool,
    verbose: bool,
    model: str | None,
) -> None:
    """Create impl folder from plan and execute implementation.

    By default, runs in interactive mode where you can interact with Claude
    during implementation. Use --no-interactive for automated execution.

    TARGET can be:
    - Plan number (e.g., #123 or 123)
    - GitHub URL (e.g., https://github.com/user/repo/issues/123)
    - Path to plan file (e.g., ./my-feature-plan.md)
    - Omitted (auto-detects plan number from plan-ref.json)

    Note: Plain numbers (e.g., 809) are always interpreted as plan numbers.
          For files with numeric names, use ./ prefix (e.g., ./809).

    The plan must have the '[erk-pr]' title prefix.

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
        if safe:
            raise click.ClickException("--yolo and --safe are mutually exclusive")
        dangerous = True
        submit = True
        no_interactive = True

    # Resolve effective dangerous mode from flags and config
    effective_dangerous = Ensure.resolve_dangerous(ctx, dangerous=dangerous, safe=safe)

    # Normalize model name (validates and expands aliases)
    model = normalize_model_name(model)

    # Validate flag combinations
    validate_flags(
        submit=submit,
        no_interactive=no_interactive,
        script=script,
    )

    # Auto-detect from impl-context or branch name when TARGET is omitted
    if target is None:
        current_branch = ctx.git.branch.get_current_branch(ctx.cwd)

        # Strategy 1: Check existing .erk/impl-context/
        impl_dir = resolve_impl_dir(ctx.cwd, branch_name=current_branch)
        if impl_dir is not None and (impl_dir / "plan.md").exists():
            user_output(f"Auto-detected impl-context at {impl_dir.relative_to(ctx.cwd)}")
            if dry_run:
                user_output("Would execute implementation from existing impl-context")
                return
            repo = discover_repo_context(ctx, ctx.cwd)
            _execute(
                ctx,
                repo=repo,
                submit=submit,
                dangerous=effective_dangerous,
                script=script,
                no_interactive=no_interactive,
                verbose=verbose,
                model=model,
                executor=ctx.prompt_executor,
            )
            return

        # Strategy 2: Extract plan number from GitHub PR
        detected_plan = extract_plan_from_current_branch(ctx)
        if detected_plan is not None:
            target = detected_plan
            user_output(f"Auto-detected plan #{target} from branch")
        else:
            branch_display = current_branch or "unknown"
            raise click.ClickException(
                f"Could not auto-detect plan from branch '{branch_display}'.\n\n"
                f"No impl-context or plan PR found. Either:\n"
                f"  1. Provide TARGET explicitly: erk implement <TARGET>\n"
                f"  2. Switch to a plan branch: erk pr co <plan>\n"
                f"  3. Set up impl first: erk exec setup-impl --issue <plan>"
            )

    # Detect target type
    target_info = detect_target_type(target)

    # Output target detection diagnostic
    if target_info.target_type in ("plan_number", "plan_url"):
        ctx.console.info(f"Detected plan #{target_info.plan_number}")
    elif target_info.target_type == "file_path":
        ctx.console.info(f"Detected plan file: {target}")

    # Dispatch based on target type
    if target_info.target_type in ("plan_number", "plan_url"):
        if target_info.plan_number is None:
            user_output(
                click.style("Error: ", fg="red") + "Failed to extract plan number from target"
            )
            raise SystemExit(1) from None

        _implement_from_issue(
            ctx,
            plan_number=target_info.plan_number,
            dry_run=dry_run,
            submit=submit,
            dangerous=effective_dangerous,
            script=script,
            no_interactive=no_interactive,
            verbose=verbose,
            model=model,
            executor=ctx.prompt_executor,
        )
    else:
        plan_file = Path(target)
        _implement_from_file(
            ctx,
            plan_file=plan_file,
            dry_run=dry_run,
            submit=submit,
            dangerous=effective_dangerous,
            script=script,
            no_interactive=no_interactive,
            verbose=verbose,
            model=model,
            executor=ctx.prompt_executor,
        )
