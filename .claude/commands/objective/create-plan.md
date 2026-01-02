---
description: Create an implementation plan from an objective step
argument-hint: <issue-number-or-url>
---

# /objective:create-plan

Create an implementation plan for a specific step in an objective's roadmap.

## Usage

```bash
/objective:create-plan 3679
/objective:create-plan https://github.com/owner/repo/issues/3679
/objective:create-plan  # prompts for issue reference
```

---

## Agent Instructions

### Step 1: Parse Issue Reference

Parse `$ARGUMENTS` to extract the issue reference:

- If argument is a URL: extract issue number from path
- If argument is a number: use directly
- If no argument provided: prompt user using AskUserQuestion with "What objective issue should I work from?"

### Step 2: Fetch and Validate Issue

```bash
gh issue view <issue-number> --json number,title,body,labels
```

**Validate this is an objective:**

1. Check for `erk-objective` label
2. If label is `erk-plan` instead: report error "This is an erk-plan issue, not an objective. Use `/erk:plan-implement` instead."
3. If neither label: warn but proceed

### Step 3: Load Objective Skill

Load the `objective` skill for format templates and guidance.

### Step 4: Parse Roadmap and Display Steps

Parse the objective body to extract roadmap steps. Look for markdown tables with columns like:

| Step | Description | Status | PR |

Extract all steps and display them to the user:

```
Objective #<number>: <title>

Roadmap Steps:
  [1] Step 1A.1: <description> (pending)
  [2] Step 1A.2: <description> (pending)
  [3] Step 1B.1: <description> (done, PR #123)
  ...
```

Show status indicators:

- `(pending)` - available to plan
- `(done, PR #XXX)` - already completed
- `(blocked)` - cannot be worked yet
- `(skipped)` - explicitly skipped

### Step 5: Prompt User to Select Step

Use AskUserQuestion to ask which step to plan:

```
Which step should I create a plan for?
- Step 1A.1: <description>
- Step 1A.2: <description>
- Step 1B.1: <description>
- (Other - specify step number or description)
```

Only show steps that are `pending` or `blocked` (not already `done` or `skipped`).

If all steps are complete, report: "All roadmap steps are complete! Consider closing the objective."

### Step 6: Gather Context for Planning

Before entering plan mode, gather relevant context:

1. **Objective context:** Goal, design decisions, current focus
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

### Step 8: Guide to Save Plan

After the plan is approved in plan mode, remind the user:

```
Plan ready! To save this as an erk-plan issue for implementation:

  /erk:plan-save

This will:
- Create a GitHub issue with the erk-plan label
- Link it to the parent objective
- Generate a plan branch for implementation
```

---

## Output Format

- **Start:** "Loading objective #<number>..."
- **After parsing:** Display roadmap steps with status
- **After selection:** "Creating plan for step <step-id>: <description>"
- **In plan mode:** Show plan content
- **End:** Guide to `/erk:plan-save`

---

## Error Cases

| Scenario                | Action                                     |
| ----------------------- | ------------------------------------------ |
| Issue not found         | Report error and exit                      |
| Issue is erk-plan       | Redirect to `/erk:plan-implement`          |
| No pending steps        | Report all steps complete, suggest closing |
| Invalid argument format | Prompt for valid issue number              |
| Roadmap not parseable   | Ask user to specify which step to plan     |

---

## Important Notes

- **Objective context matters:** Read the full objective for design decisions and lessons learned
- **One step at a time:** Each plan should focus on a single roadmap step
- **Link back:** Always reference the parent objective in the plan
- **Steelthread pattern:** If planning a Phase A step, focus on minimal vertical slice
