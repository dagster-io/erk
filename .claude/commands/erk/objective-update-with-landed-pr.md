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

### Step 1: Apply Mechanical Updates

Check `$ARGUMENTS` for optional overrides:

- `--pr <number>`: PR number that was just landed
- `--objective <number>`: Objective issue number to update
- `--branch <name>`: Original branch name
- `--plan <number>`: Plan issue number (enables direct plan lookup, avoids branch-based discovery which may fail after branch deletion)
- `--auto-close`: If set and all nodes are complete, close objective without asking

Run a single command that fetches context, updates roadmap nodes to done, and posts an action comment:

```bash
erk exec objective-apply-landed-update [--pr <number>] [--objective <number>] [--plan <number>] [--branch <name>]
```

Optionally pass `--node` flags to specify which roadmap nodes to mark as done. When omitted, the command auto-matches nodes whose `pr` field references the landing PR (e.g., `pr: "#6517"`):

```bash
# Explicit node specification:
erk exec objective-apply-landed-update [--pr <number>] [--objective <number>] [--plan <number>] [--branch <name>] --node <id1> [--node <id2> ...]

# Auto-match (no --node flags needed when nodes already have pr references):
erk exec objective-apply-landed-update [--pr <number>] [--objective <number>] [--plan <number>] [--branch <name>]
```

This returns JSON with:

- `objective`: Issue body, title, labels, URL, `objective_content` (prose from first comment)
- `plan`: Plan issue body and title
- `pr`: PR title, body, URL
- `roadmap`: Parsed roadmap with `summary`, `next_node`, `all_complete`
- `node_updates`: List of nodes updated to done (with `previous_pr`)
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
