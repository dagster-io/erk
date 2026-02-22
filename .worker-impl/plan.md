# Plan: Document Agent-Facing vs Human-Facing Paths for Backpressure Gates

## Context

Objective #7823 node 3.3: "Document which paths are agent-facing (gated) vs human-facing (transformed)".

The existing `docs/learned/architecture/agent-backpressure-gates.md` describes the gate *pattern* abstractly but lacks a concrete cross-domain reference of which code paths use gates vs transformation. This plan creates that reference doc.

**Origin:** PR #7897 was a one-shot plan that failed in CI due to the `issue_number` → `plan_number` rename (#7896). We're reconstructing the plan locally.

## Changes

### 1. Create `docs/learned/architecture/backpressure-path-registry.md`

New doc cataloging every agent-facing (gated) and human-facing (transformed) path across three domains.

**Structure:**
- Frontmatter with `read_when` and `tripwires`
- Brief intro linking back to `agent-backpressure-gates.md` for the conceptual pattern
- Decision rule: agent producer → gate, human producer → transform
- **Domain 1: Worktree Names** — table of call sites for `validate_worktree_name()` vs `sanitize_worktree_name()`
  - Gate sites: `prepare_plan_for_worktree()` in `issue_workflow.py`, `setup_impl_from_issue.py`
  - Transform sites: `create_cmd.py` (wt create), `ensure_worktree_for_branch()`
- **Domain 2: Plan Titles** — table of call sites for `validate_plan_title()` vs `generate_filename_from_title()`
  - Gate sites: `plan_save.py`, `plan_save_to_issue.py`, `issue_title_to_filename.py`
  - Transform sites: `generate_filename_from_title()` called after gate passes or internally by gate
- **Domain 3: Tripwire Candidates** — table of call sites for `validate_candidates_data()` / `normalize_candidates_data()`
  - Gate sites: `store_tripwire_candidates.py` (normalize → validate pipeline)
  - Extract: `extract_tripwire_candidates_from_comments()` (fail-open, no gate)
- **Core Function Reference** — quick-reference table mapping functions to files and roles
- **Adding New Paths** — decision tree guidance

### 2. Update `docs/learned/architecture/agent-backpressure-gates.md`

Add a `## Related Documentation` section at the end linking to the new path registry.

### 3. Run `erk docs sync`

Regenerate index and tripwire files.

## Files Modified

- `docs/learned/architecture/backpressure-path-registry.md` (new)
- `docs/learned/architecture/agent-backpressure-gates.md` (append cross-link)

## Files NOT Changed

- No source code changes (documentation-only task)
- No test changes

## Verification

1. New doc exists with correct frontmatter
2. Cross-link in `agent-backpressure-gates.md`
3. `erk docs sync` succeeds
4. Each table entry verified against source code
