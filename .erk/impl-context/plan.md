# Plan: Update Skill Documentation Terminology (Objective #8381, Phase 2)

Part of Objective #8381, Nodes 2.1-2.5 (2.6 deferred to after Phase 5)

## Context

Plans in erk migrated from GitHub issues to draft PRs (PR #7971). Phase 1 (PR #8382) updated CLAUDE.md and AGENTS.md. Phase 2 updates all skill documentation files to match. The established pattern from Phase 1: "GitHub issue" → "draft PR", "plan issue" → "plan"/"plan PR", `<issue>` → `<plan>`.

## Scope

Nodes 2.1-2.5 in a single PR. Node 2.6 (regenerate erk-exec/reference.md) is deferred — it depends on Phase 5 updating source help text first.

## Changes

### Node 2.1: erk-planning skill

**`.claude/skills/erk-planning/SKILL.md`**
- Lines 3-6: Description field — "plan issue management" → "plan management", "GitHub issues" → "GitHub PRs", "plan issue structure" → "plan structure", "create new issues" → "create new plans"
- Line 15: "update issue" → "update plan"
- Line 17: "edit the issue", "update the issue" → "edit the plan", "update the plan"
- Line 30: "GitHub issues that track" → "GitHub PRs that track"
- Line 31: "Issue body" → "PR body"
- Line 37: "Plan Issue Structure" → "Plan Structure"
- Line 40: "Issue #123" → "PR #123"
- Line 68: "Creating a Plan Issue" → "Creating a Plan"
- Line 80: "Updating an Existing Plan Issue" → "Updating an Existing Plan"
- Line 106: `gh issue view 123` → `gh pr view 123` (plans are PRs now)
- Line 142: "Create new plan issue" → "Create new plan PR"
- Line 143: "Update existing plan issue" → "Update existing plan"

**`.claude/skills/erk-planning/references/workflow.md`**
- Line 3: "updating an existing plan issue" → "updating an existing plan"
- Line 9: "Preserves issue history" → "Preserves PR history"
- Line 23: `gh issue view 123` → `gh pr view 123`
- Line 47: "Update the Issue" → "Update the Plan"
- Line 77: `/issues/123` → `/pull/123` in URL
- Line 84: "Update that issue" → "Update that PR"
- Line 92: "Issue not found" → "Plan not found" / `gh issue view` → `gh pr view`
- Lines 65, 101, 106, 109: `gh issue comment` → `gh pr comment` (plans are PRs)

### Node 2.2: objective skill

**`.claude/skills/objective/SKILL.md`**
- Lines 4-6: Description — "multi-plan tracking issues" → "multi-plan tracking documents" (objectives ARE still issues, but "tracking issues" is ambiguous)
- Line 130: `erk pr create --file plan.md` — this command still works, keep as-is. The surrounding text "create an erk-plan that references the objective" is fine.

**`.claude/skills/objective/references/workflow.md`**
- Line 114: `erk pr create --file plan.md` — same as above, keep as-is. Context text is OK.

Note: The objective skill has minimal stale terminology because objectives are genuinely GitHub issues (not plans). The `erk pr create` command syntax is still current.

### Node 2.3: session-inspector skill

**`.claude/skills/session-inspector/SKILL.md`**
- Line 22: "Creating GitHub issues from session content" → "Creating plan PRs from session content"
- Line 48: "Create GitHub issue from session plan" → "Create plan PR from session plan"
- Line 108: "Create GitHub Issue from Session" → "Create Plan PR from Session"
- Line 114: "creates GitHub issue with session content" → "creates plan PR with session content"

**`.claude/skills/session-inspector/references/tools.md`**
- Line 124: "Extract plan from session and create GitHub issue." → "Extract plan from session and create plan PR."
- Line 136: `"issue_url": "https://github.com/owner/repo/issues/123"` — this is a JSON key name, leave as-is (Phase 5 node 5.2 handles JSON API keys)
- Line 154: "Extract session XML content from GitHub issue comments." → "Extract session XML content from plan PR comments."

### Node 2.4: erk-exec skill

**`.claude/skills/erk-exec/SKILL.md`**
- Line 40: "When working with erk-plan issues:" → "When working with erk-plans:"
- Line 46: "Get metadata from plan issue" → "Get metadata from plan"

Note: erk-exec/reference.md changes are deferred to node 2.6 (after Phase 5).

### Node 2.5: bundled.py

**`src/erk/capabilities/skills/bundled.py`**
- Line 26: `"erk-planning": "Plan issue management"` → `"erk-planning": "Plan management"`

## Files Modified (10 total)

1. `.claude/skills/erk-planning/SKILL.md` (~13 changes)
2. `.claude/skills/erk-planning/references/workflow.md` (~10 changes)
3. `.claude/skills/objective/SKILL.md` (1 change)
4. `.claude/skills/objective/references/workflow.md` (0 changes — keep as-is)
5. `.claude/skills/session-inspector/SKILL.md` (4 changes)
6. `.claude/skills/session-inspector/references/tools.md` (2 changes)
7. `.claude/skills/erk-exec/SKILL.md` (2 changes)
8. `src/erk/capabilities/skills/bundled.py` (1 change)

## Verification

1. `make fast-ci` — all tests pass
2. Grep for remaining stale terms across modified files:
   - `grep -r "plan issue" .claude/skills/erk-planning/ .claude/skills/session-inspector/ .claude/skills/erk-exec/SKILL.md`
   - `grep -r "GitHub issue" .claude/skills/erk-planning/ .claude/skills/session-inspector/` (excluding objective skill, where objectives ARE issues)
   - `grep "Plan issue" src/erk/capabilities/skills/bundled.py`
3. Verify no false positives: objective skill should still reference "GitHub issues" for objectives (not plans)
