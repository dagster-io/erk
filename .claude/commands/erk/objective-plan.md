---
description: Create an implementation plan from an objective node
argument-hint: "<objective-number-or-url> [--node <node-id>]"
allowed-tools: Bash, Skill, AskUserQuestion, EnterPlanMode
---

# /erk:objective-plan

Create an implementation plan for a specific node in an objective's dependency graph.

## Usage

```bash
/erk:objective-plan 3679
/erk:objective-plan 3679 --node 2.1
/erk:objective-plan https://github.com/owner/repo/issues/3679
/erk:objective-plan  # prompts for objective reference
```

---

## Agent Instructions

### Step 0: Check for Known Node (Fast Path)

Parse `$ARGUMENTS` for `--node <node-id>`. If `--node` is present along with an issue number:

**Invoke the inner skill immediately** via the Skill tool:

```
/erk:system:objective-plan-node <objective-number> --node <node-id>
```

This skips the interactive selection flow (Steps 1-4 below) since the node is already known. The inner skill handles marker creation, marking as planning, context gathering, plan mode, and saving.

**STOP here** — do not proceed to the steps below.

### Step 1: Resolve Objective Reference

Strip `--node` from `$ARGUMENTS` if present, then run:

```bash
erk exec resolve-objective-ref $ARGUMENTS
```

**Interpret the JSON result:**

- If `"resolved": true` with `"source": "branch_name"` or `"source": "plan_metadata"`: Inform user "Using objective #N from {source}. Run with explicit argument to override."
- If `"resolved": true` with `"source": "argument"`: Use the `objective_number` directly.
- If `"resolved": false`: Use AskUserQuestion to ask "What objective issue should I work from?"

### Step 2: Fetch and Set Up Objective Context

Run:

```bash
erk exec objective-plan-setup <objective-number> --session-id "${CLAUDE_SESSION_ID}"
```

**Interpret the JSON result:**

- If `"success": false` with `"error": "not_found"`: Report error and exit.
- If `"success": false` with `"error": "is_plan"`: Redirect to `/erk:plan-implement`.
- If `"success": false` with `"error": "validation_error"`: Report error and exit.
- If `"success": true`: Continue with the roadmap data.

Display any `"warnings"` to the user.

### Step 3: Load Objective Skill

Load the `objective` skill for format templates and guidance.

### Step 4: Display Roadmap and Prompt User

Display the roadmap table from the `roadmap.phases` data in the JSON output.

Then use AskUserQuestion to ask which node to plan:

```
Which node(s) should I create a plan for?
- Node 1A.1: <description> (Recommended) ← first pending node without plan in progress
- Node 1A.2: <description>
- Node 2B.1: <description> (plan in progress, #456) ← shown but not recommended
- All of Phase 1 (nodes 1A.1, 1A.2) ← if phase has multiple pending nodes
- (Other - specify node number(s) or description)
```

**Filtering rules (based on node `status` field from phases):**

- **Show as options:** Nodes with status `"pending"`
- **Show but deprioritize:** Nodes with status `"in_progress"` - still selectable via "Other" but not recommended
- **Hide from options:** Nodes with status `"done"`, `"blocked"`, or `"skipped"`

**Phase-level options:** For each phase that has 2+ pending nodes, show an "All of Phase X" option listing the pending node IDs.

**Recommendation rule:** Use `roadmap.next_node` from the JSON as the recommended option. If `next_node` is null, no node is recommended.

If all nodes are complete or have plans in progress, report appropriately:

- All complete: "All roadmap nodes are complete! Consider closing the objective."
- All have plans: "All pending nodes have plans in progress. You can still select one via 'Other' to create a parallel plan."

### Step 5: Invoke Inner Skill or Handle Multi-Node Inline

**Single node selected:** Delegate to the inner skill as before:

```
/erk:system:objective-plan-node <objective-number> --node <selected-node-id>
```

The inner skill handles marker creation, marking as planning, context gathering, plan mode, and saving. **STOP here** — the inner skill takes over.

**Multiple nodes selected** (phase-level or explicit multi-select): Handle inline instead of delegating:

1. **Create objective-context marker:**

```bash
erk exec marker create --session-id "${CLAUDE_SESSION_ID}" --associated-objective <objective-number> objective-context
```

2. **Create multi-node roadmap-step marker** (newline-delimited node IDs):

```bash
erk exec marker create --session-id "${CLAUDE_SESSION_ID}" \
  --content "<node-id-1>
<node-id-2>
<node-id-3>" roadmap-step
```

3. **Mark all nodes as planning:**

```bash
erk exec update-objective-node <objective-number> --node <node-id-1> --node <node-id-2> --status planning
```

4. **Enter plan mode** using EnterPlanMode. The plan should cover all selected nodes and reference the parent objective.

5. **Save as PR** via `/erk:plan-save` when plan mode exits. The multi-node marker created in step 2 is read by plan-save automatically, linking all nodes to the plan.

---

## Output Format

- **Start:** "Loading objective #<number>..."
- **After parsing:** Display roadmap nodes with status
- **After selection:** "Creating plan for node <step-id>: <description>"
- **In plan mode:** Show plan content
- **End:** Always proceed with `/erk:plan-save` — do not offer direct implementation

---

## Error Cases

| Scenario                                | Action                                                           |
| --------------------------------------- | ---------------------------------------------------------------- |
| Objective not found                     | Report error and exit                                            |
| Reference is erk-plan                   | Redirect to `/erk:plan-implement`                                |
| No pending nodes                        | Report all nodes complete, suggest closing                       |
| Invalid argument format                 | Prompt for valid issue number                                    |
| Roadmap not parseable                   | Ask user to specify which node to plan                           |
| Verification fails (no objective_issue) | `/erk:plan-save` handles automatically; follow remediation steps |

---

## Important Notes

- **Objective context matters:** Read the full objective for design decisions and lessons learned
- **Single or multi-node:** Each plan can focus on a single node or multiple related nodes (e.g., all nodes in a phase)
- **Link back:** Always reference the parent objective in the plan
- **Steelthread pattern:** If planning a Phase A node, focus on minimal vertical slice

## Post-Plan Behavior

**CRITICAL: Objective plans must ALWAYS be saved as PRs.** When the exit-plan-mode hook presents save-or-implement options, ALWAYS proceed with "Create a plan PR" by running `/erk:plan-save`. Do NOT offer to implement directly — objective node plans require PR tracking for the objective's roadmap status to work correctly.
