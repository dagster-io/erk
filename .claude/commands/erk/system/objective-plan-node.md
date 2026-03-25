---
description: Create an implementation plan for a known objective node (inner skill)
argument-hint: "<objective-number> --node <node-id> [--node <node-id>...]"
allowed-tools: Bash, Task, Skill, AskUserQuestion, EnterPlanMode
---

# /erk:system:objective-plan-node

Inner skill for creating an implementation plan when the objective issue and node ID are already known. Called by the outer `/erk:objective-plan` command or directly by `plan_cmd.py` via Claude launch.

This skips interactive node selection (Steps 4-5 of the outer command) since the node is already determined.

## Usage

```bash
/erk:system:objective-plan-node 3679 --node 2.1
/erk:system:objective-plan-node 3679 --node 3.1 --node 3.2 --node 3.3
```

`<objective-number>` and at least one `--node <node-id>` are required. Multiple `--node` flags are supported for multi-node planning.

---

## Agent Instructions

### Step 1: Parse Arguments

Parse `$ARGUMENTS` to extract:

- **Objective number**: The numeric objective reference (required)
- **Node IDs**: All `--node` values (at least one required; multiple allowed)

Examples:

- `3679 --node 2.1` → objective=3679, node_ids=["2.1"]
- `3679 --node 3.1 --node 3.2 --node 3.3` → objective=3679, node_ids=["3.1", "3.2", "3.3"]

If either objective number or at least one `--node` is missing, STOP and report: "ERROR: Both objective number and at least one --node are required. Usage: /erk:system:objective-plan-node <objective-number> --node <node-id> [--node <node-id>...]"

### Step 2: Create Objective Context Marker

Launch a Task agent to fetch objective data and create the context marker:

Use the Task tool with `subagent_type: "general-purpose"` and `model: "haiku"`:

**Task Prompt:**

```
Fetch and validate objective #<objective-number> and return a structured summary.

CRITICAL: Do NOT write scripts or code. Only use the Bash tool to run the erk CLI commands listed below.

Instructions:
1. Run: erk exec get-issue-body <objective-number>
2. Validate this is an objective:
   - Check for 'erk-objective' label
   - If 'erk-pr' label instead: return error "This is an erk-pr PR, not an objective"
   - If neither label: include warning but proceed
3. Create objective context marker:
   erk exec marker create --session-id "${CLAUDE_SESSION_ID}" --associated-objective <objective-number> objective-context
4. Run: erk objective check <objective-number> --json-output --allow-legacy
5. Format the JSON output from step 4 into the structured summary below. Do NOT write Python or any other scripts to parse the data — just read the JSON output directly and format it yourself.

OBJECTIVE: #<number> — <title>
STATUS: <OPEN|CLOSED>

ROADMAP:
| Node | Phase | Description | Status |
| 1.1 | Phase 1 | <description> | done (PR #123) |
| 1.2 | Phase 1 | <description> | pending |
| 2.1 | Phase 2 | <description> | blocked |

PENDING_NODES:
- 1.2: <description>
- 3.1: <description>

RECOMMENDED: <node-id or "none">

WARNINGS: <any warnings about labels, roadmap format, etc., or "none">

Status mapping:
- "pending" → "pending"
- "done" → "done (PR #XXX)"
- "in_progress" → "plan in progress (#XXX)"
- "blocked" → "blocked"
- "skipped" → "skipped"

Only include nodes with status "pending" in PENDING_NODES section.
Use the "next_step" field from check output as RECOMMENDED.
```

Replace `<objective-number>` with the parsed objective number.

### Step 3: Verify Objective Context Marker

```bash
erk exec marker read --session-id "${CLAUDE_SESSION_ID}" objective-context
```

If this returns a value matching the objective issue number, proceed.
If it fails or returns wrong value, STOP and report:
"ERROR: objective-context marker not created. Re-run the marker command manually:
erk exec marker create --session-id '${CLAUDE_SESSION_ID}' --associated-objective <issue-number> objective-context"

### Step 4: Create Roadmap Node Marker and Mark as Planning

Create the roadmap-step marker with all selected node IDs as a comma-separated string:

```bash
# Single node:
erk exec marker create --session-id "${CLAUDE_SESSION_ID}" \
  --content "3.1" roadmap-step

# Multiple nodes:
erk exec marker create --session-id "${CLAUDE_SESSION_ID}" \
  --content "3.1,3.2,3.3" roadmap-step
```

Join all node IDs from arguments with commas (no spaces) as the `--content` value.

Then mark all nodes as `planning` in the objective's roadmap (best-effort — may already be marked by the CLI):

```bash
erk exec update-objective-node <objective-number> --node <node-id-1> [--node <node-id-2> ...] --status planning
```

Pass a `--node` flag for each node ID. If this fails, continue with planning — the CLI may have already marked them.

### Step 5: Load Objective Skill

Load the `objective` skill for format templates and guidance.

### Step 6: Gather Context

Before entering plan mode, gather relevant context:

1. **Objective context:** Goal, design decisions, implementation context
2. **Node context:** What the specific node requires
3. **Prior work:** Look at completed nodes and their PRs for patterns

Use this context to inform the plan.

### Step 7: Enter Plan Mode

Enter plan mode to create the implementation plan:

1. Use the EnterPlanMode tool
2. Focus the plan on the specific node selected
3. Reference the parent objective in the plan

**Plan should include:**

- Reference to objective: `Part of Objective #<number>, Node <node-id>`
- Clear goal for this specific node
- Implementation phases (typically 1-3 for a single node)
- Files to modify
- Test requirements

### Step 8: Save Plan as PR (Always Save)

After the plan is approved in plan mode, **always save as a PR** — do not offer direct implementation. When the `exit-plan-mode-hook` fires, proceed directly with `/erk:plan-save`. Objective node plans require PR tracking for the objective's roadmap status to work correctly.

The objective-context marker created in Step 2 is automatically read by `/erk:plan-save`. Simply run `/erk:plan-save` and it will link the plan to the objective.

**If the marker was not created (fallback):**
Create it manually before saving:

```bash
erk exec marker create --session-id "${CLAUDE_SESSION_ID}" --associated-objective <objective-number> objective-context
```

Then run `/erk:plan-save`.

### Step 9: Verify Objective Link

After saving, the JSON output includes `objective_issue`. Check that it matches the expected objective number.

If verification is needed:

```bash
erk exec get-pr-metadata <new-plan-number> objective_issue
```

Check that `value` matches the expected objective number.

---

## Output Format

- **Start:** "Planning node(s) <node-id(s)> of objective #<number>..."
- **After context:** Display node description and gathered context
- **In plan mode:** Show plan content
- **End:** Always proceed with `/erk:plan-save` — do not offer direct implementation

---

## Error Cases

| Scenario                                | Action                                                           |
| --------------------------------------- | ---------------------------------------------------------------- |
| Missing objective number or node ID     | Report error with usage instructions                             |
| Objective not found                     | Report error and exit                                            |
| Reference is erk-pr                     | Redirect to `/erk:plan-implement`                                |
| Node not found in roadmap               | Report error and list available nodes                            |
| Marker creation fails                   | Report error with manual command                                 |
| Verification fails (no objective_issue) | `/erk:plan-save` handles automatically; follow remediation steps |

---

## Important Notes

- **This is an inner skill** — it expects the node to be pre-selected, not interactive
- **Best-effort marking** — the `planning` status update may already be done by the CLI before Claude launches
- **Objective context matters:** Read the full objective for design decisions and lessons learned
- **Plans can target one or multiple nodes:** Single node is typical; multi-node is supported for related steps in the same phase
- **Link back:** Always reference the parent objective in the plan
