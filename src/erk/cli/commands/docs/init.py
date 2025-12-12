"""Initialize docs/agent directory with template files.

This command creates the docs/agent/ directory structure with starter templates
for agent documentation (glossary, conventions, guide).
"""

import click

from erk.kits.cli.output import user_output
from erk.kits.operations.agent_docs import init_docs_agent
from erk_shared.context.helpers import require_project_root


@click.command(name="init")
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Overwrite existing template files.",
)
@click.pass_context
def init_command(ctx: click.Context, *, force: bool) -> None:
    """Initialize docs/agent directory with template files.

    Creates docs/agent/ directory if it doesn't exist and adds starter
    template files:

    \b
    - glossary.md: Project terminology definitions
    - conventions.md: Coding standards and conventions
    - guide.md: How to write agent documentation

    Each template includes valid frontmatter (title, read_when) so agents
    can immediately use the documentation.

    Use --force to overwrite existing files with fresh templates.
    """
    project_root = require_project_root(ctx)

    # Initialize docs/agent
    init_result = init_docs_agent(project_root, force=force)

    # Report results
    if init_result.created:
        user_output(f"Created {len(init_result.created)} file(s):")
        for path in init_result.created:
            user_output(f"  + {path}")
        user_output()

    if init_result.overwritten:
        user_output(f"Overwrote {len(init_result.overwritten)} file(s):")
        for path in init_result.overwritten:
            user_output(f"  ~ {path}")
        user_output()

    if init_result.skipped:
        user_output(f"Skipped {len(init_result.skipped)} existing file(s):")
        for path in init_result.skipped:
            user_output(f"  - {path}")
        user_output()

    # Summary and next steps
    total_written = len(init_result.created) + len(init_result.overwritten)
    if total_written > 0:
        msg = f"✓ Initialized docs/agent with {total_written} file(s)"
        user_output(click.style(msg, fg="green"))
        user_output()
        user_output("Next steps:")
        user_output("  1. Customize the template files for your project")
        user_output("  2. Run 'erk docs sync' to generate index.md")
        user_output("  3. Run 'erk docs validate' to check frontmatter")
    elif init_result.skipped:
        user_output(click.style("ℹ️  docs/agent already exists with content", fg="cyan"))
        user_output("Use --force to overwrite with fresh templates")
    else:
        user_output(click.style("✓ docs/agent already up to date", fg="green"))
