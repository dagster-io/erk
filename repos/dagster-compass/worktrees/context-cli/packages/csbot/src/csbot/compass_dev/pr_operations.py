"""PR operations utility for squash-and-update-pr workflow."""

import json
import sys

import click

from csbot.compass_dev.pr_operations_logic import (
    auto_update_workflow,
    execute_updates,
    prepare_data,
    squash_push_draft_workflow,
)


@click.group()
def pr_ops():
    """PR operations utility for squash-and-update-pr workflow.

    Handles mechanical git/GitHub operations efficiently for PR management.
    Provides intelligent PR title generation, structured descriptions, and
    automated squashing with conflict resolution.
    """
    pass


@pr_ops.command()
def prepare():
    """Collect branch and PR information for analysis.

    Gathers comprehensive data about the current branch and associated PR:
    - Branch information from Graphite (parent, current)
    - PR details from GitHub (number, URL, status)
    - Commit analysis (count, details, file changes)
    - Automatic squashing if multiple commits exist

    Outputs JSON data structure for further processing or Claude analysis.
    """
    click.echo("🔍 Preparing PR data...", err=True)
    try:
        data = prepare_data()
        click.echo(json.dumps(data, indent=2))
    except SystemExit as e:
        sys.exit(e.code)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@pr_ops.command()
@click.option("--title", required=True, help="PR title")
@click.option("--description", required=True, help="PR description")
@click.option("--pr-url", required=True, help="PR URL")
def execute(title: str, description: str, pr_url: str):
    """Execute PR and commit updates with provided content.

    Updates both the GitHub PR and the local commit with:
    - New PR title and description
    - Enhanced commit message including PR URL
    - Consistent formatting and attribution

    This command is typically called after analysis/generation of content.
    """
    click.echo("⚡ Executing PR updates...", err=True)
    try:
        result = execute_updates(title, description, pr_url)

        if result.get("pr_updated"):
            click.echo("✅ PR updated successfully", err=True)
        else:
            click.echo("❌ PR update failed", err=True)

        if result.get("commit_updated"):
            click.echo("✅ Commit updated successfully", err=True)
        else:
            click.echo("❌ Commit update failed", err=True)

    except SystemExit as e:
        sys.exit(e.code)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@pr_ops.command()
def auto_update():
    """Automatically prepare data and prompt for Claude analysis.

    Comprehensive workflow that:
    1. Collects branch and PR information
    2. Performs automatic squashing if needed
    3. Outputs data in Claude-friendly format
    4. Provides analysis guidelines for intelligent PR content generation

    Designed to work with AI assistance for optimal PR titles and descriptions.

    **PR Title Intelligence:**
    - Analyzes commit subjects and file changes
    - Handles generic subjects (ci, fix, update, cp, wip, tmp)
    - Suggests context-appropriate titles:
      * Renames: "Rename [old] to [new] across codebase"
      * Workflows: "Enhance CI/CD workflows"
      * Python majority: "Update Python implementation"
      * Config/docs: "Update configuration and documentation"

    **PR Description Structure:**
    - Summary section with commit context
    - Key changes grouped by operation type
    - Commit details and file change statistics
    - Claude Code attribution and co-authorship
    """
    click.echo("🤖 Starting auto-update workflow...", err=True)
    try:
        data = auto_update_workflow()

        # Output data for analysis
        click.echo("=== PR DATA FOR ANALYSIS ===", err=True)
        click.echo(json.dumps(data, indent=2))
        click.echo("=== END PR DATA ===", err=True)

        click.echo(
            """
📋 Please analyze the above data and provide:
1. An intelligent PR title based on the commit and file changes
2. A structured PR description with summary, key changes, and attribution

Use the analysis guidelines:
- If commit subject is generic (ci, fix, update, cp, wip, tmp), analyze file changes
- For renames: 'Rename [old] to [new] across codebase'
- For workflows: 'Enhance CI/CD workflows'
- For Python majority: 'Update Python implementation'
- For config/docs: 'Update configuration and documentation'

Then call: compass-dev pr-operations execute --title='...' --description='...' --pr-url='...'
""",
            err=True,
        )

    except SystemExit as e:
        sys.exit(e.code)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@pr_ops.command()
def squash_push_draft():
    """Squash commits and prepare for draft PR submission.

    Streamlined workflow for creating draft PRs:

    **For Existing PRs:**
    1. Squash multiple commits into single commit
    2. Collect comprehensive PR data
    3. Output analysis-ready data structure
    4. Prompt for AI-generated content and draft submission

    **For New PRs:**
    1. Squash commits if needed
    2. Prepare branch and commit information
    3. Guide through manual PR creation process
    4. Provide templates for title and description generation

    **Draft PR Benefits:**
    - Allows iterative refinement before review
    - Triggers CI/CD for early feedback
    - Enables team collaboration on content
    - Maintains clean commit history

    Use this when you want to create or update a PR in draft state for
    further refinement before marking as ready for review.
    """
    click.echo("📝 Preparing squash and draft workflow...", err=True)
    try:
        data = squash_push_draft_workflow()

        # Output data for analysis
        click.echo("=== PR DATA FOR CLAUDE ANALYSIS ===", err=True)
        click.echo(json.dumps(data, indent=2))
        click.echo("=== END PR DATA ===", err=True)

        # Check if PR exists in the data
        has_pr = "pr_info" in data

        if has_pr:
            click.echo(
                """
📋 Claude: Please analyze the above data following the same guidelines as auto-update:

**PR Title Logic**:
- If subject is generic (ci, fix, update, cp, wip, tmp), analyze file changes:
  - Rename operations: "Rename [old] to [new] across codebase"
  - Workflow files: "Enhance CI/CD workflows"
  - Python files majority: "Update Python implementation"
  - Config/docs majority: "Update configuration and documentation"
- Otherwise: use commit subject as title

**PR Description**: Create structured description with summary, key changes, commit hash,
and Claude attribution

Then proceed with:
1. Update PR title/description using the execute command
2. Submit as draft with `gt submit -n -d`
""",
                err=True,
            )
        else:
            click.echo(
                """
📋 Claude: Please analyze the above data following the same guidelines as auto-update:

**PR Title Logic**:
- If subject is generic (ci, fix, update, cp, wip, tmp), analyze file changes:
  - Rename operations: "Rename [old] to [new] across codebase"
  - Workflow files: "Enhance CI/CD workflows"
  - Python files majority: "Update Python implementation"
  - Config/docs majority: "Update configuration and documentation"
- Otherwise: use commit subject as title

**PR Description**: Create structured description with summary, key changes, commit hash,
and Claude attribution

Then create the draft PR using: gh pr create --title='...' --body='...' --draft
""",
                err=True,
            )

    except SystemExit as e:
        sys.exit(e.code)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# Rename the group to be the main command
pr_operations = pr_ops

# Update the group docstring
pr_operations.__doc__ = """PR operations utility for squash-and-update-pr workflow.

    Advanced PR management tool that handles:
    - Intelligent squashing of multiple commits
    - AI-powered PR title and description generation
    - Mechanical git/GitHub operations
    - Draft PR creation and updates
    - Conflict resolution and error handling

    **Common Workflows:**

    1. **Auto-update existing PR:**
       `compass-dev pr-operations auto-update`

    2. **Create draft PR from commits:**
       `compass-dev pr-operations squash-push-draft`

    3. **Manual content execution:**
       ```
       compass-dev pr-operations prepare
       # (analyze output)
       compass-dev pr-operations execute --title="..." --description="..." --pr-url="..."
       ```

    **Prerequisites:**
    - GitHub CLI (`gh`) installed and authenticated
    - Graphite CLI (`gt`) installed and configured
    - Current branch tracked by Graphite
    - Existing PR (for update operations)

    **Integration with AI:**
    This tool is designed to work seamlessly with Claude Code for:
    - Intelligent analysis of commit patterns
    - Context-aware PR title generation
    - Structured description formatting
    - Best practices enforcement
    """
