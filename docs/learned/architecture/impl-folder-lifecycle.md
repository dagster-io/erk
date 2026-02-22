---
title: Implementation Folder Lifecycle
read_when:
  - "working with .impl/ or .erk/impl-context/ folders"
  - "understanding remote implementation workflow"
  - "debugging plan visibility in PRs"
last_audited: "2026-02-16 14:20 PT"
audit_result: edited
---

# Implementation Folder Lifecycle

The erk system uses two distinct folders for implementation plans, each with different visibility and lifecycle characteristics.

## .erk/impl-context/ (Committed, Visible)

| Property   | Value                                                |
| ---------- | ---------------------------------------------------- |
| Created by | Remote implementation workflow                       |
| Purpose    | Make plan visible in PR immediately                  |
| Contains   | plan.md, issue.json, progress.md, README.md          |
| Lifecycle  | Created before remote impl, deleted after completion |
| Committed  | Yes (visible in PR diff)                             |

## .impl/ (Local, Never Committed)

| Property   | Value                                                   |
| ---------- | ------------------------------------------------------- |
| Created by | Copy of .erk/impl-context/ OR local `erk implement`     |
| Purpose    | Working directory for implementation                    |
| Contains   | Same structure as .erk/impl-context/ plus run-info.json |
| Lifecycle  | Exists during implementation only                       |
| Committed  | Never (in .gitignore)                                   |

## Copy Step (Remote Only)

The workflow copies `.erk/impl-context/` to `.impl/` before implementation:

```bash
cp -r .erk/impl-context .impl
```

This ensures the implementation environment is identical whether local or remote.

## Why Two Folders?

1. **Visibility:** `.erk/impl-context/` appears in PR diffs, showing the plan to reviewers
2. **Consistency:** `.impl/` provides a consistent working directory for all implementation code
3. **Cleanup:** `.erk/impl-context/` deletion signals completion; `.impl/` remains for user review

## Related Topics

- [PR Finalization Paths](pr-finalization-paths.md) - Local vs remote PR submission
- [Issue Reference Flow](issue-reference-flow.md) - How issue.json is created and consumed
- [Planning Workflow](../planning/workflow.md) - Full plan lifecycle
