# Documentation Plan: Delete `erk pr sync` command

## Context

PR #8245 completed the removal of the vestigial `erk pr sync` command, a 373-line dual-mode CLI command with 1,592 lines of associated tests split across two files. This deletion was the logical conclusion of PR #8238, which made `erk pr checkout` self-sufficient by handling remote synchronization internally. The command had become redundant: its Graphite mode overlapped with `/erk:sync-divergence`, while its git-only fallback mode was no longer needed after checkout improvements.

The planning session demonstrated a valuable discovery pattern: it began as a simple PR review thread resolution but evolved through multiple pivots ("fix this call" to "could we delete this code?" to "can we delete the entire command?") into a comprehensive deletion plan. The agent used parallel Explore agents for multi-dimensional analysis (references and dependencies simultaneously), enabling rapid verification that deletion was safe.

A future agent needs to know: (1) how to detect vestigial features using the three-signal pattern (zero programmatic invocations, docs show alternatives, module docstring admits redundancy), (2) how to execute a complete command deletion including all test files and documentation references, and (3) how planning sessions can legitimately evolve in scope when discovery reveals larger cleanup opportunities.

## Raw Materials

PR #8245

## Summary

| Metric | Count |
|--------|-------|
| Documentation items | 11 |
| Contradictions to resolve | 0 |
| Tripwire candidates (score >= 4) | 3 |
| Potential tripwires (score 2-3) | 3 |

## Stale Documentation Cleanup

The stale documentation was already cleaned up as part of PR #8245:

### 1. pr-sync-workflow.md

**Location:** `docs/learned/erk/pr-sync-workflow.md` (DELETED)
**Action:** DELETE_STALE (completed)
**Phantom References:** `src/erk/cli/commands/pr/sync_cmd.py` (DELETED)
**Cleanup Instructions:** Already removed in PR #8245. The doc described workflow for a command that no longer exists.

## Documentation Items

### HIGH Priority

#### 1. Command deletion comprehensive pattern

**Location:** `docs/learned/cli/command-deletion-patterns.md`
**Action:** CREATE
**Source:** [PR #8245]

**Draft Content:**

```markdown
---
read-when: deleting CLI commands, removing click commands, deprecating commands
---

# Command Deletion Patterns

## When to Delete a Command

Before deleting, verify all three vestigial signals are present (see `docs/learned/planning/vestigial-feature-detection.md`):

1. Zero programmatic invocations (check `.claude/` for skill/command usage)
2. Documentation shows alternatives, not exclusive use cases
3. Module docstring or code comments indicate redundancy

## Complete Deletion Checklist

Execute these steps in order:

### Phase 1: File Deletion

1. Delete command implementation: `src/erk/cli/commands/<group>/<command>_cmd.py`
2. Delete all test files: `tests/commands/<group>/test_<command>*.py`
3. Delete command-specific documentation: `docs/learned/erk/<command>-workflow.md`

### Phase 2: Registration Updates

4. Remove import from `src/erk/cli/commands/<group>/__init__.py`
5. Remove command registration from the same file

### Phase 3: Documentation Updates

6. Update all docs referencing the command (grep for `erk <group> <command>`)
7. Update glossary if command appears in term definitions
8. Update PR footer examples if command appears in checkout scripts
9. Regenerate auto-generated docs: `erk-dev gen-exec-reference-docs`

### Phase 4: Verification

10. Grep for remaining references: `erk <command>[^-_a-z]` (pattern catches command but not related commands)
11. Run full CI: `make fast-ci`
12. Verify command removed: `erk <group> <command>` should show "No such command"

## Common Pitfalls

- **Indirect references**: Bots may find stale refs in unchanged files (broken links, example code blocks, workflow descriptions)
- **Historical references in CHANGELOG**: Keep these - they document what was removed
- **Negative test assertions**: `assert "command" not in result` is proof of removal, not a reference to update

## Example

See PR #8245 which removed `erk pr sync` (373 lines implementation, 1592 lines tests, 7 doc files updated).
```

---

#### 2. Vestigial feature detection checklist

**Location:** `docs/learned/planning/vestigial-feature-detection.md`
**Action:** CREATE
**Source:** [Plan]

**Draft Content:**

```markdown
---
read-when: considering whether to delete code, evaluating if a feature is still needed, planning cleanup or simplification
---

# Vestigial Feature Detection

A feature is likely vestigial when **all three signals** are present:

## Three-Signal Pattern

### Signal 1: Zero Programmatic Invocations

Check `.claude/` directory for skill or command usage:
- Grep for the command name in `.claude/commands/`, `.claude/skills/`
- If zero results, the command has no agentic users

### Signal 2: Documentation Shows Alternatives

Examine docs mentioning the feature:
- If docs say "use X or Y" rather than "use X for this, Y for that", one is likely redundant
- If another command provides the same functionality with simpler UX, the older command may be vestigial

### Signal 3: Module Docstring Admits Redundancy

Check the module's own docstring:
- Phrases like "no longer needed for standard workflow" are strong deletion signals
- Comments suggesting the code "remains for edge cases" warrant investigation of whether those cases still occur

## Signal Interpretation

| Signals Present | Action |
|-----------------|--------|
| All 3 | Safe to propose deletion |
| 2 of 3 | Investigate further before deletion |
| 1 of 3 | Not vestigial - do not delete |

## When NOT to Delete

- Feature has unique functionality not provided elsewhere
- Feature is used programmatically (in `.claude/` or scripts)
- Documentation describes exclusive use cases (not alternatives)
- No replacement workflow exists for affected users
```

---

#### 3. Exec reference regeneration tripwire

**Location:** `docs/learned/cli/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

Add to existing tripwires file:

```markdown
## CLI Command Deletion

**Trigger:** After deleting CLI command files from `src/erk/cli/commands/`

**Do:** Run `erk-dev gen-exec-reference-docs` to update `.claude/skills/erk-exec/reference.md`

**Why:** Auto-generated skill references become stale, causing confusion for Claude agents that rely on this documentation.

**Related:** Also update `__init__.py` imports and run full verification grep.
```

---

#### 4. Incomplete command removal - strengthen grep guidance

**Location:** `docs/learned/cli/incomplete-command-removal.md`
**Action:** UPDATE
**Source:** [PR #8245]

**Draft Content:**

Add section to existing doc:

```markdown
## Indirect Reference Detection

Direct references in updated files are easy to catch. **Indirect references** require broader grep patterns:

### Common Hidden Locations

- Broken links in markdown (docs pointing to deleted files)
- Example code blocks in unrelated docs
- Workflow descriptions mentioning the command
- Glossary entries with command examples

### Verification Pattern

After deletion, run grep with regex to catch the command but not related commands:

```bash
# Example: catching "erk pr sync" but not "erk pr sync-divergence"
grep -r "erk pr sync[^-_a-z]" docs/ .claude/
```

### Lesson from PR #8245

The tripwires bot found 3 stale references in unchanged files that manual review missed. Always run comprehensive grep verification.
```

---

#### 5. Format-after-edit tripwire

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

Add to existing tripwires file:

```markdown
## Markdown Formatting After Edits

**Trigger:** After editing markdown files with tables using the Edit tool

**Do:** Run `prettier --write <file>` to avoid CI failures

**Why:** The Edit tool doesn't auto-format. Structural changes to tables may break prettier validation.

**Example:** Editing a table in `pr-checkout-sync.md` requires running prettier afterwards to pass CI.
```

---

### MEDIUM Priority

#### 6. Dual-mode command anti-pattern

**Location:** `docs/learned/cli/anti-patterns.md`
**Action:** CREATE
**Source:** [PR #8245]

**Draft Content:**

```markdown
---
read-when: designing new CLI commands, adding --dangerous flags, considering dual-mode commands
---

# CLI Anti-Patterns

## Dual-Mode Commands via --dangerous Flag

### The Problem

Commands with `--dangerous` flag enabling alternative modes create complexity:

- **2x code paths**: Separate branches for each mode (Graphite vs git-only)
- **2x test suites**: Tests split across files for each mode
- **Unclear UX**: Users must understand when to use each mode

### Example: erk pr sync (deleted)

The deleted command had 373 lines implementing two distinct modes:
- Git-only mode: fetch - rebase - force push
- Graphite mode: track - squash - update commit - restack - submit

Required 1,592 lines of tests split across two files.

### Better Patterns

1. **Separate commands**: If modes are truly distinct, create separate commands with clear names
2. **Intelligent auto-detection**: Command chooses strategy based on context (e.g., Graphite availability)
3. **Single mode with clear scope**: Command does one thing well

### Applied Solution

`/erk:sync-divergence` provides intelligent strategy selection instead of requiring users to understand modes.
```

---

#### 7. Command consolidation strategy

**Location:** `docs/learned/refactoring/command-consolidation.md`
**Action:** CREATE
**Source:** [PR #8238, #8245]

**Draft Content:**

```markdown
---
read-when: simplifying CLI commands, consolidating overlapping functionality, planning command deprecation
---

# Command Consolidation Strategy

## Pattern: Simplification Through Deletion

Sometimes the best simplification is deletion. When simplifying command X eliminates the unique value of command Y, consider deleting Y entirely.

## Two-PR Arc Pattern

1. **PR 1: Make command self-sufficient**
   - Add functionality to command X that previously required command Y
   - Example: PR #8238 made `erk pr checkout` handle remote sync internally

2. **PR 2: Delete redundant command**
   - Remove command Y that is now redundant
   - Example: PR #8245 deleted `erk pr sync` after checkout became self-sufficient

## Identification Signals

Command Y may be redundant if:
- Its functionality is now built into command X
- Docs describe it as "optional" or "for edge cases"
- Zero programmatic invocations exist

## Verification Checklist

Before deletion:
- Confirm command X handles all necessary scenarios
- Verify no unique functionality remains in command Y
- Check for programmatic callers in `.claude/`
```

---

#### 8. Plan scope evolution handling

**Location:** `docs/learned/planning/plan-scope-evolution.md`
**Action:** CREATE
**Source:** [Plan]

**Draft Content:**

```markdown
---
read-when: planning sessions, handling user pivots, discovery-driven planning
---

# Plan Scope Evolution

## Discovery-Driven Planning

Planning sessions may legitimately evolve in scope when discovery reveals larger opportunities.

## Example Evolution (PR #8245)

1. **Start**: "Resolve PR review thread about abstraction bypass"
2. **Pivot 1**: "Could we delete this code from the simplification PR?"
3. **Pivot 2**: "Could we delete the entire command?"
4. **Execution**: Comprehensive deletion plan

## Handling Pivots

When user scope changes:

1. **Recognize the pivot**: User redirecting from fix to larger refactoring
2. **Pause to verify**: Confirm new scope before continuing implementation
3. **Use parallel analysis**: Launch Explore agents for multi-dimensional analysis (references + dependencies)
4. **Validate safety**: Apply vestigial feature detection checklist before proposing deletion

## Agent Behavior

- Correctly recognize scope pivots and adapt analysis
- Don't proceed with original scope when user clearly wants larger change
- Validate findings before committing to "safe to delete" conclusion
```

---

#### 9. Exit code handling for JSON commands

**Location:** `docs/learned/cli/tripwires.md`
**Action:** UPDATE
**Source:** [Plan]

**Draft Content:**

Add to existing tripwires file:

```markdown
## JSON Command Exit Codes

**Trigger:** When `--format json` commands return exit code 1

**Do:** Check stdout for JSON before assuming failure. Capture stdout and stderr separately.

**Why:** Some JSON commands may return exit code 1 for flow control (e.g., duplicate detection) while still providing valid JSON output with success indicators.

**Example:** `erk exec plan-save --format json` may return exit 1 with `{"success": true, "skipped_duplicate": true}` on stdout.
```

---

#### 10. PR checkout self-sufficiency update

**Location:** `docs/learned/erk/pr-commands.md` (or create if needed)
**Action:** UPDATE
**Source:** [PR #8238, #8245]

**Draft Content:**

Add or update section:

```markdown
## PR Checkout

`erk pr checkout` is now **self-sufficient** after PR #8238 and #8245.

### What This Means

- No longer requires separate `erk pr sync` step
- Handles remote synchronization automatically
- For diverged branches, use `/erk:sync-divergence` instead

### Historical Context

Previously the workflow was:
1. `erk pr checkout <number>`
2. `erk pr sync` (separate step)

Now the workflow is simply:
1. `erk pr checkout <number>` (complete)
```

---

### LOW Priority

#### 11. Negative test assertions as documentation

**Location:** `docs/learned/testing/test-as-documentation.md`
**Action:** UPDATE
**Source:** [Plan]

**Draft Content:**

Add section to existing doc:

```markdown
## Negative Assertions as Removal Proof

Test assertions can document that a feature was intentionally removed:

```python
# This assertion documents that PR footer no longer includes sync command
assert "erk pr sync" not in result
```

### Purpose

- Verifies feature is not present (test function)
- Documents that removal was intentional (documentation function)
- Prevents accidental reintroduction (regression prevention)

### Interpretation

When reviewing code, negative assertions like `assert "X" not in result` indicate:
- Feature X was previously present
- Removal was deliberate
- Test serves as proof of removal
```

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Session ID Substitution Unavailable

**What happened:** `impl-signal started` failed with "session-id-required" because `${CLAUDE_SESSION_ID}` substitution wasn't available in that context.

**Root cause:** Session ID substitution works in skills but not in all command contexts.

**Prevention:** Commands should handle missing session ID gracefully (use `2>/dev/null || true` or accept `--session-id "unknown"`).

**Recommendation:** CONTEXT_ONLY (edge case, not worth a tripwire)

### 2. Prettier Check Fails After Markdown Edits

**What happened:** CI failed on `pr-checkout-sync.md` after Edit tool changed table structure.

**Root cause:** Edit tool doesn't auto-format; structural changes to tables break prettier validation.

**Prevention:** Always run prettier after editing markdown files with structured content (tables, lists).

**Recommendation:** TRIPWIRE (see item #5 above)

### 3. Exec Reference Out of Date

**What happened:** Auto-generated skill references still contained deleted command.

**Root cause:** `erk-dev gen-exec-reference-docs` wasn't run after file deletion.

**Prevention:** Include exec reference regeneration in command deletion workflow.

**Recommendation:** TRIPWIRE (see item #3 above)

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Exec Reference Regeneration

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before deleting CLI command files
**Warning:** Run `erk-dev gen-exec-reference-docs` to update auto-generated skill references
**Target doc:** `docs/learned/cli/tripwires.md`

Without this tripwire, agents may delete commands but leave stale references in the auto-generated skill documentation. Claude agents consulting this reference will find documentation for commands that no longer exist, leading to failed tool invocations and confusion.

### 2. Format After Edit for Markdown Tables

**Score:** 5/10 (Non-obvious +1, Cross-cutting +2, Silent failure +2)
**Trigger:** After editing markdown files with tables using Edit tool
**Warning:** Run `prettier --write <file>` to avoid CI failures
**Target doc:** `docs/learned/testing/tripwires.md`

The Edit tool doesn't format its output. When editing markdown tables, the structural changes may violate prettier formatting rules, causing CI to fail. This requires an extra commit to fix - a minor but avoidable friction point.

### 3. Incomplete Command Removal - Indirect References

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)
**Trigger:** When deleting commands, verify ALL references including indirect ones
**Warning:** Grep for references including broken links, example code blocks, and workflow descriptions in unchanged files
**Target doc:** `docs/learned/cli/tripwires.md`

The tripwires bot found 3 stale references in unchanged files (git-graphite-quirks.md, pr-address-workflows.md, workspace-activation.md) that manual review missed. Comprehensive grep verification is essential.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Exit Code Handling for JSON Commands

**Score:** 3/10 (Non-obvious +2, External tool quirk +1)
**Notes:** Confusing but low impact - CI/testing catches it quickly. Would warrant promotion if this pattern becomes common across more commands.

### 2. Command Simplification Can Mean Deletion

**Score:** 2/10 (Non-obvious +2)
**Notes:** Architectural insight rather than error-prone pattern. Better suited as documentation than tripwire since it's a planning heuristic, not a pitfall.

### 3. Module Docstring as Deprecation Signal

**Score:** 2/10 (Non-obvious +2)
**Notes:** Discovery heuristic for vestigial features. Documented in vestigial-feature-detection.md rather than as tripwire.
