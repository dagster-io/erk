# Phase 3B: Decision Menu Post-Documentation

**Objective:** #5503 (Learn System Improvements)
**Steps:** 3B.1, 3B.2, 3B.3

## Summary

After `/erk:learn` creates a learn plan issue, the workflow currently ends silently after tracking. Phase 3B adds a decision menu presenting actionable next steps so the user doesn't have to remember what to do next.

## Key Architecture Decision

`/erk:learn` is a **Claude Code skill** (`.claude/commands/erk/learn.md`), not Python code. The decision menu is implemented entirely as new markdown instructions in this skill file — no Python code changes needed. The menu is presented by the Claude agent that executes the skill, using its native conversation capabilities.

## Implementation

### Step 3B.1: Add Decision Menu to Learn Skill

**File:** `.claude/commands/erk/learn.md`

Insert a new **Step 6b** between the current Step 6a (Track Learn Result) and Step 7 (Track Evaluation). This step presents a numbered decision menu.

**Menu options:**

```
Post-learn actions:
  1. Submit for implementation (recommended)
  2. Review in browser
  3. Consolidate with other learn plans
  4. Done (finish learn workflow)
```

**Behavior by option:**
1. **Submit for implementation** — Run `/erk:plan-submit`. This is the most common action: queue the learn plan for remote implementation via GitHub Actions.
2. **Review in browser** — Open `gh issue view <issue_number> --web` so the user can review/edit the plan before deciding next steps.
3. **Consolidate with other learn plans** — Run `/local:replan-learn-plans` to merge this plan with other open learn plans. Only shown when other open `erk-learn` issues exist.
4. **Done** — Continue to Step 7 (track evaluation) and end.

**CI mode behavior:** In CI (`$CI` or `$GITHUB_ACTIONS` set), auto-select option 1 (submit). This matches the existing CI detection pattern already in Step 5.

**Non-interactive mode:** If stdin is not interactive, auto-select option 1 (same as CI).

### Step 3B.2: "Link to Related Docs" — Handled by Consolidation

The original objective spec called for a "link to related docs" option. After investigation, this is already handled by two existing mechanisms:

1. **ExistingDocsChecker agent** (Phase 1B) — Already runs during learn and identifies `PARTIAL_OVERLAP` / `ALREADY_DOCUMENTED` items. The synthesized plan includes cross-references.
2. **`/local:replan-learn-plans`** — Consolidates overlapping learn plans, deduplicating against each other.

No new code is needed. The consolidation option (menu item 3) surfaces this capability. The learn plan itself already contains cross-references to existing docs from the ExistingDocsChecker output.

### Step 3B.3: "Merge with Existing Doc" — Handled by Plan Content

The original objective spec called for a "merge with existing doc" option. After investigation:

1. Learn plans already mark items as `UPDATE_EXISTING` (vs `NEW_DOC`) in the gap analysis
2. The PlanSynthesizer already generates content that targets existing files
3. When implemented, the learn plan PR modifies existing docs directly

No separate "merge" command is needed. The learn plan's implementation phase handles merging naturally. The decision menu option 1 (submit) queues this for implementation.

## Files to Modify

| File | Change |
|------|--------|
| `.claude/commands/erk/learn.md` | Add Step 6b with decision menu instructions |

**That's it — one file.** This is purely a skill instruction change. The infrastructure for all menu actions already exists.

## Detailed Skill Changes

### In `.claude/commands/erk/learn.md`:

After the current Step 6a section (ending around line 649), add:

```markdown
### Step 6b: Post-Learn Decision Menu

Present a decision menu to the user for next actions.

**CI Detection**: Reuse the CI check from Step 5:
- If CI_MODE: Auto-select option 1 (submit) and proceed to Step 7
- If not interactive: Auto-select option 1 (submit) and proceed to Step 7

**Check for other open learn plans** (for consolidation option):

\`\`\`bash
erk exec list-plans --label erk-learn --state open --format json 2>/dev/null | jq '.plans | length'
\`\`\`

If the count is > 1 (current plan + at least one other), include the consolidation option.

**Interactive mode**: Present the menu using AskUserQuestion:

If other learn plans exist (count > 1):
  Options:
  1. Submit for implementation (Recommended) — Queue for remote implementation
  2. Review in browser — Open issue in web browser for review/editing
  3. Consolidate with other learn plans — Merge overlapping learn plans
  4. Done — Finish learn workflow

If no other learn plans:
  Options:
  1. Submit for implementation (Recommended) — Queue for remote implementation
  2. Review in browser — Open issue in web browser for review/editing
  3. Done — Finish learn workflow

**Execute the selected action:**

- **Submit**: Run `/erk:plan-submit`
- **Review**: Run `gh issue view <issue_number> --web`, then inform user they can run `/erk:plan-submit` when ready
- **Consolidate**: Run `/local:replan-learn-plans`
- **Done**: Proceed directly to Step 7
```

### Update Step 7 Header

Add a note that Step 6b flows into Step 7:

```markdown
### Step 7: Track Evaluation

**CRITICAL: Always run this step**, regardless of which option was selected in Step 6b.
```

## Verification

1. **Manual test**: Run `/erk:learn` on a plan with sessions — verify the decision menu appears after the plan is saved
2. **CI test**: Verify that in CI mode the menu is skipped (auto-submit)
3. **Menu actions**: Each option should execute the corresponding command
4. **Consolidation check**: When no other learn plans exist, the consolidation option should not appear

## What This Does NOT Include

- **No Python code changes** — The decision menu is purely skill instructions
- **No new exec scripts** — All actions use existing commands
- **No tests** — Skill markdown changes are tested manually (no unit test infrastructure for Claude skills)
- **No new files** — Single file modification

## Related Documentation

- Load `learned-docs` skill for doc management patterns
- Load `dignified-python` skill (not needed — no Python changes)
- `docs/learned/planning/learn-workflow.md` — May need a brief mention of the decision menu