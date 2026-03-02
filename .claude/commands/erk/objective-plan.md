---
description: Create an implementation plan from an objective node
argument-hint: "<objective-number-or-url> [--node <node-id>]"
allowed-tools: Bash, Task, Skill, AskUserQuestion, EnterPlanMode
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

This skips the interactive selection flow (Steps 1-5 below) since the node is already known. The inner skill handles marker creation, marking as planning, context gathering, plan mode, and saving.

**STOP here** — do not proceed to the steps below.

### Step 1: Parse Issue Reference (Interactive Flow)

If `--node` was NOT provided, proceed with the full interactive flow.

Parse `$ARGUMENTS` to extract the objective reference:

- If argument is a URL: extract objective number from path
- If argument is a number: use directly
- If no argument provided: try to get the default from current branch's plan (see below), then prompt if no default

**Getting default objective from current branch's plan:**

If no argument is provided, check if the current branch is associated with a plan:

1. Get current branch name:

   ```bash
   git rev-parse --abbrev-ref HEAD
   ```

2. Check if `ref.json` exists in `.erk/impl-context/<branch>/` and extract the plan ID from it. If not found, check for legacy P-prefix pattern for backwards compatibility:
   - Legacy pattern: `^P(\d+)-` (e.g., `P5731-some-title-01-23-2354`)
   - Current format: Branch names use `plnd/` prefix; plan ID is resolved via plan-ref.json

3. If plan found, get its objective:

   ```bash
   erk exec get-plan-metadata <plan-number> objective_issue
   ```

   This returns JSON like:

   ```json
   {
     "success": true,
     "value": 123,
     "issue_number": 5731,
     "field": "objective_issue"
   }
   ```

   or if no objective:

   ```json
   {
     "success": true,
     "value": null,
     "issue_number": 5731,
     "field": "objective_issue"
   }
   ```

4. If `value` is not null, use it as the default and inform the user:
   "Using objective #<value> from current branch's plan #<plan-number>. Run with explicit argument to override."

If no default found from current branch, prompt user using AskUserQuestion with "What objective issue should I work from?"

### Step 2: Launch Task Agent for Data Fetching

Use the Task tool with `subagent_type: "general-purpose"` and `model: "haiku"` to fetch and parse objective data:

**Task Prompt:**

```
Fetch and validate objective #<objective-number> and return a structured summary.

CRITICAL: Do NOT write scripts or code. Only use the Bash tool to run the erk CLI commands listed below.

Instructions:
1. Run: erk exec get-issue-body <objective-number>
2. Validate this is an objective:
   - Check for 'erk-objective' label
   - If 'erk-plan' label instead: return error "This is an erk-plan PR, not an objective"
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

Replace `<objective-number>` with the objective number from Step 1.

**Important:** The Task agent handles all JSON parsing and marker creation. The main conversation only receives the formatted summary.

### Step 3: Verify Objective Context Marker

Verify the marker was created by the Task agent:

```bash
erk exec marker read --session-id "${CLAUDE_SESSION_ID}" objective-context
```

If this returns a value matching the objective issue number, proceed.
If it fails or returns wrong value, STOP and report:
"ERROR: objective-context marker not created. Re-run the marker command manually:
erk exec marker create --session-id '${CLAUDE_SESSION_ID}' --associated-objective <issue-number> objective-context"

### Step 4: Load Objective Skill

Load the `objective` skill for format templates and guidance.

### Step 5: Display Roadmap and Prompt User

Display the roadmap table from the Task agent's output to the user.

Then use AskUserQuestion to ask which node to plan:

```
Which node should I create a plan for?
- Node 1A.1: <description> (Recommended) ← first pending node without plan in progress
- Node 1A.2: <description>
- Node 2B.1: <description> (plan in progress, #456) ← shown but not recommended
- (Other - specify node number or description)
```

**Filtering rules (based on JSON `status` field):**

- **Show as options:** Nodes with status `"pending"`
- **Show but deprioritize:** Nodes with status `"in_progress"` - still selectable via "Other" but not recommended
- **Hide from options:** Nodes with status `"done"`, `"blocked"`, or `"skipped"`

**Recommendation rule:** Use the `next_step` field from the roadmap check JSON as the recommended option. If `next_step` is null, no node is recommended.

If all nodes are complete or have plans in progress, report appropriately:

- All complete: "All roadmap nodes are complete! Consider closing the objective."
- All have plans: "All pending nodes have plans in progress. You can still select one via 'Other' to create a parallel plan."

### Step 6: Invoke Inner Skill

After the user selects a node, invoke the inner skill via the Skill tool:

```
/erk:system:objective-plan-node <objective-number> --node <selected-node-id>
```

The inner skill handles marker creation, marking as planning, context gathering, plan mode, and saving. **STOP here** — the inner skill takes over.

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
- **One node at a time:** Each plan should focus on a single roadmap node
- **Link back:** Always reference the parent objective in the plan
- **Steelthread pattern:** If planning a Phase A node, focus on minimal vertical slice

## Post-Plan Behavior

**CRITICAL: Objective plans must ALWAYS be saved as PRs.** When the exit-plan-mode hook presents save-or-implement options, ALWAYS proceed with "Create a plan PR" by running `/erk:plan-save`. Do NOT offer to implement directly — objective node plans require PR tracking for the objective's roadmap status to work correctly.
