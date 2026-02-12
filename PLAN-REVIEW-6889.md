# Plan: Streamline Objective Update Workflow

## Context

The `/erk:objective-update-with-landed-pr` skill is slow and unreliable because the subagent uses raw `gh` commands (shell quoting failures, race conditions on body rewrites, wasted validation API calls). Three changes fix this:

1. **Deterministic step marking** - Steps already track their plan via `plan #<N>` in the roadmap. When a PR lands, we can find those steps and mark them done without LLM inference.
2. **Gateway-backed comment posting** - Replace raw `gh issue comment` with an exec command.
3. **Drop "Current Focus"** - Redundant derived data. Replace with explicit LLM body reconciliation: the subagent audits objective prose against what the PR actually did, reports contradictions, and updates stale text.

## Part 1: `erk exec objective-mark-landed` (new)

Deterministically marks roadmap steps as done when a PR lands.

### `src/erk/cli/commands/exec/scripts/objective_mark_landed.py`

**Input:** `<issue_number> --pr <pr_number> --branch <branch_name>`

**Logic:**
1. Extract plan number from branch (`P<number>-...` pattern)
2. Fetch issue, parse roadmap via `parse_roadmap(body)` from `objective_roadmap_shared`
3. Find all steps where `step.pr == f"plan #{plan_number}"`
4. For each matching step, call `_replace_step_pr_in_body()` (reuse from `update_roadmap_step.py`) to set PR to `#<pr_number>` (which sets status to `done`)
5. Single write via `github.update_issue_body()`
6. Return JSON:

```json
{
  "success": true,
  "issue_number": 6629,
  "plan_number": 6720,
  "pr_number": 6723,
  "steps_marked": ["1.3", "1.4"],
  "steps_already_done": [],
  "summary": {"total_steps": 8, "done": 5, "pending": 3, ...},
  "all_done": false,
  "url": "..."
}
```

**Key: reuse `_replace_step_pr_in_body` from `update_roadmap_step.py`.** This function handles both frontmatter YAML and markdown table dual-write. Currently it's a module-level function - needs to be importable (it already is, just import from the module).

**Edge cases:**
- No steps match `plan #<N>` → success with empty `steps_marked`, warning in output
- Branch doesn't match pattern → error exit 1
- Issue/roadmap not found → error exit 1

### Registration in `group.py`

Import + `exec_group.add_command(objective_mark_landed, name="objective-mark-landed")`

### Tests: `tests/unit/cli/commands/exec/scripts/test_objective_mark_landed.py`

~7 tests using `FakeGitHubIssues`:
1. Single step marked (step has `plan #N`, gets updated to `#PR`)
2. Multiple steps marked (two steps have same `plan #N`)
3. No steps match (no `plan #N` in roadmap) → success with empty list
4. All steps become done → `all_done: true`
5. Branch pattern invalid → error
6. Issue not found → error
7. No roadmap → error

## Part 2: `erk exec post-issue-comment` (new)

Gateway-backed comment posting. Same design as previous plan iteration.

### `src/erk/cli/commands/exec/scripts/post_issue_comment.py`

- `<issue_number> --body "text"` or `--body-file path`
- Uses `require_issues(ctx).add_comment(repo_root, number, body_text)` → returns comment ID
- If `--body-file`, reads via `Path.read_text(encoding="utf-8")`
- Mutual exclusivity validation (same pattern as `update_issue_body.py`)
- Returns `{success, issue_number, comment_id}`
- Follows `close_issue_with_comment.py` structure

### Tests: `tests/unit/cli/commands/exec/scripts/test_post_issue_comment.py`

~6 tests: success with `--body`, success with `--body-file`, multiline body, issue not found, both args error, neither arg error.

## Part 3: Drop "Current Focus" from Objectives

Remove `## Current Focus` section from all templates and instructions. All references are in skills/docs/commands (no source code).

### Files to edit:

| File | Change |
|------|--------|
| `.claude/skills/objective/references/format.md` | Remove section template, update instruction, remove phase completion pattern |
| `.claude/skills/objective/references/workflow.md` | Remove from template, remove "Check Current Focus" guidance |
| `.claude/skills/objective/references/closing.md` | Remove Trigger 2 (completion language in Current Focus), remove from checklist, remove lingering anti-pattern |
| `.claude/skills/objective/SKILL.md` | Remove from template, remove from post-update instruction |
| `.claude/commands/erk/objective-create.md` | Remove from perpetual objectives template |
| `.claude/commands/erk/land.md` | Remove from post-land instruction |
| `docs/learned/objectives/objective-lifecycle.md` | Remove from mutation descriptions |
| `docs/learned/objectives/roadmap-mutation-patterns.md` | Remove reference |

## Part 4: Update the Skill

### `.claude/commands/erk/objective-update-with-landed-pr.md`

Rewrite subagent instructions for the new flow:

**New subagent flow:**

| Step | Type | What | Command |
|------|------|------|---------|
| 1 | Exec | Fetch context | `erk exec objective-update-context` (exists) |
| 2 | Exec | Mark steps done | `erk exec objective-mark-landed` (**new**) |
| 3 | **LLM** | Reconcile body prose | Read objective body + PR changes. Identify stale/contradicted text. Compose action comment + updated body. |
| 4 | Exec | Post action comment | `erk exec post-issue-comment --body-file <tmp>` (**new**) |
| 5 | Exec | Update body (if changed) | `erk exec update-issue-body` (exists) |
| 6 | Exec | Close if all done | `erk exec close-issue-with-comment` (exists, use `all_done` from step 2) |

**LLM reconciliation instructions (step 3) should tell the subagent:**

> Read the objective body text and compare it against the PR title, description, and plan body. Identify any prose that has been invalidated by what was actually implemented:
> - Design decisions that were changed
> - Step descriptions that don't match what was built
> - Implementation context that is now stale
> - Constraints or assumptions that no longer apply
>
> Report what you found, then produce:
> 1. An action comment (what was done, lessons learned, any contradictions found)
> 2. An updated objective body with stale prose corrected
>
> If nothing is stale, still post the action comment but skip the body update.

## Key Files

| Purpose | Path |
|---------|------|
| Reuse: `_replace_step_pr_in_body` | `src/erk/cli/commands/exec/scripts/update_roadmap_step.py` |
| Reuse: `parse_roadmap`, `compute_summary`, `find_next_step` | `src/erk/cli/commands/exec/scripts/objective_roadmap_shared.py` |
| Pattern: comment posting | `src/erk/cli/commands/exec/scripts/close_issue_with_comment.py` |
| Pattern: body/body-file | `src/erk/cli/commands/exec/scripts/update_issue_body.py` |
| Pattern: branch parsing | `src/erk/cli/commands/exec/scripts/objective_update_context.py` |
| Registration | `src/erk/cli/commands/exec/group.py` |
| Gateway ABC | `packages/erk-shared/src/erk_shared/gateway/github/issues/abc.py` |
| Fake for tests | `packages/erk-shared/src/erk_shared/gateway/github/issues/fake.py` |

## Verification

1. Unit tests for both new exec commands via devrun
2. Manual: `erk exec objective-mark-landed <obj> --pr <N> --branch P<N>-...` against a real objective
3. Manual: `erk exec post-issue-comment <issue> --body "test"`
4. End-to-end: run `/erk:objective-update-with-landed-pr` on a real objective after landing a PR