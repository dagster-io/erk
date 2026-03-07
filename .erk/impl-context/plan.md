# Plan: Push down audit-branches data collection into `erk exec audit-collect`

## Context

The `/local:audit-branches` slash command is a 620-line markdown file that instructs the LLM to write bash scripts on the fly across 11 phases. In the session that just ran, this caused:

1. **~15 sequential bash calls** because each step revealed new categories (async-learn/*, non-Graphite branches with closed PRs)
2. **Shell fragility** — zsh `!=` syntax error, complex heredoc workarounds needed for every script
3. **Missing categories** — 71 `async-learn/*` branches and 40 non-Graphite branches with closed PRs weren't anticipated by the command
4. **Wrong phase ordering** — blocking worktree detection was Phase 6 but should have been first
5. **Redundant API calls** — PRs fetched 3 times (`--state all`, `--state closed`, individual `gh pr view`)
6. **gt repo sync blind spot** — command assumed gt sync cleans everything, but it only cleans Graphite-tracked branches

This is a textbook case for the **refac-cli-push-down** pattern: the data collection and categorization are purely mechanical, while only the presentation and user interaction require LLM judgment.

## Approach

Create `erk exec audit-collect` — a Python exec script that outputs comprehensive, pre-categorized JSON. Then rewrite the slash command to consume that JSON, shrinking it from ~620 lines to ~150 lines.

## Step 1: Create `erk exec audit-collect` exec script

**File:** `src/erk/cli/commands/exec/scripts/audit_collect.py`

The script collects ALL data in a single pass and outputs structured JSON with pre-categorized branches.

**Input:** No arguments needed (uses repo context from Click).

**Output JSON schema:**

```json
{
  "success": true,
  "summary": {
    "total_local_branches": 185,
    "total_worktrees": 64,
    "total_open_prs": 45
  },
  "categories": {
    "blocking_worktrees": [
      {
        "worktree_path": "...",
        "slot_name": "erk-slot-58",
        "is_slot": true,
        "branch": "plnd/...",
        "pr_number": 8593,
        "pr_state": "CLOSED"
      }
    ],
    "auto_cleanup": [
      {
        "branch": "old-branch",
        "reason": "merged_to_master",
        "ahead_of_master": 0,
        "has_remote": false
      }
    ],
    "closed_pr_branches": [
      {
        "branch": "plnd/...",
        "pr_number": 8878,
        "pr_state": "CLOSED",
        "in_worktree": false,
        "tracked_by_graphite": false
      }
    ],
    "pattern_branches": {
      "async_learn": {
        "count": 71,
        "branches": ["async-learn/8646", ...],
        "parent_pr_states": {"MERGED": 55, "CLOSED": 14, "OPEN": 2}
      }
    },
    "stale_open_prs": [
      {
        "pr_number": 8416,
        "title": "Release 0.9.0",
        "reason": "superseded_release",
        "details": "Superseded by releases 0.9.7 and 0.9.9",
        "mergeable": "UNKNOWN"
      }
    ],
    "needs_attention": [
      {
        "pr_number": 8074,
        "title": "...",
        "mergeable": "CONFLICTING",
        "updated_at": "2026-03-02",
        "branch": "plnd/..."
      }
    ],
    "active": {
      "count": 25,
      "note": "Recent open PRs with active work, skipped"
    }
  }
}
```

**Implementation approach:** Use existing gateway abstractions:

- `ctx.git.worktree.list_worktrees(repo_root)` for worktree data
- `ctx.git.branch.list_local_branches(repo_root)` for local branches
- `ctx.git.branch.list_remote_branches(repo_root)` for remote branches
- `ctx.github.get_prs(...)` or `gh pr list` subprocess for PR data
- `ctx.git.branch.get_all_branch_sync_info(repo_root)` for ahead/behind

For operations not covered by gateways (like checking Graphite tracking), use subprocess wrappers.

**Key erk-aware categorization logic (hardcoded, not LLM-inferred):**

- `__erk-slot-*-br-stub__` → skip entirely
- `async-learn/*` → group as `pattern_branches.async_learn`
- `release-*` branches → check if superseded by newer merged releases
- Branches with closed/merged PRs → `closed_pr_branches` (split by in-worktree vs not)
- Local-only, 0 ahead → `auto_cleanup`
- Open PRs with CONFLICTING/UNKNOWN status older than 7 days → `needs_attention`

**Key files to reference:**
- `src/erk/cli/commands/branch/list_cmd.py` — pattern for branch+PR data collection using gateways
- `src/erk/cli/commands/exec/scripts/close_prs.py` — pattern for exec script structure, JSON output, Click context
- `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/abc.py` — branch operations gateway
- `packages/erk-shared/src/erk_shared/gateway/git/worktree/abc.py` — worktree operations gateway
- `src/erk/cli/commands/exec/scripts/AGENTS.md` — exec script conventions

## Step 2: Register the command

**File:** `src/erk/cli/commands/exec/scripts/__init__.py`

Add `audit_collect` to the exec scripts registration.

## Step 3: Write tests

**File:** `tests/unit/cli/commands/exec/scripts/test_audit_collect.py`

Test using `ErkContext.for_test()` with fakes:
- Test with mix of open/closed PRs, local-only branches, worktrees
- Test `async-learn/*` pattern detection
- Test blocking worktree detection (branch in worktree with closed PR)
- Test superseded release detection
- Test stub branch exclusion

## Step 4: Rewrite the slash command

**File:** `.claude/commands/local/audit-branches.md`

Reduce from ~620 lines to ~150 lines with this structure:

```markdown
# /audit-branches

## Phase 1: Collect Data

Run: `erk exec audit-collect --json`

This returns pre-categorized JSON with all branch/PR/worktree data.

## Phase 2: Present Findings

Display each non-empty category as a table (format templates provided).

## Phase 3: User Selection

Use AskUserQuestion to ask which categories to clean up.

## Phase 4: Execute Cleanup

Execute in this order:
1. Untrack stubs from Graphite
2. Free blocking worktrees (slot → erk slot unassign, non-slot → git worktree remove)
3. git worktree prune && gt repo sync --no-interactive --force --no-restack
4. Close stale PRs: gh pr close <N> --comment "..."
5. Delete remaining closed-PR branches not cleaned by gt sync: git branch -D
6. Delete pattern branches (async-learn): git branch -D + git push origin --delete
7. Delete auto-cleanup branches: git branch -D
8. Final: git worktree prune

## Phase 5: Summary

Report counts of actions taken and remaining items.
```

The slash command focuses on what the LLM does best: presenting findings, interacting with the user, and handling edge cases during execution. All mechanical data collection and categorization is in tested Python code.

## Step 5: Stub untracking

Add a `stubs_tracked_by_graphite` field to the audit-collect output. The script detects stubs tracked by Graphite by running `gt log short --no-interactive` and extracting stub branch names. The slash command then runs `gt branch untrack` for each, which is simple enough to stay in the command.

## Verification

1. Run `erk exec audit-collect --json` and verify it produces valid JSON with all categories
2. Run the rewritten `/audit-branches` command and verify it presents findings correctly
3. Compare total branches found by the new command vs a manual `git branch | wc -l` to ensure nothing is missed
4. Run unit tests: `pytest tests/unit/cli/commands/exec/scripts/test_audit_collect.py`
