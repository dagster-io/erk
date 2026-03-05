---
description: List open objectives
context: fork
agent: general-purpose
model: haiku
---

# /erk:objective-list

List all open objectives in the current repository with enriched dashboard columns.

## Agent Instructions

### Step 1: Run CLI Command

Run:

```bash
erk objective list
```

### Step 2: Display Results

Show the CLI output directly to the user. The command produces a Rich table with columns:
`#`, `slug`, `prog`, `state`, `deps-state`, `deps`, `next`, `updated`, `created by`.

If no objectives found, report: "No open objectives found."

### Step 3: Suggest Next Steps

After listing, suggest:

- `/local:objective-view <number>` — View dependency graph, dependencies, and progress
- `/erk:objective-plan <number>` — Create a plan for the next node
