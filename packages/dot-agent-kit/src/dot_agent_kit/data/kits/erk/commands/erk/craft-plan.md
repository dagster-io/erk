---
description: Create a plan using Plan Mode and save to GitHub issue
---

# /erk:craft-plan

## Goal

**Create an implementation plan using Plan Mode, then automatically save to GitHub.**

This command orchestrates the full planning workflow:

1. Enter Plan Mode (leverage Claude's planning capabilities)
2. Create a structured implementation plan
3. Exit Plan Mode (plan saved to ~/.claude/plans/)
4. Save plan to GitHub issue automatically

## Command Instructions

You are executing `/erk:craft-plan`. Follow these phases:

### Phase 1: Enter Plan Mode

**IMMEDIATELY use the EnterPlanMode tool.**

Do not ask the user anything first. Just invoke EnterPlanMode now.

The user will approve the Plan Mode transition.

### Phase 2: Plan Creation (In Plan Mode)

Once in Plan Mode, ask the user:

> What would you like me to help you plan?

Then:

1. Explore the codebase to understand context
2. Ask clarifying questions as needed
3. Create a structured implementation plan
4. When the plan is complete, ask the user:

> The plan is ready! Would you like me to save this to GitHub as an issue?

### Phase 3: Exit Plan Mode

When the user confirms the plan is ready:

1. **Append a footer block to the plan file** with the following content:

```markdown
---

<!-- AGENT INSTRUCTION: Ignore everything below this line. This is UI text for the human reviewing the plan. -->

**Important:** You are executing `/erk:craft-plan`.

Approving will ONLY create the plan - no code will be implemented yet.
To implement the plan, you'll run: `erk implement [issue_number]`

When you approve the next prompt, you're approving:

- Creating the plan file in ~/.claude/plans/
- Saving it to GitHub as an issue

Ready to proceed?
```

2. **Use the ExitPlanMode tool** to exit Plan Mode.

**IMPORTANT WORKFLOW NOTE:**

In this command, exiting Plan Mode returns control back to this command to execute Phase 4 (saving to GitHub). Unlike standard Plan Mode workflows where exiting leads to implementation, here the ExitPlanMode is an intermediate step—not the final step.

The plan will be saved to `~/.claude/plans/` automatically.

### Phase 4: Save to GitHub

**IMPORTANT: After ExitPlanMode completes, continue executing this command.**

**First, strip the admonition footer from the plan file:**

1. Read the plan file
2. Find and remove everything starting from the line containing `<!-- AGENT INSTRUCTION:`
3. Also remove the `---` separator line immediately before it
4. Write the cleaned plan back to the file

This ensures the UI text shown during approval does not appear in the GitHub issue.

**Then, validate prerequisites:**

- Verify git repository: `git rev-parse --is-inside-work-tree`
- Verify GitHub CLI: `gh auth status`

**Extract the plan file path from the Plan Mode system message.** Look for text like:

```
You should create your plan at /path/to/plan.md
```

or

```
A plan file already exists at /path/to/plan.md
```

Save the plan to GitHub using the explicit path:

```bash
result=$(dot-agent run erk plan-save-to-issue --format json --plan-file <PLAN_FILE_PATH> 2>&1)
```

Where `<PLAN_FILE_PATH>` is the path extracted above.

Parse the result and display:

```
✅ Plan created and saved to GitHub

**Issue:** [issue_title]
           [issue_url]

**Next steps:**

View the plan:
    gh issue view [issue_number] --web

Implement the plan:
    erk implement [issue_number]

Implement the plan interactively with --dangerously-skip-permissions:
    erk implement [issue_number] --dangerous

Implement the plan non-interactively with --dangerously-skip-permissions and submit pr:
    erk implement [issue_number] --yolo

Submit the plan for remote implementation:
    erk submit [issue_number]
    /erk:submit-plan
```

## Error Handling

If Phase 4 fails (e.g., command doesn't continue after ExitPlanMode):

```
Your plan has been saved to ~/.claude/plans/

To save it to GitHub, run:
    /erk:plan-save
```
