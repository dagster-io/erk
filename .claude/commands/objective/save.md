---
description: Save current plan as an objective issue to GitHub
---

# /objective:save

Save the current plan file as an objective GitHub issue.

## Usage

Run after creating a plan in Plan mode:

```bash
/objective:save
```

---

## Agent Instructions

### Step 1: Get Session ID

Extract the current session ID from context (it should be available in the conversation context from session hooks).

### Step 2: Save to GitHub

Execute the objective save command:

```bash
erk exec objective-save-to-issue --session-id=<session-id> --format=display
```

### Step 3: Display Results

The command will output:

- Issue number and URL
- Title used for the issue
- Confirmation of success or error details

---

## Output Format

- **Success:** "Objective saved to GitHub issue #<number>"
- **Error:** Display the error message from the command

---

## Differences from /erk:plan-save

| Feature          | /erk:plan-save | /objective:save       |
| ---------------- | -------------- | --------------------- |
| Label            | `erk-plan`     | `erk-objective`       |
| Title suffix     | `[erk-plan]`   | None                  |
| Metadata block   | Yes            | No                    |
| Commands section | Yes            | No                    |
| Body content     | Metadata only  | Plan content directly |

---

## Error Cases

| Scenario             | Action                                     |
| -------------------- | ------------------------------------------ |
| No plan found        | Report error, guide to create a plan first |
| Not authenticated    | Report GitHub auth error                   |
| Issue creation fails | Report API error                           |
