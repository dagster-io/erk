# Documentation Plan: Eliminate --objective-issue flag from plan-save commands

## Context

This plan consolidates documentation from a significant architectural refactoring that replaced explicit CLI flag passing with automatic session marker-based context propagation. The implementation eliminated the `--objective-issue` flag from both `plan_save` and `plan_save_to_issue` commands, making both backends read objective associations from session markers as the sole linking mechanism.

The refactoring touched 16 files across backend scripts, hooks, commands, tests, and documentation. The key insight is that session-scoped context (like which objective a plan belongs to) should flow implicitly through marker files rather than requiring explicit CLI flags that users can forget or mistype. This makes the user experience cleaner and the implementation more consistent.

A future agent implementing objective-linked plans would benefit from understanding: (1) how marker-based linking works end-to-end, (2) the JSON output contracts that enable verification, and (3) the tripwires discovered during this implementation that prevent common errors.

## Raw Materials

PR #8117: Eliminate --objective-issue flag from plan-save commands

## Summary

| Metric | Count |
|--------|-------|
| Documentation items | 15 |
| Contradictions to resolve | 0 |
| Tripwire candidates (score>=4) | 3 |
| Potential tripwires (score 2-3) | 4 |

## Documentation Items

### HIGH Priority

#### 1. Edit tool read-first requirement

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Edit Tool Read-First Requirement

**Trigger:** editing a file without reading it first

Before editing any file (tests, implementation, docs), always use the Read tool to load the file content first. The Edit tool enforces this requirement and will fail with "File has not been read yet" error.

**Critical:** Even if you've read the file earlier in the conversation, you must re-read before editing. The Edit tool tracks reads per-operation, not per-conversation.

**Anti-pattern:** Attempting parallel edits to multiple files without reading them first
**Correct:** Read all files (can be parallel), then edit all files (can be parallel)

**Severity:** HIGH - causes immediate edit failures and wastes context
```

---

#### 2. Marker-based objective linking pattern

**Location:** `docs/learned/planning/marker-based-objective-linking.md` (NEW)
**Action:** CREATE
**Source:** [PR #8117]

**Draft Content:**

```markdown
---
read-when:
  - linking a plan to an objective
  - working with objective-context markers
  - understanding plan-save objective linking
---

# Marker-Based Objective Linking

## Overview

Plans are linked to objectives automatically via session markers, not CLI flags. When `/erk:objective-plan` creates a plan, it writes an `objective-context` marker. When `/erk:plan-save` runs, it reads this marker and links the plan to the objective.

## Workflow

1. `/erk:objective-plan <issue>` creates the `objective-context.marker` file in session scratch
2. User creates plan in plan mode
3. User exits plan mode (hook fires but doesn't need to know about objective)
4. `/erk:plan-save` reads marker automatically via `read_objective_context_marker(session_id, repo_root)`
5. JSON output includes `objective_issue` field for verification

## Key Files

- `src/erk/cli/commands/exec/scripts/plan_save.py` - grep for `read_objective_context_marker`
- `src/erk/cli/commands/exec/scripts/plan_save_to_issue.py` - grep for `read_objective_context_marker`
- `packages/erk-shared/src/erk_shared/scratch/session_markers.py` - marker reading function

## Verification

Check JSON output from plan-save for `objective_issue` field. If non-null, linking succeeded. Commands can also verify via `erk exec get-plan-metadata <issue> objective_issue`.

## Historical Note

Prior to PR #8117, objective linking required passing `--objective-issue=N` flag explicitly. This was error-prone and inconsistent between backends. Marker-based linking is now the sole mechanism.
```

---

#### 3. CLI reference regeneration after CLI changes

**Location:** `docs/learned/cli/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## CLI Reference Regeneration

**Trigger:** after adding/removing CLI flags, commands, or options

After modifying any Click command definitions (adding flags, removing options, changing help text), run:

```bash
erk-dev gen-exec-reference-docs
```

This regenerates `.claude/skills/erk-exec/reference.md` from CLI definitions. Without this step, CI will fail with "Exec reference check failed".

**Why:** The reference doc is auto-generated and CI verifies it matches CLI definitions. Manual edits will be overwritten.

**Severity:** MEDIUM - causes CI failures that block PR merging
```

---

#### 4. JSON output contract documentation

**Location:** `docs/learned/planning/json-output-contracts.md` (NEW)
**Action:** CREATE
**Source:** [PR #8117]

**Draft Content:**

```markdown
---
read-when:
  - parsing JSON output from exec scripts
  - verifying plan-save results
  - understanding exec script output schemas
---

# JSON Output Contracts for Exec Scripts

## Overview

Exec scripts that produce JSON output must maintain stable schemas. Commands and workflows depend on these contracts for verification and chaining.

## plan_save and plan_save_to_issue

Both save backends include these fields in JSON output:

| Field | Type | Description |
|-------|------|-------------|
| `plan_number` | int | The created issue/PR number |
| `objective_issue` | int or null | Linked objective issue number, null if not linked |
| `url` | string | GitHub URL for the created plan |

**Source files:**
- `src/erk/cli/commands/exec/scripts/plan_save.py` - grep for `"objective_issue"`
- `src/erk/cli/commands/exec/scripts/plan_save_to_issue.py` - grep for `"objective_issue"`

## Verification Pattern

Commands like `/erk:plan-save` verify linking by checking JSON output:

```
if json_output.get("objective_issue") is not None:
    # Linking succeeded
```

This replaces the old pattern of checking if `--objective-issue` flag was passed.
```

---

#### 5. Skill invocation in --print mode requires Task tool

**Location:** `docs/learned/claude-code/skill-invocation-patterns.md` (NEW)
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - invoking skills from commands with structured output
  - using context fork in --print mode
  - skill isolation requirements
---

# Skill Invocation Patterns

## Skill Forking in --print Mode

The `context: fork` skill metadata does NOT guarantee subagent isolation when Claude Code is in `--print` mode.

**Anti-pattern:**
```markdown
Invoke the pr-feedback-classifier skill...
```

**Correct pattern:**
```markdown
Use the Task tool to invoke pr-feedback-classifier with a separate agent context...
```

## When to Use Task Tool

Use explicit Task tool invocation (not skill invocation) when:
1. The command uses `--print` mode for structured output
2. The skill produces JSON that must be parsed
3. True isolation is required for classification/analysis

**Trigger:** invoking a skill with `context: fork` from a command that uses --print mode

**Severity:** HIGH - produces malformed output or context pollution
```

---

#### 6. Backend parity achievement

**Location:** `docs/learned/planning/backend-parity.md` (NEW)
**Action:** CREATE
**Source:** [PR #8117]

**Draft Content:**

```markdown
---
read-when:
  - understanding plan_save vs plan_save_to_issue
  - objective linking consistency
---

# Backend Parity: plan_save and plan_save_to_issue

## Overview

Both save backends now have identical objective linking behavior after PR #8117.

## Parity Achievement

| Behavior | plan_save | plan_save_to_issue |
|----------|-----------|-------------------|
| Marker reading | `read_objective_context_marker()` | `read_objective_context_marker()` |
| JSON output | includes `objective_issue` | includes `objective_issue` |
| CLI flags | no `--objective-issue` | no `--objective-issue` |
| Echo confirmation | "Linked to objective #N from session context" | "Linked to objective #N from session context" |

## Historical Note

Prior to PR #8117:
- `plan_save_to_issue` read marker as fallback, flag as primary
- `plan_save` only used flag, no marker reading

Now both read marker as the sole mechanism.

## Source Files

Compare implementations:
- `src/erk/cli/commands/exec/scripts/plan_save.py`
- `src/erk/cli/commands/exec/scripts/plan_save_to_issue.py`

Both use `read_objective_context_marker(session_id, repo_root)` pattern.
```

---

### MEDIUM Priority

#### 7. Auto-generated file patterns

**Location:** `docs/learned/architecture/auto-generated-files.md` (NEW)
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - editing reference documentation
  - CI failures about reference checks
  - understanding which files are auto-generated
---

# Auto-Generated Files

## Overview

Some files in the repository are auto-generated from code or other sources. Never edit these manually - regenerate them instead.

## Known Auto-Generated Files

| File | Generated From | Regeneration Command |
|------|---------------|---------------------|
| `.claude/skills/erk-exec/reference.md` | CLI definitions | `erk-dev gen-exec-reference-docs` |

## Detection

Auto-generated files often contain headers like:
```
<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
```

## CI Enforcement

CI checks verify auto-generated files match their sources. Failures like "Exec reference check failed" indicate regeneration is needed.
```

---

#### 8. Batch review thread resolution pattern

**Location:** `docs/learned/pr-operations/batch-operations.md` (NEW or UPDATE)
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - resolving multiple PR review threads
  - batch operations on PR comments
---

# Batch Operations for PR Reviews

## Batch Thread Resolution

When resolving multiple review threads, use JSON stdin instead of individual calls:

```bash
echo '[{"thread_id": "123", "comment": "Fixed"}, {"thread_id": "456", "comment": "Addressed"}]' | erk exec resolve-review-threads
```

**Anti-pattern:** Multiple individual calls to resolve one thread at a time
**Correct:** Build JSON array, pipe to single batch command

## Why Batch

- Fewer API calls to GitHub
- Atomic resolution (all or none)
- Easier to track in commit messages

See `erk exec resolve-review-threads --help` for full schema.
```

---

#### 9. Session marker reading lifecycle

**Location:** `docs/learned/planning/workflow-markers.md`
**Action:** UPDATE
**Source:** [PR #8117]

**Draft Content:**

```markdown
## Marker Lifecycle: objective-context

The `objective-context.marker` is the sole mechanism for linking plans to objectives.

### Lifecycle Stages

1. **Creation**: `/erk:objective-plan` calls `erk exec marker create --marker-type objective-context --objective-issue N`
2. **Persistence**: Marker stored in `.erk/scratch/sessions/{session_id}/objective-context.marker`
3. **Reading**: `plan_save` and `plan_save_to_issue` call `read_objective_context_marker(session_id, repo_root)`
4. **Consumption**: Marker data used to link plan, reported in JSON output

### Key Change

Marker reading is now PRIMARY, not fallback. Both save backends read the marker as the sole mechanism for objective linking.

See `packages/erk-shared/src/erk_shared/scratch/session_markers.py` for function definition.
```

---

#### 10. Automated PR review architecture

**Location:** `docs/learned/architecture/automated-pr-review.md` (NEW)
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - understanding PR review workflow
  - working with automated review bots
  - zero-manual-review PRs
---

# Automated PR Review Architecture

## Overview

PRs in erk can receive zero human review comments and still get comprehensive feedback via automated review bots.

## Review Bots

| Bot | Purpose |
|-----|---------|
| dignified-python-review | Enforces Python coding standards |
| test-coverage-review | Checks for missing test coverage |
| tripwires-review | Validates tripwire documentation |
| dignified-code-simplifier-review | Suggests code simplifications |
| audit-pr-docs | Detects documentation drift |

## Addressing Reviews

Use `/erk:pr-address` to programmatically address bot feedback:
1. Classifies feedback into LOCAL vs SKIP vs DISCUSSION
2. Applies LOCAL fixes in batches
3. Resolves threads via `erk exec resolve-review-threads`

## Example

PR #8117 had zero human review comments - all feedback from bots, all addressed programmatically.
```

---

#### 11. Documentation drift detection

**Location:** `docs/learned/documentation/automated-drift-detection.md` (NEW)
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - documentation accuracy concerns
  - audit-pr-docs failures
  - cross-referencing code and docs
---

# Automated Documentation Drift Detection

## Overview

The `audit-pr-docs` bot detects when documentation claims don't match implementation behavior.

## Example Detection

PR #8117: Bot caught semantic drift in `docs/learned/hooks/erk.md`:
- **Old claim:** "objective-context marker triggers hook to suggest correct save command"
- **Actual behavior:** "marker is read by plan-save to link the plan to its parent objective"

## How It Works

The bot:
1. Reads PR diff to understand code changes
2. Scans affected documentation files
3. Cross-references claims against implementation
4. Flags semantic inconsistencies

## Addressing Detections

Fix the documentation to match actual behavior, then resolve the review thread.
```

---

#### 12. Workaround for existing .impl/ folders

**Location:** `docs/learned/planning/impl-context.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Workaround: When setup-impl Fails

If `erk exec setup-impl` fails but `.impl/` folder already exists, bypass setup-impl and read plan files directly:

1. Read `.impl/plan-ref.json` for plan metadata
2. Read `.impl/plan.md` for plan content
3. Continue implementation without setup-impl

**When this happens:**
- Implementing from a branch where .impl/ was already created
- setup-impl has bugs (e.g., function signature mismatches)

**Key files:**
- `.impl/plan-ref.json` - contains issue number, type, branch info
- `.impl/plan.md` - contains the plan text

This workaround is preferable to being blocked by infrastructure bugs.
```

---

#### 13. Session continuation with Analysis summary

**Location:** `docs/learned/sessions/continuation-patterns.md` (NEW or UPDATE)
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - continuing sessions after context exhaustion
  - handing off between session parts
---

# Session Continuation Patterns

## Analysis Summary Pattern

When continuing a session after context exhaustion, provide a detailed Analysis summary:

```
Analysis: [Session continued from part N]
- Completed tasks: 1-6
- Current task: #7 (documentation updates)
- Files modified: [list]
- Remaining work: [description]
```

This allows the agent to resume efficiently without re-reading full history.

## Why It Works

- Agent gets context without cost of re-reading files
- Task numbering provides clear roadmap
- Scope summary prevents drift

## Example

Part 3 of PR #8117 implementation used this pattern effectively to continue from task #7 documentation updates.
```

---

#### 14. Command simplification pattern

**Location:** `docs/learned/cli/command-simplification.md` (NEW)
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - deciding between CLI flags and markers
  - simplifying command interfaces
  - session-scoped context design
---

# Command Simplification: Flags vs Markers

## Decision Framework

Use markers instead of CLI flags when:
1. Context is session-scoped (created and consumed within same session)
2. Flag would need to be passed between multiple commands
3. Users might forget to pass the flag

Use CLI flags when:
1. Context is user-specified each time
2. Value varies between invocations in same session
3. Explicit control is important

## Example: Objective Linking

**Old:** `erk exec plan-save --objective-issue=3679`
**New:** `erk exec plan-save` (reads marker automatically)

The objective issue doesn't change within a session, so marker-based implicit context is appropriate.

## Migration Pattern

1. Create marker writer (usually in setup/init command)
2. Add marker reader in consuming command
3. Keep flag as deprecated fallback (optional)
4. Remove flag after migration period
```

---

#### 15. Hook simplification pattern

**Location:** `docs/learned/hooks/hook-evolution.md` (NEW or UPDATE)
**Action:** CREATE
**Source:** [PR #8117]

**Draft Content:**

```markdown
---
read-when:
  - designing hook interfaces
  - reducing hook complexity
  - encapsulation in hooks
---

# Hook Simplification: Encapsulation via Markers

## Principle

Hooks shouldn't need to know about all domain concepts. If a hook would need a parameter only to pass it elsewhere, that's a sign the consuming command should read context directly.

## Example: exit-plan-mode-hook

**Before PR #8117:**
```python
def build_blocking_message(session_id: str, objective_id: int | None) -> str:
    if objective_id:
        return f"/erk:plan-save --objective-issue={objective_id}"
    return "/erk:plan-save"
```

**After PR #8117:**
```python
def build_blocking_message(session_id: str) -> str:
    return "/erk:plan-save"  # plan-save reads marker internally
```

## Why This Is Better

- Hook doesn't need to know about objectives
- All objective logic encapsulated in plan-save
- Simpler function signature
- Single save command (no conditional)

See `src/erk/cli/commands/exec/scripts/exit_plan_mode_hook.py`.
```

---

### LOW Priority

#### 16. Prettier failures on .erk/impl-context/

**Location:** `docs/learned/ci/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Prettier and Transient Files

**Trigger:** CI prettier failures on `.erk/impl-context/` files

The `.erk/impl-context/` directory contains generated plan files that are transient (cleaned up after implementation). Prettier formatting issues here may be false positives.

**Resolution:** Run `make prettier` to format. Don't manually edit these files.

**Severity:** LOW - these files are temporary and don't affect functionality
```

---

#### 17. libcst-refactor for mechanical edits

**Location:** `docs/learned/refactoring/mechanical-refactoring.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Example: Function Signature Refactoring

When removing a parameter from a function that has many call sites, use the libcst-refactor agent:

**Case:** Removing `objective_id` parameter from `build_blocking_message()` in exit_plan_mode_hook.py

**Scope:** 26 call sites in test_exit_plan_mode_hook.py

**Approach:** Rather than manually editing each call, delegate to libcst-refactor agent which can mechanically update all call sites consistently.

This maintains code consistency and prevents typos in repetitive edits.
```

---

## Stale Documentation Cleanup

No stale documentation identified. All existing documentation references were verified by the existing-docs-checker:
- plan-save.md references exist
- workflow-markers.md references exist
- hooks/erk.md references exist

The PR updated these docs in-place rather than leaving phantom references.

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Edit Tool Read-First Failure

**What happened:** Agent attempted to edit 5 documentation files in parallel without reading them first. All 5 edits failed with "File has not been read yet" error.

**Root cause:** The Edit tool enforces a safety check requiring files to be Read before editing, even if read earlier in conversation. This is a per-operation check, not per-conversation.

**Prevention:** Always call Read tool before Edit tool. When editing multiple files, read all first (can be parallel), then edit all (can be parallel).

**Recommendation:** TRIPWIRE - Score 6/10, highest priority

### 2. CLI Reference Out of Sync

**What happened:** CI failed with "Exec reference check failed" after removing `--objective-issue` flag from CLI commands.

**Root cause:** `.claude/skills/erk-exec/reference.md` is auto-generated from CLI definitions. After CLI changes, must regenerate.

**Prevention:** After any CLI flag/command changes, run `erk-dev gen-exec-reference-docs` before CI.

**Recommendation:** TRIPWIRE - Score 5/10

### 3. setup-impl Signature Mismatch

**What happened:** `erk exec setup-impl` failed with TypeError because `_handle_issue_setup` passes `branch_slug` parameter that `setup_impl_from_issue()` doesn't accept.

**Root cause:** Function signature changed but call site not updated.

**Prevention:** This should be caught by type checker. Agent worked around by reading .impl/ directly.

**Recommendation:** SHOULD_BE_CODE - fix the bug, not document it

### 4. Skill Isolation in --print Mode

**What happened:** Discovered that `context: fork` skill metadata doesn't create true subagent isolation when Claude Code is in `--print` mode.

**Root cause:** The fork metadata is advisory, not enforced in all modes.

**Prevention:** Use explicit Task tool invocation for skills that need guaranteed isolation.

**Recommendation:** TRIPWIRE - Score 4/10

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Edit Tool Read-First Requirement

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Repeated pattern +1, Silent failure +1)
**Trigger:** Before editing any file in tests or implementation
**Warning:** Always use Read tool before Edit tool. The Edit tool enforces this requirement and will fail with "File has not been read yet" error. Even if you've read the file earlier in conversation, re-read before editing.
**Target doc:** `docs/learned/testing/tripwires.md`

This tripwire is critically important because the error message doesn't clearly indicate the solution (that you must re-read even if the file was read earlier). Agents who encounter this error waste context on failed edit attempts. The pattern occurred multiple times in the implementation session (5 parallel edits all failed), demonstrating it's a recurring trap.

### 2. CLI Reference Regeneration

**Score:** 5/10 (Cross-cutting +2, Destructive potential +2, External tool quirk +1)
**Trigger:** After modifying any Click command options or arguments
**Warning:** Run `erk-dev gen-exec-reference-docs` to regenerate .claude/skills/erk-exec/reference.md before CI. The reference doc is auto-generated from CLI definitions.
**Target doc:** `docs/learned/cli/tripwires.md`

This tripwire prevents CI failures that block PR merging. The reference.md file looks editable but must not be manually modified. Any CLI changes require regeneration, which is easy to forget after a large refactoring session.

### 3. Skill Invocation in --print Mode

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)
**Trigger:** When invoking skills with `context: fork` from commands that use --print mode
**Warning:** Use Task tool for guaranteed subagent isolation; `context: fork` metadata is insufficient in --print mode.
**Target doc:** `docs/learned/claude-code/tripwires.md` (NEW file needed)

This tripwire addresses a subtle interaction between skill metadata and Claude Code execution modes. The `context: fork` setting appears to promise isolation but doesn't deliver it in all cases. Commands that need to parse skill output as JSON are particularly affected.

---

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. setup-impl failures with existing .impl/

**Score:** 3/10 (Non-obvious +2, Repeated pattern +1)
**Notes:** Workaround documented but root cause (signature bug) should be fixed in code. If the bug persists through multiple releases, consider promoting to tripwire. Currently documented as a pattern in impl-context.md.

### 2. Prettier failures on .erk/impl-context/

**Score:** 2/10 (Non-obvious +1, External tool quirk +1)
**Notes:** LOW severity because files are transient. Documented as note in ci/tripwires.md. Would only promote if agents repeatedly struggle with this.

### 3. Function signature mismatches (branch_slug)

**Score:** 2/10 (Non-obvious +1, Cross-cutting +1)
**Notes:** Should be caught by type checker. This is a code fix, not a documentation item. If type checking discipline improves, this won't recur.

### 4. Batch review thread resolution

**Score:** 2/10 (Non-obvious +1, External tool quirk +1)
**Notes:** Efficiency pattern, not error-prone. Documented as pattern in pr-operations/batch-operations.md. No harm from doing individual calls, just inefficient.

---

## Code Change Items (SHOULD_BE_CODE)

Items that belong in code artifacts rather than docs/learned/:

### 1. next() vs list comprehension [0] access pattern

**Current:** Pattern detected by dignified-code-simplifier bot during PR review
**Should be:** Added to dignified-python skill as a coding standard
**Action:** Update dignified-python skill with: "Always prefer `next((x for x in items if cond), None)` over `[x for x in items if cond][0]` to avoid IndexError"
**Source:** session-6cf2be55.md, pr-comments-analysis.md

### 2. setup-impl signature mismatch bug

**Current:** Documented as error in session analysis
**Should be:** Fixed in code - `src/erk/cli/commands/exec/scripts/setup_impl.py`
**Action:** Fix `_handle_issue_setup` to not pass `branch_slug` to `setup_impl_from_issue()`, or update `setup_impl_from_issue()` to accept it
**Source:** session-1b2fa935-part1.md

---

## Implementation Recommendations

### Immediate Actions (before next session)

1. Add Edit-tool read-first tripwire to `docs/learned/testing/tripwires.md`
2. Add CLI reference regeneration tripwire to `docs/learned/cli/tripwires.md`
3. Create `docs/learned/claude-code/skill-invocation-patterns.md` with --print mode tripwire

### Session 1 Priorities

1. Create `docs/learned/planning/marker-based-objective-linking.md` (consolidate PR knowledge)
2. Create `docs/learned/planning/json-output-contracts.md` (plan_save, plan_save_to_issue)
3. Update `docs/learned/planning/workflow-markers.md` (marker lifecycle, primary not fallback)

### Session 2 Priorities

1. Create `docs/learned/planning/backend-parity.md` (both backends identical)
2. Create `docs/learned/architecture/automated-pr-review.md` (5-bot workflow)
3. Create `docs/learned/architecture/auto-generated-files.md` (reference.md pattern)

### Session 3 Priorities

1. Create `docs/learned/documentation/automated-drift-detection.md` (audit-pr-docs)
2. Create or update `docs/learned/pr-operations/batch-operations.md` (review thread resolution)
3. Create `docs/learned/cli/command-simplification.md` (flags vs markers decision framework)

### Cornerstone Redirects (non-blocking)

1. Add next() vs [0] pattern to dignified-python skill
2. Fix setup-impl signature bug in code
