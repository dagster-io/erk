# Plan: Update erk-exec and skill documentation for .erk/impl-context/ unification

**Part of Objective #8365, Node 3.2**

## Context

Objective #8365 eliminates the `.impl/` folder in favor of `.erk/impl-context/<branch>/`. Phase 1 updated code paths, Phase 2 updated CI workflows. Phase 3 updates documentation layers. PR #8369 (node 3.1) already handles command files AND several files originally in 3.2's scope (erk-planning SKILL.md, erk-planning workflow.md, commit-categorizer.md, docs/learned/planning/workflow.md).

Node 3.2's **remaining unique scope** is:
1. erk-exec skill files (SKILL.md + reference.md via source exec scripts)
2. learned-docs SKILL.md

## Files to Modify

### A. Exec script Click help strings (source for reference.md)

These 3 exec scripts have `.impl/` in their Click help strings that appear in reference.md:

1. **`src/erk/cli/commands/exec/scripts/impl_init.py`**
   - Line 133: `"""Initialize implementation by validating .impl/ folder."""`
   - → `"""Initialize implementation by validating impl-context directory."""`

2. **`src/erk/cli/commands/exec/scripts/objective_link_pr.py`**
   - Line 68: `"""Link PR number to objective roadmap nodes from .impl/ metadata."""`
   - → `"""Link PR number to objective roadmap nodes from impl-context metadata."""`

3. **`src/erk/cli/commands/exec/scripts/setup_impl_from_pr.py`**
   - Line 267: `"""Set up .impl/ folder from GitHub PR in current worktree."""`
   - → `"""Set up impl-context directory from GitHub PR in current worktree."""`
   - Line 258: `help="Skip .impl/ folder creation (for local execution without file overhead)"`
   - → `help="Skip impl-context directory creation (for local execution without file overhead)"`

**Note:** Only update the Click-visible help strings (function docstrings used by Click and `help=` kwargs). Leave module-level docstrings for node 4.1 scope.

### B. Regenerate reference.md

After updating exec script help strings:
```bash
erk-dev gen-exec-reference-docs
```

This auto-regenerates `.claude/skills/erk-exec/reference.md`.

### C. erk-exec SKILL.md

**`.claude/skills/erk-exec/SKILL.md`** line 47:
- `| setup-impl-from-pr | Set up .impl/ from PR |`
- → `| setup-impl-from-pr | Set up impl-context from PR |`

### D. learned-docs SKILL.md

**`.claude/skills/learned-docs/SKILL.md`** line 59:
- `"working with .impl/ folders"`
- → `"working with .erk/impl-context/ directories"`

## Implementation Steps

1. Edit the 3 exec script Click help strings (A above)
2. Edit erk-exec SKILL.md (C above)
3. Edit learned-docs SKILL.md (D above)
4. Regenerate reference.md (B above)
5. Run CI checks to verify

## Dependencies

- **PR #8369 (node 3.1)**: Open but non-conflicting — touches different files. Can proceed independently.
- **Node 4.1** (source docstrings): Will handle the module-level docstrings in these same exec scripts later.

## Verification

1. `erk-dev gen-exec-reference-docs --check` — confirms reference.md is in sync
2. `make fast-ci` — runs full lint/format/type/test suite
3. Grep `.impl/` across modified files to confirm no remaining old references
4. Confirm reference.md no longer contains `.impl/` in the 3 updated command entries
