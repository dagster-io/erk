---
description: Update objective issue after landing a PR
---

# /erk:system:objective-update-with-landed-pr

Update an objective issue after landing a PR from a plan branch.

## Usage

Run after landing a PR:

```bash
/erk:system:objective-update-with-landed-pr
```

---

## Agent Instructions

> **Design note:** All steps run inline in the caller's context (no subagent delegation).
> Step 2 (prose reconciliation + insight generation) requires LLM judgment, and Step 3 (closing prompt)
> requires direct user interaction.

### Step 1: Apply Mechanical Updates

Check `$ARGUMENTS` for optional overrides:

- `--pr <number>`: PR number that was just landed (also used as the plan number)
- `--objective <number>`: Objective number to update
- `--branch <name>`: Original branch name
- `--auto-close`: If set and all nodes are complete, close objective without asking

Run a single command that fetches context and updates roadmap nodes to done. The PR number doubles as the plan number (in erk, the PR IS the plan):

```bash
erk exec objective-apply-landed-update [--pr <number>] [--objective <number>] [--branch <name>]
```

Optionally pass `--node` flags to specify which roadmap nodes to mark as done. When omitted, the command auto-matches nodes whose `pr` field references the landing PR (e.g., `pr: "#6517"`):

```bash
# Explicit node specification:
erk exec objective-apply-landed-update [--pr <number>] [--objective <number>] [--branch <name>] --node <id1> [--node <id2> ...]

# Auto-match (no --node flags needed when nodes already have pr references):
erk exec objective-apply-landed-update [--pr <number>] [--objective <number>] [--branch <name>]
```

This returns JSON with:

- `objective`: Issue body, title, labels, URL, `objective_content` (prose from first comment)
- `plan`: Plan body and title
- `pr`: PR title, body, URL
- `roadmap`: Parsed roadmap with `summary`, `next_node`, `all_complete`
- `node_updates`: List of nodes updated to done (with `previous_pr`)
- `changed_files`: List of files changed in the PR

If this returns `success: false`, display the error and stop.

### Step 1.5: Fetch Commit Messages

Fetch the PR's commit messages for use in insight generation:

```bash
erk exec get-pr-commits <pr_number>
```

### Step 2: Prose Reconciliation + Insight Generation

Compare `objective.objective_content` (the prose from the first comment's `objective-body` block) against what the PR actually did.

If `objective_content` is null, skip prose reconciliation entirely (objective has no prose comment).

- Read each Design Decision. Did the PR override or refine any?
- Read Implementation Context. Does the architecture description still match?
- Read upcoming node descriptions. Did this PR change the landscape?
- If nothing is stale, skip prose update entirely.

**If `node_updates` from Step 1 was empty** (auto-match found no nodes) and the roadmap has non-terminal nodes (`in_progress` or `pending`), assess during prose reconciliation whether any of those nodes were completed by this PR. For each node the PR completed:

```bash
erk exec update-objective-node <objective_number> --node <node_id> --status done --pr "#<pr_number>"
```

This keeps the YAML accurate and ensures `all_complete` reflects the true state for Step 3.

| Contradiction Type          | Example                                                      | Section to Update                                            |
| --------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| **Decision override**       | Objective says "Use polling", PR implemented WebSockets      | Design Decisions                                             |
| **Scope change**            | Node says "Add 3 methods", PR only needed 2                  | Node description (via `update-objective-node --description`) |
| **Naming divergence**       | Node says `@json_output`, PR implemented `@json_command`     | Node description (via `update-objective-node --description`) |
| **Architecture drift**      | Context says "config in config.py", PR moved it to settings/ | Implementation Context                                       |
| **Constraint invalidation** | Requirement listed is no longer valid                        | Implementation Context                                       |
| **New discovery**           | PR revealed a caching bug affecting future nodes             | Implementation Context or new Design Decision                |

**Node description reconciliation:** For each node in `roadmap.phases[].nodes[]`, compare the `description` against what the PR actually implemented:

- **Done nodes** (from `node_updates` in Step 1): Did the implementation rename, reshape, or change scope? Update if the description no longer accurately describes what was built.
- **Pending/in_progress nodes**: Did this PR change APIs, types, or patterns that make a future node's description inaccurate?

For each stale description:

```bash
erk exec update-objective-node <objective_number> --node <node_id> --description "<corrected description>"
```

Keep descriptions concise (same style/length as existing nodes). Do node description updates _before_ prose updates, since `update-objective-node` re-renders the comment table.

**If prose reconciliation found stale sections**, update the objective's first comment. Parse `objective_comment_id` from `objective.body`'s `objective-header` metadata block, then update:

```bash
gh api repos/{owner}/{repo}/issues/comments/{comment_id} -X PATCH -f body="<updated comment body>"
```

**Plan-vs-Actual Insight Generation:**

After prose reconciliation, compare two things:
1. **Plan intent** — the original plan from `plan.body` + node descriptions from the roadmap
2. **Actual implementation** — `changed_files` list + commit messages (from Step 1.5)

From this delta, generate 1-3 insights focused on what's useful for remaining objective nodes:
- **Scope divergence**: Plan said N files, PR touched M — what was unexpected?
- **API/naming changes**: Did the implementation choose different names than planned? Future nodes need to know.
- **Discovered coupling**: Did the PR reveal dependencies between modules not anticipated in the roadmap?
- **Tooling/approach notes**: What approach worked (or didn't) that future nodes should reuse (or avoid)?
- **Node staleness**: Did this PR invalidate assumptions in pending node descriptions?

Each insight is a single sentence. Omit trivial observations. Empty list if genuinely nothing noteworthy.

### Step 2.5: Post Action Comment

After prose reconciliation and insight generation, post the action comment via the existing exec command.

Build JSON with these fields and pipe it to the command:

```bash
echo '<json>' | erk exec objective-post-action-comment
```

JSON fields:
- `issue_number`: The objective issue number
- `date`: Today's date (`YYYY-MM-DD`)
- `pr_number`: The PR number that was landed
- `phase_step`: Comma-separated node IDs (or `"N/A"` if none)
- `title`: `"Objective Complete"` if auto-closed, otherwise `"Landed PR #<number>"`
- `what_was_done`: `["Landed <pr.title> (#<pr.number>)"]`
- `lessons_learned`: Generated insights from Step 2 (or `[]`)
- `roadmap_updates`: `["Node <id>: -> done"]` per node from `node_updates`
- `body_reconciliation`: Any section updates from prose reconciliation (or `[]`)

### Step 3: Closing Triggers

**If `auto_closed: true` in Step 1 output:** The exec command already closed the objective. The action comment posted in Step 2.5 reflects "Objective Complete". Report: "All nodes complete - objective closed automatically" and show the objective URL. Skip the rest of Step 3.

Use `roadmap.all_complete` from Step 1 output as the primary signal. Additionally, if `node_updates` from Step 1 was empty (auto-match found no nodes) AND Step 2 prose reconciliation confirmed all roadmap nodes are now done, treat `all_complete` as `true` for the purposes of this step.

**If `all_complete` is `true`:**

- Ask the user directly:
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
- **After writes:** "Applied mechanical updates for #<number>"
- **After comment:** "Posted action comment with insights for #<number>"
- **End:** Either "Objective #<number> closed" or "Objective updated. Next focus: [next action]"
- **Always:** Display the objective URL

---

## Error Cases

| Scenario                              | Action                                       |
| ------------------------------------- | -------------------------------------------- |
| `objective-apply-landed-update` fails | Display error from JSON and stop             |
| Issue not found                       | Report error and exit                        |
| Issue has no `erk-objective` label    | Warn user this may not be an objective issue |
