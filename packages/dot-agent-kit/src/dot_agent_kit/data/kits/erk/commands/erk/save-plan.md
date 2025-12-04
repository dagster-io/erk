---
description: Save the current session's plan to GitHub as an issue
---

# /erk:save-plan

## Goal

**Save the plan from the current session to GitHub as an issue.**

This command is designed to be used after exiting Plan Mode. It:

1. Gets the session ID from context (injected by `session-id-injector-hook`)
2. Validates prerequisites (git repo, gh CLI auth)
3. Creates a GitHub issue with the plan content using session-scoped lookup
4. Displays next steps for implementation

## Command Instructions

You are executing `/erk:save-plan`. Follow these steps:

### Step 1: Get Session ID

Extract the session ID from the `SESSION_CONTEXT` reminder that appears in your conversation context.

Look for a system reminder containing: `session_id=<uuid>`

The session ID will look like: `a1b2c3d4-e5f6-7890-abcd-ef1234567890`

If you cannot find a session ID in the current conversation context:

```
❌ Error: No session ID found in current context

The session-id-injector-hook should inject SESSION_CONTEXT into each prompt.
If missing, you can fall back to specifying a plan file manually:
    dot-agent run erk plan-save-to-issue --format json --plan-file <PATH>
```

### Step 2: Validate Prerequisites

1. Verify you're in a git repository:

   ```bash
   git rev-parse --is-inside-work-tree
   ```

2. Verify GitHub CLI is authenticated:
   ```bash
   gh auth status
   ```

If either fails, display an error and stop.

### Step 3: Save Plan to GitHub

Run the kit command with the **session ID** for session-scoped lookup:

```bash
result=$(dot-agent run erk plan-save-to-issue --format json --session-id "<SESSION_ID>" 2>&1)
```

Where `<SESSION_ID>` is the UUID extracted from Step 1.

**Fallback**: If no session ID is available but you can see the plan file path in conversation context (from Plan Mode messages like "You should create your plan at /path/to/plan.md"), use:

```bash
result=$(dot-agent run erk plan-save-to-issue --format json --plan-file "<PLAN_FILE_PATH>" 2>&1)
```

Parse the JSON result.

### Step 4: Handle Result

**On success**:

1. Create the saved marker to signal that the plan was saved (prevents implementation on exit):

   ```bash
   mkdir -p .erk/scratch/<SESSION_ID> && touch .erk/scratch/<SESSION_ID>/plan-saved-to-github
   ```

   Where `<SESSION_ID>` is the UUID extracted from Step 1.

2. Display:

   ```
   ✅ Plan saved to GitHub

   **Issue:** [title from result]
              [url from result]

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

3. Call `ExitPlanMode` to cleanly exit plan mode (the saved marker ensures no implementation is triggered)

**On failure**, display the error from the JSON result and suggest checking:

- That the plan file exists at the extracted path
- GitHub CLI authentication
- Network connectivity

## Usage

Run this command after Claude naturally enters and exits Plan Mode:

1. Claude enters Plan Mode for a complex task
2. You approve the plan
3. Claude exits Plan Mode (plan saved to `~/.claude/plans/`)
4. Run `/erk:save-plan` in the **same session** to save to GitHub

## Why Session-Scoped Plan Lookup?

Multiple Claude sessions can run in parallel, each creating their own plans. Using the "most recent" file by modification time could pick up the wrong plan from a different session. By using session-scoped lookup via the session ID, the CLI command parses session logs to find the `slug` field that corresponds to the plan filename, ensuring we save the correct plan for this specific session.
