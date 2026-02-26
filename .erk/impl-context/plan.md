# Documentation Plan: Fix modal keystroke leakage to underlying view

## Context

This PR (#8299) fixed a critical UX bug where keystrokes in modal screens would leak through to the underlying view and trigger unintended actions. For example, opening the launch modal and pressing "s" to submit would also activate sort mode on the main screen, or pressing any unmapped key in a modal would propagate to app-level bindings.

The fix established a consistent pattern across three modal screens (HelpScreen, LaunchScreen, PlanBodyScreen): unconditionally call `event.prevent_default()` and `event.stop()` at the start of every `on_key()` handler to consume all keystrokes before any conditional logic. This pattern is non-obvious because Textual's event propagation is pass-through by default - modal screens don't automatically consume keystrokes, they only handle BINDINGS entries and pass everything else through to underlying widgets.

Documentation matters because future agents implementing modal screens will face this same trap. The pattern requires understanding Textual's event model and the distinction between `prevent_default()` (stops Textual's default handling) and `stop()` (prevents event bubbling). Beyond the core bug fix, this implementation revealed several cross-cutting workflow patterns: how to handle multi-round PR review feedback, when to create plan PRs for cross-cutting test requests, and the stdin JSON format expected by batch PR operations.

## Raw Materials

PR #8299 - associated sessions analyzed for documentation insights.

## Summary

| Metric | Count |
|--------|-------|
| Documentation items | 14 |
| Contradictions to resolve | 0 |
| Tripwire candidates (score>=4) | 3 |
| Potential tripwires (score 2-3) | 2 |

## Stale Documentation Cleanup

Existing docs with phantom references requiring action:

### 1. Fix phantom reference in modal-widget-embedding.md

**Location:** `docs/learned/tui/modal-widget-embedding.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `src/erk/tui/screens/objective_plans_screen.py` (file does not exist)
**Source:** [Existing docs check]

**Cleanup Instructions:**

The document describes a valid reusable pattern for modal widget embedding but references a non-existent screen implementation at line 58. Remove or update the reference to `objective_plans_screen.py`. If the pattern has current implementations, reference those instead; otherwise, mark the reference as historical or remove it entirely.

## Documentation Items

### HIGH Priority

#### 1. Modal keystroke consumption tripwire

**Location:** `docs/learned/tui/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] [PR #8299]

**Draft Content:**

```markdown
## Modal Keystroke Consumption

**Trigger:** Before implementing `on_key()` in any ModalScreen subclass

**Warning:** Always call `event.prevent_default()` and `event.stop()` unconditionally at the start of the handler to prevent keystroke leakage to underlying views. Textual's event propagation is pass-through by default - modal screens do not automatically consume keystrokes.

**Why this matters:** Without both calls, keys not in BINDINGS leak through to parent widgets and app-level bindings. Users experience unintended side effects (e.g., sort mode activating while submitting from a modal).

**Pattern:**
- Call `event.prevent_default()` first (prevents Textual base class handlers)
- Call `event.stop()` second (prevents bubbling to parent widgets)
- Only then check key membership for conditional logic

**See:** `src/erk/tui/screens/help_screen.py`, `src/erk/tui/screens/launch_screen.py`, `src/erk/tui/screens/plan_body_screen.py` for reference implementations.

**Cross-reference:** docs/learned/textual/quirks.md for general event handler pattern
```

---

#### 2. Generalize event handler pattern in quirks doc

**Location:** `docs/learned/textual/quirks.md`
**Action:** UPDATE
**Source:** [Impl] [PR #8299]

**Draft Content:**

Rename section "Click Handlers Need Both prevent_default() and stop()" to "Event Handlers Need Both prevent_default() and stop()" and expand to cover all event types:

```markdown
## Event Handlers Need Both prevent_default() and stop()

When overriding ANY event handler in a modal or specialized widget:

1. Call `event.prevent_default()` to prevent Textual's default handling and base class implementations
2. Call `event.stop()` to prevent event bubbling up the DOM tree to parent widgets

**Why both are needed:**
- `prevent_default()`: Stops Textual from calling handlers in base classes and internal logic (e.g., DataTable's click handling)
- `stop()`: Stops the event from bubbling up to parent widgets (e.g., app-level key bindings)

Without both, events leak through in various ways:
- To base class implementations
- To parent widgets
- To the underlying view when a modal is open

**Click event example:** See DataTable click handling section below.

**Keyboard event example:** Modal screens must consume all keystrokes to prevent leakage. See `src/erk/tui/screens/help_screen.py` for the canonical pattern: call both methods unconditionally at the start of `on_key()`, then handle specific keys.

**Cross-reference:** docs/learned/tui/tripwires.md for modal-specific tripwire
```

---

#### 3. PR review iteration workflow

**Location:** `docs/learned/pr-operations/pr-review-iteration-workflow.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - handling multiple rounds of PR review feedback
  - deciding between implementing directly vs creating follow-up plan
  - resolving review threads after making fixes
tripwires: 2
---

# PR Review Iteration Workflow

## Overview

PR review often requires multiple rounds. This document establishes the workflow for handling iterative review feedback efficiently.

## Two-Phase Review Pattern

**Phase 1: Simple Fixes**
1. Classify feedback using pr-feedback-classifier skill
2. Make local fixes (docstrings, style, small refactors)
3. Commit all fixes in a batch commit
4. Resolve threads with substantive comments referencing the commit
5. Push and trigger new review round

**Phase 2: Complex Follow-up**
When second-round feedback requests cross-cutting work (e.g., test coverage across 3+ files):
1. Enter plan mode rather than implementing directly
2. Create a plan PR with structured implementation approach
3. Resolve threads with references to the plan PR (e.g., "Test coverage planned in #NNNN")

## Substantive Thread Resolution

When resolving review threads, provide context rather than generic "Fixed" messages:
- Reference specific commits: "Fixed in abc1234"
- Reference follow-up PRs: "Test coverage planned in #8304"
- Explain if deferring: "Deferred to follow-up per [rationale]"

This creates better PR history and helps reviewers understand what happened.

## See Also

- docs/learned/pr-operations/tripwires.md for plan-first guidance on cross-cutting feedback
- `.claude/skills/pr-operations/SKILL.md` for command reference
```

---

#### 4. Plan-first tripwire for cross-cutting PR feedback

**Location:** `docs/learned/pr-operations/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Plan-First for Cross-Cutting PR Feedback

**Trigger:** When `/erk:pr-address` identifies complexity: "cross_cutting" with a shared theme across 3+ files

**Warning:** Create a plan PR instead of implementing directly to maintain plan-first workflow. Cross-cutting changes (e.g., "add test coverage for X across 3 files") deserve tracked plans.

**Why this matters:** Direct implementation of cross-cutting work:
- Risks inconsistency across files
- Lacks reviewable design decisions
- Can't be easily interrupted or resumed

**Workflow:**
1. Recognize cross-cutting theme in classifier output
2. Enter plan mode
3. Create plan PR with `/erk:plan-save`
4. Resolve review threads referencing the plan PR

**See:** docs/learned/pr-operations/pr-review-iteration-workflow.md for complete multi-round workflow
```

---

### MEDIUM Priority

#### 5. Update modal screen pattern checklist

**Location:** `docs/learned/tui/modal-screen-pattern.md`
**Action:** UPDATE
**Source:** [Impl] [PR #8299]

**Draft Content:**

Add step 8 to the existing 7-element checklist:

```markdown
8. **Implement on_key() with event consumption**
   - Add `on_key(self, event: Key) -> None` method
   - Call `event.prevent_default()` unconditionally at the start
   - Call `event.stop()` unconditionally after prevent_default
   - Conditionally dismiss based on key membership
   - Exclude keys already in BINDINGS from dismiss logic (they have their own handlers)
   - See docs/learned/tui/tripwires.md for modal keystroke consumption warning
```

---

#### 6. Task-based skill invocation pattern

**Location:** `docs/learned/commands/task-based-skill-invocation.md`
**Action:** CREATE
**Source:** [Plan] [Impl]

**Draft Content:**

```markdown
---
read-when:
  - invoking classifier skills from commands
  - skill has context: fork metadata
  - running in --print mode
tripwires: 1
---

# Task-Based Skill Invocation Pattern

## Overview

Skills with `context: fork` metadata require special handling when invoked from commands running in `--print` mode. Direct skill invocation may not provide proper agent isolation.

## The Problem

When a command runs in `--print` mode, the `context: fork` skill metadata may not guarantee isolation. The skill may execute in the same context as the calling command.

## Solution: Task Tool Delegation

Use the Task tool with a general-purpose subagent to invoke the skill:

```
Task(
  prompt: "Load and follow .claude/skills/pr-feedback-classifier/SKILL.md with PR #NNNN",
  subagent_type: "general-purpose"
)
```

This ensures:
- The skill runs in a separate agent context
- Output is captured and returned to the calling command
- The calling command can parse JSON output from the skill

## Example

The `/erk:pr-address` command uses this pattern for the pr-feedback-classifier skill. See `.claude/commands/erk/pr-address.md` for the complete implementation.

## When to Use

- Classifier skills that return structured output
- Skills needing isolation from the command's context
- Any skill with `context: fork` metadata when in `--print` mode
```

---

#### 7. TUI event handler testing strategy

**Location:** `docs/learned/testing/testing-tui-event-handlers.md`
**Action:** CREATE
**Source:** [PR #8299]

**Draft Content:**

```markdown
---
read-when:
  - writing tests for Textual event handlers
  - testing modal isolation behavior
  - test coverage requested for TUI event handling
tripwires: 1
---

# TUI Event Handler Testing Strategy

## Overview

Testing Textual event handlers (click, key) requires understanding Textual's pilot test infrastructure and what behaviors are worth testing.

## What to Test

**Worth testing:**
- Event handlers dismiss modals with correct return values
- Event handlers fire expected actions on specific keys
- Modal screens don't crash on unexpected input

**Harder to test (may require integration tests):**
- Event bubbling prevention (prevent_default + stop behavior)
- Modal isolation from underlying view
- App-level binding non-interference

## Testing Approaches

**Unit tests with Pilot:**
Use Textual's pilot infrastructure to simulate key presses and verify screen state changes. See existing TUI tests in `tests/tui/` for patterns.

**Manual verification for isolation:**
When automated testing of event bubbling is impractical, document manual verification steps:
- Run `erk dash -i`
- Open modal, press unmapped key
- Verify modal closes AND underlying view is unchanged

## When Deferring Tests Is Acceptable

For bug fixes with clear manual verification, deferring test coverage to a follow-up PR is acceptable if:
- The fix is low-risk (pattern application, not logic change)
- Manual verification is documented
- A tracked plan PR exists for test coverage (e.g., #8304)

**See:** docs/learned/testing/bug-fix-testing-strategy.md for general guidance
```

---

#### 8. Git rebase cherry-pick skip behavior

**Location:** `docs/learned/reference/git-rebase-skip-behavior.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - git push fails with non-fast-forward during PR iteration
  - git rebase shows "skipped previously applied commit" warning
  - branch diverged during PR review
tripwires: 1
---

# Git Rebase Cherry-Pick Skip Behavior

## Overview

When rebasing local commits onto a remote branch that contains equivalent changes with different SHAs, Git automatically detects and skips duplicate commits.

## The Warning

```
hint: Skipping commit 9da36fc47:
hint:   Previous commit message
hint: It was already applied to the target branch
```

**This is expected behavior, not an error.** Git's cherry-pick detection recognized that the changes are already present in the remote history.

## When This Occurs

Common during PR iteration when:
- CI commits changes (PR description updates, auto-formatting)
- Another agent pushed equivalent fixes
- `setup-impl` cleanup commits run concurrently with local work

## Resolution Pattern

1. `git fetch origin` to update remote refs
2. `git log HEAD..origin/$BRANCH` to see what remote has that local doesn't
3. `git log origin/$BRANCH..HEAD` to see what local has that remote doesn't
4. `git rebase origin/$BRANCH` to rebase local on top of remote
5. If "skipped previously applied commit" appears, this is success
6. `git push` to complete

## See Also

- docs/learned/erk/git-pr-workflow.md for complete PR submission workflow
```

---

#### 9. Stdin JSON format for batch PR operations

**Location:** `docs/learned/pr-operations/batch-operation-formats.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - using erk exec commands for batch operations
  - resolving multiple review threads
  - command rejects CLI flag format
tripwires: 1
---

# Batch Operation Formats for PR Commands

## Overview

Many `erk exec` commands for PR operations use stdin JSON format rather than CLI flags. Always check `<command> -h` before first use.

## Stdin JSON Pattern

Commands like `resolve-review-threads` expect JSON on stdin:

```bash
echo '[{"thread_id": "PRR_...", "comment": "Fixed in abc1234"}]' | erk exec resolve-review-threads
```

**NOT:**
```bash
erk exec resolve-review-threads --pr 8299 --thread-ids "PRR_..."  # Wrong!
```

## Why Stdin JSON

- Batch operations may have complex per-item data
- CLI flags can't easily express arrays of objects
- JSON is self-describing and extensible

## Commands Using This Pattern

- `erk exec resolve-review-threads` - resolve multiple threads with individual comments
- Check help text for other batch commands

## Discovering the Format

Always run `<command> -h` before first use to discover:
- Whether stdin or flags are expected
- Required JSON schema for stdin format
- Example invocations
```

---

#### 10. Bug fix test coverage expectations

**Location:** `docs/learned/testing/bug-fix-testing-strategy.md`
**Action:** CREATE
**Source:** [PR #8299]

**Draft Content:**

```markdown
---
read-when:
  - fixing a bug and deciding on test coverage
  - test coverage bot flags missing tests
  - deferring tests to follow-up PR
tripwires: 1
---

# Bug Fix Testing Strategy

## Overview

Bug fixes occupy a middle ground between "always test everything" and "ship fast". This document provides guidance on when tests are required vs. deferrable.

## When Tests Are Required

- Logic changes that could regress
- Complex conditional behavior
- Security-sensitive code paths
- Changes to public APIs

## When Deferring Is Acceptable

Tests may be deferred to a follow-up PR when:
1. **Pattern application**: The fix applies a known-correct pattern (like `prevent_default()` + `stop()`)
2. **Manual verification is clear**: Steps to verify manually are documented
3. **Low regression risk**: The change is additive, not modifying existing logic
4. **Tracked follow-up**: A plan PR exists for test coverage (create one if deferring)

## Process for Deferring

1. Document manual verification steps in PR description
2. Create a plan PR for test coverage using `/erk:plan-save`
3. Reference the plan PR when resolving test coverage review comments
4. Ensure the plan PR is linked to the original PR for traceability

## See Also

- docs/learned/testing/testing-tui-event-handlers.md for TUI-specific guidance
```

---

#### 11. Docstring accuracy for conditional event handlers

**Location:** `docs/learned/conventions.md`
**Action:** UPDATE
**Source:** [PR #8299]

**Draft Content:**

Add section to conventions.md:

```markdown
## Docstring Accuracy for Event Handlers

Event handlers with conditional logic must have precise docstrings that accurately reflect the conditions.

**Bad:** "Consume all keys; dismiss on any key press."
**Good:** "Consume all keys; dismiss on keys not handled by bindings (escape, q excluded)."

When an event handler:
- Consumes all events but only acts on some
- Has an exclusion list (keys in BINDINGS)
- Has conditional dismiss/action logic

The docstring must specify the exceptions. Reviewers and future maintainers rely on docstrings to understand behavior without reading implementation.
```

---

#### 12. Batch thread resolution with context

**Location:** `docs/learned/pr-operations/batch-operation-formats.md`
**Action:** UPDATE (merge with item 9)
**Source:** [Impl]

**Draft Content:**

Add section to the batch operations doc:

```markdown
## Substantive Resolution Comments

When resolving review threads in batch, provide context rather than generic messages:

**Good patterns:**
- `"Fixed in commit abc1234"` - specific reference
- `"Test coverage planned in #8304"` - follow-up PR reference
- `"Addressed by removing the conditional per reviewer feedback"` - explanation

**Avoid:**
- `"Fixed"` - no context
- `"Done"` - no traceability
- `"Will do"` - not actionable

This creates better PR history and helps reviewers understand resolution without re-reading code.
```

---

### LOW Priority

#### 13. Implementation plan location detection

**Location:** `docs/learned/planning/impl-directory-detection.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - reading plan.md in implementation agent
  - setup-impl completed but plan not found
  - .impl directory structure questions
tripwires: 1
---

# Implementation Plan Location Detection

## Overview

The location of `plan.md` varies based on execution context. Do not hardcode `.impl/plan.md`.

## Directory Variations

| Context | Directory | When Used |
|---------|-----------|-----------|
| Local implementation | `.impl/` | Standard local `erk implement` |
| Worker context | `.worker-impl/` | CI workflow workers |
| Impl context | `.erk/impl-context/` | Branch-scoped discovery |

## Correct Pattern

Always use `erk exec setup-impl` JSON output to locate the plan:

```bash
setup_output=$(erk exec setup-impl --json)
plan_path=$(echo "$setup_output" | jq -r '.plan_path')
```

## Fallback: GitHub Fetch

If local path fails, fetch from GitHub:

```bash
gh pr view $PR_NUMBER --json body -q .body > .impl/plan.md
```

## Anti-Pattern

```bash
cat .impl/plan.md  # May not exist!
```

This assumes a hardcoded path that varies by context.
```

---

#### 14. LBYL dictionary access in TUI context

**Location:** `docs/learned/tui/tripwires.md`
**Action:** UPDATE
**Source:** [PR #8299]

**Draft Content:**

Add cross-reference to existing TUI tripwires:

```markdown
## LBYL Dictionary Access in Event Handlers

**Trigger:** Using `.get()` for dictionary access in TUI event handlers

**Warning:** Use LBYL membership test (`if key in dict:`) instead of `.get()` pattern. This applies to all Python code per dignified-python standards.

**TUI-specific example:** In `on_key()` handlers checking key bindings:
- **Bad:** `command = self._key_to_command.get(event.key)` then `if command is not None:`
- **Good:** `if event.key in self._key_to_command:` then direct access

**See:** `.claude/skills/dignified-python-core.md` for complete LBYL guidance
```

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Modal Keystroke Leakage

**What happened:** Keystrokes in modal screens propagated to underlying views, causing unintended actions (e.g., "s" key triggering sort while submit modal was open).

**Root cause:** Textual's event propagation is pass-through by default. Modal screens using BINDINGS only handle explicit matches; all other keys bubble to parent widgets.

**Prevention:** All ModalScreen subclasses must override `on_key()` with unconditional `event.prevent_default()` + `event.stop()` calls at the handler start.

**Recommendation:** TRIPWIRE - This is the primary tripwire from this PR.

### 2. Git Push Rejection During PR Iteration

**What happened:** `git push` failed with "non-fast-forward" after concurrent CI activity updated the remote branch.

**Root cause:** PR description updates, setup-impl cleanup commits, or other CI operations create divergence between local and remote.

**Prevention:** Always use `git pull --rebase` (not `git pull`) to rebase local commits on top of remote changes. The "skipped previously applied commit" warning is expected when remote contains equivalent changes.

**Recommendation:** ADD_TO_DOC - Document in git rebase reference.

### 3. Wrong Command Format for Batch Operations

**What happened:** Agent tried `erk exec resolve-review-threads --pr N --thread-ids X` but command expected stdin JSON.

**Root cause:** Assumed CLI flag pattern without checking help text.

**Prevention:** Always run `<command> -h` before first use to discover stdin/flag patterns.

**Recommendation:** ADD_TO_DOC - Document in batch operations guide.

### 4. Plan File Not Found at Expected Path

**What happened:** Agent tried to read `.impl/plan.md` but file was at `.worker-impl/plan.md` from previous session context.

**Root cause:** Hardcoded path assumption; implementation context varies by execution environment.

**Prevention:** Use `setup-impl` JSON output for actual paths; never hardcode `.impl/plan.md`.

**Recommendation:** ADD_TO_DOC - Document in planning directory detection guide.

### 5. Classifier Skill Invocation Failure

**What happened:** Agent ran `erk exec classify-pr-feedback` expecting an exec command, but classifier is a skill.

**Root cause:** Confusion between exec commands and skills; `context: fork` metadata in `--print` mode doesn't guarantee isolation.

**Prevention:** Use Task tool with `subagent_type: "general-purpose"` for skills needing true isolation.

**Recommendation:** ADD_TO_DOC - Document in task-based skill invocation pattern.

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Modal Keystroke Consumption Pattern

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2)
**Trigger:** Before implementing `on_key()` in any ModalScreen subclass
**Warning:** Always call `event.prevent_default()` and `event.stop()` unconditionally at the start of the handler to prevent keystroke leakage to underlying views.
**Target doc:** `docs/learned/tui/tripwires.md`

This is tripwire-worthy because the Textual event model is counterintuitive - developers expect modals to isolate input automatically. The bug manifests as subtle UX issues (unintended actions) that are hard to diagnose without understanding the event propagation model. Every modal screen faces this same trap.

### 2. Plan-First for Cross-Cutting PR Feedback

**Score:** 5/10 (Non-obvious +2, Cross-cutting +2, Repeated pattern +1)
**Trigger:** When `/erk:pr-address` identifies complexity: "cross_cutting" with shared theme across 3+ files
**Warning:** Create a plan PR instead of implementing directly to maintain plan-first workflow. Cross-cutting changes deserve tracked plans.
**Target doc:** `docs/learned/pr-operations/tripwires.md`

This is tripwire-worthy because the default agent behavior is to implement immediately. Without this tripwire, agents will attempt direct implementation of cross-cutting work, leading to inconsistency, lack of reviewable design, and interruptibility issues.

### 3. Git Rebase During PR Iteration

**Score:** 4/10 (Non-obvious +2, Repeated pattern +1, External tool quirk +1)
**Trigger:** When `git push` fails with "non-fast-forward" during PR review iteration
**Warning:** Use `git pull --rebase` (not `git pull`) to rebase local commits on top of remote changes. "Skipped previously applied commit" is expected when remote contains equivalent changes.
**Target doc:** `docs/learned/reference/git-rebase-skip-behavior.md`

This pattern occurs frequently during PR iteration when CI or other agents push to the same branch. The "skipped" warning can be alarming without understanding it's expected behavior.

---

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Stdin JSON Format for Batch Operations

**Score:** 3/10 (Non-obvious +2, External tool quirk +1)
**Notes:** Could be promoted if this pattern causes repeated errors across multiple sessions. The current fix was a one-time discovery, but the pattern applies to multiple erk exec commands. If agents continue to assume CLI flag patterns, this should be elevated to tripwire status.

### 2. Implementation Plan Location Detection

**Score:** 2/10 (Non-obvious +2)
**Notes:** Not quite cross-cutting (specific to implementation agents), but caused real errors during implementation. Could be promoted if agents continue to hardcode `.impl/plan.md` paths. The variety of execution contexts (`.impl/`, `.worker-impl/`, `.erk/impl-context/`) makes this a recurring trap.
