---
title: Implementation Folder Lifecycle
read_when:
  - "working with .impl/ or .worker-impl/ folders"
  - "understanding remote implementation workflow"
  - "debugging plan visibility in PRs"
---

# Implementation Folder Lifecycle

The erk system uses two distinct folders for implementation plans, each with different visibility and lifecycle characteristics.

## .worker-impl/ (Committed, Visible)

| Property   | Value                                                |
| ---------- | ---------------------------------------------------- |
| Created by | `create-worker-impl-from-issue` command              |
| Purpose    | Make plan visible in PR immediately                  |
| Contains   | plan.md, issue.json, progress.md, README.md          |
| Lifecycle  | Created before remote impl, deleted after completion |
| Committed  | Yes (visible in PR diff)                             |

## .impl/ (Local, Never Committed)

| Property   | Value                                              |
| ---------- | -------------------------------------------------- |
| Created by | Copy of .worker-impl/ OR local `erk implement`     |
| Purpose    | Working directory for implementation               |
| Contains   | Same structure as .worker-impl/ plus run-info.json |
| Lifecycle  | Exists during implementation only                  |
| Committed  | Never (in .gitignore)                              |

## Copy Step (Remote Only)

The workflow copies `.worker-impl/` to `.impl/` before implementation:

```bash
cp -r .worker-impl .impl
```

This ensures the implementation environment is identical whether local or remote.

## Why Two Folders?

1. **Visibility:** `.worker-impl/` appears in PR diffs, showing the plan to reviewers
2. **Consistency:** `.impl/` provides a consistent working directory for all implementation code
3. **Cleanup:** `.worker-impl/` deletion signals completion; `.impl/` remains for user review

## Related Topics

- [PR Finalization Paths](pr-finalization-paths.md) - Local vs remote PR submission
- [Issue Reference Flow](issue-reference-flow.md) - How issue.json is created and consumed
- [Planning Workflow](../planning/workflow.md) - Full plan lifecycle
