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

### Step 0: Parse Arguments and Fetch All Context

Check `$ARGUMENTS` for pre-provided context:

- `--pr <number>`: PR number that was just landed
- `--objective <number>`: Objective issue number to update
- `--branch <name>`: Original branch name (contains plan issue number in `P<number>-...` pattern)
- `--auto-close`: If set and all steps are complete, close objective without asking

**If all three data arguments are provided**, fetch everything in one call:

```bash
erk exec objective-update-context --pr <number> --objective <number> --branch <name>
```

This returns a single JSON blob with `{success, objective, plan, pr}` containing all issue bodies and PR details needed for the update. Parse and store the result.

**If arguments are not provided**, discover from git state:

1. Get current branch: `git branch --show-current`
2. Parse plan issue number from branch pattern `P<number>-...`
3. Ask user for objective number if not discoverable
4. Find merged PR: `gh pr list --state merged --head <branch-name> --limit 1 --json number,title,url`
5. Then run `erk exec objective-update-context` with the discovered values

If the branch doesn't match the pattern or no merged PR is found, ask the user for the missing information.

### Step 1: Load Objective Skill

Load the `objective` skill for format templates and guidelines.

### Step 2: Analyze Context and Compose Updates

Using the data from Step 0, analyze the objective body to identify:

- Current roadmap structure (phases and steps)
- Which phase/steps this PR likely completed
- Current status of all steps
- What "Current Focus" says

Then compose both updates:

**Action Comment** (using objective skill template):

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

**Updated Objective Body:**

For each completed step, edit the roadmap table row:

1. Set the PR cell to `#<pr-number>` for the completed step
2. Set the Status cell to `-` (inference determines status from PR column)
3. If the PR title meaningfully differs from the step description, update the description to reflect what was actually implemented

**Status inference rules** (the parser uses these to determine effective status):

- Step has `#NNN` in PR column → Status `-` → inferred as `done`
- Step has `plan #NNN` in PR column → Status `-` → inferred as `in_progress`
- Step has no PR → Status stays as-is (inferred as `pending`)
- `blocked`/`skipped` in Status column are explicit overrides — only change if you know the blocker is resolved

Also update "Current Focus" to describe the next pending step or next phase of work.

### Step 3: Execute Both Writes in Parallel

Execute the action comment and body update in parallel:

```bash
# Post action comment
gh issue comment <issue-number> --body "$(cat <<'EOF'
[action comment content]
EOF
)"
```

```bash
# Update objective body
erk exec update-issue-body <issue-number> --body "$(cat <<'BODY_EOF'
<full updated body text>
BODY_EOF
)"
```

### Step 4: Validate and Check Closing Triggers

Run validation and closing check in one call:

```bash
erk objective check <objective-number> --json-output
```

This returns counts: `total_steps`, `done`, `skipped`, `pending`, `blocked`, `in_progress`.

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
- **After writes:** "Posted action comment and updated objective body for #<number>"
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
