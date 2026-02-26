---
description: Save plan to GitHub with explicit objective link (inner skill)
argument-hint: "--objective=<N> [--plan-type=<type>]"
allowed-tools: Bash, Skill
---

# /erk:system:plan-save-with-objective

Inner skill for saving a plan with an explicit objective link. Called by `/erk:replan` when the source plan has an objective. This avoids exposing `--objective` in the user-facing `/erk:plan-save` command.

## Usage

```bash
/erk:system:plan-save-with-objective --objective=123
/erk:system:plan-save-with-objective --objective=123 --plan-type=learn
```

`--objective=<N>` is required. `--plan-type=<type>` is optional.

---

## Agent Instructions

### Step 1: Parse Arguments

Parse `$ARGUMENTS` to extract:

- **Objective number**: The `--objective=<N>` value (required)
- **Plan type**: The `--plan-type=<type>` value (optional)

If `--objective` is missing, STOP and report: "ERROR: --objective is required. Usage: /erk:system:plan-save-with-objective --objective=<N> [--plan-type=<type>]"

```
If $ARGUMENTS contains "--objective=<number>":
  - Extract the number
  - Store as OBJECTIVE_NUMBER
Else:
  - STOP with error

If $ARGUMENTS contains "--plan-type=<type>":
  - Set PLAN_TYPE_FLAG to "--plan-type=<type>"
Else:
  - Set PLAN_TYPE_FLAG to empty string
```

### Step 2: Generate Branch Slug

Read the plan title from the plan file written in plan mode (the first `# ` heading).

Generate a branch slug from the title:

- 2-4 hyphenated lowercase words, max 30 characters
- Capture distinctive essence, drop filler words (the, a, for, implementation, plan)
- Prefer action verbs: add, fix, refactor, update, consolidate, extract, migrate
- Examples: "fix-auth-session", "add-plan-validation", "refactor-gateway-abc"

Store the result as `BRANCH_SLUG`.

### Step 3: Run Save Command

Run this command with the session ID, branch slug, objective, and optional plan type:

```bash
erk exec plan-save --format json --session-id="${CLAUDE_SESSION_ID}" --branch-slug="${BRANCH_SLUG}" --objective=<OBJECTIVE_NUMBER> ${PLAN_TYPE_FLAG}
```

Parse the JSON output to extract `plan_number` and `objective_issue` for verification in Step 4.

If the command fails, display the error and stop.

### Step 4: Verify Objective Link

Verify the objective link was saved correctly:

```bash
erk exec get-plan-metadata <plan_number> objective_issue
```

Parse the JSON response:

- If `success: true` and `value` matches `OBJECTIVE_NUMBER`: verification passed
- If `success: false` or value doesn't match: fix the link

**On verification failure, fix the link:**

```bash
erk exec update-plan-header <plan_number> objective_issue=<OBJECTIVE_NUMBER>
```

Then re-verify:

```bash
erk exec get-plan-metadata <plan_number> objective_issue
```

If still failing after fix attempt, display error:

```
ERROR: Objective link could not be set for plan #<plan_number>
Expected objective: #<OBJECTIVE_NUMBER>
Manual fix: erk exec update-plan-header <plan_number> objective_issue=<OBJECTIVE_NUMBER>
```

### Step 5: Display Results

Display results using the same format as `/erk:plan-save` Step 4.

**If JSON contains `skipped_duplicate: true`:**

Display: `Plan already saved as #<plan_number> (duplicate skipped)`

**Otherwise, on success**, display based on `plan_backend` from JSON output:

**Header (both backends):**

```
Plan "<title>" saved as <"draft PR" if plan_backend=="draft_pr", else "issue"> #<plan_number>
URL: <plan_url>
Verified objective link: #<OBJECTIVE_NUMBER>
```

**Next steps block:**

Follow the same format as `/erk:plan-save` Step 4 for the `plan_backend` type, including slot options.

On failure, display the error message.

---

## Error Cases

| Scenario                          | Action                                           |
| --------------------------------- | ------------------------------------------------ |
| Missing --objective               | Report error with usage instructions             |
| plan-save command fails           | Display error and stop                           |
| Objective link verification fails | Auto-fix with update-plan-header, then re-verify |
| Auto-fix fails                    | Display error with manual fix command            |

---

## Important Notes

- **This is an inner skill** — not user-facing, called only by `/erk:replan`
- **Always verifies** the objective link after saving, auto-fixing if needed
- **Same output format** as `/erk:plan-save` for consistent user experience
