---
title: Backend Naming Conventions
read_when:
  - "referencing the plan backend by name in code or documentation"
  - "confused about draft_pr vs planned_pr vs github-draft-pr naming"
  - "adding user-facing output that mentions the backend"
---

# Backend Naming Conventions

The plan backend has inconsistent naming across different contexts. This glossary documents the official name for each context.

## Naming Map

| Context                    | Name               | Example                                            |
| -------------------------- | ------------------ | -------------------------------------------------- |
| Provider name (API)        | `github-draft-pr`  | `plan_backend.get_provider_name()` returns this    |
| Python class               | `PlannedPRBackend` | `from erk_shared.plan_store.planned_pr import ...` |
| Config value (legacy)      | `planned_pr`       | Formerly `ERK_PLAN_BACKEND=planned_pr`             |
| User-facing documentation  | "planned PR"       | "Plans are stored as planned pull requests"        |
| Issue-based (legacy) API   | `github`           | `get_provider_name()` for GitHubPlanStore          |
| Issue-based (legacy) class | `GitHubPlanStore`  | Legacy issue-based storage                         |

## Key Distinctions

- **`planned_pr`** (underscore) was the env var / config value
- **`PlannedPRBackend`** (no underscore, PascalCase) is the class name
- **`github-draft-pr`** (hyphenated) is the provider name string returned by the API
- **`draft_pr`** appears in some older references but is not an official name

## Which Name to Use

| When Writing...        | Use                                                                          |
| ---------------------- | ---------------------------------------------------------------------------- |
| Backend detection code | `get_provider_name() == "github-draft-pr"`                                   |
| Import statements      | `PlannedPRBackend`                                                           |
| User-facing CLI output | "plan" (backend-agnostic, see [output-styling.md](../cli/output-styling.md)) |
| Documentation          | "planned PR" or "PlannedPRBackend"                                           |

## Related Documentation

- [Planned PR Backend](planned-pr-backend.md) — Full backend documentation
- [Plan ID Semantics](plan-id-semantics.md) — How plan_id differs by backend
- [Output Styling](../cli/output-styling.md) — User-facing terminology guidelines
