# Plan: Consolidated Feb 26 Learn Session Documentation

> **Consolidates:** #8274, #8282, #8284, #8285, #8286, #8292, #8293, #8294, #8298, #8303, #8307, #8311, #8313, #8315, #8317, #8318

## Context

16 erk-learn documentation plans were generated from Feb 26 implementation sessions. Deep investigation of all 16 against the current codebase reveals:

- **All code changes are already merged** - these are documentation-only plans
- **Significant overlap** between plans (e.g., #8317/#8307 both cover modal keystrokes, #8274/#8298 both cover impl directories)
- **Some items already documented** - investigation found existing coverage that plan authors didn't discover
- **Stale documentation found** - 3 docs reference deleted code/functions

This consolidated plan focuses on high-value documentation gaps, stale doc fixes, and tripwire additions.

## Source Plans

| #    | Title                                                             | Items Merged       |
| ---- | ----------------------------------------------------------------- | ------------------ |
| 8274 | Branch-scoped impl directories under .erk/impl-context/           | 3 items            |
| 8282 | --sync flag to auto-submit PR checkouts to Graphite               | 3 items            |
| 8284 | Delete get_branch_issue() dead code and simplify to plan-ref.json | 1 item             |
| 8285 | Stack Filter for erk dash TUI                                     | 2 items            |
| 8286 | Inline objective filter to erk dash TUI (`o` key)                 | 2 items            |
| 8292 | Persistent status bar messages for workflow operations            | 3 items            |
| 8293 | Clean up documentation for deleted legacy branch-naming code      | 0 items (complete) |
| 8294 | .ensure() to NonIdealState classes and IssueComments wrapper      | 2 items            |
| 8298 | resolve_impl_dir and branch-scoped impl directory patterns        | 3 items            |
| 8303 | Flat format elimination and metadata block adoption               | 3 items            |
| 8307 | Fix modal keystroke leakage to underlying view                    | 2 items            |
| 8311 | Dispatch to Queue keyboard shortcut 's' to 'd'                    | 1 item             |
| 8313 | Replace fix-conflicts modal with lightweight toast pattern        | 2 items            |
| 8315 | Force parameter to stage_files gateway for gitignored paths       | 1 item             |
| 8317 | Fix modal dismiss keys (Esc/q/Space) not working                  | 1 item             |
| 8318 | Update CHANGELOG.md Unreleased section with 100 commits           | 2 items            |

## Investigation Findings

### Already Complete (No Action Needed)

- **#8293**: All cleanup work merged in PR #8289. Stale docs deleted, cross-references updated.
- **#8284**: Most documentation items already updated. PR #8269 merged. Only field naming conventions remain (LOW priority, dropped).
- **#8294**: discriminated-union-error-handling.md (460+ lines) already comprehensively documents .ensure(), NonIdealStateMixin, EnsurableResult, IssueComments wrapper. Only minor tripwire additions needed.
- **#8311**: Keyboard shortcut change fully implemented. Only metadata block documentation overlap with #8303.

### Stale Documentation (Must Fix)

1. **`docs/learned/planning/impl-context.md` lines 66-68**: References non-existent `src/erk/cli/commands/submit.py`
2. **`docs/learned/planning/planned-pr-lifecycle.md` lines 13-17**: References `extract_metadata_prefix()` which never existed
3. **`docs/learned/planning/metadata-block-fallback.md` lines 44-54**: Shows only 3 eras, missing v4 (pure metadata blocks)
4. **`docs/learned/tui/modal-widget-embedding.md` line 58**: References non-existent `objective_plans_screen.py`

### Overlap Analysis

- **#8317 + #8307**: Both describe modal keystroke consumption patterns. Merged into single tripwire + pattern documentation.
- **#8274 + #8298**: Both cover branch-scoped impl directories and FakeGit testing. Merged into single impl directory doc update.
- **#8285 + #8286**: Nearly identical filter toggle architecture. Documented as unified filter pipeline pattern.
- **#8313 + #8311 + #8303**: All touch PR body format/metadata blocks. Merged into metadata block format doc update.

## Implementation Steps

### Step 1: Fix Stale Documentation References _(from #8274, #8298, #8303, #8286)_

**File:** `docs/learned/planning/impl-context.md`

- Lines 66-68: Replace reference to `src/erk/cli/commands/submit.py` with correct path `packages/erk-shared/src/erk_shared/impl_folder.py`
- Verification: All file paths in doc exist in codebase

**File:** `docs/learned/planning/planned-pr-lifecycle.md`

- Lines 13-17: Remove tripwire reference to `extract_metadata_prefix()` (never existed). Replace with `find_metadata_block()` from `packages/erk-shared/src/erk_shared/gateway/github/metadata/core.py`
- Verification: Referenced function names exist in codebase

**File:** `docs/learned/planning/metadata-block-fallback.md`

- Lines 44-54: Add v4 era documenting pure metadata blocks (self-delimiting via HTML comment markers `<!-- erk:metadata-block:{key} -->`). Reference `find_metadata_block()` and `render_metadata_block()` from `metadata/core.py`
- Verification: Era descriptions match actual code behavior

**File:** `docs/learned/tui/modal-widget-embedding.md`

- Line 58: Remove or update reference to non-existent `objective_plans_screen.py`. The objective filter is now inline in `src/erk/tui/app.py` (action_toggle_objective_filter at line 573)
- Verification: All referenced files exist

### Step 2: Create TUI Filter Pipeline Documentation _(from #8285, #8286)_

**File:** `docs/learned/tui/filter-pipeline.md` (NEW)

**Content outline:**

1. Architecture overview: `_apply_filter_and_sort()` in `src/erk/tui/app.py:335-345` applies filters in sequence: objective filter -> stack filter -> text filter -> sort
2. Filter toggle pattern: State variables (`_objective_filter_issue`, `_stack_filter_branches`), toggle action, clear method
3. Progressive escape chain: `action_exit_app()` at line 415-421 clears filters in order: objective -> stack -> text -> quit
4. Key bindings: `o` for objective filter (line 107), `s` for stack filter (line 119)
5. Gateway query delegation: `get_branch_stack()` in `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/abc.py:154-166`

**Source:** Investigation of #8285 and #8286 found identical architectural patterns for both filters.

**Verification:** Function names and line numbers match actual code in `src/erk/tui/app.py`

### Step 3: Create TUI Multi-Operation Tracking Documentation _(from #8292)_

**File:** `docs/learned/tui/multi-operation-tracking.md` (NEW)

**Content outline:**

1. Problem: Multiple concurrent background operations need status tracking
2. Architecture: `_OperationState` frozen dataclass (`src/erk/tui/widgets/status_bar.py:10-15`), `_operations` dict registry (line 51-52)
3. Lifecycle: `start_operation(op_id, label)` -> `update_operation(op_id, progress)` -> `finish_operation(op_id)` (status_bar.py lines 83-120)
4. Op ID convention: `f"{operation}-{resource_type}-{resource_id}"` e.g., `"close-plan-123"`
5. Streaming subprocess integration: `_run_streaming_operation()` at `app.py:663-739` with ANSI stripping and line collection
6. `_OperationResult(success, output_lines, return_code)` at `app.py:46-87`
7. Toast + status bar pattern: Status bar for ongoing operations, `self.notify()` for completion

**Source:** Investigation of #8292 found complete implementation with consistent patterns across all workflow commands.

**Verification:** All referenced functions exist at stated locations

### Step 4: Add TUI Tripwires _(from #8285, #8286, #8292, #8307, #8317, #8282)_

**File:** `docs/learned/tui/tripwires.md` (UPDATE - currently 44 tripwires)

**Add tripwires for:**

From modal keystroke patterns (#8307, #8317):

- Modal `on_key()` must call `event.prevent_default()` and `event.stop()` BEFORE any logic. Without this, keystrokes leak to underlying view.
- Dismiss-on-unhandled pattern: `if event.key not in (bound_keys): self.dismiss()`. Inverted condition is a common bug.

From filter pipeline (#8285, #8286):

- New filter implementations must follow the existing toggle pattern (state variable + action + clear method + escape chain entry)
- `action_exit_app()` escape chain must clear new filters in the correct order (most specific first)
- Key binding repurposing requires checking for conflicts in all screens that may be active

From multi-operation tracking (#8292):

- Always call `finish_operation()` in both success and error paths (use try/finally pattern)
- Op IDs must be unique across concurrent operations
- Merge stdout/stderr when calling subprocess to capture all output for progress display
- ANSI escape sequences must be stripped before displaying in status bar

From TUI-CLI coordination (#8282):

- When adding CLI flags that affect behavior, check if TUI command palette generates commands that need the flag. `src/erk/tui/commands/registry.py` generates shell commands that must include new flags.

**Verification:** Run `wc -l docs/learned/tui/tripwires.md` to confirm tripwire count increased

### Step 5: Update Planning Tripwires for Metadata Blocks _(from #8303, #8313, #8311)_

**File:** `docs/learned/planning/tripwires.md` (UPDATE)

**Add/update tripwires for:**

- `find_metadata_block()` is the current extraction function (not `extract_metadata_prefix()` or `extract_plan_header_block()` which are deleted)
- Metadata blocks are self-delimiting via HTML comment markers `<!-- erk:metadata-block:{key} -->` - never use `PLAN_CONTENT_SEPARATOR` for new code (backward compat only)
- PR body metadata position changed from top to bottom - don't assume metadata is at top of body

**Verification:** Tripwire references match actual function names in `packages/erk-shared/src/erk_shared/gateway/github/metadata/core.py`

### Step 6: Update Architecture Tripwires _(from #8294, #8315)_

**File:** `docs/learned/architecture/tripwires.md` (UPDATE)

**Add tripwires for:**

- Protocol property descriptors conflict with frozen dataclass fields. Use `NonIdealStateMixin` (at `packages/erk-shared/src/erk_shared/non_ideal_state.py:40-49`) when the NonIdealState class uses dataclass fields.
- When adding parameters to gateway ABC methods, all 5 implementations must be updated (ABC, Real, Fake, DryRun, Printing). Fake may accept but not track new parameters when assertion is not needed.
- `@handle_non_ideal_exit` decorator must come AFTER `@click.command()` / `@click.pass_context` decorators (outermost position in decorator stack).

**Source:** Investigation of #8294 and #8315

**Verification:** Referenced classes and functions exist at stated paths

### Step 7: Create Subagent Output Handling Documentation _(from #8318)_

**File:** `docs/learned/planning/subagent-output-handling.md` (NEW)

**Content outline:**

1. Problem: Task agents with large JSON output produce persisted-output markers instead of inline content
2. Pattern: Use Python JSON parsing (not Read/cat/grep) to handle persisted output files
3. When this occurs: Commit categorizer agent, any Task agent producing >N lines of structured output
4. Anti-pattern: Using Read tool or grep on persisted-output file paths

**Source:** #8318 session encountered this pattern 3-4 times during changelog workflow

**Verification:** Document describes behavior observable when running `/local:changelog-update`

### Step 8: Update CLI Activation Scripts Documentation _(from #8282)_

**File:** `docs/learned/cli/activation-scripts.md` (UPDATE)

**Add section on:**

- Dynamic post-CD commands: `post_cd_commands` parameter allows injecting commands that run after `cd` in activation scripts
- Example: `--sync` flag causes `gt submit --no-interactive` to run after checkout CD
- Implementation: `src/erk/cli/commands/pr/checkout_cmd.py` line ~145 uses `should_submit_to_graphite` guard

**File:** `docs/learned/cli/shell-activation-pattern.md` (UPDATE)

**Add section on:**

- Post-CD command execution: Commands appended after the `cd` line in activation scripts
- Used by: PR checkout with `--sync` flag

**Source:** Investigation of #8282 found these docs exist but don't cover post-CD commands

**Verification:** Referenced implementation matches code in `checkout_cmd.py`

### Step 9: Add Testing Tripwires _(from #8274, #8298, #8282)_

**File:** `docs/learned/testing/tripwires.md` (UPDATE)

**Add tripwires for:**

- FakeGit `current_branches` must be configured when testing branch-scoped impl directory code. Without this, `resolve_impl_dir()` gets wrong branch and resolves wrong directory.
- When adding new parameters to gateway methods, truth-table testing pattern covers all boolean combinations. Bot reviewers enforce this coverage.
- Branch name sanitization (`_sanitize_branch_for_dirname()` at `packages/erk-shared/src/erk_shared/impl_folder.py:34-36`) replaces "/" with "--". Test data must account for this.

**Source:** Investigation of #8274, #8298 found FakeGit configuration is a critical testing gap; #8282 found parameter truth-table testing pattern

**Verification:** Referenced functions exist at stated paths

### Step 10: Run `erk docs sync` to Regenerate Index Files

After all documentation changes, run `erk docs sync` to:

- Regenerate `docs/learned/index.md` with new document entries
- Update tripwires-index.md with new tripwire counts
- Validate frontmatter on new documents

**Verification:** `erk docs sync` exits 0 and index files are updated

## Attribution

Items by source:

- **#8274, #8298**: Steps 1, 9 (impl directory docs, testing tripwires)
- **#8282**: Steps 4, 8, 9 (TUI-CLI coordination, activation scripts, testing tripwires)
- **#8284**: Step 1 (stale reference fixes only; main work already complete)
- **#8285, #8286**: Steps 2, 4 (filter pipeline, TUI tripwires)
- **#8292**: Steps 3, 4 (multi-operation tracking, TUI tripwires)
- **#8293**: No steps (all work already complete in PR #8289)
- **#8294**: Step 6 (architecture tripwires)
- **#8303**: Steps 1, 5 (metadata block format, planning tripwires)
- **#8307, #8317**: Step 4 (modal keystroke tripwires)
- **#8311**: Step 5 (metadata position tripwire)
- **#8313**: Steps 4, 5 (background operations pattern, metadata lifecycle)
- **#8315**: Step 6 (gateway parameter tripwires)
- **#8318**: Step 7 (subagent output handling)

## Dropped Items

These items from source plans were dropped as already adequately documented or too low value:

- **#8284 field naming conventions**: LOW priority, single-function scope
- **#8293 all items**: Cleanup already complete in PR #8289
- **#8294 .ensure() migration guide**: discriminated-union-error-handling.md already covers this comprehensively
- **#8307/#8313 PR review iteration workflow**: Process documentation, not code pattern
- **#8313 timeline forensics technique**: Investigative technique, too specialized
- **#8318 plan-mode-restrictions.md**: Narrow scope, hook behavior already documented in hooks/
- **#8311 keyboard shortcut change doc**: Simple change, self-documenting in code
- **Various "automated review bot" items**: Process docs about bot behavior, not code patterns

## Verification

After implementation:

1. All stale file references fixed (grep for deleted file names returns 0 results in docs/)
2. New docs have valid frontmatter (erk docs sync succeeds)
3. Tripwire counts increased in each updated tripwires.md file
4. All referenced function names and file paths exist in current codebase
