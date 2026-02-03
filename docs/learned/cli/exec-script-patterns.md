---
title: Exec Script Patterns
category: cli
read_when:
  - "Creating new exec CLI commands"
tripwires:
  - action: "importing from erk_shared.gateway when creating exec commands"
    warning: "Gateway ABCs use submodule paths: `erk_shared.gateway.{service}.{resource}.abc`"
last_audited: "2026-02-03 04:00 PT"
audit_result: edited
---

# Exec Script Patterns

For the full template (result dataclasses, Click entry point, context helpers), see the co-located `AGENTS.md` at `src/erk/cli/commands/exec/scripts/AGENTS.md` which is auto-loaded when editing exec scripts.

## Gateway Import Paths

**IMPORTANT:** Gateway ABCs use submodule paths, not top-level imports.

```python
# Correct
from erk_shared.gateway.github.issues.abc import GitHubIssues

# Incorrect - will raise ImportError
from erk_shared.gateway.github.abc import GitHubIssues
```

## Plan Metadata Functions

Plan header operations live in `erk_shared.gateway.github.metadata.plan_header`:

```python
from erk_shared.gateway.github.metadata.plan_header import (
    extract_plan_header_comment_id,
    extract_plan_from_comment,
)
```

## Error Code Convention

Use lowercase `snake_case` error codes that are:

- **Machine-readable** for programmatic handling
- **Descriptive** (e.g., `missing_erk_plan_label` not `invalid_input`)
- **Actionable** (users understand what went wrong)

## Parameterized URL Construction

Use `get_repo_identifier(ctx)` from `erk_shared.context.helpers` — never hardcode repository names. Always check for `None` before constructing URLs (LBYL).
