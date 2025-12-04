import json
import shlex
import subprocess
from collections.abc import Iterable
from pathlib import Path

import click
from erk_shared.github.issues import IssueInfo
from erk_shared.impl_folder import create_impl_folder, get_impl_path
from erk_shared.naming import (
    default_branch_for_worktree,
    ensure_simple_worktree_name,
    ensure_unique_worktree_name,
    ensure_unique_worktree_name_with_date,
    format_branch_timestamp_suffix,
    sanitize_worktree_name,
    strip_plan_from_filename,
)
from erk_shared.output.output import user_output

from erk.cli.config import LoadedConfig
from erk.cli.core import discover_repo_context, worktree_path_for
from erk.cli.ensure import Ensure
from erk.cli.github_parsing import parse_issue_identifier
from erk.cli.shell_utils import render_navigation_script
from erk.cli.subprocess_utils import run_with_error_reporting
from erk.core.context import ErkContext
from erk.core.repo_discovery import RepoContext, ensure_erk_metadata_dir
from erk.core.worktree_metadata import set_worktree_project


def run_post_worktree_setup(
    ctx: ErkContext,
    config: LoadedConfig,
    worktree_path: Path,
    repo_root: Path,
    name: str,
) -> None:
    """Run post-worktree-creation setup: .env file and post-create commands.

    Args:
        ctx: Erk context
        config: Loaded local configuration
        worktree_path: Path to the newly created worktree
        repo_root: Path to repository root
        name: Worktree name
    """
    # Write .env file if template exists
    env_content = make_env_content(
        config, worktree_path=worktree_path, repo_root=repo_root, name=name
    )
    if env_content:
        env_path = worktree_path / ".env"
        env_path.write_text(env_content, encoding="utf-8")

    # Run post-create commands
    if config.post_create_commands:
        run_commands_in_worktree(
            ctx=ctx,
            commands=config.post_create_commands,
            worktree_path=worktree_path,
            shell=config.post_create_shell,
        )


def ensure_worktree_for_branch(
    ctx: ErkContext,
    repo: RepoContext,
    branch: str,
    *,
    is_plan_derived: bool = False,
) -> tuple[Path, bool]:
    """Ensure worktree exists for branch, creating if necessary.

    This function checks if a worktree already exists for the given branch.
    If it does, validates branch match and returns path. If not, creates a new worktree
    with config-driven post-create commands and .env generation.

    Args:
        ctx: The Erk context with git operations
        repo: Repository context with root and worktrees directory
        branch: The branch name to ensure a worktree for
        is_plan_derived: If True, use dated worktree names (for plan workflows).
                        If False, use simple names (for manual checkout).

    Returns:
        Tuple of (worktree_path, was_created)
        - worktree_path: Path to the worktree directory
        - was_created: True if worktree was newly created, False if it already existed

    Raises:
        SystemExit: If branch doesn't exist, tracking branch creation fails,
                   or worktree name collision with different branch
    """
    # Check if worktree already exists for this branch
    existing_path = ctx.git.is_branch_checked_out(repo.root, branch)
    if existing_path is not None:
        return existing_path, False

    # Get trunk branch for validation
    trunk_branch = ctx.git.detect_trunk_branch(repo.root)

    # Validate that we're not trying to create worktree for trunk branch
    Ensure.invariant(
        branch != trunk_branch,
        f'Cannot create worktree for trunk branch "{trunk_branch}".\n'
        f"The trunk branch should be checked out in the root worktree.\n"
        f"To switch to {trunk_branch}, use:\n"
        f"  erk checkout root",
    )

    # Branch not checked out - need to create worktree
    # First check if branch exists locally
    local_branches = ctx.git.list_local_branches(repo.root)

    if branch not in local_branches:
        # Not a local branch - check if remote branch exists
        remote_branches = ctx.git.list_remote_branches(repo.root)
        remote_ref = f"origin/{branch}"

        if remote_ref not in remote_branches:
            # Branch doesn't exist locally or on origin
            user_output(
                f"Error: Branch '{branch}' does not exist.\n"
                f"To create a new branch and worktree, run:\n"
                f"  erk wt create --branch {branch}"
            )
            raise SystemExit(1)

        # Remote branch exists - create local tracking branch
        user_output(f"Branch '{branch}' exists on origin, creating local tracking branch...")
        try:
            ctx.git.create_tracking_branch(repo.root, branch, remote_ref)
        except subprocess.CalledProcessError as e:
            user_output(
                f"Error: Failed to create local tracking branch from {remote_ref}\n"
                f"Details: {e.stderr}\n"
                f"Suggested action:\n"
                f"  1. Check git status and resolve any issues\n"
                f"  2. Manually create branch: git branch --track {branch} {remote_ref}\n"
                f"  3. Or use: erk wt create --branch {branch}"
            )
            raise SystemExit(1) from e

    # Branch exists but not checked out - auto-create worktree
    user_output(f"Branch '{branch}' not checked out, creating worktree...")

    # Load local config for .env template and post-create commands
    config = (
        ctx.local_config
        if ctx.local_config is not None
        else LoadedConfig(env={}, post_create_commands=[], post_create_shell=None)
    )

    # Generate and ensure unique worktree name
    name = sanitize_worktree_name(branch)

    # Use appropriate naming strategy based on whether worktree is plan-derived
    if is_plan_derived:
        # Plan workflows need date suffixes to create multiple worktrees from same plan
        name = ensure_unique_worktree_name_with_date(name, repo.worktrees_dir, ctx.git)
    else:
        # Manual checkouts use simple names for predictability
        name = ensure_simple_worktree_name(name, repo.worktrees_dir, ctx.git)

    # Calculate worktree path
    wt_path = worktree_path_for(repo.worktrees_dir, name)

    # Check for name collision with different branch (for non-plan checkouts)
    if not is_plan_derived and ctx.git.path_exists(wt_path):
        # Worktree exists - check what branch it has
        worktrees = ctx.git.list_worktrees(repo.root)
        for wt in worktrees:
            if wt.path == wt_path:
                if wt.branch != branch:
                    # Detached HEAD: provide specific guidance
                    if wt.branch is None:
                        user_output(
                            f"Error: Worktree '{name}' is in detached HEAD state "
                            f"(possibly mid-rebase).\n\n"
                            f"Cannot create new worktree for branch '{branch}' with same name.\n\n"
                            f"Options:\n"
                            f"  1. Resume work in existing worktree: erk wt goto {name}\n"
                            f"  2. Complete or abort the rebase first, then try again\n"
                            f"  3. Use a different branch name"
                        )
                        raise SystemExit(1)
                    # Different branch: existing error handling
                    user_output(
                        f"Error: Worktree '{name}' already exists "
                        f"with different branch '{wt.branch}'.\n"
                        f"Cannot create worktree for branch '{branch}' with same name.\n"
                        f"Options:\n"
                        f"  1. Switch to existing worktree: erk wt goto {name}\n"
                        f"  2. Use a different branch name"
                    )
                    raise SystemExit(1)
                # Same branch - return existing path
                return wt_path, False
        # Path exists but not in worktree list (shouldn't happen, but handle gracefully)
        user_output(
            f"Error: Directory '{wt_path}' exists but is not a git worktree.\n"
            f"Please remove or rename the directory and try again."
        )
        raise SystemExit(1)

    # Create worktree from existing branch
    add_worktree(
        ctx,
        repo.root,
        wt_path,
        branch=branch,
        ref=None,
        use_existing_branch=True,
        use_graphite=False,
        skip_remote_check=True,
    )

    user_output(click.style(f"✓ Created worktree: {name}", fg="green"))

    # Run post-worktree setup (.env and post-create commands)
    run_post_worktree_setup(ctx, config, wt_path, repo.root, name)

    return wt_path, True


def add_worktree(
    ctx: ErkContext,
    repo_root: Path,
    path: Path,
    *,
    branch: str | None,
    ref: str | None,
    use_existing_branch: bool,
    use_graphite: bool,
    skip_remote_check: bool,
) -> None:
    """Create a git worktree.

    If `use_existing_branch` is True and `branch` is provided, checks out the existing branch
    in the new worktree: `git worktree add <path> <branch>`.

    If `use_existing_branch` is False and `branch` is provided, creates a new branch:
    - With graphite: `gt create <branch>` followed by `git worktree add <path> <branch>`
    - Without graphite: `git worktree add -b <branch> <path> <ref or HEAD>`

    Otherwise, uses `git worktree add <path> <ref or HEAD>`.
    """

    if branch and use_existing_branch:
        # Validate branch is not already checked out
        existing_path = ctx.git.is_branch_checked_out(repo_root, branch)
        if existing_path:
            user_output(
                f"Error: Branch '{branch}' is already checked out at {existing_path}\n"
                f"Git doesn't allow the same branch to be checked out in multiple worktrees.\n\n"
                f"Options:\n"
                f"  • Use a different branch name\n"
                f"  • Create a new branch instead: erk create {path.name}\n"
                f"  • Switch to that worktree: erk checkout {branch}",
            )
            raise SystemExit(1)

        ctx.git.add_worktree(repo_root, path, branch=branch, ref=None, create_branch=False)

        # Track existing branch with Graphite if enabled
        if use_graphite and ref:
            # Only track if not already tracked (idempotent)
            all_branches = ctx.graphite.get_all_branches(ctx.git, repo_root)
            if branch not in all_branches:
                ctx.graphite.track_branch(path, branch, ref)
    elif branch:
        # Check if branch name exists on remote origin (only when creating new branches)
        if not skip_remote_check:
            try:
                remote_branches = ctx.git.list_remote_branches(repo_root)
                remote_ref = f"origin/{branch}"

                if remote_ref in remote_branches:
                    user_output(
                        click.style("Error: ", fg="red")
                        + f"Branch '{branch}' already exists on remote 'origin'\n\n"
                        + "A branch with this name is already pushed to the remote repository.\n"
                        + "Please choose a different name for your new branch."
                    )
                    raise SystemExit(1)
            except Exception as e:
                # Remote unavailable or other error - proceed with warning
                user_output(
                    click.style("Warning: ", fg="yellow")
                    + f"Could not check remote branches: {e}\n"
                    + "Proceeding with branch creation..."
                )

        if use_graphite:
            cwd = ctx.cwd
            original_branch = ctx.git.get_current_branch(cwd)
            if original_branch is None:
                raise ValueError("Cannot create graphite branch from detached HEAD")
            if ctx.git.has_staged_changes(repo_root):
                user_output(
                    "Error: Staged changes detected. "
                    "Graphite cannot create a branch while staged changes are present.\n"
                    "`gt create --no-interactive` attempts to commit staged files but fails when "
                    "no commit message is provided.\n\n"
                    "Resolve the staged changes before running `erk create`:\n"
                    '  • Commit them: git commit -m "message"\n'
                    "  • Unstage them: git reset\n"
                    "  • Stash them: git stash\n"
                    "  • Disable Graphite: erk config set use_graphite false",
                )
                raise SystemExit(1)
            run_with_error_reporting(
                ["gt", "create", "--no-interactive", branch],
                cwd=cwd,
                error_prefix=f"Failed to create Graphite branch '{branch}'",
                troubleshooting=[
                    "Check if branch name is valid",
                    "Ensure Graphite is properly configured (gt repo init)",
                    f"Try creating the branch manually: gt create {branch}",
                    "Disable Graphite: erk config set use_graphite false",
                ],
            )
            ctx.git.checkout_branch(cwd, original_branch)
            ctx.git.add_worktree(repo_root, path, branch=branch, ref=None, create_branch=False)
        else:
            ctx.git.add_worktree(repo_root, path, branch=branch, ref=ref, create_branch=True)
    else:
        ctx.git.add_worktree(repo_root, path, branch=None, ref=ref, create_branch=False)


def make_env_content(
    cfg: LoadedConfig,
    *,
    worktree_path: Path,
    repo_root: Path,
    name: str,
    project_root: Path | None = None,
    project_name: str | None = None,
) -> str:
    """Render .env content using config templates.

    Substitution variables:
      - {worktree_path}  - Path to the worktree directory
      - {repo_root}      - Path to the git repository root
      - {name}           - Worktree name
      - {project_root}   - Path to project directory (if in project context)
      - {project_name}   - Project name (if in project context)
    """

    variables: dict[str, str] = {
        "worktree_path": str(worktree_path),
        "repo_root": str(repo_root),
        "name": name,
    }

    # Add project variables if available
    if project_root is not None:
        variables["project_root"] = str(project_root)
    if project_name is not None:
        variables["project_name"] = project_name

    lines: list[str] = []
    for key, template in cfg.env.items():
        value = template.format(**variables)
        # Quote value to be safe; dotenv parsers commonly accept quotes.
        lines.append(f"{key}={quote_env_value(value)}")

    # Always include these basics for convenience
    lines.append(f"WORKTREE_PATH={quote_env_value(str(worktree_path))}")
    lines.append(f"REPO_ROOT={quote_env_value(str(repo_root))}")
    lines.append(f"WORKTREE_NAME={quote_env_value(name)}")

    # Add project env vars if available
    if project_root is not None:
        lines.append(f"PROJECT_ROOT={quote_env_value(str(project_root))}")
    if project_name is not None:
        lines.append(f"PROJECT_NAME={quote_env_value(project_name)}")

    return "\n".join(lines) + "\n"


def quote_env_value(value: str) -> str:
    """Return a quoted value suitable for .env files."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _create_json_response(
    *,
    worktree_name: str,
    worktree_path: Path,
    branch_name: str | None,
    plan_file_path: Path | None,
    status: str,
) -> str:
    """Generate JSON response for create command.

    Args:
        worktree_name: Name of the worktree
        worktree_path: Path to the worktree directory
        branch_name: Git branch name (may be None if not available)
        plan_file_path: Path to plan file if exists, None otherwise
        status: Status string ("created" or "exists")

    Returns:
        JSON string with worktree information
    """
    return json.dumps(
        {
            "worktree_name": worktree_name,
            "worktree_path": str(worktree_path),
            "branch_name": branch_name,
            "plan_file": str(plan_file_path) if plan_file_path else None,
            "status": status,
        }
    )


@click.command("create")
@click.argument("name", metavar="NAME", required=False)
@click.option(
    "--branch",
    "branch",
    type=str,
    help=("Branch name to create and check out in the worktree. Defaults to NAME if omitted."),
)
@click.option(
    "--ref",
    "ref",
    type=str,
    default=None,
    help=("Git ref to base the worktree on (e.g. HEAD, origin/main). Defaults to HEAD if omitted."),
)
@click.option(
    "--no-post",
    is_flag=True,
    help="Skip running post-create commands from config.toml.",
)
@click.option(
    "--from-plan",
    "from_plan",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help=(
        "Path to a plan markdown file. Will derive worktree name from filename "
        "and create .impl/ folder with plan.md in the worktree. "
        "Worktree names are automatically suffixed with the current date (-YY-MM-DD) "
        "and versioned if duplicates exist."
    ),
)
@click.option(
    "--keep-plan",
    is_flag=True,
    help="Copy the plan file instead of moving it (requires --from-plan).",
)
@click.option(
    "--from-issue",
    "from_issue",
    type=str,
    help=(
        "GitHub issue number or URL with erk-plan label. Fetches issue content "
        "and creates worktree with .impl/ folder and .impl/issue.json metadata. "
        "Worktree names are automatically suffixed with the current date (-YY-MM-DD) "
        "and versioned if duplicates exist."
    ),
)
@click.option(
    "--copy-plan",
    is_flag=True,
    default=False,
    help=(
        "Copy .impl directory from current worktree to new worktree. "
        "Useful for multi-phase workflows where each phase builds on the previous plan. "
        "Mutually exclusive with --from-plan."
    ),
)
@click.option(
    "--from-current-branch",
    is_flag=True,
    help=(
        "Move the current branch to the new worktree, then switch current worktree to --ref "
        "(defaults to main/master). NAME defaults to current branch name."
    ),
)
@click.option(
    "--from-branch",
    "from_branch",
    type=str,
    default=None,
    help=("Create worktree from an existing branch. NAME defaults to the branch name."),
)
@click.option(
    "--script",
    is_flag=True,
    hidden=True,
    help="Output shell script for directory change instead of messages.",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output JSON with worktree information instead of human-readable messages.",
)
@click.option(
    "--stay",
    is_flag=True,
    help="Stay in current directory instead of switching to new worktree.",
)
@click.option(
    "--skip-remote-check",
    is_flag=True,
    default=False,
    help="Skip checking if branch exists on remote (for offline work)",
)
@click.pass_obj
def create_wt(
    ctx: ErkContext,
    name: str | None,
    branch: str | None,
    ref: str | None,
    no_post: bool,
    from_plan: Path | None,
    keep_plan: bool,
    from_issue: str | None,
    copy_plan: bool,
    from_current_branch: bool,
    from_branch: str | None,
    script: bool,
    output_json: bool,
    stay: bool,
    skip_remote_check: bool,
) -> None:
    """Create a worktree and write a .env file.

    Reads config.toml for env templates and post-create commands (if present).
    If --from-plan is provided, derives name from the plan filename and creates
    .impl/ folder in the worktree.
    If --from-issue is provided, fetches the GitHub issue, validates the erk-plan label,
    derives name from the issue title, and creates .impl/ folder with issue.json metadata.
    If --from-current-branch is provided, moves the current branch to the new worktree.
    If --from-branch is provided, creates a worktree from an existing branch.

    By default, the command checks if a branch with the same name already exists on
    the 'origin' remote. If a conflict is detected, the command fails with an error.
    Use --skip-remote-check to bypass this validation for offline workflows.
    """

    # Validate mutually exclusive options
    flags_set = sum(
        [
            from_current_branch,
            from_branch is not None,
            from_plan is not None,
            from_issue is not None,
        ]
    )
    Ensure.invariant(
        flags_set <= 1,
        "Cannot use multiple of: --from-current-branch, --from-branch, --from-plan, --from-issue",
    )

    # Validate --json and --script are mutually exclusive
    Ensure.invariant(not (output_json and script), "Cannot use both --json and --script")

    # Validate --keep-plan requires --from-plan
    Ensure.invariant(not keep_plan or from_plan is not None, "--keep-plan requires --from-plan")

    # Validate --copy-plan and --from-plan/--from-issue are mutually exclusive
    Ensure.invariant(
        not (copy_plan and (from_plan is not None or from_issue is not None)),
        "--copy-plan and --from-plan/--from-issue are mutually exclusive. "
        "Use --copy-plan to copy from current worktree OR --from-plan <file> to use a plan "
        "file OR --from-issue <number> to use a GitHub issue.",
    )

    # Validate .impl directory exists if --copy-plan is used
    if copy_plan:
        impl_source_check = ctx.cwd / ".impl"
        Ensure.path_is_dir(
            ctx,
            impl_source_check,
            f"No .impl directory found in current worktree ({ctx.cwd}). "
            "Use 'erk create --from-plan <file>' to create a worktree with a plan from a file.",
        )

    # Initialize variables used in conditional blocks (for type checking)
    issue_number_parsed: int | None = None
    issue_info: IssueInfo | None = None

    # Handle --from-current-branch flag
    if from_current_branch:
        # Get the current branch
        current_branch = Ensure.not_none(
            ctx.git.get_current_branch(ctx.cwd), "HEAD is detached (not on a branch)"
        )

        # Set branch to current branch and derive name if not provided
        Ensure.invariant(
            not branch, "Cannot specify --branch with --from-current-branch (uses current branch)."
        )
        branch = current_branch

        if not name:
            name = sanitize_worktree_name(current_branch)

    # Handle --from-branch flag
    elif from_branch:
        Ensure.invariant(
            not branch, "Cannot specify --branch with --from-branch (uses the specified branch)."
        )
        branch = from_branch

        if not name:
            name = sanitize_worktree_name(from_branch)

    # Handle --from-plan flag
    elif from_plan:
        Ensure.invariant(
            not name, "Cannot specify both NAME and --from-plan. Use one or the other."
        )
        # Derive name from plan filename (strip extension)
        plan_stem = from_plan.stem  # filename without extension
        cleaned_stem = strip_plan_from_filename(plan_stem)
        base_name = sanitize_worktree_name(cleaned_stem)
        # Note: Apply ensure_unique_worktree_name() and truncation after getting erks_dir
        name = base_name

    # Handle --from-issue flag
    elif from_issue:
        Ensure.invariant(
            not name, "Cannot specify both NAME and --from-issue. Use one or the other."
        )
        # Parse issue number from URL or plain number - raises click.ClickException if invalid
        issue_number_parsed = parse_issue_identifier(from_issue)
        # Note: name will be derived from issue title after fetching
        # Defer fetch until after repo discovery below
        name = None  # Will be set after fetching issue

    # Regular create (no special flags)
    else:
        # Allow --branch alone to derive name from branch
        if not name and branch:
            name = sanitize_worktree_name(branch)
        elif not name:
            user_output(
                "Must provide NAME or --from-plan or --from-branch "
                "or --from-current-branch or --from-issue or --branch option."
            )
            raise SystemExit(1)

    # Track if name came from plan file (will need unique naming with date suffix)
    # Note: from_issue uses gh issue develop which creates a unique branch name,
    # so it doesn't need the date suffix treatment
    is_plan_derived = from_plan is not None

    # Discover repo context (needed for all paths)
    repo = discover_repo_context(ctx, ctx.cwd)
    ensure_erk_metadata_dir(repo)

    # Track linked branch name for issue-based worktrees
    linked_branch_name: str | None = None

    # Handle issue fetching after repo discovery
    if from_issue:
        # Type narrowing: issue_number_parsed must be set if from_issue is True
        assert issue_number_parsed is not None, (
            "issue_number_parsed must be set when from_issue is True"
        )

        # Fetch issue using integration layer
        try:
            issue_info = ctx.issues.get_issue(repo.root, issue_number_parsed)
        except RuntimeError as e:
            user_output(
                click.style("Error: ", fg="red")
                + f"Failed to fetch issue #{issue_number_parsed}\n"
                + f"Details: {e}\n\n"
                + "Troubleshooting:\n"
                + "  • Verify issue number is correct\n"
                + "  • Check repository access: gh auth status\n"
                + f"  • Try viewing manually: gh issue view {issue_number_parsed}"
            )
            raise SystemExit(1) from e

        # Validate erk-plan label
        if "erk-plan" not in issue_info.labels:
            user_output(
                click.style("Error: ", fg="red")
                + f"Issue #{issue_number_parsed} must have 'erk-plan' label\n\n"
                + "To add the label:\n"
                + f"  gh issue edit {issue_number_parsed} --add-label erk-plan\n\n"
                + "Or create issues via:\n"
                + "  /erk:create-plan-issue-from-plan-file"
            )
            raise SystemExit(1)

        # Create branch name using GitHub's native branch linking via `gh issue develop`
        trunk_branch = ctx.git.detect_trunk_branch(repo.root)
        # Compute branch name that matches worktree naming convention
        # First truncate to 31 chars, then append timestamp suffix
        base_branch_name = sanitize_worktree_name(f"{issue_number_parsed}-{issue_info.title}")
        timestamp_suffix = format_branch_timestamp_suffix(ctx.time.now())
        desired_branch_name = base_branch_name + timestamp_suffix
        dev_branch = ctx.issue_link_branches.create_development_branch(
            repo.root,
            issue_number_parsed,
            branch_name=desired_branch_name,
            base_branch=trunk_branch,
        )
        linked_branch_name = dev_branch.branch_name

        if dev_branch.already_existed:
            user_output(f"Using existing linked branch: {linked_branch_name}")
        else:
            user_output(f"Created linked branch: {linked_branch_name}")

        # Use the linked branch name for the worktree name
        # (already has timestamp suffix, sanitize_worktree_name will preserve it)
        name = sanitize_worktree_name(linked_branch_name)

    # At this point, name should always be set
    assert name is not None, "name must be set by now"

    # Sanitize the name to ensure consistency (truncate to 31 chars, normalize)
    # This applies to user-provided names as well as derived names
    # Note: sanitize_worktree_name is idempotent - preserves timestamp suffixes
    if not is_plan_derived:
        name = sanitize_worktree_name(name)

    # Validate that name is not a reserved word
    Ensure.invariant(
        name.lower() != "root", '"root" is a reserved name and cannot be used for a worktree.'
    )

    cfg = ctx.local_config
    trunk_branch = ctx.git.detect_trunk_branch(repo.root)

    # Validate that name is not trunk branch (should use root worktree)
    if name == trunk_branch:
        user_output(
            f'Error: "{name}" cannot be used as a worktree name.\n'
            f"To switch to the {name} branch in the root repository, use:\n"
            f"  erk checkout root",
        )
        raise SystemExit(1)

    # Apply date prefix and uniqueness for plan-derived names
    if is_plan_derived:
        name = ensure_unique_worktree_name(name, repo.worktrees_dir, ctx.git)

    wt_path = worktree_path_for(repo.worktrees_dir, name)

    if ctx.git.path_exists(wt_path):
        if output_json:
            # For JSON output, emit a status: "exists" response with available info
            existing_branch = ctx.git.get_current_branch(wt_path)
            plan_path = get_impl_path(wt_path, git_ops=ctx.git)
            json_response = _create_json_response(
                worktree_name=name,
                worktree_path=wt_path,
                branch_name=existing_branch,
                plan_file_path=plan_path,
                status="exists",
            )
            user_output(json_response)
            raise SystemExit(1)
        else:
            user_output(f"Worktree path already exists: {wt_path}")
            raise SystemExit(1)

    # Handle from-current-branch logic: switch current worktree first
    to_branch = None
    if from_current_branch:
        current_branch = Ensure.not_none(
            ctx.git.get_current_branch(ctx.cwd), "Unable to determine current branch"
        )

        # Determine preferred branch to checkout (prioritize Graphite parent)
        parent_branch = (
            ctx.graphite.get_parent_branch(ctx.git, repo.root, current_branch)
            if current_branch
            else None
        )

        if parent_branch:
            # Prefer Graphite parent branch
            to_branch = parent_branch
        elif ref:
            # Use ref if provided
            to_branch = ref
        else:
            # Fall back to default branch (main/master)
            to_branch = ctx.git.detect_trunk_branch(repo.root)

        # Check for edge case: can't move main to worktree then switch to main
        Ensure.invariant(
            current_branch != to_branch,
            f"Cannot use --from-current-branch when on '{current_branch}'.\n"
            f"The current branch cannot be moved to a worktree and then checked out again.\n\n"
            f"Alternatives:\n"
            f"  • Create a new branch: erk create {name}\n"
            f"  • Switch to a feature branch first, then use --from-current-branch\n"
            f"  • Use --from-branch to create from a different existing branch",
        )

        # Check if target branch is available (not checked out in another worktree)
        checkout_path = ctx.git.is_branch_checked_out(repo.root, to_branch)
        if checkout_path is not None:
            # Target branch is in use, fall back to detached HEAD
            ctx.git.checkout_detached(ctx.cwd, current_branch)
        else:
            # Target branch is available, checkout normally
            ctx.git.checkout_branch(ctx.cwd, to_branch)

        # Create worktree with existing branch
        add_worktree(
            ctx,
            repo.root,
            wt_path,
            branch=branch,
            ref=None,
            use_existing_branch=True,
            use_graphite=False,
            skip_remote_check=skip_remote_check,
        )
    elif from_branch:
        # Validate that we're not trying to create worktree for trunk branch
        if branch == trunk_branch:
            user_output(
                f'Error: Cannot create worktree for trunk branch "{trunk_branch}".\n'
                f"The trunk branch should be checked out in the root worktree.\n"
                f"To switch to {trunk_branch}, use:\n"
                f"  erk checkout root"
            )
            raise SystemExit(1)

        # Create worktree with existing branch
        add_worktree(
            ctx,
            repo.root,
            wt_path,
            branch=branch,
            ref=None,
            use_existing_branch=True,
            use_graphite=False,
            skip_remote_check=skip_remote_check,
        )
    elif linked_branch_name:
        # Issue-based worktree: use the branch created by gh issue develop
        use_graphite = ctx.global_config.use_graphite if ctx.global_config else False
        add_worktree(
            ctx,
            repo.root,
            wt_path,
            branch=linked_branch_name,
            ref=trunk_branch,  # Needed for Graphite tracking
            use_existing_branch=True,
            use_graphite=use_graphite,  # Respect global config
            skip_remote_check=skip_remote_check,
        )
    else:
        # Create worktree via git. If no branch provided, derive a sensible default.
        if branch is None:
            branch = default_branch_for_worktree(name)

        # Get graphite setting from global config
        use_graphite = ctx.global_config.use_graphite if ctx.global_config else False
        add_worktree(
            ctx,
            repo.root,
            wt_path,
            branch=branch,
            ref=ref,
            use_graphite=use_graphite,
            use_existing_branch=False,
            skip_remote_check=skip_remote_check,
        )

    # Write .env based on config (with project variables if applicable)
    project_root = wt_path / ctx.project.path_from_repo if ctx.project else None
    project_name = ctx.project.name if ctx.project else None
    env_content = make_env_content(
        cfg,
        worktree_path=wt_path,
        repo_root=repo.root,
        name=name,
        project_root=project_root,
        project_name=project_name,
    )
    (wt_path / ".env").write_text(env_content, encoding="utf-8")

    # Record project association if in a project context
    if ctx.project is not None:
        set_worktree_project(repo.repo_dir, name, ctx.project.path_from_repo)

    # Create impl folder if plan file provided
    # Track impl folder destination: set to .impl/ path only if
    # --from-plan or --from-issue was provided
    impl_folder_destination: Path | None = None
    if from_plan:
        # Read plan content from source file
        plan_content = from_plan.read_text(encoding="utf-8")

        # Create .impl/ folder in new worktree
        impl_folder_destination = create_impl_folder(wt_path, plan_content)

        # Handle --keep-plan flag
        if keep_plan:
            if not script and not output_json:
                user_output(f"Copied plan to {impl_folder_destination}")
        else:
            from_plan.unlink()  # Remove source file
            if not script and not output_json:
                user_output(f"Moved plan to {impl_folder_destination}")

    # Create impl folder if issue provided
    if from_issue:
        # Type narrowing: issue_info must be set if from_issue is True
        assert issue_info is not None, "issue_info must be set when from_issue is True"

        # Use issue body as plan content
        plan_content = issue_info.body

        # Create .impl/ folder in new worktree
        impl_folder_destination = create_impl_folder(wt_path, plan_content)

        # Create .impl/issue.json metadata
        issue_json_path = wt_path / ".impl" / "issue.json"
        issue_metadata = {
            "number": issue_info.number,
            "url": issue_info.url,
            "title": issue_info.title,
        }
        issue_json_path.write_text(json.dumps(issue_metadata, indent=2), encoding="utf-8")

        if not script and not output_json:
            user_output(f"Created worktree from issue #{issue_info.number}: {issue_info.title}")

    # Copy .impl directory if --copy-plan flag is set
    if copy_plan:
        import shutil

        impl_source = ctx.cwd / ".impl"
        impl_dest = wt_path / ".impl"

        # Copy entire directory
        shutil.copytree(impl_source, impl_dest)

        # Set impl_folder_destination for JSON response
        impl_folder_destination = impl_dest

        if not script and not output_json:
            user_output(
                "  "
                + click.style("✓", fg="green")
                + f" Copied .impl from {click.style(str(ctx.cwd), fg='yellow')}"
            )

    # Post-create commands (suppress output if JSON mode)
    if not no_post and cfg.post_create_commands:
        if not output_json:
            user_output("Running post-create commands...")
        run_commands_in_worktree(
            ctx=ctx,
            commands=cfg.post_create_commands,
            worktree_path=wt_path,
            shell=cfg.post_create_shell,
        )

    if script and not stay:
        script_content = render_navigation_script(
            wt_path,
            repo.root,
            comment="cd to new worktree",
            success_message="✓ Went to new worktree.",
        )
        result = ctx.script_writer.write_activation_script(
            script_content,
            command_name="create",
            comment=f"cd to {name}",
        )
        result.output_for_shell_integration()
    elif output_json:
        # Output JSON with worktree information
        json_response = _create_json_response(
            worktree_name=name,
            worktree_path=wt_path,
            branch_name=branch,
            plan_file_path=impl_folder_destination,
            status="created",
        )
        user_output(json_response)
    elif stay:
        # User explicitly opted out of navigation
        user_output(f"Created worktree at {wt_path} checked out at branch '{branch}'")
    else:
        # Shell integration not detected - provide setup instructions
        user_output(f"Created worktree at {wt_path} checked out at branch '{branch}'")
        user_output("\nShell integration not detected. Run 'erk init --shell' to set up.")
        user_output("Or use: source <(erk wt create --from-current-branch --script)")


def run_commands_in_worktree(
    *,
    ctx: ErkContext,
    commands: Iterable[str],
    worktree_path: Path,
    shell: str | None,
) -> None:
    """Run commands serially in the worktree directory.

    Each command is executed in its own subprocess. If `shell` is provided, commands
    run through that shell (e.g., "bash -lc <cmd>"). Otherwise, commands are tokenized
    via `shlex.split` and run directly.

    Args:
        ctx: Erk context
        commands: Iterable of commands to run
        worktree_path: Path to worktree where commands should run
        shell: Optional shell to use for command execution
    """

    for cmd in commands:
        # Output per-command diagnostic
        ctx.feedback.info(f"Running: {cmd}")
        cmd_list = [shell, "-lc", cmd] if shell else shlex.split(cmd)
        run_with_error_reporting(
            cmd_list,
            cwd=worktree_path,
            error_prefix="Post-create command failed",
            troubleshooting=[
                "The worktree was created successfully, but a post-create command failed",
                "You can still use the worktree or re-run the command manually",
            ],
        )
