# Documentation Plan: Add a print statement

## Context

This plan originated from a deceptively simple task: "Add a print statement." While the request sounds trivial, the implementation session revealed several valuable patterns and pitfalls that warrant permanent documentation. The planning phase validated the erk plan mode workflow, while the implementation phase exposed nuanced challenges around automated review handling, test architecture decisions, and git divergence during managed PR workflows.

The documentation opportunities here are particularly valuable because they emerge from real implementation friction. When an automated code review bot flagged the newly added `click.echo()` call as a "debug print that should be removed," the agent had to navigate a scenario where following automated feedback would have directly contradicted the plan's intent. Similarly, the initial over-engineering of tests (using `CliRunner` for what was actually a Layer 3 pure unit test) demonstrates a common misidentification pattern that costs developer time.

Future agents implementing CLI features, writing entry point tests, or handling automated PR feedback will benefit from these documented patterns. The insights are cross-cutting: they apply not just to print statements but to any CLI entry point modification, any Layer 3 test scenario, and any situation where automated reviewers may generate false positives.

## Raw Materials

https://gist.github.com/schrockn/b71b3a76f0dadd2d987f28c147cf74f6

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 8     |
| Contradictions to resolve      | 1     |
| Tripwire candidates (score>=4) | 2     |
| Potential tripwires (score2-3) | 3     |

## Documentation Items

### HIGH Priority

#### 1. False Positive Detection in Automated Review

**Location:** `docs/learned/review/handling-contradictory-feedback.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

When automated review bots flag code that directly implements the current plan, do NOT automatically make changes. Check plan intent by reading `.impl/plan.md`. If the feedback contradicts the plan's explicit goal, escalate to user via `AskUserQuestion` before making changes. Document resolution by explaining why feedback was a false positive.

**Example:** Plan requested adding a print statement. Automated bot flagged `click.echo()` as "debug print that should be removed." Agent correctly recognized contradiction, asked user to clarify, user confirmed to keep feature, and resolved thread with explanation of false positive context.

#### 2. Master Branch Warning Tripwire

**Location:** `docs/learned/planning/tripwires.md`
**Action:** CREATE or UPDATE
**Source:** [Plan]
**Score:** 5/10

**Draft Content:**

Tripwire: Before calling `plan-save-to-issue` command. Warning: Do not edit on master branch directly. Use the plan save workflow to ensure proper issue creation and branching. Editing directly on master during plan mode can lead to commits pushed to trunk without review and difficulty tracking which changes belong to which plan.

#### 3. Print Statement Standards Clarification

**Location:** `.claude/skills/dignified-python/cli-patterns.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

When adding user-facing output to CLI entry points, always use `click.echo()`, never bare `print()`. Example:

```python
import click

def main():
    click.echo("Hello from erk")
```

Why not print()? `click.echo()` handles encoding correctly, integrates with Click's output handling, and can be captured/mocked cleanly in tests. Note: When someone requests "add a print statement" in erk context, this means "add an output statement" which should use `click.echo()`.

### MEDIUM Priority

#### 1. Simplified CLI Entry Point Test Pattern

**Location:** `docs/learned/testing/cli-entry-point-patterns.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

CLI entry points appear complex because they involve the Click framework, but they are actually Layer 3 pure unit tests when the entry point has no gateway dependencies. Use mocking instead of CliRunner.

**Simplified Pattern (Recommended, 11 lines):**

```python
from unittest.mock import patch

def test_main_prints_greeting():
    with patch("erk.click.echo") as mock_echo, \
         patch("erk.cli"):
        from erk import main
        main()
        mock_echo.assert_called_once_with("Hello from erk")
```

Over-engineered approaches use `CliRunner`, fixtures, and multiple nested patches (20+ lines). Use pure mocking for entry point testing. Use CliRunner only when testing CLI argument parsing or command invocation chains.

#### 2. Test Layer Misidentification Tripwire

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]
**Score:** 4/10

**Draft Content:**

Tripwire: Before writing tests for CLI entry points. Warning: CLI entry points appear complex (Click framework) but are Layer 3 pure unit tests. Use mocking (not CliRunner) to keep tests simple and focused. Signs you're over-engineering: using CliRunner for simple output functions, creating fixtures, test file 20+ lines for one call, multiple nested context managers.

#### 3. Concurrent Remote Updates During PR Review

**Location:** `docs/learned/erk/divergence-resolution.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

When using `/erk:pr-address` or iterating on PR feedback, expect remote branch divergence. Automated systems may add commits during workflows ("WIP: Prepare..." commits, CI formatting, bot changes). Resolution pattern: (1) `git fetch origin`, (2) check status, (3) `git rebase origin/$BRANCH` (NOT `gt restack` for same-branch divergence), (4) `git push --force-with-lease`. Key distinction: same-branch divergence uses `git rebase`, stack divergence uses `gt restack`.

#### 4. Plan Serialization Flow

**Location:** `docs/learned/planning/plan-persistence.md`
**Action:** CREATE
**Source:** [Plan]

**Draft Content:**

Plans transition through states: (1) In-memory during plan mode, (2) Local markdown in `~/.claude/plans/`, (3) GitHub issue via `plan-save-to-issue`. The command outputs JSON with issue_number, issue_url, and archive_paths. Commands reference session via `--session-id` flag. In hooks, session ID comes from stdin JSON, not environment variables.

### LOW Priority

#### 1. Exit-Plan-Mode Hook Decision Flow

**Location:** `docs/learned/planning/hook-decision-flow.md`
**Action:** CREATE
**Source:** [Plan]

**Draft Content:**

Exit-plan-mode hook presents 5 options: (1) Save the plan (Recommended, creates issue), (2) Implement here (skip issue creation), (3) Save + implement (issue AND implement now), (4) View/Edit plan, (5) Save + submit for review (queue for external). Use Save (1) by default for async implementation. Use Implement (2) for quick fixes. Use Save+implement (3) when want tracking and immediate completion.

#### 2. Session ID Substitution in Plan Workflows

**Location:** `docs/learned/claude-code/session-id-availability.md`
**Action:** UPDATE
**Source:** [Plan]

**Draft Content:**

In erk plan mode, use `--session-id "${CLAUDE_SESSION_ID}"` in commands. Skills use string substitution. Hooks receive ID via stdin JSON and must interpolate actual value: `f"erk exec plan-save-to-issue --session-id {session_id} ..."`.

#### 3. Overlapping Automated Feedback

**Location:** `docs/learned/pr-operations/bot-coordination.md`
**Action:** CREATE or UPDATE
**Source:** [Impl]

**Draft Content:**

Multiple automated bots (Dignified Python Review, Code Simplifier, Tripwires) may analyze same code and flag same locations with different perspectives. Read all comments before acting. Multiple perspectives may inform single resolution. Identify root issue. Respond to each comment. Future improvement: aggregate or deduplicate bot feedback.

## Contradiction Resolutions

### 1. Print Statement Standards Conflict

**Existing doc:** `.claude/skills/dignified-python/cli-patterns.md`
**Conflict:** Plan title "Add a print statement" conflicts with "Use `click.echo()` for output, NEVER `print()`"
**Resolution:** Implementation correctly applied `click.echo()`. UPDATE CLI patterns skill to clarify that "print statement" in erk context means "output statement" which should use `click.echo()`. Add entry point greeting pattern as example.

## Prevention Insights

### 1. Automated Review False Positive

**What happened:** Code Simplifier bot flagged `click.echo()` as debug print despite it being core feature.
**Root cause:** Automated reviewers lack context about plan intent.
**Prevention:** When feedback contradicts `.impl/plan.md`, escalate to user via AskUserQuestion.

### 2. Test Over-Engineering

**What happened:** Agent initially created complex `CliRunner` test with multiple fixtures.
**Root cause:** CLI context created complexity perception. Simple mocking sufficed.
**Prevention:** Load `fake-driven-testing` skill before writing tests. Entry points without gateway deps are Layer 3 (pure unit).

### 3. Git Push Rejection (Non-Fast-Forward)

**What happened:** Push rejected; remote had "WIP: Prepare..." commit from automation.
**Root cause:** PR workflows cause divergence when automation adds commits.
**Prevention:** Expect remote updates in managed workflows. Always `git fetch` before push. Use `git rebase origin/$BRANCH` for same-branch divergence.

## Tripwire Candidates

### 1. Master Branch Warning (plan-save-to-issue) — Score: 5/10 ✓ MEETS THRESHOLD

**Trigger:** Before calling `plan-save-to-issue` command
**Warning:** Do not edit on master branch directly.
**Rationale:** Non-obvious (+2), Cross-cutting: all plan workflows (+2), Destructive potential (+2), Silent failure (+2), Demonstrated in planning session (+1)

This prevents commits on trunk without review, breaking the plan-oriented workflow that erk enforces.

### 2. CLI Entry Point Layer Misidentification — Score: 4/10 ✓ MEETS THRESHOLD

**Trigger:** Before writing tests for CLI entry points
**Warning:** CLI entry points are Layer 3 pure unit tests. Use mocking, not CliRunner.
**Rationale:** Non-obvious (+2), Cross-cutting: all entry point tests (+2), Prevents repeated pattern: test over-engineering (+1), External tool context: Click (+1)

Session demonstrated this directly: agent over-engineered 20+ line test before self-correcting to 11-line mock test.

### Potential Tripwires (Score 2-3)

- **Concurrent Remote Updates During PR Review (Score: 3)**: Becomes stronger candidate if automation commits frequent. Currently documented as pattern.
- **False Positive Handling in Automated Review (Score: 3)**: Recommend documenting as pattern first. Promote to tripwire if false positives continue.
- **Overlapping Automated Feedback (Score: 2)**: Architectural improvement. Low priority unless bots expand significantly.