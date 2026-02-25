"""Plan command group."""

from pathlib import Path

import click

from erk.cli.capability_check import is_learned_docs_available
from erk.cli.commands.plan.duplicate_check_cmd import duplicate_check_plan
from erk_shared.gateway.git.repo_ops.real import RealGitRepoOps


@click.group("plan")
def plan_group() -> None:
    """Manage implementation plans."""
    pass


plan_group.add_command(duplicate_check_plan)
if is_learned_docs_available(repo_ops=RealGitRepoOps(), cwd=Path.cwd()):
    from erk.cli.commands.plan.docs import docs_group
    from erk.cli.commands.plan.learn import learn_group

    plan_group.add_command(docs_group)
    plan_group.add_command(learn_group)
