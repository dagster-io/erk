# Plan: Optimize /erk:plan-save Command Performance

## Enrichment Details

### Process Summary

- **Mode**: enriched
- **Guidance applied**: no
- **Guidance text**: (none provided)
- **Questions asked**: 2
- **Context categories extracted**: 8 of 8

### Clarifications Made

1. **Input method**: User specified that optimal markdown orchestration is the priority - this confirms the combined command should eliminate the temp file entirely by reading from stdin, which is the most efficient path for markdown orchestration (no disk I/O).

2. **Deprecation**: User confirmed immediate removal of old commands - no deprecation period needed. This simplifies Phase 3 to just deleting the old files rather than adding deprecation warnings.

### Context Categories Populated

- [x] API/Tool Quirks
- [x] Architectural Insights
- [x] Domain Logic & Business Rules
- [x] Complex Reasoning
- [x] Known Pitfalls
- [x] Raw Discoveries Log
- [x] Planning Artifacts
- [x] Implementation Risks

---

## Goal

Speed up the `/erk:plan-save` command through three optimizations:
1. Use haiku model (simple orchestration task)
2. Combine two kit CLI commands into one (eliminate temp file, reduce overhead)
3. Simplify output instructions (reduce agent work)

## Context

Current `/erk:plan-save` flow:
```bash
# Validate prerequisites
git rev-parse --is-inside-work-tree && gh auth status

# Call 1: Extract plan from ~/.claude/plans/
dot-agent run erk save-plan-from-session --extract-only --format json

# Detect enrichment (bash grep)
grep -q "## Enrichment Details"

# Write temp file
cat > $temp_file <<< "$plan_content"

# Call 2: Create GitHub issue
dot-agent run erk create-enriched-plan-from-context --plan-file $temp_file

# Parse and display results
```

**Call Site Analysis:**
- `save-plan-from-session` is used by:
  - `/erk:plan-save` (with --extract-only)
  - `/erk:plan-save-enriched` (with --extract-only)
  - Disk-saving mode (without --extract-only) is **NOT used** by any command

- `create-enriched-plan-from-context` is used by:
  - `/erk:plan-save` ONLY
  - `/erk:plan-save-enriched` uses `gh issue create` directly instead

## Implementation Plan

### Phase 1: Add Haiku Model (Quick Win)

**File:** `.claude/commands/erk/plan-save.md`

Add to frontmatter:
```yaml
---
description: Save plan from ~/.claude/plans/ to GitHub issue (no enrichment)
model: haiku
---
```

**Rationale:** This command does simple bash orchestration + JSON parsing - perfect for haiku.

**Testing:** Run `/erk:plan-save` and verify it still works correctly.

---

### Phase 2: Create Combined Kit CLI Command

Create new command that does: extract plan from `~/.claude/plans/` -> create GitHub issue in one shot, reading plan from stdin.

#### Step 2.1: Create new kit CLI command

**File:** `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/plan_save_to_issue.py`

```python
"""Extract plan from ~/.claude/plans/ and create GitHub issue in one operation.

Usage:
    dot-agent run erk plan-save-to-issue [--format json|display]

This command combines plan extraction and issue creation:
1. Extract latest plan from ~/.claude/plans/
2. Create GitHub issue with plan content (schema v2 format)

Output:
    --format json (default): {"success": true, "issue_number": N, "issue_url": "...", "title": "..."}
    --format display: Formatted text ready for display

Exit Codes:
    0: Success - plan extracted and issue created
    1: Error - no plan found, gh failure, etc.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import click
from erk_shared.github.metadata import (
    format_plan_content_comment,
    format_plan_header_body,
)
from erk_shared.naming import sanitize_worktree_name
from erk_shared.plan_utils import extract_title_from_plan

from dot_agent_kit.context_helpers import require_github_issues, require_repo_root
from dot_agent_kit.data.kits.erk.session_plan_extractor import get_latest_plan


@click.command(name="plan-save-to-issue")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "display"]),
    default="json",
    help="Output format: json (default) or display (formatted text)",
)
@click.pass_context
def plan_save_to_issue(ctx: click.Context, output_format: str) -> None:
    """Extract plan from ~/.claude/plans/ and create GitHub issue.

    Combines plan extraction and issue creation in a single operation.
    Uses schema v2 format (metadata in body, plan in first comment).
    """
    # Get GitHub Issues from context
    github = require_github_issues(ctx)
    repo_root = require_repo_root(ctx)
    cwd = Path.cwd()

    # Step 1: Extract latest plan from ~/.claude/plans/
    plan = get_latest_plan(str(cwd), session_id=None)

    if not plan:
        if output_format == "display":
            click.echo("Error: No plan found in ~/.claude/plans/", err=True)
            click.echo("\nTo fix:", err=True)
            click.echo("1. Create a plan (enter Plan mode if needed)", err=True)
            click.echo("2. Exit Plan mode using ExitPlanMode tool", err=True)
            click.echo("3. Run this command again", err=True)
        else:
            click.echo(json.dumps({"success": False, "error": "No plan found in ~/.claude/plans/"}))
        raise SystemExit(1)

    # Step 2: Extract title
    title = extract_title_from_plan(plan)

    # Step 3: Get GitHub username
    username = github.get_current_username()
    if username is None:
        error_msg = "Could not get GitHub username (gh CLI not authenticated?)"
        if output_format == "display":
            click.echo(f"Error: {error_msg}", err=True)
        else:
            click.echo(json.dumps({"success": False, "error": error_msg}))
        raise SystemExit(1)

    # Step 4: Prepare metadata
    worktree_name = sanitize_worktree_name(title)
    created_at = datetime.now(UTC).isoformat()
    formatted_body = format_plan_header_body(
        created_at=created_at,
        created_by=username,
        worktree_name=worktree_name,
    )

    # Step 5: Ensure erk-plan label exists
    try:
        github.ensure_label_exists(
            repo_root=repo_root,
            label="erk-plan",
            description="Implementation plan for manual execution",
            color="0E8A16",
        )
    except RuntimeError as e:
        error_msg = f"Failed to ensure label exists: {e}"
        if output_format == "display":
            click.echo(f"Error: {error_msg}", err=True)
        else:
            click.echo(json.dumps({"success": False, "error": error_msg}))
        raise SystemExit(1) from e

    # Step 6: Create issue
    try:
        result = github.create_issue(repo_root, title, formatted_body, labels=["erk-plan"])
    except RuntimeError as e:
        error_msg = f"Failed to create GitHub issue: {e}"
        if output_format == "display":
            click.echo(f"Error: {error_msg}", err=True)
        else:
            click.echo(json.dumps({"success": False, "error": error_msg}))
        raise SystemExit(1) from e

    # Step 7: Add plan as first comment
    plan_comment = format_plan_content_comment(plan.strip())
    try:
        github.add_comment(repo_root, result.number, plan_comment)
    except RuntimeError as e:
        # Issue created but comment failed - partial success
        error_msg = f"Issue #{result.number} created but failed to add plan comment: {e}"
        if output_format == "display":
            click.echo(f"Warning: {error_msg}", err=True)
            click.echo(f"Please manually add plan content to: {result.url}", err=True)
        else:
            click.echo(json.dumps({
                "success": False,
                "error": error_msg,
                "issue_number": result.number,
                "issue_url": result.url,
            }))
        raise SystemExit(1) from e

    # Step 8: Output success
    # Detect enrichment status for informational output
    is_enriched = "## Enrichment Details" in plan

    if output_format == "display":
        click.echo(f"Plan saved to GitHub issue #{result.number}")
        click.echo(f"URL: {result.url}")
        click.echo(f"Enrichment: {'Yes' if is_enriched else 'No'}")
    else:
        click.echo(json.dumps({
            "success": True,
            "issue_number": result.number,
            "issue_url": result.url,
            "title": title,
            "enriched": is_enriched,
        }))
```

#### Step 2.2: Register new command in kit manifest

**File:** `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit.toml`

Add to `[kit_cli_commands]` section:
```toml
plan-save-to-issue = "kit_cli_commands/erk/plan_save_to_issue.py"
```

#### Step 2.3: Create unit tests

**File:** `packages/dot-agent-kit/tests/unit/kits/erk/test_plan_save_to_issue.py`

```python
"""Unit tests for plan-save-to-issue command."""

import json
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner
from erk_shared.github.issues import FakeGitHubIssues

from dot_agent_kit.context import DotAgentContext
from dot_agent_kit.data.kits.erk.kit_cli_commands.erk.plan_save_to_issue import (
    plan_save_to_issue,
)


def test_plan_save_to_issue_success() -> None:
    """Test successful plan extraction and issue creation."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    plan = "# My Feature\n\n- Step 1\n- Step 2"

    with patch(
        "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.plan_save_to_issue.get_latest_plan",
        return_value=plan,
    ):
        result = runner.invoke(
            plan_save_to_issue,
            ["--format", "json"],
            obj=DotAgentContext.for_test(github_issues=fake_gh),
        )

    assert result.exit_code == 0, f"Failed: {result.output}"
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["issue_number"] == 1
    assert output["title"] == "My Feature"
    assert output["enriched"] is False


def test_plan_save_to_issue_enriched_plan() -> None:
    """Test detection of enriched plan."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    plan = "# My Feature\n\n## Enrichment Details\n\nContext here"

    with patch(
        "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.plan_save_to_issue.get_latest_plan",
        return_value=plan,
    ):
        result = runner.invoke(
            plan_save_to_issue,
            ["--format", "json"],
            obj=DotAgentContext.for_test(github_issues=fake_gh),
        )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["enriched"] is True


def test_plan_save_to_issue_no_plan() -> None:
    """Test error when no plan found."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    with patch(
        "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.plan_save_to_issue.get_latest_plan",
        return_value=None,
    ):
        result = runner.invoke(
            plan_save_to_issue,
            ["--format", "json"],
            obj=DotAgentContext.for_test(github_issues=fake_gh),
        )

    assert result.exit_code == 1
    output = json.loads(result.output)
    assert output["success"] is False
    assert "No plan found" in output["error"]


def test_plan_save_to_issue_schema_v2() -> None:
    """Verify schema v2 format (metadata in body, plan in comment)."""
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()

    plan = "# Test Plan\n\n- Step 1"

    with patch(
        "dot_agent_kit.data.kits.erk.kit_cli_commands.erk.plan_save_to_issue.get_latest_plan",
        return_value=plan,
    ):
        result = runner.invoke(
            plan_save_to_issue,
            [],
            obj=DotAgentContext.for_test(github_issues=fake_gh),
        )

    assert result.exit_code == 0

    # Verify schema v2: metadata in body
    assert len(fake_gh.created_issues) == 1
    _title, body, _labels = fake_gh.created_issues[0]
    assert "plan-header" in body
    assert "schema_version: '2'" in body
    assert "Step 1" not in body  # Plan NOT in body

    # Verify schema v2: plan in first comment
    assert len(fake_gh.added_comments) == 1
    _issue_num, comment = fake_gh.added_comments[0]
    assert "Step 1" in comment
```

---

### Phase 3: Update /erk:plan-save to Use Combined Command

#### Step 3.1: Update command markdown

**File:** `.claude/commands/erk/plan-save.md`

Update to use single kit CLI call:

**Architecture section:**
```
/erk:plan-save (orchestrator)
  |
  +-> Validate prerequisites (git repo, gh auth)
  +-> Call kit CLI: dot-agent run erk plan-save-to-issue --format json
  |     |
  |     +-> Extracts plan from ~/.claude/plans/
  |     +-> Creates GitHub issue (schema v2)
  |     +-> Returns JSON: {issue_number, issue_url, title, enriched}
  +-> Display results with enrichment status
```

**Step 2 (replace current Steps 2-5):**
```markdown
### Step 2: Extract Plan and Create GitHub Issue

Use the combined kit CLI command:

\`\`\`bash
result=$(dot-agent run erk plan-save-to-issue --format json 2>&1)
\`\`\`

**Parse the result:**

\`\`\`bash
if echo "$result" | jq -e '.success' > /dev/null 2>&1; then
    # SUCCESS
    issue_number=$(echo "$result" | jq -r '.issue_number')
    issue_url=$(echo "$result" | jq -r '.issue_url')
    title=$(echo "$result" | jq -r '.title')
    enriched=$(echo "$result" | jq -r '.enriched')

    if [ "$enriched" = "true" ]; then
        enrichment_status="Enriched"
        enrichment_note="This plan includes semantic context (8 categories)"
    else
        enrichment_status="Raw"
        enrichment_note="This plan has no enrichment. Use /erk:plan-save-enriched to add context."
    fi
else
    # FAILURE
    error_msg=$(echo "$result" | jq -r '.error // "Unknown error"')
    echo "Error: $error_msg"
fi
\`\`\`
```

**Remove:**
- Step 3 (Detect Enrichment Status) - now in kit CLI output
- Step 4 (Save Plan to Temporary File) - eliminated
- Step 5 (Create GitHub Issue via Kit CLI) - merged into Step 2

**Renumber:**
- Old Step 6 becomes new Step 3 (Display Success Output)

#### Step 3.2: Simplify output instructions

Reduce Step 6 (now Step 3) to simpler output:

```markdown
### Step 3: Display Success Output

\`\`\`
Plan saved to GitHub issue

**Enrichment status:** [Enriched/Raw]
[enrichment_note]

**Issue:** #[issue_number] - [title]
**URL:** [issue_url]

**Next steps:**
- View: gh issue view [issue_number]
- Implement: erk implement [issue_number]
- Submit to queue: erk submit [issue_number]
\`\`\`
```

---

### Phase 4: Delete Old Kit CLI Commands

Since no deprecation period is needed:

#### Step 4.1: Delete save-plan-from-session

**Delete file:** `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/plan_save_from_session.py`

**Delete tests:** Any test files for this command

**Remove from kit.toml:** Remove the command registration

#### Step 4.2: Delete create-enriched-plan-from-context

**Delete file:** `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/create_enriched_plan_from_context.py`

**Delete tests:** `packages/dot-agent-kit/tests/unit/kits/erk/test_create_enriched_plan_from_context.py`

**Remove from kit.toml:** Remove the command registration

#### Step 4.3: Update /erk:plan-save-enriched

This command currently uses `save-plan-from-session --extract-only`. Update it to either:
1. Use the new `plan-save-to-issue` command (if appropriate), OR
2. Read directly from `~/.claude/plans/` via inline logic

Review `/erk:plan-save-enriched` and `extract-plan-from-session.md` include file.

**File to update:** `.claude/docs/erk/includes/planning/extract-plan-from-session.md`

Replace content with direct plans directory access or update to new command.

---

### Phase 5: Verification

1. Run `/erk:plan-save` - verify:
   - Uses haiku model (check model in response)
   - Single kit CLI call (no temp file)
   - Correct enrichment detection
   - Proper output format

2. Run `/erk:plan-save-enriched` - verify it still works after include update

3. Run tests: `pytest packages/dot-agent-kit/tests/unit/kits/erk/test_plan_save_to_issue.py`

4. Verify old commands removed from `dot-agent run erk --help`

---

## Context & Understanding

### API/Tool Quirks

- **Schema v2 format**: GitHub issues use a two-step creation: body has metadata only, plan content goes in first comment. This is intentional for fast querying of metadata.
- **Click context passing**: Kit CLI commands receive `DotAgentContext` via `@click.pass_context` and `ctx.obj`. The context provides `github_issues` and `repo_root` through helper functions like `require_github_issues()`.
- **Session ID discovery**: The `get_session_context()` function checks both `SESSION_CONTEXT` (format: `session_id=<uuid>`) and `CLAUDE_SESSION_ID` environment variables, though these are now unused since we read from `~/.claude/plans/` directly.

### Architectural Insights

- **Command-to-Kit-CLI separation**: Slash commands (`.claude/commands/`) are markdown orchestrators that call kit CLI commands (`dot-agent run erk <cmd>`). This separates presentation from logic.
- **include files pattern**: Common steps are factored into `.claude/docs/erk/includes/` for reuse across commands. The `validate-prerequisites.md` and `extract-plan-from-session.md` are examples.
- **FakeGitHubIssues for testing**: Tests use `FakeGitHubIssues` from `erk_shared.github.issues` which tracks `created_issues`, `added_comments`, and `created_labels` for assertions.
- **LBYL pattern**: All kit CLI commands follow Look Before You Leap - explicit validation at boundaries, no bare try/except.

### Domain Logic & Business Rules

- **`erk-plan` label required**: All plan issues must have the `erk-plan` label. The kit CLI ensures the label exists before creating issues.
- **Enrichment detection**: A plan is "enriched" if it contains the `## Enrichment Details` section. This is a simple string check.
- **Title extraction priority**: H1 -> H2 -> first non-empty line, with 100 char limit (GitHub recommendation).
- **Worktree name derivation**: The `sanitize_worktree_name()` function derives a git-safe branch name from the plan title.

### Complex Reasoning

- **Why eliminate temp file**: The current flow writes plan content to a temp file just to pass it to another command. By combining commands, we eliminate disk I/O and process spawning overhead. The combined command reads from `~/.claude/plans/` directly.
- **Why haiku model**: The `/erk:plan-save` command does simple orchestration (run command, parse JSON, format output). No complex reasoning needed - haiku is sufficient and faster.
- **Why immediate deletion**: The old commands have single callers that we're updating. No external consumers exist. A deprecation period would add complexity without benefit.

### Known Pitfalls

- **Don't forget kit.toml registration**: New kit CLI commands must be registered in `kit.toml` or they won't be discoverable via `dot-agent run`.
- **Test isolation with mocks**: When testing commands that read from `~/.claude/plans/`, mock `get_latest_plan()` rather than creating actual files, to avoid test pollution.
- **JSON output on stdout only**: Kit CLI commands must output JSON to stdout and errors to stderr. Mixing them breaks parsing.
- **Exit codes matter**: Exit code 0 for success, 1 for error. The orchestrating command relies on these.

### Raw Discoveries Log

- `plan_save_from_session.py` has unused disk-saving mode (no `--extract-only` callers)
- `create_enriched_plan_from_context.py` is only called by `/erk:plan-save`
- `/erk:plan-save-enriched` uses `gh issue create` directly, not the kit CLI command
- The `session_plan_extractor.py` module is simple: it just reads the most recently modified `.md` file from `~/.claude/plans/`
- Haiku model is already used in `launch-plan-extractor-agent.md` include
- `require_github_issues()` and `require_repo_root()` are the standard context helpers
- Schema v2 uses `format_plan_header_body()` and `format_plan_content_comment()` from `erk_shared.github.metadata`

### Planning Artifacts

- **Files examined**:
  - `.claude/commands/erk/plan-save.md` (298 lines) - main command to optimize
  - `.claude/commands/erk/plan-save-enriched.md` (279 lines) - related command
  - `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/plan_save_from_session.py` (180 lines) - command to replace
  - `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/create_enriched_plan_from_context.py` (138 lines) - command to replace
  - `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/session_plan_extractor.py` (83 lines) - plan extraction logic to reuse
  - `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/plan_utils.py` (187 lines) - utility functions
  - `packages/dot-agent-kit/tests/unit/kits/erk/test_create_enriched_plan_from_context.py` (285 lines) - test patterns to follow
  - `.claude/docs/erk/includes/planning/validate-prerequisites.md` - include file
  - `.claude/docs/erk/includes/planning/extract-plan-from-session.md` - include file to update
  - `.claude/docs/erk/includes/planning/launch-plan-extractor-agent.md` - haiku model reference

- **Commands run**:
  - `ls` to discover kit CLI command files
  - `grep` to find model references and call sites

### Implementation Risks

- **Include file dependency**: The `extract-plan-from-session.md` include is used by multiple commands. Updating it affects all callers - must verify `/erk:plan-save-enriched` still works.
- **Test coverage**: New command needs comprehensive tests covering success, failure, schema v2 format, and enrichment detection.
- **Kit reinstall required**: After modifying `kit.toml`, users may need to reinstall the kit for changes to take effect.
- **Breaking change**: Removing old commands is a breaking change if any external scripts depend on them. The call site analysis shows no external usage, but this should be verified.
