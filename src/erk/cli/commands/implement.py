"""Command to implement features from GitHub issues or plan files.

This command runs implementation in the current directory using Claude.
It creates a .impl/ folder with the plan content and invokes Claude for execution.

Usage:
- GitHub issue mode: erk implement 123 or erk implement <URL>
- Plan file mode: erk implement path/to/plan.md
- Auto-detect mode: erk implement (on PXXXX-* branch)
"""

from pathlib import Path

import click

from erk.cli.alias import alias
from erk.cli.commands.completions import complete_plan_files
from erk.cli.commands.docker_executor import (
    execute_docker_interactive,
    execute_docker_non_interactive,
)
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
from erk.cli.help_formatter import CommandWithHiddenOptions
from erk.core.claude_executor import ClaudeExecutor
from erk.core.context import ErkContext
from erk.core.repo_discovery import ensure_erk_metadata_dir
from erk_shared.impl_folder import create_impl_folder, save_issue_reference
from erk_shared.output.output import user_output


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
    issue_number: str,
    dry_run: bool,
    submit: bool,
    dangerous: bool,
    script: bool,
    no_interactive: bool,
    verbose: bool,
    model: str | None,
    executor: ClaudeExecutor,
    docker: bool,
    docker_image: str,
) -> None:
    """Implement feature from GitHub issue in current directory.

    Args:
        ctx: Erk context
        issue_number: GitHub issue number
        dry_run: Whether to perform dry run
        submit: Whether to auto-submit PR after implementation
        dangerous: Whether to skip permission prompts
        script: Whether to output activation script
        no_interactive: Whether to execute non-interactively
        verbose: Whether to show raw output or filtered output
        model: Optional model name (haiku, sonnet, opus) to pass to Claude CLI
        executor: Claude CLI executor for command execution
        docker: Whether to run in Docker container
        docker_image: Docker image to use
    """
    # Discover repo context for issue fetch
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)

    # Fetch plan from GitHub
    ctx.console.info("Fetching issue from GitHub...")
    try:
        plan = ctx.plan_store.get_plan(repo.root, issue_number)
    except RuntimeError as e:
        user_output(click.style("Error: ", fg="red") + str(e))
        raise SystemExit(1) from None

    # Validate erk-plan label
    if "erk-plan" not in plan.labels:
        user_output(
            click.style("Error: ", fg="red")
            + f"Issue #{issue_number} does not have the 'erk-plan' label.\n"
            "Create a plan using 'erk plan create' or add the label manually."
        )
        raise SystemExit(1) from None

    ctx.console.info(f"Issue: {plan.title}")

    # Create dry-run description
    dry_run_desc = f"Would create .impl/ from issue #{issue_number}\n  Title: {plan.title}"
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

    # Create .impl/ folder in current directory
    ctx.console.info("Creating .impl/ folder with plan...")
    create_impl_folder(
        worktree_path=ctx.cwd,
        plan_content=plan.body,
        overwrite=True,
    )
    ctx.console.success("✓ Created .impl/ folder")

    # Save issue reference for PR linking
    ctx.console.info("Saving issue reference for PR linking...")
    impl_dir = ctx.cwd / ".impl"
    save_issue_reference(impl_dir, int(issue_number), plan.url, plan.title)
    ctx.console.success(f"✓ Saved issue reference: {plan.url}")

    # Execute based on mode
    if script:
        # Script mode - output activation script (stays in current directory)
        branch = ctx.git.get_current_branch(ctx.cwd)
        if branch is None:
            branch = "current"
        target_description = f"#{issue_number}"
        output_activation_instructions(
            ctx,
            wt_path=ctx.cwd,
            branch=branch,
            script=script,
            submit=submit,
            dangerous=dangerous,
            model=model,
            target_description=target_description,
        )
    elif docker:
        # Docker mode - run Claude inside container
        if no_interactive:
            commands = build_command_sequence(submit)
            exit_code = execute_docker_non_interactive(
                repo_root=repo.root,
                worktree_path=ctx.cwd,
                image_name=docker_image,
                model=model,
                commands=commands,
                verbose=verbose,
            )
            if exit_code != 0:
                raise SystemExit(exit_code)
        else:
            # Docker interactive mode - replaces process
            execute_docker_interactive(
                repo_root=repo.root,
                worktree_path=ctx.cwd,
                image_name=docker_image,
                model=model,
            )
    elif no_interactive:
        # Non-interactive mode - execute via subprocess
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
        # Interactive mode - hand off to Claude (never returns)
        execute_interactive_mode(
            ctx,
            repo_root=repo.root,
            worktree_path=ctx.cwd,
            dangerous=dangerous,
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
    executor: ClaudeExecutor,
    docker: bool,
    docker_image: str,
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
        executor: Claude CLI executor for command execution
        docker: Whether to run in Docker container
        docker_image: Docker image to use
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

    # Create .impl/ folder in current directory
    ctx.console.info("Creating .impl/ folder with plan...")
    create_impl_folder(
        worktree_path=ctx.cwd,
        plan_content=plan_source.plan_content,
        overwrite=True,
    )
    ctx.console.success("✓ Created .impl/ folder")

    # NOTE: We do NOT delete the original plan file. The user may want to
    # reference it or use it again.

    # Execute based on mode
    if script:
        # Script mode - output activation script (stays in current directory)
        branch = ctx.git.get_current_branch(ctx.cwd)
        if branch is None:
            branch = "current"
        target_description = str(plan_file)
        output_activation_instructions(
            ctx,
            wt_path=ctx.cwd,
            branch=branch,
            script=script,
            submit=submit,
            dangerous=dangerous,
            model=model,
            target_description=target_description,
        )
    elif docker:
        # Docker mode - run Claude inside container
        if no_interactive:
            commands = build_command_sequence(submit)
            exit_code = execute_docker_non_interactive(
                repo_root=repo.root,
                worktree_path=ctx.cwd,
                image_name=docker_image,
                model=model,
                commands=commands,
                verbose=verbose,
            )
            if exit_code != 0:
                raise SystemExit(exit_code)
        else:
            # Docker interactive mode - replaces process
            execute_docker_interactive(
                repo_root=repo.root,
                worktree_path=ctx.cwd,
                image_name=docker_image,
                model=model,
            )
    elif no_interactive:
        # Non-interactive mode - execute via subprocess
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
        # Interactive mode - hand off to Claude (never returns)
        execute_interactive_mode(
            ctx,
            repo_root=repo.root,
            worktree_path=ctx.cwd,
            dangerous=dangerous,
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
    no_interactive: bool,
    script: bool,
    yolo: bool,
    verbose: bool,
    model: str | None,
    docker: bool,
    docker_image: str,
) -> None:
    """Create .impl/ folder from GitHub issue or plan file and execute implementation.

    By default, runs in interactive mode where you can interact with Claude
    during implementation. Use --no-interactive for automated execution.

    TARGET can be:
    - GitHub issue number (e.g., #123 or 123)
    - GitHub issue URL (e.g., https://github.com/user/repo/issues/123)
    - Path to plan file (e.g., ./my-feature-plan.md)
    - Omitted (auto-detects plan number from branch name when on PXXXX-* branch)

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

    \b
      # Docker isolation mode (filesystem-isolated, safe to skip permissions)
      erk implement 123 --docker
    """
    # Handle --yolo flag (shorthand for dangerous + submit + no-interactive)
    if yolo:
        dangerous = True
        submit = True
        no_interactive = True

    # Normalize model name (validates and expands aliases)
    model = normalize_model_name(model)

    # Validate flag combinations
    validate_flags(submit, no_interactive, script)

    # Auto-detect plan number from branch name when TARGET is omitted
    if target is None:
        # Extract plan number from current branch
        detected_plan = extract_plan_from_current_branch(ctx)
        if detected_plan is None:
            current_branch = ctx.git.get_current_branch(ctx.cwd) or "unknown"
            raise click.ClickException(
                f"Could not auto-detect plan number from branch '{current_branch}'.\n\n"
                f"Branch does not follow PXXXX-* pattern. Either:\n"
                f"  1. Provide TARGET explicitly: erk implement <TARGET>\n"
                f"  2. Switch to a plan branch: erk br checkout P<num>-...\n"
                f"  3. Create branch from plan: erk br create --for-plan <issue>"
            )

        # Use detected plan number as target
        target = detected_plan
        user_output(f"Auto-detected plan #{target} from branch name")

    # Detect target type
    target_info = detect_target_type(target)

    # Output target detection diagnostic
    if target_info.target_type in ("issue_number", "issue_url"):
        ctx.console.info(f"Detected GitHub issue #{target_info.issue_number}")
    elif target_info.target_type == "file_path":
        ctx.console.info(f"Detected plan file: {target}")

    # Dispatch based on target type
    if target_info.target_type in ("issue_number", "issue_url"):
        if target_info.issue_number is None:
            user_output(
                click.style("Error: ", fg="red") + "Failed to extract issue number from target"
            )
            raise SystemExit(1) from None

        _implement_from_issue(
            ctx,
            issue_number=target_info.issue_number,
            dry_run=dry_run,
            submit=submit,
            dangerous=dangerous,
            script=script,
            no_interactive=no_interactive,
            verbose=verbose,
            model=model,
            executor=ctx.claude_executor,
            docker=docker,
            docker_image=docker_image,
        )
    else:
        plan_file = Path(target)
        _implement_from_file(
            ctx,
            plan_file=plan_file,
            dry_run=dry_run,
            submit=submit,
            dangerous=dangerous,
            script=script,
            no_interactive=no_interactive,
            verbose=verbose,
            model=model,
            executor=ctx.claude_executor,
            docker=docker,
            docker_image=docker_image,
        )
