---
description: Update objective issue after closing an affiliated plan
---

# /erk:objective-update-with-closed-plan

Update an objective issue after closing a plan that was affiliated with it. Resets roadmap nodes back to pending and reconciles stale prose references.

## Usage

Run after closing a plan:

```bash
/erk:objective-update-with-closed-plan --plan <number> --objective <number>
```

---

## Agent Instructions

> **Design note:** All steps run inline in the caller's context (no subagent delegation).
> This is deliberate — prose reconciliation requires judgment that benefits from
> the caller's model quality.

### Step 1: Parse Arguments and Fetch Context

Extract from `$ARGUMENTS`:

- `--plan <number>`: Plan issue number that was just closed (required)
- `--objective <number>`: Objective issue number to update (required)

Fetch objective and plan context:

```bash
erk exec objective-fetch-context --plan <plan-number> --objective <objective-number>
```

This returns JSON with:

- `objective`: Issue body, title, labels, URL
- `plan`: Plan issue body and title
- `roadmap.matched_steps`: Node IDs where `plan == #<plan_number>` (deterministic match)
- `roadmap.phases`: Serialized roadmap phases
- `roadmap.summary`: Node counts (done, pending, etc.)
- `roadmap.next_step`: First pending node or null
- `roadmap.all_complete`: True if every node is done or skipped

If this returns `success: false`, display the error and stop.

### Step 2: Update Roadmap Nodes

Read `matched_steps` from the context blob. These are the nodes affiliated with the closed plan.

If `matched_steps` is empty, skip to Step 3 (no nodes to reset).

**Reset matched nodes to pending with plan reference cleared:**

**CRITICAL: Pass ALL nodes as multiple `--node` flags in ONE command. Do NOT run separate commands per node — sequential calls cause race conditions and duplicate API calls.**

```bash
erk exec update-objective-node <objective-number> --node <node-id-1> --node <node-id-2> ... --plan "" --status pending --include-body
```

The `--include-body` flag returns the fully-mutated body as `updated_body` — use this for prose reconciliation (do NOT re-fetch via `gh issue view`).

### Step 3: Perform Prose Reconciliation

Compare `objective.objective_content` (the prose from the first comment's `objective-body` block) against the closed plan's body. Check for stale references that should be updated now that the plan has been abandoned.

If `objective_content` is null, skip prose reconciliation entirely (objective has no prose comment).

| Contradiction Type      | Example                                                         | Section to Update      |
| ----------------------- | --------------------------------------------------------------- | ---------------------- |
| Decision invalidated    | Objective says "Use approach X from plan" but plan is abandoned | Design Decisions       |
| Scope assumption        | Node descriptions assume plan's approach                        | Node descriptions      |
| Architecture reference  | Context references plan-specific implementation                 | Implementation Context |
| Constraint invalidation | Requirement listed is no longer valid                           | Implementation Context |

If nothing is stale, skip prose update entirely.

### Step 4: Update Objective Prose (First Comment)

**Only if prose reconciliation found stale sections**, update the objective's first comment (where prose lives). Use `objective_comment_id` from the `objective-header` metadata block in `objective.body` to get the comment ID.

```bash
# Update the first comment (not the issue body) with reconciled prose
gh api repos/{owner}/{repo}/issues/comments/{comment_id} -X PATCH -f body="<updated comment body>"
```

If nothing is stale, skip this step entirely.

### Step 5: Post Action Comment

Post a structured action comment directly to the objective issue:

```bash
gh issue comment <objective-number> --body "$(cat <<'EOF'
## Action: Plan #<plan> Closed

**Date:** YYYY-MM-DD
**Plan:** #<plan>
**Phase/Step:** X.Y, X.Z

### What Was Done
- Plan #<plan> was closed
- Reset nodes to pending for re-planning

### Roadmap Updates
- Node X.Y: in_progress -> pending (plan cleared)

### Body Reconciliation
- **Section**: What changed (or "No stale references found")
EOF
)"
```

### Step 6: Validate Objective

```bash
erk objective check <objective-number> --json-output
```

If checks fail, report failures and attempt to fix.

### Step 7: Report

Display what was updated:

- Which nodes were reset to pending
- Whether prose was reconciled
- The objective URL

---

## Output Format

- **Start:** "Updating objective #<number> after closing plan #<plan-number>"
- **After writes:** "Reset roadmap nodes and posted action comment for #<number>"
- **End:** "Objective updated. Next focus: [next action from roadmap.next_step]"
- **Always:** Display the objective URL

---

## Error Cases

| Scenario                        | Action                                      |
| ------------------------------- | ------------------------------------------- |
| `objective-fetch-context` fails | Display error from JSON and stop            |
| Issue not found                 | Report error and exit                       |
| No matched nodes                | Skip node update, still post action comment |
