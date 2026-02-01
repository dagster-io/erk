# Plan: Optimize objective-update-with-landed-pr command

## Problem
The command takes ~2 minutes because each step is a separate LLM turn (5-15s each). With all args provided, there are ~8 sequential turns.

## Approach
Create a new `erk exec objective-update-context` script that bundles all GitHub API fetches into one subprocess call (zero LLM turns). Then simplify the slash command to start with all context pre-loaded.

## Changes

### 1. New exec script: `objective_update_context.py`

**File:** `src/erk/cli/commands/exec/scripts/objective_update_context.py`

**CLI:** `erk exec objective-update-context --pr 6517 --objective 6423 --branch P6513-...`

**What it does (single subprocess, zero LLM turns):**
1. Parse plan issue number from `--branch` pattern (`P<number>-...`)
2. Fetch objective issue body via `require_issues(ctx).get_issue(repo_root, objective_number)`
3. Fetch plan issue body via `require_issues(ctx).get_issue(repo_root, plan_number)`
4. Fetch PR details via `require_github(ctx).get_pr(repo_root, pr_number)`
5. Return single JSON blob:

```json
{
  "success": true,
  "objective": {"number": 6423, "title": "...", "body": "...", "state": "...", "labels": [...], "url": "..."},
  "plan": {"number": 6513, "title": "...", "body": "..."},
  "pr": {"number": 6517, "title": "...", "body": "...", "url": "..."}
}
```

**Error handling:** LBYL with `IssueNotFound` / `PRNotFound` discriminated unions. If any fetch fails, return `{"success": false, "error": "..."}` with exit code 1.

**Gateway access:** Uses `require_issues(ctx)` for issues and `require_github(ctx)` for PR. Uses `require_repo_root(ctx)` for repo path.

### 2. Register in group.py

**File:** `src/erk/cli/commands/exec/group.py`

Add import and `exec_group.add_command(objective_update_context, name="objective-update-context")`.

### 3. Update the slash command

**File:** `.claude/commands/erk/objective-update-with-landed-pr.md`

**Restructure steps to minimize LLM turns:**

| Turn | What happens |
|------|-------------|
| 1 | Parse args + run `erk exec objective-update-context` (one Bash call gets all data) |
| 2 | Load `objective` skill (kept per user request) |
| 3 | Analyze data + compose action comment + compose updated body. **Execute both writes in parallel:** `gh issue comment` + `erk exec update-issue-body` |
| 4 | Run `erk objective check --json-output` (validation + closing check combined). Act on result. |

**Down from ~8 turns to ~4 turns.**

Key command changes:
- Replace Steps 1/3/4 (3 separate fetch calls) with single `erk exec objective-update-context` call in Step 0
- Keep Step 2 (load objective skill) as-is
- Merge Steps 5+6 (comment + body update) into one parallel-write step
- Merge validation + closing check into one `erk objective check --json-output` call
- Remove "Important Notes" about comment-before-body ordering (they're independent)

### 4. Unit test for the new exec script

**File:** `tests/unit/cli/commands/exec/scripts/test_objective_update_context.py`

Test cases using Click CliRunner + `ErkContext.for_test(...)` with fake gateways:
- Happy path: all three fetches succeed, returns combined JSON
- Objective not found: returns error JSON, exit 1
- PR not found: returns error JSON, exit 1
- Branch pattern doesn't contain plan number: returns error JSON, exit 1

## Files to create/modify

| File | Action |
|------|--------|
| `src/erk/cli/commands/exec/scripts/objective_update_context.py` | Create |
| `src/erk/cli/commands/exec/group.py` | Add import + registration |
| `.claude/commands/erk/objective-update-with-landed-pr.md` | Rewrite steps |
| `tests/unit/cli/commands/exec/scripts/test_objective_update_context.py` | Create |

## Verification
1. Run `erk exec objective-update-context --help` to confirm registration
2. Run unit tests for the new script
3. Invoke the full command on a real objective+PR and confirm:
   - Only ~4 LLM turns instead of ~8
   - Objective body updated correctly
   - Action comment posted correctly
   - Validation passes