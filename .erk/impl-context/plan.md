# Fix pr-submit step labels for resubmission

## Context

When `/erk:pr-submit` updates an existing PR (resubmission), step labels say "Push and Create PR", "Generate Title and Body", "Link PR to Objective" — implying fresh creation. The `push-and-create-pr` exec script already returns `pr.was_created` (boolean) in its JSON output, but the slash command ignores it.

## Change

**File:** `.claude/commands/erk/pr-submit.md`

### 1. Add branching instruction after Step 1

After Step 1's JSON parsing, add an instruction block:

> Check `pr.was_created` in the JSON output. If `false`, this is a resubmission — use "Update" language in all subsequent step headers and skip Step 5 (objective linking is already done).

### 2. Update step headers to be conditional

- **Step 1 reporting:** After parsing JSON, report either:
  - `was_created: true` → "Created PR #N"
  - `was_created: false` → "Pushed changes (PR #N already exists)"

- **Step 3 header:** "Generate Title and Body" → conditional:
  - Create path: "Generate Title and Body"
  - Update path: "Update Title and Body"

- **Step 4 header:** "Apply Description" → conditional:
  - Create path: "Apply Description"
  - Update path: "Update Description"

- **Step 5:** Add a conditional skip:
  - Create path: run objective linking as today
  - Update path: skip entirely (already linked on first submit)

- **Step 6 reporting:** Conditional success message:
  - Create path: "PR created successfully"
  - Update path: "PR updated successfully"

## Verification

- Run `/erk:pr-submit` on a branch with an existing PR — confirm "Update" language and Step 5 skipped
- Run `/erk:pr-submit` on a new branch — confirm "Create" language and Step 5 runs
