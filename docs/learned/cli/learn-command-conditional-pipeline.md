---
title: Learn Command Conditional Pipeline
last_audited: "2026-02-16 04:53 PT"
audit_result: clean
read_when:
  - "modifying the erk learn command flow"
  - "adding session discovery logic to learn workflow"
  - "understanding how preprocessed materials bypass session discovery"
tripwires:
  - action: "adding session discovery code before checking for preprocessed materials"
    warning: "Check gist URL first to avoid misleading output. The learn command checks _get_learn_materials_gist_url() BEFORE session discovery. If a gist exists, all session discovery is skipped."
---

# Learn Command Conditional Pipeline

The `erk learn` command checks for preprocessed materials **before** session discovery, avoiding expensive and misleading session lookup when materials already exist.

## Pattern: Check Preprocessed Before Discovery

<!-- Source: src/erk/cli/commands/learn/learn_cmd.py, learn_cmd -->

The `learn_cmd()` function in `src/erk/cli/commands/learn/learn_cmd.py` checks for a gist URL before session discovery:

1. `_get_learn_materials_gist_url()` → checks plan header for gist_url
2. If gist exists:
   - Display "Preprocessed learn materials available" message
   - Skip ALL session discovery
   - Launch with gist_url directly via `_confirm_and_launch()`
3. If no gist:
   - Existing flow: discover sessions, display, confirm, launch

## Why This Order Matters

Without the early gist check, the command would:

1. Run session discovery (which may find zero readable sessions)
2. Display confusing "no sessions found" output
3. Then somehow still need to use the gist

The early `_get_learn_materials_gist_url()` call short-circuits the entire discovery pipeline, providing a cleaner user experience.

## Implementation Details

### \_get_learn_materials_gist_url()

<!-- Source: src/erk/cli/commands/learn/learn_cmd.py, _get_learn_materials_gist_url -->

See `_get_learn_materials_gist_url()` in `src/erk/cli/commands/learn/learn_cmd.py`. Checks the plan's GitHub issue body for a `learn_materials_gist_url` field in the `plan-header` metadata block. Returns `str | None`.

Uses LBYL pattern: checks `isinstance(issue, IssueNotFound)` before accessing issue body.

### \_confirm_and_launch()

<!-- Source: src/erk/cli/commands/learn/learn_cmd.py, _confirm_and_launch -->

See `_confirm_and_launch()` in `src/erk/cli/commands/learn/learn_cmd.py`. Shared by both the gist-exists path and the session-discovery path. Handles:

- Auto-launch with `-i` (interactive) flag
- User confirmation prompt
- Interactive Claude execution via `prompt_executor.execute_interactive()`

## Related Documentation

- [Learn Pipeline Workflow](../planning/learn-pipeline-workflow.md) — Full pipeline architecture
- [Async Learn Local Preprocessing](../planning/async-learn-local-preprocessing.md) — How preprocessing creates the gist
