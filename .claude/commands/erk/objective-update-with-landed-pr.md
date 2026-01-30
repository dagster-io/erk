---
description: Update objective issue after landing a PR
---

# /erk:objective-update-with-landed-pr

Update an objective issue after landing a PR from a plan branch.

## Usage

Run after landing a PR:

```bash
/erk:objective-update-with-landed-pr
```

---

## Agent Instructions

### Step 0: Parse Arguments (if provided)

Check `$ARGUMENTS` for pre-provided context:

- `--pr <number>`: PR number that was just landed
- `--objective <number>`: Objective issue number to update
- `--branch <name>`: Original branch name (contains plan issue number in `P<number>-...` pattern)
- `--auto-close`: If set and all steps are complete, close objective without asking

**If all arguments are provided:** Use them directly. Parse the plan issue number from the branch name pattern to get implementation details. Skip Steps 1 and 4 (discovery steps).

**If arguments are not provided:** Continue with Steps 1 and 4 to discover from git state (manual invocation case).

### Step 1: Get Current Branch and Find Parent Objective

**Skip this step if `--objective` was provided in arguments.**

```bash
git branch --show-current
```

Parse the plan issue number from the branch name pattern `P<number>-...`

Example: `P3679-phase-1b-implement-fakes` -> Plan Issue #3679

**Important:** The branch pattern `P<number>-...` points to an **erk-plan** issue, not the objective. After getting the plan issue number:

1. Read the plan issue: `erk exec get-issue-body <plan-number>` (returns JSON with body)
2. Find the parent objective reference (look for "Objective: #XXXX" or "[#XXXX]" link in the body)
3. Use the objective issue number for all subsequent steps

If the branch doesn't match the pattern:

1. Ask the user for the objective issue number
2. Use AskUserQuestion tool with options like "#3679", "#3680", or "Other"

If the plan issue has no objective reference, ask the user which objective to update.

### Step 2: Load Objective Skill

Load the `objective` skill for format templates and guidelines.

### Step 3: Read Current Objective State

```bash
erk exec get-issue-body <issue-number>
```

This returns JSON with `{success, issue_number, title, body, labels, url}`. Analyze the objective body to identify:

- Current roadmap structure (phases and steps)
- Which phase/steps this PR likely completed
- Current status of all steps
- What "Current Focus" says

### Step 4: Get PR Information

**Skip this step if `--pr` was provided in arguments.**

Find the most recently merged PR for this branch:

```bash
gh pr list --state merged --head <branch-name> --limit 1 --json number,title,url
```

If no merged PR is found:

- Ask user if they want to specify a PR number
- Or proceed without PR reference

### Step 5: Post Action Comment

Post an action comment using the objective skill template.

**Template:**

```markdown
## Action: [Brief title - what was accomplished]

**Date:** YYYY-MM-DD
**PR:** #<pr-number>
**Phase/Step:** <phase.step>

### What Was Done

- [Concrete action 1]
- [Concrete action 2]

### Lessons Learned

- [Insight that should inform future work]

### Roadmap Updates

- Step X.Y: pending -> done
```

**Inferring content (DO NOT ask the user):**

- **What Was Done:** Infer from PR title, PR description, and commit messages. The plan issue body contains the implementation plan with specific steps - use this to understand what was accomplished.
- **Lessons Learned:** Infer from implementation patterns, architectural decisions made, or any non-obvious approaches taken. If the implementation was straightforward with no surprises, note what pattern worked well.
- Be concrete and specific based on available context

Use:

```bash
gh issue comment <issue-number> --body "$(cat <<'EOF'
[action comment content]
EOF
)"
```

### Step 6: Update Roadmap Step

After posting the action comment, update the roadmap table using the inference-driven update command.

**For each completed step**, run:

```bash
erk exec objective-roadmap-update <objective-number> --step <step-id> --pr "#<pr-number>"
```

This command:

- Sets the PR cell to the landed PR reference
- Resets the Status cell to `-` so inference determines status (PR `#NNN` → done)
- Re-validates the roadmap after mutation
- Returns JSON with the updated step and summary statistics

**Example:** If PR #6317 completed step 2.1:

```bash
erk exec objective-roadmap-update 6295 --step 2.1 --pr "#6317"
```

The JSON output includes `summary` with step counts — use this for Step 7.

**For "Current Focus" updates**, fetch and edit the body separately:

1. Fetch current body: `erk exec get-issue-body <issue-number>` (parse JSON to get `body` field)
2. Update the "Current Focus" section text
3. Update: `erk exec update-issue-body <issue-number> --body "<new-body>"`

### Step 7: Check Closing Triggers

**After updating, check if the objective should be closed.**

Use the `summary` from the `objective-roadmap-update` JSON output (or run `erk exec objective-roadmap-check <objective-number>` to get fresh counts):

- `total_steps`: Total steps
- `done` + `skipped`: Completed steps
- `pending` + `blocked` + `in_progress`: Remaining steps

**If ALL steps are `done` or `skipped`:**

**If `--auto-close` was provided:**

1. Post a final "Action: Objective Complete" comment with summary
2. Close the issue: `gh issue close <issue-number>`
3. Report: "All steps complete - objective closed automatically"

**Otherwise (interactive mode):**

Ask the user:

```
All roadmap steps are complete. Should I close objective #<number> now?
- Yes, close with final summary
- Not yet, there may be follow-up work
- I'll close it manually later
```

**If user says yes:**

1. Post a final "Action: Objective Complete" comment with summary
2. Close the issue: `gh issue close <issue-number>`

**If not all steps are complete:**

Report the update is done and what the next focus should be.

---

## Output Format

- **Start:** "Updating objective #<number> after landing PR #<pr-number>"
- **After action comment:** "Posted action comment to #<number>"
- **After body update:** "Updated objective body - marked step X.Y as done"
- **End:** Either "Objective #<number> closed" or "Objective updated. Next focus: [next action]"
- **Always:** Display the objective URL: `https://github.com/<owner>/<repo>/issues/<number>`

---

## Error Cases

| Scenario                           | Action                                       |
| ---------------------------------- | -------------------------------------------- |
| Branch doesn't match pattern       | Ask user for issue number                    |
| Plan has no objective reference    | Ask user which objective to update           |
| No merged PR found                 | Ask if user wants to specify a PR number     |
| Issue not found                    | Report error and exit                        |
| Issue has no `erk-objective` label | Warn user this may not be an objective issue |

---

## Important Notes

- **Two-step workflow:** Always post action comment FIRST, then update body
- **Lessons are mandatory:** Every action comment must include lessons learned
- **Be specific:** "Fixed auth flow" not "Made improvements"
- **Check closing triggers:** Don't let objectives linger in "ready to close" state
