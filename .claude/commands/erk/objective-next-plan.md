---
description: Create an implementation plan from an objective step
argument-hint: <issue-number-or-url>
---

# /erk:objective-create-plan

Create an implementation plan for a specific step in an objective's roadmap.

## Usage

```bash
/erk:objective-create-plan 3679
/erk:objective-create-plan https://github.com/owner/repo/issues/3679
/erk:objective-create-plan  # prompts for issue reference
```

---

## Agent Instructions

### Step 1: Parse Issue Reference

Parse `$ARGUMENTS` to extract the issue reference:

- If argument is a URL: extract issue number from path
- If argument is a number: use directly
- If no argument provided: try to get the default from current branch's plan (see below), then prompt if no default

**Getting default objective from current branch's plan:**

If no argument is provided, check if the current branch is associated with a plan:

1. Get current branch name:

   ```bash
   git rev-parse --abbrev-ref HEAD
   ```

2. Check if branch follows the P-prefix pattern (e.g., `P5731-some-title-01-23-2354`):
   - Pattern: `^P(\d+)-` (case insensitive)
   - Extract the issue number if matched

3. If plan issue found, get its objective:

   ```bash
   erk exec get-plan-metadata <plan-issue-number> objective_issue
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
   "Using objective #<value> from current branch's plan #<plan-issue>. Run with explicit argument to override."

If no default found from current branch, prompt user using AskUserQuestion with "What objective issue should I work from?"

### Step 2: Launch Task Agent for Data Fetching

Use the Task tool with `subagent_type: "general-purpose"` and `model: "haiku"` to fetch and parse objective data:

**Task Prompt:**

```
Fetch and validate objective #<issue-number> and return a structured summary.

Instructions:
1. Run: erk exec get-issue-body <issue-number>
2. Validate this is an objective:
   - Check for 'erk-objective' label
   - If 'erk-plan' label instead: return error "This is an erk-plan issue, not an objective"
   - If neither label: include warning but proceed
3. Create objective context marker:
   erk exec marker create --session-id "${CLAUDE_SESSION_ID}" --associated-objective <issue-number> objective-context
4. Run: erk objective check <issue-number> --json-output --allow-legacy
5. Return a compact structured summary in this exact format:

OBJECTIVE: #<number> — <title>
STATUS: <OPEN|CLOSED>

ROADMAP:
| Step | Phase | Description | Status |
| 1.1 | Phase 1 | <description> | done (PR #123) |
| 1.2 | Phase 1 | <description> | pending |
| 2.1 | Phase 2 | <description> | blocked |

PENDING_STEPS:
- 1.2: <description>
- 3.1: <description>

RECOMMENDED: <step-id or "none">

WARNINGS: <any warnings about labels, roadmap format, etc., or "none">

Status mapping:
- "pending" → "pending"
- "done" → "done (PR #XXX)"
- "in_progress" → "plan in progress (#XXX)"
- "blocked" → "blocked"
- "skipped" → "skipped"

Only include steps with status "pending" in PENDING_STEPS section.
Use the "next_step" field from check output as RECOMMENDED.
```

Replace `<issue-number>` with the issue number from Step 1.

**Important:** The Task agent handles all JSON parsing and marker creation. The main conversation only receives the formatted summary.

### Step 3: Load Objective Skill

Load the `objective` skill for format templates and guidance.

### Step 4: Display Roadmap and Prompt User

Display the roadmap table from the Task agent's output to the user.

Then use AskUserQuestion to ask which step to plan:

```
Which step should I create a plan for?
- Step 1A.1: <description> (Recommended) ← first pending step without plan in progress
- Step 1A.2: <description>
- Step 2B.1: <description> (plan in progress, #456) ← shown but not recommended
- (Other - specify step number or description)
```

**Filtering rules (based on JSON `status` field):**

- **Show as options:** Steps with status `"pending"`
- **Show but deprioritize:** Steps with status `"in_progress"` - still selectable via "Other" but not recommended
- **Hide from options:** Steps with status `"done"`, `"blocked"`, or `"skipped"`

**Recommendation rule:** Use the `next_step` field from the roadmap check JSON as the recommended option. If `next_step` is null, no step is recommended.

If all steps are complete or have plans in progress, report appropriately:

- All complete: "All roadmap steps are complete! Consider closing the objective."
- All have plans: "All pending steps have plans in progress. You can still select one via 'Other' to create a parallel plan."

### Step 5: Create Roadmap Step Marker

After the user selects a step, create a marker to store the selected step ID for later use by `plan-save`:

```bash
erk exec marker create --session-id "${CLAUDE_SESSION_ID}" \
  --content "<step-id>" roadmap-step
```

Replace `<step-id>` with the step ID selected by the user (e.g., "2A.1"). This marker enables `plan-save` to automatically update the objective's roadmap table with the plan issue number.

### Step 6: Gather Context

Before entering plan mode, gather relevant context:

1. **Objective context:** Goal, design decisions, implementation context
2. **Step context:** What the specific step requires
3. **Prior work:** Look at completed steps and their PRs for patterns

Use this context to inform the plan.

### Step 7: Enter Plan Mode

Enter plan mode to create the implementation plan:

1. Use the EnterPlanMode tool
2. Focus the plan on the specific step selected
3. Reference the parent objective in the plan

**Plan should include:**

- Reference to objective: `Part of Objective #<number>, Step <step-id>`
- Clear goal for this specific step
- Implementation phases (typically 1-3 for a single step)
- Files to modify
- Test requirements

### Step 8: Save Plan with Objective Link

After the plan is approved in plan mode, the `exit-plan-mode-hook` will prompt to save or implement.

**If the objective-context marker was created in Step 2:**
The hook will automatically suggest the correct command with `--objective-issue=<objective-number>`. Simply follow the hook's suggestion.

**If the marker was not created (fallback):**
Use the objective-aware save command manually:

```bash
/erk:plan-save --objective-issue=<objective-number>
```

Replace `<objective-number>` with the objective issue number from Step 2.

This will:

- Create a GitHub issue with the erk-plan label
- Link it to the parent objective (stored in metadata)
- Enable objective-aware landing via `/erk:land`

### Step 9: Verify Objective Link

After the plan is approved in plan mode, the `exit-plan-mode-hook` will prompt to save or implement.

**If the objective-context marker was created in Step 2:**
The hook will automatically suggest `/erk:plan-save --objective-issue=<objective-number>`.

When you run this command, it will:

- Save the plan to GitHub with objective metadata
- Automatically verify the objective link was saved correctly
- Display "Verified objective link: #<number>" on success
- Fail with remediation steps if verification fails

**Note:** If using `erk exec plan-save-to-issue` directly (not recommended), you must verify manually:

```bash
erk exec get-issue-body <new-issue-number>
```

Check the `body` field in the JSON response contains `objective_issue`.

---

## Output Format

- **Start:** "Loading objective #<number>..."
- **After parsing:** Display roadmap steps with status
- **After selection:** "Creating plan for step <step-id>: <description>"
- **In plan mode:** Show plan content
- **End:** Guide to `/erk:plan-save`

---

## Error Cases

| Scenario                                | Action                                                           |
| --------------------------------------- | ---------------------------------------------------------------- |
| Issue not found                         | Report error and exit                                            |
| Issue is erk-plan                       | Redirect to `/erk:plan-implement`                                |
| No pending steps                        | Report all steps complete, suggest closing                       |
| Invalid argument format                 | Prompt for valid issue number                                    |
| Roadmap not parseable                   | Ask user to specify which step to plan                           |
| Verification fails (no objective_issue) | `/erk:plan-save` handles automatically; follow remediation steps |

---

## Important Notes

- **Objective context matters:** Read the full objective for design decisions and lessons learned
- **One step at a time:** Each plan should focus on a single roadmap step
- **Link back:** Always reference the parent objective in the plan
- **Steelthread pattern:** If planning a Phase A step, focus on minimal vertical slice
