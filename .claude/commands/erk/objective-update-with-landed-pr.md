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

### Step 1: Delegate to Subagent

Use the Task tool to spawn a specialized subagent that will compose the updates and execute them in one turn.

The subagent prompt should include:

1. **The full JSON context blob from Step 0** (objective body, plan body, PR details)
2. **The `--auto-close` flag** (if present in `$ARGUMENTS`)
3. **All templates and rules below**

**Subagent Instructions:**

You are updating objective issue #<objective-number> after landing PR #<pr-number>. You have the full context including the objective body, plan body, and PR details.

Your tasks:

1. **Analyze which steps the PR completed** by comparing the plan body against the objective roadmap
2. **Update roadmap steps** using a SINGLE batched command with ALL completed steps:

**CRITICAL: Pass ALL completed steps as multiple `--step` flags in ONE command. Do NOT run separate commands per step — sequential calls cause race conditions and duplicate API calls.**

Before running update-roadmap-step, extract the existing plan reference for each completed step from the objective roadmap YAML (available in the context blob). Pass `--plan "#<plan-number>"` to preserve it, or `--plan ""` if the step had no plan.

```bash
erk exec update-roadmap-step <objective-number> --step <step-id-1> --step <step-id-2> ... --pr "#<pr-number>" --plan "#<plan-number>" --include-body
```

This handles both frontmatter and table dual-write automatically. The `--include-body` flag returns the fully-mutated body in the JSON output as `updated_body`, which you MUST use for prose reconciliation in step 3 (do NOT re-fetch via `gh issue view`).

3. **Perform prose reconciliation.** Use the `updated_body` from the step update JSON output (do NOT re-fetch the issue body via `gh issue view`) and compare against what the PR actually did. Check each reconcilable section:

**Reconciliation Checklist:**

1. Read each Design Decision. Did the PR override or refine any? If so, update the decision text.
2. Read Implementation Context. Does the architecture description still match reality after this PR? If not, correct it.
3. Read step descriptions for upcoming steps. Did this PR change the landscape such that future step descriptions need adjustment?
4. If nothing is stale, skip Body Reconciliation subsection and skip body update.

| Contradiction Type          | Example                                                      | Section to Update                             |
| --------------------------- | ------------------------------------------------------------ | --------------------------------------------- |
| **Decision override**       | Objective says "Use polling", PR implemented WebSockets      | Design Decisions                              |
| **Scope change**            | Step says "Add 3 methods", PR only needed 2                  | Step description in roadmap                   |
| **Architecture drift**      | Context says "config in config.py", PR moved it to settings/ | Implementation Context                        |
| **Constraint invalidation** | Requirement listed is no longer valid                        | Implementation Context                        |
| **New discovery**           | PR revealed a caching bug affecting future steps             | Implementation Context or new Design Decision |

These are common contradiction types, not an exhaustive list. Flag any divergence between the objective text and what was actually implemented, even if it doesn't fit a predefined category.

4. **Compose an action comment** using this template:

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

### Body Reconciliation

- **[Section name]**: [What changed and why]
```

**Inferring content (DO NOT ask the user):**

- **What Was Done:** Infer from PR title, PR description, and commit messages. The plan body contains the implementation plan - use it to understand what was accomplished.
- **Lessons Learned:** Infer from implementation patterns or architectural decisions. If straightforward, note what pattern worked well.
- **Body Reconciliation:** Only include this subsection if prose sections needed updating. If nothing is stale, omit entirely (not "No changes needed").

5. **Compose the updated objective body** by editing the roadmap table:
   - Set the PR cell to `#<pr-number>` for completed steps, preserve Plan cell value
   - Set the Status cell to the correct display value: `done` for completed steps (PR is `#NNN`), `in-progress` for in-flight plans (Plan is `#NNN`), `pending` for no refs
   - If PR title meaningfully differs from step description, update the description
   - Update "Current Focus" to describe the next pending step or next phase

**Status display rules:**

- Step has `#NNN` in PR column → Status `done`, preserve Plan column
- Step has `#NNN` in Plan column → Status `in-progress`
- Step has no Plan or PR → Status `pending`
- `blocked`/`skipped` are explicit overrides — only change if blocker is resolved

6. **Execute both writes in parallel:**

```bash
# Post action comment
gh issue comment <issue-number> --body "$(cat <<'EOF'
[action comment content]
EOF
)"
```

If prose reconciliation found stale sections, update the objective body:

```bash
# Update reconciled prose in objective body (skip if no prose changes)
erk exec update-issue-body <issue-number> --body "$(cat <<'BODY_EOF'
<full updated body text with reconciled sections>
BODY_EOF
)"
```

7. **Validate the objective after mutation:**

```bash
erk objective check <issue-number> --json-output
```

- If any checks fail, report failures and attempt to fix the issue body
- This catches inference errors (e.g., wrong status derivation, inconsistent PR/plan cells)

8. **Check closing triggers:**

**If ALL steps are `done` or `skipped`:**

**If `--auto-close` was provided:**

- Post a final "Action: Objective Complete" comment with summary
- Close the issue: `gh issue close <issue-number>`
- Report: "All steps complete - objective closed automatically"

**Otherwise (interactive mode):**

- Report back to parent: "All steps complete, user should be asked if they want to close"
- Parent will ask: "All roadmap steps are complete. Should I close objective #<number> now?"

**If not all steps are complete:**

- Report the update is complete and what the next focus should be

### Step 2: Handle Subagent Response

The subagent will report back with the result. If it reports "All steps complete, user should be asked if they want to close", ask the user:

```
All roadmap steps are complete. Should I close objective #<number> now?
- Yes, close with final summary
- Not yet, there may be follow-up work
- I'll close it manually later
```

If the user says yes:

1. Post a final "Action: Objective Complete" comment with summary
2. Close the issue: `gh issue close <issue-number>`

Otherwise, acknowledge the user's choice and report the update is complete.

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
