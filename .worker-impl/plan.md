# Plan: Implement `erk exec objective-roadmap check`

Part of Objective #6295, Step 1.1

## Goal

Create `erk exec objective-roadmap check <N>` that regex-parses an objective's roadmap tables and returns structured JSON with phases, steps, statuses, next step, and validation errors.

## Design Decisions (from Objective)

- **Regex-based parser** — no LLM inference, no complex type hierarchies
- **Inline implementation** — parser logic lives in the exec script, not a separate library
- **Plain number step IDs** — `{phase}.{step}` format (e.g., `1.1`, `2.3`). Accept letter-style (`1A.1`) with a warning
- **Checkpoint pattern** — structured errors guide the agent to fix markdown

## Output JSON Schema

```json
{
  "success": true,
  "issue_number": 6295,
  "title": "Objective: ...",
  "phases": [
    {
      "number": 1,
      "name": "Check Command",
      "steps": [
        {
          "id": "1.1",
          "description": "Implement erk exec objective-roadmap check...",
          "status": "pending",
          "pr": null
        },
        {
          "id": "1.2",
          "description": "Tests: well-formed objective...",
          "status": "done",
          "pr": "#6300"
        }
      ]
    }
  ],
  "summary": {
    "total_steps": 10,
    "pending": 8,
    "done": 1,
    "in_progress": 1,
    "blocked": 0,
    "skipped": 0
  },
  "next_step": {
    "id": "1.1",
    "description": "Implement erk exec...",
    "phase": "Check Command"
  },
  "validation_errors": []
}
```

On validation errors (malformed table):
```json
{
  "success": false,
  "issue_number": 6295,
  "title": "Objective: ...",
  "validation_errors": [
    "Phase 2 table row 3 has 3 columns, expected 4",
    "Step ID '1A.1' uses letter format — prefer plain numbers (1.1)"
  ]
}
```

Note: Letter-format step IDs are warnings, not errors — `success` stays `true` if everything else is valid.

## Status Inference Rules

| PR Column    | Status Column          | Result        |
|-------------|------------------------|---------------|
| (empty)     | not blocked/skipped    | `pending`     |
| `#N`        | not blocked/skipped    | `done`        |
| `plan #N`   | not blocked/skipped    | `in_progress` |
| (any)       | `blocked`              | `blocked`     |
| (any)       | `skipped`              | `skipped`     |

## Implementation

### File 1: `src/erk/cli/commands/exec/scripts/objective_roadmap_check.py` (new)

Click command following existing exec script patterns:

```python
@click.command(name="objective-roadmap-check")
@click.argument("objective_number", type=int)
@click.pass_context
def objective_roadmap_check(ctx, objective_number):
```

**Parser logic (inline in this file):**

1. Fetch issue via `require_github_issues(ctx).get_issue(repo_root, objective_number)`
2. Find phase headers: regex for `### Phase (\d+)(?:[A-Z]?):\s*(.+)` (captures phase number and name, strips trailing markup like `(1 PR)`)
3. Find markdown tables after each phase header: regex for `\| Step \| Description \| Status \| PR \|` header row, then parse subsequent `|...|` rows
4. For each row: extract step ID, description, status column, PR column
5. Infer status using the rules table above
6. Determine `next_step`: first `pending` step in phase order
7. Collect validation errors (wrong column count, letter-format IDs)
8. Return JSON

### File 2: `src/erk/cli/commands/exec/group.py` (modify)

Add import and registration:
```python
from erk.cli.commands.exec.scripts.objective_roadmap_check import objective_roadmap_check
exec_group.add_command(objective_roadmap_check, name="objective-roadmap-check")
```

### File 3: `tests/unit/cli/commands/exec/scripts/test_objective_roadmap_check.py` (new)

Tests using `FakeGitHubIssues` + `ErkContext.for_test()` + `CliRunner`:

1. **Well-formed objective** — multiple phases, mixed statuses, verify full JSON structure
2. **All pending** — verify next_step is first step
3. **All done** — verify next_step is null
4. **Mixed statuses** — pending, done, in_progress, blocked, skipped — verify correct inference
5. **Malformed table** — wrong column count → validation error
6. **Letter-format step IDs** — `1A.1` accepted with warning in validation_errors
7. **No roadmap tables** — validation error about missing tables
8. **Status column overrides PR column** — blocked step with PR still shows blocked

Each test creates an `IssueInfo` with appropriate body markdown and invokes the command.

## Files Modified

| File | Action |
|------|--------|
| `src/erk/cli/commands/exec/scripts/objective_roadmap_check.py` | Create |
| `src/erk/cli/commands/exec/group.py` | Add import + registration |
| `tests/unit/cli/commands/exec/scripts/test_objective_roadmap_check.py` | Create |

## Verification

1. Run unit tests: `pytest tests/unit/cli/commands/exec/scripts/test_objective_roadmap_check.py`
2. Run type checker: `ty check src/erk/cli/commands/exec/scripts/objective_roadmap_check.py`
3. Run linter: `ruff check src/erk/cli/commands/exec/scripts/`
4. Manual smoke test: `erk exec objective-roadmap-check 6295` against the real objective