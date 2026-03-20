# Plan: Derive Implementation Insights from Plan-vs-Actual Delta

## Context

When PRs affiliated with an objective land, the system runs `objective-apply-landed-update` which mechanically marks roadmap nodes as "done" and posts an action comment. The action comment has a `lessons_learned` field that is **always empty `[]`**. The data model supports it but nobody populates it.

**Goal:** Extract insights by comparing the original plan (in the PR body) against what actually landed (changed files, commit messages). Feed these insights back to the objective via the action comment's `lessons_learned` field. No session data required — purely PR-data-driven.

**Key design decisions:**
- **Defer action comment posting to the skill** (remove from exec script, post after insight generation)
- **Add changed files** to the exec script output; skill fetches commit messages separately
- **Insight source:** The delta between plan intent and actual implementation

## Steps

### Step 1: Update TypedDict — remove `action_comment_id`, add `changed_files`

**File:** `packages/erk-shared/src/erk_shared/objective_apply_landed_update_result.py`

- Remove `action_comment_id: int` from `ApplyLandedUpdateResultDict`
- Add `changed_files: list[str]` — files changed in the PR

### Step 2: Modify exec script — stop posting comment, add changed files

**File:** `src/erk/cli/commands/exec/scripts/objective_apply_landed_update.py`

Remove:
- The `_format_action_comment` import (lines 30-32)
- The action comment posting block (lines 286-306: `date_str` through `remote.add_issue_comment`)
- `action_comment_id` from the result dict (line 339)
- `require_time` import (no longer needed)

Add (after fetching PR details, ~line 243):
- `changed_files = github.get_pr_changed_files(repo_root, pr_number)` — already in the gateway ABC

Add to result dict:
- `"changed_files": changed_files`

Keep: auto-close logic (`github.issues.close_issue`) — mechanical, stays in exec script.

### Step 3: Update the skill — add insight generation, post action comment

**File:** `.claude/commands/erk/system/objective-update-with-landed-pr.md`

**Update Step 1 output docs:** Remove `action_comment_id`, add `changed_files`.

**New Step 1.5: Fetch commit messages:**
```bash
erk exec get-pr-commits <pr_number>
```

**Modify Step 2 — add plan-vs-actual insight generation after prose reconciliation:**

The LLM compares two things:
1. **Plan intent** — the original plan from `plan.body` + node descriptions from the roadmap
2. **Actual implementation** — `changed_files` list + commit messages

From this delta, generate 1-3 insights focused on what's useful for remaining objective nodes:
- **Scope divergence**: Plan said N files, PR touched M — what was unexpected?
- **API/naming changes**: Did the implementation choose different names than planned? Future nodes need to know.
- **Discovered coupling**: Did the PR reveal dependencies between modules not anticipated in the roadmap?
- **Tooling/approach notes**: What approach worked (or didn't) that future nodes should reuse (or avoid)?
- **Node staleness**: Did this PR invalidate assumptions in pending node descriptions?

Each insight is a single sentence. Omit trivial observations. Empty list if genuinely nothing noteworthy.

**New Step 2.5: Post action comment** (after prose reconciliation + insights):

Pipe JSON to existing exec command:
```bash
echo '<json>' | erk exec objective-post-action-comment
```

JSON fields:
- `issue_number`, `date`, `pr_number`, `phase_step`, `title`
- `what_was_done`: `["Landed <pr.title> (#<pr.number>)"]`
- `lessons_learned`: generated insights (or `[]`)
- `roadmap_updates`: `["Node <id>: -> done"]` per node
- `body_reconciliation`: any section updates from prose reconciliation

### Step 4: Update tests

**File:** `tests/unit/cli/commands/exec/scripts/test_objective_apply_landed_update.py`

- Remove all assertions about `action_comment_id` and `remote.added_issue_comments`
- Add assertions for `changed_files` in output JSON
- Update `FakeLocalGitHub` construction to include `pr_changed_files` where needed
- Rename `test_no_node_flags_still_posts_comment` (no comment posted anymore)

### Step 5: Update documentation

**Files:**
- `docs/learned/objectives/objective-lifecycle.md` — update "Action Comments" section
- `docs/learned/objectives/exec-command-consolidation.md` — reflect comment posting moved to skill
- `.claude/skills/erk-exec/reference.md` — update output schema

## Critical files

| File | Change |
|------|--------|
| `packages/erk-shared/src/erk_shared/objective_apply_landed_update_result.py` | Remove `action_comment_id`, add `changed_files` |
| `src/erk/cli/commands/exec/scripts/objective_apply_landed_update.py` | Remove comment posting, add `changed_files` fetching |
| `.claude/commands/erk/system/objective-update-with-landed-pr.md` | Add insight generation, commit fetching, comment posting |
| `tests/unit/cli/commands/exec/scripts/test_objective_apply_landed_update.py` | Update all assertions |
| `src/erk/cli/commands/exec/scripts/objective_post_action_comment.py` | No changes (skill calls this) |

## Existing code to reuse

- `github.get_pr_changed_files(repo_root, pr_number)` — gateway ABC, implemented in real + fake
- `FakeLocalGitHub(pr_changed_files={6517: [...]})` — fake already supports this
- `erk exec get-pr-commits <pr>` — existing exec script for commit messages
- `erk exec objective-post-action-comment` — existing exec script for posting formatted comments
- `_format_action_comment(...)` in `objective_post_action_comment.py` — unchanged

## Verification

1. **Unit tests:** `pytest tests/unit/cli/commands/exec/scripts/test_objective_apply_landed_update.py`
2. **Type check:** `ty` on modified files
3. **Lint:** `ruff check` on modified files
4. **Manual test:** Land a PR affiliated with an objective and verify:
   - Exec script output includes `changed_files`, no `action_comment_id`
   - Skill generates insights from plan-vs-actual delta
   - Action comment on objective issue has populated `lessons_learned`
