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

> **Design note:** All steps run inline in the caller's context (no subagent delegation).
> Step 2 (prose reconciliation) requires LLM judgment, and Step 3 (closing prompt)
> requires direct user interaction.

### Do NOT Improvise

**CRITICAL: Follow these steps exactly. Do NOT substitute raw `gh` commands for any `erk exec` command.** If an `erk exec` command fails, STOP and report the error to the user. Do not attempt to replicate its behavior manually with `gh api`, `gh issue view`, or any other command.

- **`erk exec objective-fetch-context`** is the ONLY way to fetch context (Step 1)
- **`erk exec update-objective-node`** is the ONLY way to update roadmap nodes (Step 2)
- **`erk exec objective-post-action-comment`** is the ONLY way to post action comments (Step 4)

### Step 1: Fetch All Context

Check `$ARGUMENTS` for optional overrides:

- `--pr <number>`: PR number that was just landed
- `--objective <number>`: Objective issue number to update
- `--branch <name>`: Original branch name
- `--auto-close`: If set and all nodes are complete, close objective without asking

Run a single command that fetches context, updates roadmap nodes to done, and posts an action comment:

**EXACT command: `erk exec objective-fetch-context`** — do NOT use any other command name.

```bash
erk exec objective-apply-landed-update [--pr <number>] [--objective <number>] [--branch <name>]
```

**CRITICAL: If this command fails, STOP and report the error. Do NOT fall back to raw `gh` commands.**

Note: `plnd/` branches work correctly with this command — for PlannedPRBackend, the plan IS the PR, and `--pr` enables direct lookup without branch-based search.

This returns JSON with:

- `objective`: Issue body, title, labels, URL, `objective_content` (prose from first comment)
- `plan`: Plan issue body and title
- `pr`: PR title, body, URL
- `roadmap`: Parsed roadmap with `matched_steps`, `summary`, `next_node`, `all_complete`
- `node_updates`: List of nodes updated to done (with `previous_plan`, `previous_pr`)
- `action_comment_id`: ID of the posted action comment

If this returns `success: false`, display the error and stop.

### Step 2: Prose Reconciliation

Compare `objective.objective_content` (the prose from the first comment's `objective-body` block) against what the PR actually did.

If `objective_content` is null, skip prose reconciliation entirely (objective has no prose comment).

- Read each Design Decision. Did the PR override or refine any?
- Read Implementation Context. Does the architecture description still match?
- Read upcoming node descriptions. Did this PR change the landscape?
- If nothing is stale, skip prose update entirely.

| Contradiction Type          | Example                                                      | Section to Update                             |
| --------------------------- | ------------------------------------------------------------ | --------------------------------------------- |
| **Decision override**       | Objective says "Use polling", PR implemented WebSockets      | Design Decisions                              |
| **Scope change**            | Node says "Add 3 methods", PR only needed 2                  | Node description in roadmap                   |
| **Architecture drift**      | Context says "config in config.py", PR moved it to settings/ | Implementation Context                        |
| **Constraint invalidation** | Requirement listed is no longer valid                        | Implementation Context                        |
| **New discovery**           | PR revealed a caching bug affecting future nodes             | Implementation Context or new Design Decision |

**If prose reconciliation found stale sections**, update the objective's first comment. Parse `objective_comment_id` from `objective.body`'s `objective-header` metadata block, then update:

```bash
gh api repos/{owner}/{repo}/issues/comments/{comment_id} -X PATCH -f body="<updated comment body>"
```

### Step 3: Closing Triggers

Use `roadmap.all_complete` from Step 1 output to determine next action.

**If `all_complete` is `true`:**

- **If `--auto-close` was provided:** Post "Action: Objective Complete" comment, close the issue (`gh issue close <issue-number>`), report: "All nodes complete - objective closed automatically"
- **Otherwise:** Ask the user directly:
  ```
  All roadmap nodes are complete. Should I close objective #<number> now?
  - Yes, close with final summary
  - Not yet, there may be follow-up work
  - I'll close it manually later
  ```
  If yes: post final comment and close. Otherwise: acknowledge and report complete.

**If `all_complete` is `false`:**

- Report the update is complete. Use `roadmap.next_node` to describe next focus.

---

## Output Format

- **Start:** "Updating objective #<number> after landing PR #<pr-number>"
- **After writes:** "Applied mechanical updates and posted action comment for #<number>"
- **End:** Either "Objective #<number> closed" or "Objective updated. Next focus: [next action]"
- **Always:** Display the objective URL

---

## Error Cases

| Scenario                              | Action                                       |
| ------------------------------------- | -------------------------------------------- |
| `objective-apply-landed-update` fails | Display error from JSON and stop             |
| Issue not found                       | Report error and exit                        |
| Issue has no `erk-objective` label    | Warn user this may not be an objective issue |
