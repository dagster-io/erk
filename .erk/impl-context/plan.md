# Plan: Objective Roadmap Table Sync Validation

## Context

When an agent manually edits the objective YAML roadmap (issue body) without using `erk exec update-objective-node`, the prose roadmap table in the objective comment drifts out of sync. There's no validation to catch this. Additionally, the objective skill docs don't explicitly instruct agents to use the programmatic tools or to validate after mutations.

Two changes:
1. Add a **Check 8** to `erk objective check` that validates the prose roadmap table in the objective comment matches what would be rendered from the YAML source of truth.
2. Update the **objective skill docs** to instruct agents to always use `erk exec update-objective-node` and run `erk objective check` after any objective mutation.

## Implementation

### 1. Add roadmap-table-sync check to `validate_objective()`

**File:** `src/erk/cli/commands/objective/check_cmd.py`

After Check 7 (PR reference format), add Check 8:

- Only run when `objective_comment_id` is present in the header metadata (v2 format)
- Fetch the comment body via `github_issues.get_comment_by_id(repo_root, comment_id)`
- Call `rerender_comment_roadmap(issue.body, comment_body)` from `roadmap.py`
- If `rerender_comment_roadmap` returns `None` → skip check (no markers found)
- If the returned string equals the current `comment_body` → PASS ("Roadmap table in sync with YAML")
- If they differ → FAIL ("Roadmap table out of sync with YAML source of truth")

**Imports to add:**
- `from erk_shared.gateway.github.metadata.roadmap import rerender_comment_roadmap` (already has `parse_roadmap` imported)

**Key design choice:** Compare the full re-rendered comment body rather than parsing individual cells from the table. This is simpler and catches any drift (status, PR, description, ordering).

### 2. Add tests for Check 8

**File:** `tests/unit/cli/commands/objective/test_check_cmd.py`

Add test fixtures that include both:
- An issue body with `objective-header` (containing `objective_comment_id`) and `objective-roadmap` YAML
- A comment body with `<!-- erk:roadmap-table -->` markers containing the prose table

Tests:
- `test_roadmap_table_in_sync_passes()` — comment table matches YAML → PASS
- `test_roadmap_table_out_of_sync_fails()` — comment has stale status (e.g. "pending" when YAML says "skipped") → FAIL
- `test_roadmap_table_check_skipped_without_comment_id()` — no `objective_comment_id` in header → check not run, no FAIL

For the fake: `FakeGitHubIssues` already supports `get_comment_by_id`. Need to seed it with comment data. Check `FakeGitHubIssues` constructor — it takes `issues` dict but comments need to be added. Look at how comments are stored (likely `comments` dict keyed by comment_id).

### 3. Update objective skill docs

**File:** `.claude/skills/objective/references/updating.md`

Add a section after the existing table:

```markdown
## Programmatic Updates (Required)

**Always use `erk exec update-objective-node` to mutate node status/PR.** Never manually edit the YAML or prose table — the exec command updates both atomically.

```bash
erk exec update-objective-node <issue> --node <id> --status skipped
erk exec update-objective-node <issue> --node <id> --pr '#1234'
```

**After any objective mutation, validate:**

```bash
erk objective check <issue-number>
```

This catches drift between the YAML source of truth and the rendered roadmap table.
```

**File:** `.claude/skills/objective/SKILL.md`

In the "Quick Reference" section, add under "Logging an Action":

```markdown
### Updating Node Status

Always use the programmatic command — never manually edit YAML or prose tables:

```bash
erk exec update-objective-node <issue> --node <id> --status <status>
erk exec update-objective-node <issue> --node <id> --pr '#1234'
```

Then validate: `erk objective check <issue-number>`
```

## Files to Modify

| File | Change |
|------|--------|
| `src/erk/cli/commands/objective/check_cmd.py` | Add Check 8 (roadmap table sync) |
| `tests/unit/cli/commands/objective/test_check_cmd.py` | Add 3 tests for Check 8 |
| `.claude/skills/objective/references/updating.md` | Add programmatic update instructions |
| `.claude/skills/objective/SKILL.md` | Add node status update quick reference |

## Verification

1. Run `pytest tests/unit/cli/commands/objective/test_check_cmd.py` — all existing + new tests pass
2. Run `erk objective check 8832` against the live objective — should pass (we already fixed the drift manually)
3. Run `ty` for type checking
4. Run `ruff` for linting
