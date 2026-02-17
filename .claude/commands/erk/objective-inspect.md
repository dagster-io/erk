---
description: View an objective's dependency graph and progress
argument-hint: "<issue-number-or-url>"
---

# /erk:objective-inspect

Display an objective's dependency graph, showing node statuses, dependencies, and the recommended next step.

## Usage

```bash
/erk:objective-inspect 3679
/erk:objective-inspect https://github.com/owner/repo/issues/3679
/erk:objective-inspect  # prompts for issue reference
```

---

## Agent Instructions

### Step 1: Parse Issue Reference

Parse `$ARGUMENTS` to extract the issue reference:

- If argument is a URL: extract issue number from path
- If argument is a number: use directly
- If no argument provided: prompt user with AskUserQuestion: "What objective issue number should I inspect?"

### Step 2: Run Inspect Command

Run the CLI command to display the dependency graph:

```bash
erk objective inspect <issue-number>
```

Display the full output to the user.

### Step 3: Suggest Next Actions

After displaying the graph, suggest relevant follow-up commands:

- `/erk:objective-plan <issue-number>` - Create a plan for the next step
- `/local:objective-view <issue-number>` - View associations and PR links

---

## Error Cases

| Scenario                      | Action                                                |
| ----------------------------- | ----------------------------------------------------- |
| Issue not found               | Report error and exit                                 |
| Issue is not an objective     | Report that the issue lacks the `erk-objective` label |
| No argument and user declines | Exit gracefully                                       |
