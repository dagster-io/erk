"""Clean up .erk/impl-context/ staging directory before implementation.

Replaces the inline bash logic in plan-implement.md Step 2d.
Removes the directory from filesystem, stages the deletions via git add,
commits, and pushes to remote.

Usage:
    erk exec cleanup-impl-context

Output:
    JSON with cleanup result:
    {"cleaned": true}
    {"cleaned": false, "reason": "not_found"}

Exit Codes:
    0: Always (idempotent - safe to run when directory doesn't exist)

Examples:
    $ erk exec cleanup-impl-context
    {"cleaned": true}
"""

import json

import click

from erk_shared.context.helpers import require_cwd, require_git, require_repo_root
from erk_shared.impl_context import impl_context_exists, remove_impl_context


@click.command(name="cleanup-impl-context")
@click.pass_context
def cleanup_impl_context(ctx: click.Context) -> None:
    """Clean up .erk/impl-context/ staging directory.

    Removes the .erk/impl-context/ directory from the filesystem, stages
    the deletions with git add, commits, and pushes to remote. This is
    idempotent - if the directory doesn't exist, reports not_found and exits 0.

    Two-phase cleanup: shutil.rmtree (via remove_impl_context) removes files,
    then git add stages the deletions for commit.
    """
    cwd = require_cwd(ctx)
    repo_root = require_repo_root(ctx)
    git = require_git(ctx)

    if not impl_context_exists(repo_root):
        click.echo(json.dumps({"cleaned": False, "reason": "not_found"}))
        return

    # Phase 1: Remove from filesystem
    remove_impl_context(repo_root)

    # Phase 2: Stage deletions, commit, and push
    git.commit.stage_files(repo_root, [".erk/impl-context/"])
    git.commit.commit(repo_root, "Remove .erk/impl-context/ before implementation")

    current_branch = git.branch.get_current_branch(cwd)
    if current_branch is not None:
        git.remote.push_to_remote(
            repo_root, "origin", current_branch, set_upstream=False, force=False
        )

    click.echo(json.dumps({"cleaned": True}))
