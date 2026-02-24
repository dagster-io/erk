# Documentation Plan: Simplify plan-implement workflow with consolidated setup-impl command

## Context

PR #7998 consolidates the complex 15-step plan-implement workflow into a simplified 10-step workflow by extracting inline bash logic into 4 new testable `erk exec` commands. The centerpiece is `setup-impl`, which replaces Steps 0-2d with a single unified entry point handling all input paths (issue/file/branch auto-detect). This reduces plan-implement.md from 360 lines to approximately 180 lines and fixes a bug where `upload-impl-session` incorrectly passed `--issue-number` instead of `--plan-id`.

Documentation matters for this implementation because it represents a major workflow simplification that future agents will encounter when implementing plans. Without documentation, agents may attempt to follow outdated patterns from training data or struggle to understand the priority ordering when auto-detecting plan sources. The PR also surfaced several important patterns: LBYL boundary enforcement (distinguishing ternary value assignment from control flow), test isolation via cwd injection, and dead exception handler detection. These patterns apply broadly across erk development.

The sessions revealed recurring friction around LBYL boundaries - all PR violations involved ternary expressions or exception handling. This is the hardest dignified-python rule to internalize, making it a prime candidate for tripwire documentation. Additionally, the test isolation failure in session-eb335a89 demonstrates a critical pattern where functions deep in call chains need testability hooks (optional cwd parameters) that aren't obvious until tests fail.

## Raw Materials

Materials were gathered from PR #7998 implementation sessions and code diff analysis.

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 22    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 3     |
| Potential tripwires (score2-3) | 4     |

## Documentation Items

### HIGH Priority

#### 1. Test isolation via cwd injection

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] session-eb335a89

**Draft Content:**

```markdown
## Test Isolation with cwd Injection

### Tripwire: cwd Hardcoding Breaks Test Isolation

**Trigger:** Before implementing CLI commands or helper functions that will be tested

**Warning:** NEVER hardcode `Path.cwd()` in implementation code. When tests use `ErkContext.for_test(cwd=tmp_path)`, all filesystem operations in the call chain must respect the injected cwd.

**Pattern:** Add optional `cwd: Path | None = None` parameter to functions that reference the current directory:

- Default to `Path.cwd()` for production
- Accept injection for tests
- Thread the parameter through all layers of the call chain

**Why this matters:** Test failures manifest as exit code mismatches (e.g., `AssertionError: assert 1 == 0`) with no obvious connection to cwd. Debugging requires tracing through call chains to find hardcoded `Path.cwd()` calls.

See `src/erk/cli/commands/exec/scripts/impl_init.py` for the `_validate_impl_folder()` implementation showing this pattern.
```

---

#### 2. Ternary expression boundaries

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE
**Source:** [PR #7998] 5 review violations

**Draft Content:**

```markdown
## Ternary Expression Boundaries

### Tripwire: Ternaries for Value Assignment Only

**Trigger:** Before using ternary expressions in CLI commands or core logic

**Warning:** Ternaries acceptable for simple value assignment (`x = value if condition else None`) but control flow decisions MUST use explicit if/else blocks. The dignified-code-simplifier bot will flag control-flow ternaries as non-LBYL.

**Acceptable:**
- `plan_id = int(ref.id) if ref.id else None` (value assignment)

**Not acceptable:**
- `return early if condition else do_complex_thing()` (control flow)
- Ternary inside function call that changes behavior

**Conversion pattern:** When converting ternary to if/else:
1. Use three-line if/else block
2. Place type annotation on truthy branch: `plan_id: int | None = int(plan_ref.plan_id)`
3. Watch indentation carefully (12 spaces for nested conditional body inside 8-space if block)

See `src/erk/cli/commands/exec/scripts/setup_impl.py` for conversion examples.
```

---

#### 3. SystemExit as process boundary

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE
**Source:** [PR #7998] threads at setup_impl.py:278, upload_impl_session.py:86

**Draft Content:**

```markdown
## SystemExit as Process Boundary

### Tripwire: Never Catch SystemExit for Control Flow

**Trigger:** Before catching SystemExit in exception handlers

**Warning:** Never catch SystemExit for control flow. Valid only at CLI entry points for exit code translation. SystemExit is for process boundaries, not internal logic.

**Check:** Before adding `except SystemExit`, verify the called function can actually raise SystemExit(0). Often these handlers are dead code catching impossible exceptions.

**Valid use case:** CLI entry point translating exit codes
**Invalid use case:** Catching SystemExit inside a command to detect "success" vs "failure"

If a function raises SystemExit on error, consider whether a non-raising variant exists or should be created.
```

---

#### 4. Documentation drift: plan-implement.md

**Location:** `docs/learned/cli/plan-implement.md`
**Action:** UPDATE
**Source:** [Impl] existing-docs-check

**Draft Content:**

```markdown
## Plan-Implement Workflow (Consolidated)

Update this document to reflect the simplified workflow:

### Key Change
Steps 0-2d (8 sub-steps spanning decision trees) are now consolidated into a single `setup-impl` command.

### Before
- 15 steps with complex decision trees
- 360 lines of instructions
- Inline bash for branch detection, cleanup, validation

### After
- ~10 steps with unified entry point
- ~180 lines of instructions
- All logic delegated to testable exec commands

### Update Required
Replace the legacy multi-step setup sections with:

```bash
# Step 1: Set Up Implementation
erk exec setup-impl [--issue N | --file PATH]
```

The command handles:
- Issue-based plans: `--issue N`
- File-based plans: `--file PATH`
- Auto-detection: No args (detects from branch name or existing .impl/)

Synchronize with `.claude/commands/erk/plan-implement.md` which already uses the new pattern.
```

---

#### 5. setup-impl consolidated command

**Location:** `docs/learned/planning/setup-impl-command.md`
**Action:** CREATE
**Source:** [Impl] diff-analysis, session-417b05cc-part1

**Draft Content:**

```markdown
---
read-when: implementing plans, running setup-impl, setting up .impl/ folder
tripwires: 0
---

# setup-impl Command Reference

## Purpose

Consolidated setup command replacing Steps 0-2d of the plan-implement workflow. Single entry point handling all input paths.

## Usage

```bash
erk exec setup-impl                    # Auto-detect from branch/existing .impl/
erk exec setup-impl --issue 123        # Setup from GitHub issue
erk exec setup-impl --file plan.md     # Setup from local file
```

## Decision Tree

Priority ordering for plan source detection:

1. **Explicit args**: `--issue` or `--file` if provided
2. **Existing .impl/**: If `.impl/plan.md` already exists, use it
3. **Branch detection**: Extract issue number from branch name (P{N}- or {N}- patterns)
4. **PR lookup fallback**: Query GitHub API for PR associated with current branch
5. **plan-save fallback**: Prompt user to save current plan first

## Integration Points

The command composes:
- `cleanup-impl-context` - Removes `.erk/impl-context/` staging artifacts
- `impl-init` - Validates `.impl/` structure and extracts metadata
- `setup-impl-from-issue` - Fetches plan from GitHub issue

## JSON Output Protocol

Returns standardized output for agent consumption:
- `{"success": true, "plan_id": N, "has_plan_tracking": bool, ...}`
- `{"success": false, "error": "message"}`

See `src/erk/cli/commands/exec/scripts/setup_impl.py` for implementation.
```

---

### MEDIUM Priority

#### 6. upload-impl-session command

**Location:** `docs/learned/cli/erk-exec-commands.md`
**Action:** UPDATE (add to Session Operations section)
**Source:** [Impl] diff-analysis, PR comments

**Draft Content:**

```markdown
## Session Operations

### upload-impl-session

Uploads session data for async learn workflow.

**Usage:** `erk exec upload-impl-session --session-id <id>`

**Purpose:** Enables asynchronous documentation extraction from implementation sessions. Called at end of plan-implement workflow.

**Important:** Uses `--plan-id` parameter (NOT `--issue-number`). The original workflow had a bug passing the wrong parameter name.

**Behavior:**
- Reads plan reference from `.impl/ref.json`
- Captures session info
- Uploads to git branch for learn processing
- Always exits 0 (non-critical operation)

See `src/erk/cli/commands/exec/scripts/upload_impl_session.py` for implementation.
```

---

#### 7. LBYL ternary conversion pattern

**Location:** `docs/learned/architecture/lbyl-patterns.md`
**Action:** CREATE
**Source:** [Impl] session-417b05cc-part2

**Draft Content:**

```markdown
---
read-when: converting ternary expressions, fixing LBYL violations, addressing bot review comments
tripwires: 0
---

# LBYL Ternary Conversion Patterns

## When to Convert

Convert ternary expressions to explicit if/else blocks when:
- The ternary controls program flow (not just value assignment)
- The expression is complex or nested
- Bot review flags the ternary as non-LBYL

## Conversion Pattern

Before:
```python
plan_id = int(plan_ref.plan_id) if plan_ref.plan_id else None
```

After:
```python
if plan_ref.plan_id:
    plan_id: int | None = int(plan_ref.plan_id)
else:
    plan_id = None
```

## Indentation Guidelines

- Standard block: 4 spaces per level
- Nested conditional body: Count carefully
- Example: Body of if inside an 8-space if block = 12 spaces

## Type Annotations

Place type annotation on the truthy branch assignment to help type checkers understand the conditional typing.
```

---

#### 8. Dead exception handler detection

**Location:** `docs/learned/architecture/exception-analysis.md`
**Action:** CREATE
**Source:** [Impl] session-417b05cc-part2

**Draft Content:**

```markdown
---
read-when: converting try/except to LBYL, cleaning up exception handlers, analyzing control flow
tripwires: 0
---

# Dead Exception Handler Detection

## The Problem

Try/except blocks may catch exceptions that can never be raised in the current code path. Converting these to LBYL adds unnecessary scaffolding.

## Detection Protocol

Before converting try/except to LBYL:

1. **Trace the exception source**: Which function in the try block raises this exception?
2. **Check all code paths**: Can that function actually raise the exception given current inputs?
3. **Verify conditions**: Does the exception require a condition that's already been checked?

## Example

```python
# This handler may be dead code
try:
    result = require_claude_installation(ctx)
except SystemExit:
    handle_missing_claude()
```

If `ctx.obj` is always initialized before this point, and `require_claude_installation` only raises SystemExit when `ctx.obj` is None, the handler is unreachable.

## Resolution

- If exception cannot occur: **Delete the handler entirely**
- If exception can occur: Convert to LBYL guard
- If uncertain: Add comment explaining why handler exists

See `src/erk/cli/commands/exec/scripts/setup_impl.py` for examples where handlers were removed.
```

---

#### 9. Python subprocess for JSON stdin

**Location:** `docs/learned/integrations/json-stdin-pattern.md`
**Action:** CREATE
**Source:** [Impl] session-417b05cc-part2

**Draft Content:**

```markdown
---
read-when: passing JSON to commands via stdin, shell escaping issues, subprocess invocation
tripwires: 1
---

# Python Subprocess for JSON stdin

## The Problem

Shell escaping breaks JSON strings containing backslashes and quotes:

```bash
# BROKEN - shell mangles escape sequences
echo '[{"key": "value\\with\\backslash"}]' | command
```

Error: `Invalid \escape` during JSON parse

## The Solution

Use Python subprocess to construct and pass JSON in-memory:

```python
import json
import subprocess

data = [{"key": "value\\with\\backslash"}]
result = subprocess.run(
    ['erk', 'exec', 'command'],
    input=json.dumps(data),
    text=True,
    capture_output=True
)
```

## When to Apply

- Passing structured data (JSON, arrays) to commands via stdin
- Any command that parses stdin as JSON
- Batch operations with complex payloads

## Tripwire

**Trigger:** When passing structured data to commands via stdin in bash

**Warning:** Use Python subprocess.run() with json.dumps(), never `echo '[...]' | command`. Shell escaping breaks JSON strings.
```

---

#### 10. False positive review handling

**Location:** `docs/learned/pr-operations/false-positive-handling.md`
**Action:** CREATE
**Source:** [Impl] session-417b05cc-part1, PR comments

**Draft Content:**

```markdown
---
read-when: addressing automated review comments, bot flags code, LBYL violations
tripwires: 1
---

# False Positive Review Handling

## Protocol

When automated reviews suggest changes:

1. **Read the actual code**: Don't trust the review summary; inspect the flagged lines
2. **Search for suggested pattern**: Look for the LBYL guard the review claims is missing
3. **Check surrounding context**: The guard may be on the preceding line
4. **Distinguish outer and inner**: A try/except might have a valid inner exception while outer is dead code

## Response Pattern

If the pattern already exists:
- Reply with evidence pointing to specific line numbers
- Explain why the code is correct as written
- Use batch thread resolution to mark as addressed

If the flag is legitimate:
- Apply the suggested fix
- Verify the fix doesn't break existing behavior
- Commit with descriptive message

## Example False Positive

Bot flags `except Exception: pass` as EAFP, but:
- Line 136 has LBYL guard checking condition
- The try/except on line 139 is defensive for edge cases after primary success
- Correct response: Reply explaining the guard exists

See `src/erk/cli/commands/exec/scripts/upload_impl_session.py` for the defensive exception pattern.
```

---

#### 11. Defensive exception handling pattern

**Location:** `docs/learned/architecture/defensive-exception-handling.md`
**Action:** CREATE
**Source:** [PR #7998] thread #5 (false positive)

**Draft Content:**

```markdown
---
read-when: using try/except with pass, defensive error handling, non-critical operations
tripwires: 0
---

# Defensive Exception Handling Pattern

## When try/except with pass is Valid

Try/except with pass or minimal handling is acceptable when:

1. **Outer LBYL guard exists**: Primary validation happens before the try block
2. **Failure is truly non-critical**: Operation already succeeded; this is cleanup/logging
3. **Context documents why**: Comment explains what failure means and why it's safe

## Pattern

```python
# LBYL guard - primary validation
if not condition_for_success:
    return error_result

# Primary operation
do_critical_thing()

# Non-critical follow-up (defensive)
try:
    do_optional_cleanup()
except Exception:
    pass  # Cleanup failure doesn't affect success
```

## Distinguishing from EAFP

- **EAFP (bad)**: Using try/except as primary control flow
- **Defensive (ok)**: Using try/except for non-critical operations after success

See `src/erk/cli/commands/exec/scripts/upload_impl_session.py` for the pattern in context.
```

---

#### 12. Bot review metadata format

**Location:** `docs/learned/ci/bot-review-format.md`
**Action:** CREATE
**Source:** [PR #7998] comments analysis

**Draft Content:**

```markdown
---
read-when: parsing bot review comments, automating review handling, building review tools
tripwires: 0
---

# Bot Review Metadata Format

## Structure

Bot reviews use structured markdown with embedded metadata:

### Comment Markers
- `<!-- review-type -->` markers identify review category
- YAML metadata in details blocks enable programmatic parsing
- Activity logs show review history

### Metadata Block Example

```markdown
<details>
<summary>Review metadata</summary>

```yaml
review_type: dignified-code-simplifier
severity: medium
rule_id: eafp-violation
```

</details>
```

## Activity Logs

Each review maintains an activity log showing:
- Initial review timestamp
- Fix attempts
- Re-review results
- Resolution status

## Integration Points

This format enables:
- Automated classification of review comments
- Batch processing of similar issues
- Audit trails for review history
```

---

#### 13. Learn branch workflow

**Location:** `docs/learned/workflows/learn-branch-workflow.md`
**Action:** CREATE
**Source:** [PR #7998] discussion comment #6

**Draft Content:**

```markdown
---
read-when: capturing documentation from PR reviews, creating learn branches, post-PR documentation
tripwires: 0
---

# Learn Branch Workflow

## Purpose

Capture documentation opportunities discovered during PR review without blocking the PR itself.

## Workflow

1. **During PR review**: Identify patterns, gotchas, or insights worth documenting
2. **Create learn branch**: `learn/{plan-number}` tracks documentation work
3. **Session upload**: `upload-impl-session` captures session data for async processing
4. **Documentation PR**: Separate PR adds docs without blocking original work

## Branch Naming

- Format: `learn/{plan-number}`
- Example: `learn/7998`

## Integration with Plan System

Learn branches associate with their source plan via:
- Branch name containing plan number
- Session metadata linking to plan issue
- PR references in documentation

## Why Separate Branch

- Keeps original PR focused on code changes
- Documentation can be refined without blocking merge
- Enables async review of documentation quality
```

---

#### 14. Command composition pattern

**Location:** `docs/learned/architecture/command-composition.md`
**Action:** CREATE
**Source:** [Impl] diff-analysis

**Draft Content:**

```markdown
---
read-when: building higher-level commands, composing exec commands, CLI architecture
tripwires: 0
---

# Command Composition Pattern

## Principle

Higher-level commands compose multiple lower-level exec commands rather than duplicating logic.

## Example: setup-impl

The `setup-impl` command composes:
- `cleanup-impl-context` - Pre-cleanup
- `setup-impl-from-issue` - Issue fetching
- `impl-init` - Validation

## Composition Pattern

```python
def higher_level_command(ctx, ...):
    # Compose lower-level commands
    cleanup_result = run_cleanup(ctx)
    if not cleanup_result.success:
        return cleanup_result

    setup_result = run_setup(ctx, ...)
    if not setup_result.success:
        return setup_result

    return run_validation(ctx)
```

## Benefits

- Lower-level commands are independently testable
- Composition logic is explicit and traceable
- Error handling is consistent at each level

## Anti-pattern

Duplicating bash scripts inline in multiple places. Extract to testable Python commands instead.

See `src/erk/cli/commands/exec/scripts/setup_impl.py` for the composition implementation.
```

---

### LOW Priority

#### 15. Batch review thread resolution

**Location:** `docs/learned/pr-operations/pr-address-workflow.md`
**Action:** UPDATE (add batch resolution section)
**Source:** [Impl] sessions

**Draft Content:**

```markdown
## Batch Thread Resolution

### JSON Array Input

The `resolve-review-threads` command accepts JSON array input for batch processing:

```bash
python -c "
import json, subprocess
threads = [{'thread_id': 123, 'comment': 'Fixed'}, ...]
subprocess.run(['erk', 'exec', 'resolve-review-threads'], input=json.dumps(threads), text=True)
"
```

### Batch Grouping Strategy

Organize fixes by complexity:
1. **Local fixes**: Single-line changes, auto-proceed
2. **Single-file**: Multiple changes in one file, auto-proceed
3. **Cross-cutting**: Changes across files, user confirmation
4. **Complex**: Architectural changes, always confirm

### Commit Granularity

Group related fixes into single commit per batch rather than one commit per fix. Reduces git history noise while maintaining logical grouping.
```

---

#### 16. False positive detection protocol

**Location:** `docs/learned/pr-operations/pr-address-workflow.md`
**Action:** UPDATE (add verification subsection)
**Source:** [Impl] session-417b05cc-part1

**Draft Content:**

```markdown
## False Positive Verification

Before applying automated review suggestions:

1. **Read surrounding context**: Not just the flagged line
2. **Verify issue exists**: Search for the pattern the review claims is missing
3. **Check preceding lines**: Guards often appear on the line before the flagged code

This prevents unnecessary code churn from misunderstood patterns.
```

---

#### 17. Batch commit granularity

**Location:** `docs/learned/pr-operations/pr-address-workflow.md`
**Action:** UPDATE (add guideline)
**Source:** [Impl] session-417b05cc-part1

**Draft Content:**

```markdown
## Commit Granularity

Group related PR fixes into single commit per batch:
- One commit for all "local fixes" in a batch
- One commit for cross-file changes in a batch
- Reduces git history noise
- Maintains logical grouping for review
```

---

#### 18. Thread resolution completeness check

**Location:** `docs/learned/pr-operations/pr-address-workflow.md`
**Action:** UPDATE (add verification step)
**Source:** [Impl] session-417b05cc-part1

**Draft Content:**

```markdown
## Completeness Verification

After batch PR comment resolution:

1. Re-run the PR feedback classifier
2. Verify all actionable threads show as resolved
3. Catch missed threads before declaring success

This prevents partial resolution from going unnoticed.
```

---

#### 19. Test coverage reporting format

**Location:** `docs/learned/testing/test-coverage.md`
**Action:** UPDATE
**Source:** [PR #7998] insight #7

**Draft Content:**

```markdown
## Detailed Coverage Reporting

When reporting test coverage for new code:

1. **Count new source files**: List each new `.py` file
2. **Map to test files**: Show corresponding test file for each
3. **Test count breakdown**: Number of tests per file
4. **Coverage areas**: Happy paths, error handling, edge cases
5. **Net change calculation**: Lines added vs removed
```

---

#### 20. Branch detection chain

**Location:** `docs/learned/planning/workflow.md`
**Action:** UPDATE
**Source:** [Impl] diff-analysis

**Draft Content:**

```markdown
## Branch Plan Detection

### Detection Methods

Priority order for detecting plan from current branch:

1. **Branch name pattern**: `extract_leading_issue_number()` finds P{N}- or {N}- prefixes
2. **PR lookup fallback**: Query `github.get_pr_for_branch()` for draft-PR branches
3. **Manual specification**: User provides `--issue` or `--file` explicitly

### Testability Pattern

Core logic extracted to `_detect_plan_from_branch_impl()` pure function:
- No Click or GitHub dependencies
- Returns data structure, not exit codes
- Enables unit testing without mocks

See `src/erk/cli/commands/exec/scripts/detect_plan_from_branch.py` for implementation.
```

---

#### 21. File-based plan setup

**Location:** `docs/learned/planning/workflow.md`
**Action:** UPDATE
**Source:** [Impl] diff-analysis

**Draft Content:**

```markdown
## File-Based Plan Creation

Plans can be created from local markdown files without GitHub issue tracking:

### Title Extraction
- First `# ` heading becomes plan title
- Falls back to filename if no heading

### Branch Name Generation
- Slugify title: lowercase, replace spaces with hyphens
- Limit to 30 characters
- Example: `my-feature-plan-for-the-new`

### Tracking Status
- `has_plan_tracking: false` in output
- No GitHub issue created
- Suitable for local experimentation

See `src/erk/cli/commands/exec/scripts/setup_impl.py` for the `_setup_from_file()` implementation.
```

---

#### 22. Pure function extraction pattern

**Location:** `docs/learned/testing/testability-patterns.md`
**Action:** UPDATE
**Source:** [Impl] diff-analysis

**Draft Content:**

```markdown
## Pure Function Extraction (_impl suffix)

### Pattern

Extract core logic into pure function with `_impl` suffix:

```python
# CLI wrapper with Click/GitHub dependencies
def detect_plan_from_branch(ctx):
    github = require_github(ctx)
    result = _detect_plan_from_branch_impl(branch, github)
    click.echo(json.dumps(result))

# Pure function - no Click, testable
def _detect_plan_from_branch_impl(branch: str, github: GitHubGateway) -> dict:
    # Core logic here
    return {"plan_id": ...}
```

### Benefits

- Pure function can be unit tested with fakes
- CLI wrapper is thin, low risk
- Separation of concerns: IO vs logic

See `src/erk/cli/commands/exec/scripts/detect_plan_from_branch.py` for example.
```

---

## Contradiction Resolutions

No contradictions found. All agent inputs align with each other and existing documentation.

The existing docs checker identified documentation drift (command file vs learned doc using different patterns), but this is an UPDATE_EXISTING situation, not a contradiction. Both describe the same workflow, but the command file has been updated while the learned doc is stale.

## Stale Documentation Cleanup

No stale documentation detected. All referenced files exist in the codebase. However, documentation drift was detected:

### 1. plan-implement.md drift

**Location:** `docs/learned/cli/plan-implement.md`
**Action:** UPDATE_EXISTING
**Issue:** Describes legacy multi-step setup process (Steps 0-2d separate)
**Cleanup Instructions:** Replace sections describing legacy setup with consolidated `setup-impl` command. Synchronize with `.claude/commands/erk/plan-implement.md` which already uses new pattern.

### 2. erk-exec-commands.md missing entries

**Location:** `docs/learned/cli/erk-exec-commands.md`
**Action:** UPDATE_EXISTING
**Issue:** Missing entries for `setup-impl` and `upload-impl-session`
**Cleanup Instructions:** Add both commands to appropriate sections with usage and purpose.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Test Isolation Breaks with Hardcoded Path.cwd()

**What happened:** Tests failed with `AssertionError: assert 1 == 0` when `ErkContext.for_test(cwd=tmp_path)` was used, but implementation code called `Path.cwd()` directly.

**Root cause:** Functions deep in the call chain (`_validate_impl_folder`) used hardcoded `Path.cwd()` without accepting an override parameter. The test-injected cwd wasn't propagated through the call chain.

**Prevention:** Add optional `cwd: Path | None = None` parameter to all functions that reference current directory. Thread the parameter through all layers of the call chain.

**Recommendation:** TRIPWIRE

### 2. Bot Flags Already-Correct LBYL Code

**What happened:** Automated reviewer flagged code as EAFP violation when the LBYL guard existed on the preceding line.

**Root cause:** Pattern matching limitations in automated reviewer - may flag code that checks condition on preceding line.

**Prevention:** Before applying bot fix, read surrounding context (not just flagged line) to verify issue exists.

**Recommendation:** ADD_TO_DOC

### 3. Shell Escaping Breaks JSON stdin

**What happened:** Passing JSON via `echo '[...]' | command` resulted in "Invalid \escape" JSON parse error.

**Root cause:** Bash echo/pipe mangles JSON strings containing backslashes and quotes.

**Prevention:** Use Python subprocess.run() with json.dumps() to pass structured data to commands.

**Recommendation:** TRIPWIRE (potential)

### 4. Indentation Errors After Edit Operations

**What happened:** Replace operation on multi-line if/else block had incorrect indentation for nested statements.

**Root cause:** String replacement doesn't preserve Python's significant whitespace when spans multiple indent levels.

**Prevention:** Count exact spaces in original code; use consistent indentation (4 spaces per level) in replacement.

**Recommendation:** CONTEXT_ONLY

### 5. Dead Exception Handlers Accumulate

**What happened:** Code contained try/except handlers catching exceptions that could never be raised given the current code flow.

**Root cause:** Catching exceptions without verifying they can be raised in practice. Code was copied from patterns where the exception was possible.

**Prevention:** Trace exception raises through call stack before adding try/except. If exception cannot occur, delete handler rather than converting to LBYL.

**Recommendation:** ADD_TO_DOC

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Test isolation via cwd injection

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before implementing CLI commands that will be tested
**Warning:** NEVER hardcode `Path.cwd()` - accept optional `cwd: Path | None = None` parameter that defaults to `Path.cwd()` for production but can be overridden in tests. When tests use `ErkContext.for_test(cwd=tmp_path)`, all filesystem operations in the call chain must respect the injected cwd.
**Target doc:** `docs/learned/testing/tripwires.md`

This is tripwire-worthy because the failure mode is completely non-obvious. Tests fail with generic exit code mismatches that don't indicate the root cause. The pattern is cross-cutting (applies to any CLI command with filesystem operations) and causes silent test failures that may be misdiagnosed as test bugs rather than implementation issues.

### 2. Ternary expression boundaries

**Score:** 5/10 (Non-obvious +2, Cross-cutting +2, Repeated pattern +1)
**Trigger:** Before using ternary expressions in CLI commands or core logic
**Warning:** Ternaries acceptable for simple value assignment (`x = value if condition else None`) but control flow decisions MUST use explicit if/else blocks. Bot will flag control-flow ternaries as non-LBYL.
**Target doc:** `docs/learned/architecture/tripwires.md`

This is tripwire-worthy because the boundary between "value assignment" and "control flow" is subjective and non-obvious. All 5 PR violations in this implementation involved this boundary confusion. The pattern applies across all Python code in erk, making it highly cross-cutting.

### 3. SystemExit as process boundary

**Score:** 5/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +1)
**Trigger:** Before catching SystemExit
**Warning:** Never catch SystemExit for control flow. Valid only at CLI entry points for exit code translation. SystemExit is for process boundaries, not internal logic flow. Check if the called function can actually raise SystemExit(0) - often it's dead code.
**Target doc:** `docs/learned/architecture/tripwires.md`

This is tripwire-worthy because catching SystemExit masks real exit conditions and can hide bugs. Developers may add these handlers defensively without tracing whether the exception can actually occur, leading to dead code that obscures intent.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Python subprocess for JSON stdin

**Score:** 3/10 (Non-obvious +2, External tool +1)
**Notes:** Scored lower because the error is obvious (JSON parse failure), not silent. Pattern is specific to shell integration, not broadly cross-cutting. May warrant tripwire if shell-to-command integration becomes more common.

### 2. False positive verification

**Score:** 3/10 (Non-obvious +2, Repeated pattern +1)
**Notes:** Specific to bot review workflow; doesn't apply to manual development. May elevate to tripwire if bot reviews become more prevalent and false positive rate increases.

### 3. Thread resolution completeness

**Score:** 3/10 (Non-obvious +1, Silent failure +2)
**Notes:** Specific to PR address workflow; missing threads are eventually noticed during re-review. Not destructive, just delays completion.

### 4. Batch commit granularity

**Score:** 2/10 (Repeated pattern +1, Cross-cutting +1)
**Notes:** Style preference, not correctness issue. Low severity - messy git history is annoying but not harmful.

## Implementation Order

Based on dependencies and impact:

### Phase 1: Fix Documentation Drift (HIGH Priority)

1. Update `docs/learned/cli/plan-implement.md` to use consolidated setup-impl
2. Add setup-impl and upload-impl-session to `docs/learned/cli/erk-exec-commands.md`
3. Add 3 HIGH-priority tripwires to `docs/learned/testing/tripwires.md` and `docs/learned/architecture/tripwires.md`

### Phase 2: Core Pattern Documentation (MEDIUM Priority)

4. Create `docs/learned/planning/setup-impl-command.md` (decision tree, integration points)
5. Create `docs/learned/architecture/lbyl-patterns.md` (ternary conversion, indentation)
6. Create `docs/learned/architecture/exception-analysis.md` (dead code detection)
7. Create `docs/learned/pr-operations/false-positive-handling.md` (verification protocol)
8. Create `docs/learned/workflows/learn-branch-workflow.md` (PR documentation workflow)

### Phase 3: Supporting Documentation (MEDIUM Priority)

9. Create `docs/learned/integrations/json-stdin-pattern.md` (subprocess pattern)
10. Create `docs/learned/architecture/defensive-exception-handling.md` (valid try/except pattern)
11. Create `docs/learned/ci/bot-review-format.md` (metadata structure)
12. Create `docs/learned/architecture/command-composition.md` (orchestration pattern)

### Phase 4: Workflow Updates (LOW Priority)

13. Update `docs/learned/pr-operations/pr-address-workflow.md` (batch resolution, completeness check)
14. Update `docs/learned/planning/workflow.md` (branch detection, file-based plans)
15. Update `docs/learned/testing/test-coverage.md` (reporting format)
16. Update `docs/learned/testing/testability-patterns.md` (pure function extraction)
