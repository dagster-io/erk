# Documentation Plan: Eliminate tmux from codespace remote execution

## Context

PR #8327 removed the tmux session management layer from erk's codespace remote execution. This was a clean architectural simplification - commands now run directly over SSH without tmux, reducing complexity while maintaining the bootstrap sequence (git pull, uv sync, venv activation). The change touched 8 files, removing 183 lines of code and documentation.

The most valuable learnings from this work came not from the feature removal itself (which was straightforward), but from the error patterns and recovery workflows encountered during implementation. A merge conflict blocked plan-save, demonstrating plan mode's dependency on repo state. A missed CLI integration test caused CI failure, revealing the importance of multi-layer test discovery. These cross-cutting concerns apply far beyond this specific PR.

Future agents working on refactoring, feature removal, or plan mode operations will benefit from the tripwires and patterns captured here. The systematic 4-layer removal pattern (caller -> impl -> tests -> docs) demonstrated in this PR is generalizable to any feature elimination work.

## Raw Materials

PR #8327: https://github.com/dagster-io/erk/pull/8327

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 5     |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 2     |
| Potential tripwires (score2-3) | 2     |

## Documentation Items

### HIGH Priority

#### 1. Merge conflict detection before plan mode

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Source:** [Plan], [Impl]

**Draft Content:**

```markdown
## Merge Conflicts Block Plan Mode

**Action**: Entering plan mode or running /erk:plan-save when repo has merge conflicts
**Trigger**: Merge conflict markers (<<<<<<< HEAD) in Python source files cause import-time SyntaxError
**Prevention**:
- Run `git diff --check` or `grep -r '<<<<<<' src/` before entering plan mode
- Check `erk --version` succeeds before attempting plan operations
- Plan mode is read-only and cannot fix repo errors - must exit to resolve conflicts
**Severity**: HIGH (blocks all erk commands, not just plan-save)

Plan mode prevents file edits, creating an implicit dependency on repo state. When the repo has syntax errors or merge conflicts, all erk CLI commands become blocked because Python fails at import time. The error message ("SyntaxError: invalid syntax") is cryptic and doesn't indicate the root cause is merge conflict markers.
```

---

#### 2. Multi-layer test discovery during refactoring

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl], [PR #8327]

**Draft Content:**

```markdown
## Multi-Layer Test Discovery

**Action**: Removing or refactoring core module functions
**Trigger**: Modified/deleted core functions may be tested in BOTH unit tests AND CLI integration tests
**Prevention**:
- Grep entire tests/ directory for imports: `grep -r "from erk.core.module_name" tests/`
- Check tests/unit/core/ (obvious location) AND tests/unit/cli/commands/ (easy to miss)
- Run full test suite, not just module-specific tests
**Severity**: MEDIUM-HIGH (causes CI failures, requires rework)

When modifying core modules in src/erk/core/, remember that CLI commands import these modules and have their own integration tests in tests/unit/cli/commands/. PR #8327 demonstrated this: the obvious unit tests in tests/unit/core/codespace/ were updated, but a CLI test in tests/unit/cli/commands/codespace/run/objective/test_plan_cmd.py was initially missed, causing CI failure.
```

---

### MEDIUM Priority

#### 3. Systematic feature removal pattern

**Location:** `docs/learned/refactoring/feature-removal-pattern.md`
**Action:** CREATE
**Source:** [Plan], [Impl], [PR #8327]

**Draft Content:**

```markdown
---
read-when:
  - removing a feature or function
  - deleting functionality from the codebase
  - refactoring that eliminates code paths
---

# Systematic Feature Removal Checklist

When removing features, functions, or architectural patterns, follow this 4-layer checklist to ensure complete removal.

## The 4-Layer Removal Pattern

### 1. Find Caller Sites

Identify all code that imports or uses the target:

- Grep for function/class name: `grep -r "function_name" src/`
- Check for import statements: `grep -r "from erk.module import function_name" src/`
- Look for string references (CLI commands, config values)

### 2. Remove Implementation

Delete the core functionality:

- Remove functions, classes, and helper methods
- Remove associated imports (check for unused imports after removal)
- Consider using Write tool for large block removals rather than multiple Edits

### 3. Remove Tests

Find and delete ALL related tests:

- Unit tests: `tests/unit/core/` (obvious)
- CLI integration tests: `tests/unit/cli/commands/` (easy to miss)
- Grep entire tests/ directory: `grep -r "from erk.module import" tests/`
- Don't just delete - verify remaining tests still pass

### 4. Remove Documentation

Clean up docs that reference the removed feature:

- Check docs/learned/ for related documentation
- Update or delete tripwires that warned about the feature
- Update index files and tripwire counts
- Check for references in CLAUDE.md or AGENTS.md

## Example: PR #8327 Tmux Removal

1. **Caller**: Found plan_cmd.py imports build_codespace_tmux_command
2. **Implementation**: Removed _sanitize_tmux_session_name() and build_codespace_tmux_command() from codespace_run.py
3. **Tests**: Deleted 7 tmux tests from test_codespace_run.py, updated 1 CLI test in test_plan_cmd.py
4. **Documentation**: Deleted codespace-tmux-persistence.md, removed 2 tripwires from integrations/tripwires.md

## Cross-Layer Dependencies

Be aware that core modules are often tested at multiple layers:
- Direct unit tests in tests/unit/core/
- Indirect integration tests via CLI commands in tests/unit/cli/commands/

See testing/tripwires.md for the "Multi-Layer Test Discovery" tripwire.
```

---

#### 4. Plan mode read-only constraints

**Location:** `docs/learned/planning/plan-mode-constraints.md`
**Action:** CREATE
**Source:** [Plan]

**Draft Content:**

```markdown
---
read-when:
  - plan-save fails unexpectedly
  - plan mode cannot execute erk commands
  - repo errors block planning operations
---

# Plan Mode Read-Only Constraints

Plan mode prevents file edits, which creates an implicit dependency on the repository being in a working state.

## The Constraint

When in plan mode, Claude cannot modify files. This means:

- Syntax errors cannot be fixed from within plan mode
- Merge conflicts cannot be resolved from within plan mode
- Broken imports cannot be repaired from within plan mode

## Consequences

If the repo has issues that break Python imports, ALL erk CLI commands become blocked. This affects:

- `/erk:plan-save` - cannot create the plan issue
- `erk exec` commands - fail at import time
- Any command that imports from erk modules

## Workarounds

### Before Entering Plan Mode

Pre-validate repo state:
- Check git status for merge conflicts: `git diff --check`
- Verify erk runs: `erk --version`
- Grep for conflict markers: `grep -r '<<<<<<' src/`

### When Blocked During Plan Mode

1. **Exit plan mode** to fix the issue (you can re-enter afterward)
2. **Resolve conflicts or syntax errors** using normal file editing
3. **Re-enter plan mode** and retry the operation

### Alternative: Save Partial Plan

If you've done significant planning work:
1. Copy the plan content manually (from conversation)
2. Exit plan mode and fix repo issues
3. Re-enter plan mode and recreate from saved content

## Related

- See planning/tripwires.md for merge conflict detection tripwire
- See plan-agent.md for plan mode workflow details
```

---

#### 5. Exec reference docs CI requirement

**Location:** `docs/learned/ci/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Exec Reference Doc Sync

**Action**: Modifying erk exec scripts without regenerating reference docs
**Trigger**: Changes to exec scripts cause .claude/skills/erk-exec/reference.md to become stale
**Prevention**: Run `erk-dev gen-exec-reference-docs` after modifying exec script behavior
**Severity**: LOW (CI catches it automatically, but wastes iteration time)

The reference.md file is generated from exec scripts, not hand-written. The CI validates it's up to date. If you modify exec scripts, regenerate before pushing to avoid a CI round-trip.
```

---

## Contradiction Resolutions

**None identified.** The existing `codespace-tmux-persistence.md` documented the current state (tmux usage), and the PR correctly removed this documentation when eliminating the feature. This was proper evolution, not contradiction.

## Stale Documentation Cleanup

The stale documentation cleanup was already completed as part of PR #8327:

### 1. Codespace tmux persistence documentation

**Location:** `docs/learned/integrations/codespace-tmux-persistence.md`
**Action:** Already deleted by PR #8327
**Cleanup Instructions:** File was correctly removed when the feature was eliminated. No additional action needed.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Import-time SyntaxError from merge conflicts

**What happened:** Plan-save failed with cryptic "SyntaxError: invalid syntax" error. The actual cause was merge conflict markers (<<<<<<< HEAD) left in plan_body_screen.py from a parallel merge.

**Root cause:** Git merge/rebase left conflict markers in Python source. When erk CLI tried to import modules, Python failed at import time with a syntax error that didn't indicate the real problem.

**Prevention:** Check git status and grep for conflict markers before running erk commands. Plan mode's read-only nature means it cannot fix these issues - must exit plan mode to resolve.

**Recommendation:** TRIPWIRE (see Tripwire Candidates section)

### 2. Missed CLI integration test

**What happened:** After updating the obvious unit tests in tests/unit/core/codespace/, CI still failed. A CLI integration test in tests/unit/cli/commands/codespace/run/objective/test_plan_cmd.py also asserted tmux behavior.

**Root cause:** Test discovery was incomplete - only checked the obvious unit test location without grepping for all imports of the modified module.

**Prevention:** Always grep entire tests/ directory for imports of modified modules before marking refactoring complete.

**Recommendation:** TRIPWIRE (see Tripwire Candidates section)

### 3. Exec reference doc staleness

**What happened:** CI failed on exec reference check after implementation was otherwise complete.

**Root cause:** The .claude/skills/erk-exec/reference.md file is generated from code, and modifying exec scripts without regenerating causes staleness.

**Prevention:** Run `erk-dev gen-exec-reference-docs` after modifying exec scripts.

**Recommendation:** ADD_TO_DOC (documented in CI tripwires above)

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Merge conflicts block plan mode

**Score:** 6/10 (Non-obvious +2, Destructive potential +2, Silent failure +2)
**Trigger:** Before entering plan mode or running /erk:plan-save
**Warning:** Merge conflict markers (<<<<<<< HEAD) in Python source files cause import-time SyntaxError that blocks ALL erk commands. Check `git diff --check` and verify `erk --version` succeeds before plan operations.
**Target doc:** `docs/learned/planning/tripwires.md`

This tripwire is essential because the failure mode is non-obvious. A merge conflict in any Python file - not just files related to your current work - can block plan-save. The error message ("SyntaxError: invalid syntax") gives no indication that the root cause is conflict markers elsewhere in the codebase. Additionally, plan mode's read-only constraint means you cannot fix the issue without exiting plan mode entirely.

### 2. Multi-layer test file discovery

**Score:** 5/10 (Non-obvious +2, Cross-cutting +2, Repeated pattern +1)
**Trigger:** Before marking refactoring complete on core modules
**Warning:** Modified/deleted core functions may be tested in BOTH unit tests (tests/unit/core/) AND CLI integration tests (tests/unit/cli/commands/). Grep entire tests/ directory for imports.
**Target doc:** `docs/learned/testing/tripwires.md`

This tripwire applies broadly to any refactoring of core modules. The natural instinct is to check only the unit tests that obviously correspond to the module being modified. But CLI commands import core modules and have their own integration tests. Missing these causes CI failures that could have been caught with a comprehensive grep. The pattern occurred in PR #8327 and is likely to recur whenever core modules are modified.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Import-time SyntaxError pattern (subsumed)

**Score:** 3/10 (Non-obvious +2, Destructive +2, but duplicate of #1)
**Notes:** This error pattern is a symptom of the merge conflict issue. Rather than creating a separate tripwire, it's better documented as part of the merge conflict tripwire's explanation. The key insight (SyntaxError can mean conflict markers) is captured in the primary tripwire.

### 2. Exec reference doc staleness

**Score:** 2/10 (External tool quirk +1, Silent until CI +1)
**Notes:** Severity is LOW because CI catches it automatically. The cost is one wasted CI iteration, not blocked functionality. Added to CI tripwires as a note rather than a standalone tripwire.
