# Plan: Improve Code-Level Documentation for Backpressure Gates

## Context

Objective #7823 is closed with all code landed. The remaining gap (node 3.3) is documenting agent-facing vs human-facing path distinction. Rather than adding a learned doc, improve the code-level documentation directly and have `agent-backpressure-gates.md` point readers to the code.

## Files to Modify

1. **`packages/erk-shared/src/erk_shared/naming.py`** — Improve module-level and function docstrings for `validate_plan_title`, `validate_worktree_name`, `generate_filename_from_title`, `sanitize_worktree_name`
2. **`packages/erk-shared/src/erk_shared/gateway/github/metadata/tripwire_candidates.py`** — Improve docstrings for `validate_candidates_data`, `validate_candidates_json`
3. **`docs/learned/architecture/agent-backpressure-gates.md`** — Replace the single example with a brief "see the code" pointer listing the four gate functions and their locations

## Changes

### naming.py

- Add a section comment grouping the gate functions (e.g., `# --- Agent Backpressure Gates ---`)
- Enhance `validate_plan_title` docstring: list the agent-facing callers (`plan_save_to_issue`, `plan_save`, `issue_title_to_filename`) and note the human-facing bypass (`generate_filename_from_title`)
- Enhance `validate_worktree_name` docstring: note it's an internal consistency check (validates system-generated names, not direct agent input), list callers via `prepare_plan_for_worktree` and `setup_impl_from_issue`, note human bypass is `sanitize_worktree_name`
- Enhance `generate_filename_from_title` and `sanitize_worktree_name` docstrings: note these are human-facing silent transformation counterparts to the gates above

### tripwire_candidates.py

- Enhance `validate_candidates_data` docstring: list agent-facing callers (`normalize_tripwire_candidates`, `store_tripwire_candidates`), note the pre-gate recovery layer (`normalize_candidates_data`)

### agent-backpressure-gates.md

- Replace the "Example: Objective Slug Validation" section with a "Gate Inventory" section that simply lists the four gate functions with file paths and a one-line description, directing readers to the code docstrings for details
- Update `last_audited` in frontmatter

## Verification

1. Run `make fast-ci` to ensure no formatting/lint issues
