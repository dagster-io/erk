# Fix pr-submit step labels for resubmission

## Context

When `/erk:pr-submit` is used to update an existing PR (resubmission), the output shows misleading step labels like "Push and Create PR" and "Link PR to Objective" — implying a fresh creation. The `push-and-create-pr` exec script already returns `was_created: true/false` in its JSON output, but the slash command doesn't use it.

## Change

**File:** `.claude/commands/erk/pr-submit.md`

Update the command to:

1. **Reorder Steps 1 and 2** — Run `get-pr-context` first (to detect if PR exists), then push. Actually, we can't do this because the PR might not exist yet before pushing. Instead, keep `push-and-create-pr` first but **use the `was_created` field from its JSON output** to branch behavior.

2. **Add conditional step labels after Step 1** — After parsing the Step 1 JSON, instruct Claude:
   - If `was_created` is `true`: use "Create" language for subsequent steps
   - If `was_created` is `false`: use "Update" language and skip the objective-link step

3. **Specific label changes for resubmit path:**
   - Step 1: "Push and Create PR" → report as "Pushed changes (PR #N already exists)"
   - Step 3: "Generate Title and Body" → "Update Title and Body"
   - Step 4: "Apply Description" → "Update Description"
   - Step 5: "Link PR to Objective" → skip entirely (already linked on first submit)
   - Step 6: report "PR updated successfully" instead of generic success

4. **Add a branching instruction** right after Step 1 that says:
   > Check the `was_created` field in the JSON output. If `false`, this is a resubmission — use "Update" language in step headers and skip Step 5 (objective linking).

## Verification

- Run `/erk:pr-submit` on a branch with an existing PR and confirm step labels say "Update" not "Create"
- Run `/erk:pr-submit` on a new branch and confirm step labels still say "Create"
- Confirm Step 5 (objective linking) is skipped on resubmission
