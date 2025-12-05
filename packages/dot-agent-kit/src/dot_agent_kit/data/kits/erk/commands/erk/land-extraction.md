---
description: Non-interactive extraction plan creation for erk pr land
---

# /erk:land-extraction

Creates an extraction plan during `erk pr land` flow. This command runs non-interactively, auto-selecting ALL sessions and including ALL suggestions without user confirmation.

**This command is designed to be invoked by `erk pr land`, not by users directly.**

## Usage

This command is invoked automatically by `erk pr land` after merging a PR:

```bash
claude --print --verbose --permission-mode bypassPermissions --output-format stream-json /erk:land-extraction
```

## Differences from /erk:create-extraction-plan

| Aspect | /erk:create-extraction-plan | /erk:land-extraction |
|--------|----------------------------|----------------------|
| Session selection | Interactive prompt | Auto-select ALL sessions |
| Suggestion confirmation | Asks user to confirm | Includes ALL suggestions |
| Execution mode | Interactive | Non-interactive (`--print`) |
| Use case | Manual extraction | Automated during `erk pr land` |

---

## Agent Instructions

You are creating an extraction plan non-interactively during `erk pr land`. Follow these steps:

### Step 1: Discover Sessions

Run the session discovery helper with size filtering:

```bash
dot-agent run erk list-sessions --min-size 1024
```

The JSON output includes:

- `branch_context.is_on_trunk`: Whether on main/master branch
- `current_session_id`: Current session ID from SESSION_CONTEXT env
- `sessions`: List of recent sessions with metadata (only meaningful sessions >= 1KB)
- `project_dir`: Path to session logs
- `filtered_count`: Number of tiny sessions filtered out

**IMPORTANT**: This command runs non-interactively. Auto-select ALL sessions without prompting.

If sessions are found, briefly output:

> "Auto-selected [N] session(s) for extraction analysis"

If no meaningful sessions exist (all filtered as tiny), output:

> "No meaningful sessions found. Skipping extraction."

Then exit successfully (no error).

### Step 2: Load and Preprocess Sessions

For each session, preprocess the session logs:

```bash
dot-agent run erk preprocess-session <project-dir>/<session-id>.jsonl --stdout
```

Load all sessions - do not skip any.

### Step 3: Verify Existing Documentation

Before analyzing gaps, scan the project for existing documentation:

```bash
# Check for existing agent docs
ls -la docs/agent/ 2>/dev/null || echo "No docs/agent/ directory"

# Check for existing skills
ls -la .claude/skills/ 2>/dev/null || echo "No .claude/skills/ directory"

# Check root-level docs
ls -la *.md README* CONTRIBUTING* 2>/dev/null
```

Create a mental inventory of what's already documented.

### Steps 4-7: Analyze Sessions

@../../docs/erk/includes/extract-docs-analysis-shared.md

### Step 8: Include ALL Suggestions

**CRITICAL**: This command runs non-interactively. Do NOT prompt for confirmation.

Include ALL Category A and Category B findings in the extraction plan. Users will filter suggestions later when implementing the extraction plan.

### Step 9: Format Plan Content

Format all suggestions as an implementation plan with this structure:

- **Objective**: Brief statement of what documentation will be added/improved
- **Source Information**: Session ID(s) that were analyzed
- **Documentation Items**: Each suggestion should include:
  - Type (Category A or B)
  - Location (where in the docs structure)
  - Action (add, update, create)
  - Priority (based on effort and impact)
  - Content (the actual draft content)

### Step 10: Create Extraction Plan Issue

**CRITICAL: Use this exact CLI command. Do NOT use `gh issue create` directly.**

Get the session ID from the `SESSION_CONTEXT` reminder in your conversation context.

```bash
dot-agent run erk create-extraction-plan \
    --plan-content="<the formatted plan content>" \
    --session-id="<session-id-from-SESSION_CONTEXT>" \
    --extraction-session-ids="<comma-separated-session-ids-that-were-analyzed>"
```

This command automatically:

1. Writes plan to `.erk/scratch/<session-id>/extraction-plan.md`
2. Creates GitHub issue with `erk-plan` + `erk-extraction` labels
3. Sets `plan_type: extraction` in plan-header metadata

### Step 11: Output Result

Output a brief summary suitable for non-interactive execution:

```
Extraction plan created: #<issue_number>
  Sessions analyzed: <N>
  Suggestions: <N> Category A, <N> Category B
```

If no suggestions were identified, output:

```
No documentation gaps identified. Skipping extraction plan creation.
```

### Error Handling

If any step fails, output a clear error message and exit with non-zero status. The `erk pr land` command will halt before deleting the worktree, allowing manual investigation.

---

## Output Format

This command produces minimal output suitable for non-interactive execution:

- Progress indicators are brief
- Final output is a single summary line
- Errors are clear and actionable
