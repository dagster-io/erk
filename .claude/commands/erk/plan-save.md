---
description: Save the current session's plan to GitHub
argument-hint: "[--plan-type=learn]"
---

# /erk:plan-save

Save the current session's plan to GitHub with session context.

## Usage

```bash
/erk:plan-save                           # Standalone plan
/erk:plan-save --plan-type=learn         # Learn plan (erk-learn label)
/erk:plan-save --objective=123           # Explicit objective link (overrides marker)
/erk:plan-save --current-branch          # Use current branch instead of creating new plnd/ branch
```

Objective linking: if a plan was created via `/erk:objective-plan`, the session's objective-context marker is read automatically by the save command. Use `--objective=<number>` to override the marker or provide the link when no marker exists (e.g., during replan).

## Plan Storage

The plan is saved using the configured backend:

- **Draft PR backend** (`PLAN_BACKEND = "draft_pr"`): Creates a branch, pushes a plan commit, and opens a draft PR. Plan content is in the PR body after the metadata separator.
  The JSON output contract includes `plan_number`, `plan_url`, `title`, `branch_name`, `plan_backend`.

## Agent Instructions

### Step 1: Parse Arguments

Check `$ARGUMENTS` for the `--plan-type`, `--objective`, and `--current-branch` flags:

```
If $ARGUMENTS contains "--plan-type=<type>":
  - Extract the type (standard or learn)
  - Store as PLAN_TYPE variable
  - Set PLAN_TYPE_FLAG to "--plan-type=<type>"
Else:
  - Set PLAN_TYPE_FLAG to empty string

If $ARGUMENTS contains "--objective=<number>":
  - Extract the number
  - Set OBJECTIVE_FLAG to "--objective=<number>"
Else:
  - Set OBJECTIVE_FLAG to empty string

If $ARGUMENTS contains "--current-branch":
  - Set CURRENT_BRANCH_FLAG to "--current-branch"
Else:
  - Set CURRENT_BRANCH_FLAG to empty string
```

### Step 2: Generate Branch Slug

**Skip this step if `--current-branch` was passed.** The current branch is used directly.

Before saving, generate a branch slug from the plan title. Read the plan title from the plan file you wrote in plan mode (the first `# ` heading).

Generate a branch slug from the title:

- 2-4 hyphenated lowercase words, max 30 characters
- Capture distinctive essence, drop filler words (the, a, for, implementation, plan)
- Prefer action verbs: add, fix, refactor, update, consolidate, extract, migrate
- Examples: "fix-auth-session", "add-plan-validation", "refactor-gateway-abc"

Store the result as `BRANCH_SLUG`.

### Step 3: Generate Plan Summary

Write a concise 2-3 sentence summary of the plan. This summary will be visible
at the top of the PR description (above the collapsed full plan).

Guidelines:

- Focus on WHAT the plan does and WHY
- Do not repeat the title
- Plain text, no markdown headers or formatting
- Avoid special shell characters (backticks, dollar signs)
- Store as PLAN_SUMMARY

### Step 4: Run Save Command

Run this command with the session ID, summary, and optional flags.

If CURRENT_BRANCH_FLAG is set, pass `--current-branch` (no branch slug needed):

```bash
erk exec plan-save --format json --session-id="${CLAUDE_SESSION_ID}" --current-branch --summary="${PLAN_SUMMARY}" ${PLAN_TYPE_FLAG} ${OBJECTIVE_FLAG}
```

Otherwise, pass the branch slug:

```bash
erk exec plan-save --format json --session-id="${CLAUDE_SESSION_ID}" --branch-slug="${BRANCH_SLUG}" --summary="${PLAN_SUMMARY}" ${PLAN_TYPE_FLAG} ${OBJECTIVE_FLAG}
```

Parse the JSON output to extract `plan_number` for verification in Step 5.

If the command fails, display the error and stop.

### Step 5: Verify Objective Link (if applicable)

**Only run this step if `objective_issue` is non-null in the JSON output from Step 4.**

Verify the objective link was saved correctly:

```bash
erk exec get-plan-metadata <plan_number> objective_issue
```

Parse the JSON response:

- If `success: true` and `value` matches the expected objective number: verification passed
- If `success: false` or value doesn't match: verification failed

**On verification success:**

Display: `Verified objective link: #<objective-number>`

**On verification failure:**

Display error and remediation steps:

```
ERROR: Objective link verification failed
Expected objective: #<expected>
Actual: <actual-or-null>

The plan was saved but without the correct objective link.
Fix: Close draft PR #<plan_number>,
ensure the objective-context marker exists, and re-run /erk:plan-save.
```

Exit without creating the plan-saved marker. The session continues so the user can retry.

### Step 6: Update Objective Roadmap (if objective linked)

**Only run this step if `objective_issue` was non-null in JSON output and verification passed.**

Update the objective's roadmap table to show that a plan has been created for this node:

1. **Read the roadmap node marker** to get the node ID(s):

```bash
node_ids=$(erk exec marker read --session-id "${CLAUDE_SESSION_ID}" roadmap-step)
```

If the marker doesn't exist (command fails), skip this step - the plan wasn't created via `objective-plan`.

The marker may contain multiple newline-delimited node IDs (for multi-node plans).

2. **Update the roadmap table** using the dedicated command with all node IDs:

```bash
# Build --node flags for each node ID (may be multiple lines)
node_flags=""
while IFS= read -r node_id; do
  [ -n "$node_id" ] && node_flags="$node_flags --node $node_id"
done <<< "$node_ids"
erk exec update-objective-node <objective-issue> $node_flags --pr "#<plan_number>" --status in_progress
```

This atomically fetches the objective body, finds the matching node rows, sets the Status cell to `in-progress`, and writes the updated body back.

3. **Report the update:**

Display: `Updated objective #<objective-issue> roadmap: node(s) <node_ids> → plan #<plan_number>`

**Error handling:** If the roadmap update fails, warn but continue - the plan was saved successfully, just the roadmap tracking didn't update. The user can manually update the objective.

### Step 7: Display Results

**If JSON contains `skipped_duplicate: true`:**

Display: `Plan already saved as #<plan_number> (duplicate skipped)`

Then call ExitPlanMode. The exit-plan-mode hook will present "what next?" options.

**Otherwise, on success**, display:

```
Plan "<title>" saved as draft PR #<plan_number>
URL: <issue_url>
```

If objective was verified, also display: `Verified objective link: #<objective-number>`

Then call ExitPlanMode. The exit-plan-mode hook will present "what next?" options
(implement in current worktree, implement in new worktree, or done).

On failure, display the error message and suggest:

- Checking that a plan exists (enter Plan mode and exit it first)
- Verifying GitHub CLI authentication (`gh auth status`)
- Checking network connectivity

### Step 5: Push Planning Session

After saving successfully, push the planning session for cross-machine learning.
This captures the in-progress session state so it's available even if implementation
happens on a different machine.

Run `erk exec capture-session-info` to get the session file path, then push it:

```bash
erk exec upload-impl-session --session-id "${CLAUDE_SESSION_ID}" 2>/dev/null || true
```

If the plan was saved successfully and `plan_number` is known, use push-session directly
for better stage tracking:

```bash
erk exec push-session \
    --session-file "<session_file_path>" \
    --session-id "${CLAUDE_SESSION_ID}" \
    --stage planning \
    --source local \
    --pr-number <plan_number> \
    2>/dev/null || true
```

Where `<session_file_path>` is obtained from `erk exec capture-session-info` output
and `<plan_number>` is from Step 2's JSON output.

**Note:** This is non-critical. If it fails, the plan was still saved successfully.
The `2>/dev/null || true` ensures graceful degradation.

## Session Tracking

After successfully saving a plan, the plan number is stored in a marker file that enables automatic plan updates in the same session.

**To read the saved plan number:**

```bash
erk exec marker read --session-id "${CLAUDE_SESSION_ID}" plan-saved-issue
```

This returns the plan number (exit code 0) or exits with code 1 if no plan was saved in this session.
