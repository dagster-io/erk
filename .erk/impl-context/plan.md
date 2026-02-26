# Documentation Plan: Rename "issue" exec scripts to PR terminology + add batch variants

## Context

PR #8280 renamed five exec scripts from "issue"-based terminology to correct "PR"/"plan" terminology, aligning command names with their actual behavior: all operate on GitHub PRs via PlanBackend, not generic GitHub issues. The PR also introduced two new batch commands (`add-plan-labels`, `close-prs`) that demonstrate exemplary patterns for batch stdin JSON processing with LBYL validation, frozen dataclass results, and discriminated union error handling.

This implementation work uncovered significant documentation drift: 7+ docs still referenced the old `setup_impl_from_issue.py` filename, multiple behavior descriptions no longer matched actual code, and architectural patterns (like branch detection via `plan-ref.json` instead of branch name prefixes) had shifted without corresponding documentation updates. The session work also demonstrated valuable workflow patterns for future agents: systematic test infrastructure discovery, parallel explore agents for planning, and design conflict escalation via AskUserQuestion.

Future agents would benefit from understanding: (1) how to write batch exec commands following the established contract, (2) the correct branch detection and checkout patterns in setup commands, (3) fake configuration patterns for testing exec scripts, and (4) the systematic documentation audit process needed after renaming functions or files.

## Raw Materials

See PR #8280 and associated implementation sessions for source context.

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 27    |
| Contradictions to resolve      | 2     |
| Tripwire candidates (score>=4) | 4     |
| Potential tripwires (score2-3) | 3     |

## Stale Documentation Cleanup

Existing docs with phantom references requiring action. These must be addressed BEFORE creating new documentation.

### 1. docs/learned/planning/impl-context.md

**Location:** `docs/learned/planning/impl-context.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `setup_impl_from_issue.py`
**Cleanup Instructions:** Replace all references to `setup_impl_from_issue.py` with `setup_impl_from_pr.py`. The file was renamed in PR #8280.

### 2. docs/learned/planning/tripwires.md

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `setup_impl_from_issue.py`
**Cleanup Instructions:** Replace all references to `setup_impl_from_issue.py` with `setup_impl_from_pr.py`.

### 3. docs/learned/planning/planned-pr-backend.md

**Location:** `docs/learned/planning/planned-pr-backend.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `setup_impl_from_issue.py`
**Cleanup Instructions:** Replace all references to `setup_impl_from_issue.py` with `setup_impl_from_pr.py`.

### 4. docs/learned/architecture/inference-hoisting.md

**Location:** `docs/learned/architecture/inference-hoisting.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `setup_impl_from_issue.py`
**Cleanup Instructions:** Replace all references to `setup_impl_from_issue.py` with `setup_impl_from_pr.py`.

### 5. docs/learned/architecture/convergence-points.md

**Location:** `docs/learned/architecture/convergence-points.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `setup_impl_from_issue.py`
**Cleanup Instructions:** Replace all references to `setup_impl_from_issue.py` with `setup_impl_from_pr.py`.

### 6. docs/learned/cli/plan-implement.md

**Location:** `docs/learned/cli/plan-implement.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `setup_impl_from_issue.py`
**Cleanup Instructions:** Replace all references to `setup_impl_from_issue.py` with `setup_impl_from_pr.py`.

### 7. docs/learned/architecture/branch-manager-decision-tree.md

**Location:** `docs/learned/architecture/branch-manager-decision-tree.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `generate_issue_branch_name()` (removed function)
**Cleanup Instructions:** Remove references to `generate_issue_branch_name()` which no longer exists. Also update branch operation semantics (see Contradiction Resolution #2).

## Contradiction Resolutions

### 1. Terminology Inconsistency: "issue" vs "PR" vs "plan"

**Existing docs:** Multiple docs in planning/, cli/, architecture/ reference `setup_impl_from_issue.py`
**Conflict:** Documentation describes non-existent file names after PR #8280 renamed the files
**Resolution:** This is stale documentation, not a contradiction. All references to the old file names must be updated to the new names. See Stale Documentation Cleanup section above.

### 2. Branch Operation Semantics

**Existing doc:** `docs/learned/architecture/branch-manager-decision-tree.md:76`
**Claims:** `setup_impl_from_pr()` calls `create_branch()`
**Reality:** Actually calls `create_tracking_branch()` or `checkout_branch()`, never `create_branch()`
**Resolution:** UPDATE_EXISTING - Update the doc to accurately describe the three checkout scenarios:
1. Already on the target branch: sync with remote
2. Local branch exists: `checkout_branch()` then sync
3. Remote-only branch: `create_tracking_branch()` from origin (no sync needed after creation)

## Documentation Items

### HIGH Priority

#### 1. Fix branch operation semantics in branch-manager-decision-tree.md

**Location:** `docs/learned/architecture/branch-manager-decision-tree.md`
**Action:** UPDATE
**Source:** [PR #8280]

**Draft Content:**

```markdown
## Branch Checkout in setup_impl_from_pr

The `_checkout_plan_branch()` helper implements three-case branching logic:

1. **Already on branch**: If current branch matches target, just sync with remote
2. **Local branch exists**: Call `checkout_branch()` then sync with remote
3. **Remote-only branch**: Call `create_tracking_branch()` from `origin/branch` - no sync needed because tracking branches are created at remote HEAD

Key insight: `create_tracking_branch()` is semantically different from `checkout_branch()`. The former creates a new local branch tracking a remote branch (already synced by definition), while the latter switches to an existing local branch (may need sync).

See `src/erk/cli/commands/exec/scripts/setup_impl_from_pr.py` for implementation.
```

---

#### 2. Update detection pattern docs in planned-pr-branch-sync.md

**Location:** `docs/learned/planning/planned-pr-branch-sync.md`
**Action:** UPDATE
**Source:** [PR #8280]

**Draft Content:**

Update the detection pattern description. Replace any description of "header field pattern" or "branch name prefix matching" with:

```markdown
## Branch Detection Pattern

The current implementation uses `github.get_pr()` + `head_ref_name` to determine the target branch, not plan header fields. This is more reliable because:

- PR API is the canonical source for branch information
- Header fields are optional and may be missing
- Avoids parsing inconsistencies in plan markdown

See `src/erk/cli/commands/exec/scripts/setup_impl_from_pr.py` for the `_setup_planned_pr_plan()` function.
```

---

#### 3. Update detection pattern docs in remote-implementation-idempotency.md

**Location:** `docs/learned/planning/remote-implementation-idempotency.md`
**Action:** UPDATE
**Source:** [PR #8280]

**Draft Content:**

Replace the outdated branch-name prefix matching description with:

```markdown
## Detection Mechanism

Implementation idempotency is detected via `.impl/plan-ref.json`, not branch name patterns. The `read_plan_ref()` function checks for an existing plan reference file in the `.impl/` directory.

Example output when existing implementation is detected:
```
Found existing .impl/ for plan #77, skipping branch setup
```

This shift from branch-name detection to plan-ref.json provides:
- More reliable detection (file presence vs name parsing)
- Clearer intent (explicit plan reference vs inferred from name)
- Better error messages (can report the exact plan number)
```

---

#### 4. Update setup-impl-from-pr behavior in erk-exec-commands.md

**Location:** `docs/learned/cli/erk-exec-commands.md`
**Action:** UPDATE
**Source:** [PR #8280]

**Draft Content:**

Update the `setup-impl-from-pr` command description. Change from "creates/checks out branches" to:

```markdown
### setup-impl-from-pr

Syncs existing planned-PR branches using `.impl/plan-ref.json` for idempotency detection. Does NOT create new branches - expects the branch to already exist (locally or on remote).

**Behavior:**
- Checks for existing `.impl/plan-ref.json` - if found for this plan, skips branch setup
- Fetches branch from remote
- Applies 3-case checkout logic (already on / local exists / remote-only)
- Writes plan content to `.impl/plan.md`

**Input:** `--plan-number N` (required)
**Output:** JSON with `success`, `branch`, `plan_path` fields
```

---

#### 5. Document Planned-PR branch detection pattern

**Location:** `docs/learned/planning/planned-pr-branch-detection.md`
**Action:** CREATE
**Source:** [PR #8280] + [Impl]

**Draft Content:**

```markdown
---
read-when:
  - implementing planned-PR setup commands
  - working with github.get_pr() for branch detection
  - understanding plan content fallback hierarchy
---

# Planned-PR Branch Detection

## Overview

When setting up a local environment from a planned-PR (GitHub PR with `erk-plan` label), the branch name must be determined reliably. This document describes the canonical detection pattern.

## Branch Name Detection

Use `github.get_pr()` + `head_ref_name` instead of parsing plan header fields:

- PR API is the authoritative source for branch information
- Header fields (like `BRANCH_NAME:` in plan markdown) are optional
- API-based detection avoids markdown parsing edge cases

See `src/erk/cli/commands/exec/scripts/setup_impl_from_pr.py` for implementation.

## Plan Content Fallback Hierarchy

When retrieving plan content for a planned-PR:

1. **First**: Check `.erk/impl-context/plan.md` on the branch (if branch exists locally)
2. **Fallback**: Extract plan from PR body via PlanBackend

This hierarchy ensures local modifications are preserved while allowing fresh checkout from PR metadata.

## 3-Case Branch Checkout

The `_checkout_plan_branch()` helper implements:

1. **Already on branch**: Current branch matches target - just sync
2. **Local branch exists**: `checkout_branch()` then sync
3. **Remote-only**: `create_tracking_branch()` from origin (no sync needed)

## Tripwires

- When fetching plan branch names, use `github.get_pr()` + `head_ref_name`, not header field parsing
- When setting up `.impl/` from PR, check for existing `.impl/plan-ref.json` first to avoid unnecessary branch switching
```

---

#### 6. Document Branch Manager operations reference

**Location:** `docs/learned/architecture/branch-manager-operations-reference.md`
**Action:** CREATE
**Source:** [PR #8280]

**Draft Content:**

```markdown
---
read-when:
  - using BranchManager for branch operations
  - confused about create vs checkout vs track semantics
  - implementing branch switching logic
---

# Branch Manager Operations Reference

## Overview

BranchManager provides three distinct branch operations with different semantics. Understanding when to use each prevents common errors.

## Operations

### create_branch()

Creates a new local branch from current HEAD. Use when:
- Starting fresh work that doesn't exist anywhere
- Creating a branch for new feature development

Does NOT:
- Fetch from remote
- Set up tracking relationship

### checkout_branch()

Switches to an existing local branch. Use when:
- Branch already exists locally
- Switching between existing branches

Typically followed by sync to pull remote changes.

### create_tracking_branch()

Creates a local branch that tracks a remote branch. Use when:
- Branch exists on remote but not locally
- Setting up for the first time from `origin/branch-name`

Key insight: No sync needed after `create_tracking_branch()` because the local branch is created at the remote HEAD position.

## Decision Tree

1. Does the branch exist locally?
   - Yes: Use `checkout_branch()`, then sync
   - No: Continue to step 2

2. Does the branch exist on remote?
   - Yes: Use `create_tracking_branch()` (no sync needed)
   - No: Use `create_branch()` to create fresh

See `src/erk/gateway/git.py` for BranchManager implementation.
```

---

#### 7. Document Detection Patterns architecture

**Location:** `docs/learned/architecture/detection-patterns.md`
**Action:** CREATE
**Source:** [PR #8280]

**Draft Content:**

```markdown
---
read-when:
  - implementing idempotency checks
  - working with plan-ref.json
  - understanding detection mechanism evolution
---

# Detection Patterns

## Overview

Erk uses detection patterns to determine existing state before performing operations. This document describes the evolution from branch-name-based detection to file-based detection.

## Historical: Branch Name Detection

**Old pattern (deprecated):**
- Parse branch name for prefix pattern like `P{issue_number}-*`
- Infer plan association from naming convention

**Problems:**
- Naming conventions can vary
- Requires string parsing with edge cases
- No explicit link to plan metadata

## Current: plan-ref.json Detection

**New pattern:**
- Check for `.impl/plan-ref.json` file
- Use `read_plan_ref()` to parse JSON content
- Explicit plan number and metadata stored in file

**Benefits:**
- File presence is unambiguous
- JSON content provides rich metadata
- Enables clear error messages with plan numbers
- Decouples branch naming from plan association

## Implementation

See `src/erk/impl_folder.py` for `read_plan_ref()` implementation.

## Tripwires

- Prefer file-based detection (`plan-ref.json`) over branch name parsing
- When adding new detection patterns, use explicit files over naming conventions
```

---

#### 8. Update command reference table with new/renamed commands

**Location:** `docs/learned/cli/erk-exec-commands.md`
**Action:** UPDATE
**Source:** [PR #8280]

**Draft Content:**

Add the following commands to the command reference table:

```markdown
## New Batch Commands

| Command | Description | Input |
|---------|-------------|-------|
| `add-plan-labels` | Add labels to multiple plans in batch | stdin JSON array of `{plan_number, label}` |
| `close-prs` | Close multiple plans with comments in batch | stdin JSON array of `{plan_number, comment}` |

## Renamed Commands

| Old Name | New Name |
|----------|----------|
| `close-issue-with-comment` | `close-pr` |
| `plan-update-issue` | `plan-update` |
| `setup-impl-from-issue` | `setup-impl-from-pr` |
| `issue-title-to-filename` | `plan-title-to-filename` |
| `create-issue-from-session` | `create-pr-from-session` |

All old names are removed with no aliases. Update all callers immediately.
```

---

### MEDIUM Priority

#### 9. Document PR review thread resolution workflow

**Location:** `docs/learned/pr-operations/thread-resolution-workflow.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - resolving PR review comments programmatically
  - automating PR review workflows
  - using get-pr-feedback and resolve-review-threads commands
---

# PR Review Thread Resolution Workflow

## Overview

This document describes the programmatic workflow for resolving PR review threads after addressing feedback.

## Pipeline

1. **Fetch feedback**: `erk exec get-pr-feedback --pr <number>`
2. **Extract thread IDs**: Parse JSON output for unresolved thread IDs
3. **Resolve threads**: Pipe thread IDs to `erk exec resolve-review-threads`

## Example

```bash
# Get feedback and extract unresolved thread IDs
erk exec get-pr-feedback --pr 8280 | python3 -c "
import json, sys
data = json.load(sys.stdin)
threads = [t['thread_id'] for t in data.get('threads', []) if not t.get('resolved')]
print(json.dumps(threads))
" | erk exec resolve-review-threads
```

## When to Use

Use this workflow after implementing PR review feedback to programmatically mark threads as resolved, avoiding manual clicking in the GitHub UI.

See implementation sessions for PR #8280 for practical usage examples.
```

---

#### 10. Document parallel explore agent pattern

**Location:** `docs/learned/planning/parallel-explore-agents.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - planning complex implementations
  - need to investigate multiple code areas
  - launching explore agents
---

# Parallel Explore Agents

## Overview

When planning implementations that touch multiple code areas, launch parallel explore agents to gather information simultaneously rather than sequentially investigating each area.

## Pattern

1. **Identify investigation areas**: List the distinct areas needing exploration
2. **Launch agents in parallel**: Use Task tool to spawn explore agents for each area
3. **Aggregate findings**: Collect results from all agents before planning
4. **Create unified plan**: Use aggregated findings to write comprehensive implementation plan

## Benefits

- Reduces total planning time (parallel vs sequential exploration)
- Each agent focuses on one area deeply
- Findings can cross-reference each other in the final plan

## Example Usage

For PR review addressing with 6 feedback items across doc files, test files, and .gitignore:
- Agent 1: Explore doc files needing updates
- Agent 2: Explore source file for test coverage
- Agent 3: Explore .gitignore history and constraints

## Tripwires

- Always instruct explore agents to check `docs/learned/index.md` first for relevant documentation
- Provide specific file paths or grep patterns to each agent for focused exploration
```

---

#### 11. Document design conflict escalation pattern

**Location:** `docs/learned/planning/design-conflict-escalation.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - PR reviewer feedback conflicts with recent design decisions
  - automated reviewers suggest reverting intentional changes
  - uncertain whether to implement review feedback
---

# Design Conflict Escalation

## Overview

When automated reviewers or PR feedback conflicts with recent intentional design decisions, escalate to the user rather than blindly implementing reviewer suggestions.

## Pattern

1. **Identify conflict**: Reviewer suggests X, but recent PR intentionally did opposite
2. **Research context**: Find the PR/objective that made the original decision
3. **Present options**: Use AskUserQuestion with context-rich options explaining the tradeoff
4. **Implement user choice**: Proceed with whichever option the user selects

## Example

Conflict: Reviewer says "restore .impl/ to .gitignore", but PR #8314 (Objective #8197) intentionally removed it.

Options presented:
- "Implement reviewer suggestion (revert that aspect of #8314)"
- "Reject feedback, explain the intentional design decision"

## Key Insight

Automated reviewers can flag legitimate concerns even when they conflict with recent PRs. The original design decision may have been wrong, or circumstances may have changed. User judgment is needed.

## When NOT to Escalate

- Obvious typos or mistakes
- Feedback that doesn't conflict with intentional decisions
- Style/formatting suggestions
```

---

#### 12. Document test infrastructure discovery workflow

**Location:** `docs/learned/testing/test-infrastructure-discovery.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - writing tests for exec scripts
  - need to understand test infrastructure
  - looking for existing test patterns to follow
---

# Test Infrastructure Discovery Workflow

## Overview

When writing tests for new code, follow this systematic discovery workflow to find existing patterns and infrastructure.

## Workflow

1. **Read source file**: Understand what needs testing - inputs, outputs, dependencies
2. **Find similar tests**: Glob for test files in the same directory or similar functionality
3. **Check fakes directory**: Look in `tests/fakes/` for fake implementations of dependencies
4. **Read fake implementations**: Understand constructor parameters and failure simulation modes
5. **Check context helpers**: Look for `context_for_test()` and similar test setup utilities

## Example: Testing exec scripts

```
1. Read: src/erk/cli/commands/exec/scripts/my_command.py
2. Glob: tests/unit/cli/commands/exec/scripts/test_*.py
3. Check: tests/fakes/ for FakeGitHubIssues, FakeClaudeInstallation, etc.
4. Read fake constructors to understand:
   - What parameters control behavior
   - How to simulate failures (e.g., username=None for auth failure)
   - Factory methods like for_test() for success modes
5. Use context_for_test() to wire up fakes
```

## Benefits

- Follows established patterns (consistency)
- Discovers available test infrastructure
- Avoids reinventing existing utilities
- Tests match project conventions
```

---

#### 13. Document parallel tool use for context gathering

**Location:** `docs/learned/architecture/parallel-tool-use.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - gathering context from multiple files
  - optimizing agent efficiency
  - reading related files
---

# Parallel Tool Use

## Overview

When gathering context from multiple related files, issue Read tool calls in parallel to reduce round trips and improve efficiency.

## Pattern

Instead of:
```
Read file A
Wait for response
Read file B
Wait for response
Read file C
Wait for response
```

Do:
```
Read file A, B, C in parallel
Wait for all responses
```

## When to Use

- Reading multiple doc files to understand current state
- Gathering context from source + test + config files
- Loading related modules before making changes

## Implementation Notes

- Claude's tool use supports parallel calls in a single response
- No explicit syntax needed - simply include multiple Read tool calls
- Particularly valuable when files are independent (no read-before-read dependency)

## Tripwires

- Don't parallelize when one file's content determines what to read next
- Do parallelize when files are mentioned in a plan or todo list
```

---

#### 14. Document fake configuration patterns

**Location:** `docs/learned/testing/fake-configuration-patterns.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - writing tests for exec scripts that use github_issues
  - writing tests for exec scripts that use claude_installation
  - setting up test context with gateway fakes
---

# Fake Configuration Patterns

## Overview

Erk's test fakes have specific configuration patterns for simulating success and failure modes. This document covers the non-obvious patterns.

## FakeGitHubIssues

### Authentication Failure Mode

```python
# username=None simulates authentication failure
fake = FakeGitHubIssues(username=None)
```

This causes operations to fail as if the user is not authenticated.

### Success Mode

```python
# Provide username for successful authentication
fake = FakeGitHubIssues(username="test-user")
```

## FakeClaudeInstallation

### Session-Scoped Plan Lookup

```python
# Use for_test() factory with plans dict keyed by session ID
fake = FakeClaudeInstallation.for_test(
    plans={"session-id-123": "plan content here"}
)
```

This enables `get_latest_plan(session_id="session-id-123")` to return the configured plan.

## context_for_test() Gateway Naming

When setting up test context, use the correct gateway parameter names:

```python
# CORRECT: github_issues (not github)
ctx = context_for_test(github_issues=fake_github_issues)

# WRONG: github
ctx = context_for_test(github=fake_github_issues)  # Won't work as expected
```

The `github_issues` gateway is separate from `github` - they serve different purposes.

## Tripwires

- When testing exec scripts with github_issues: Check FakeGitHubIssues constructor - username=None simulates auth failure
- When testing exec scripts with claude_installation: Use FakeClaudeInstallation.for_test(plans={...}) for session-scoped lookup
- When setting up test context: Use context_for_test(github_issues=...) not context_for_test(github=...)
```

---

#### 15. Document plan-update branch sync behavior

**Location:** `docs/learned/planning/plan-update-branch-sync.md`
**Action:** CREATE
**Source:** [PR #8280]

**Draft Content:**

```markdown
---
read-when:
  - using plan-update command
  - understanding plan sync to branches
  - debugging branch sync failures
---

# Plan Update Branch Sync

## Overview

The `plan-update` command includes best-effort branch synchronization that commits and pushes updated plan content to the associated branch.

## Flow

1. Find plan content (priority: `--plan-path` > session scratch > `~/.claude/plans/`)
2. Update plan content via PlanBackend
3. Extract title from plan H1, prepend title tag from labels
4. Update plan title via PlanBackend
5. Best-effort branch sync: commit + push to `.erk/impl-context/plan.md`

## Branch Detection

The command reads `BRANCH_NAME` from plan header fields to determine the target branch. If no branch field exists, branch sync is skipped.

## Non-Blocking Push Semantics

Branch sync failure does NOT fail the command. The primary operation (updating plan content on GitHub) succeeds even if the branch push fails. This prevents transient git issues from blocking plan updates.

## When Branch Sync Occurs

- Plan has `BRANCH_NAME` header field
- Branch exists locally or on remote
- User has push permissions

## Tripwires

- Use `plan-update` not the old `plan-update-issue` name
- Branch sync is best-effort - don't depend on it for critical workflows
```

---

#### 16. Document documentation audit protocol

**Location:** `docs/learned/refactoring/documentation-audit-protocol.md`
**Action:** CREATE
**Source:** [PR #8280]

**Draft Content:**

```markdown
---
read-when:
  - after renaming functions or files
  - after major refactoring
  - documentation seems stale
---

# Documentation Audit Protocol

## Overview

After renaming functions, files, or CLI commands, perform a systematic audit to update all documentation references. Documentation drift is the #1 cause of stale docs.

## Protocol

1. **Grep for old names** in all documentation locations:
   ```bash
   grep -r "old_name" --include="*.md" docs/ .claude/
   ```

2. **Check skill files**:
   ```bash
   grep -r "old_name" --include="*.md" .claude/skills/
   ```

3. **Check command files**:
   ```bash
   grep -r "old_name" --include="*.md" .claude/commands/
   ```

4. **Check test files** for outdated comments:
   ```bash
   grep -r "old_name" --include="*.py" tests/
   ```

5. **Update all references** found in steps 1-4

6. **Verify zero matches** after updates:
   ```bash
   grep -r "old_name" --include="*.md" --include="*.py" . | grep -v CHANGELOG
   ```

## Why This Matters

- Stale references confuse future agents
- Phantom file paths trigger false-positive warnings
- Inconsistent terminology undermines trust in docs

## Tripwires

- After renaming functions or files: Grep docs/, .claude/, and tests/ for all references to old names
- Update all references or documentation will drift
```

---

#### 17. Document CLI output reference

**Location:** `docs/learned/cli/command-output-reference.md`
**Action:** CREATE
**Source:** [PR #8280]

**Draft Content:**

```markdown
---
read-when:
  - documenting CLI command behavior
  - testing CLI output
  - updating docs with example outputs
---

# CLI Command Output Reference

## Overview

This document provides canonical output examples for key CLI commands. Use these to verify documentation accuracy and detect output drift.

## setup-impl-from-pr

### Existing Implementation Detected

```
Found existing .impl/ for plan #77, skipping branch setup
```

### Successful Setup

```json
{"success": true, "branch": "plnd/feature-xyz", "plan_path": ".impl/plan.md"}
```

## add-plan-labels (batch)

### Success Response

```json
{"success": true, "results": [{"plan_number": 123, "success": true, "label": "erk-learn"}]}
```

### Partial Failure

```json
{"success": false, "results": [{"plan_number": 123, "success": true, "label": "erk-learn"}, {"plan_number": 456, "success": false, "error": "Plan not found"}]}
```

## close-prs (batch)

### Success Response

```json
{"success": true, "results": [{"plan_number": 123, "success": true, "comment_id": "IC_abc123"}]}
```

## Maintenance

When command output changes, update this reference. If docs show different output, the docs need updating.
```

---

#### 18. Document removed sections protocol

**Location:** `docs/learned/documentation/removed-sections-protocol.md`
**Action:** CREATE
**Source:** [PR #8280]

**Draft Content:**

```markdown
---
read-when:
  - removing obsolete documentation
  - tracking what was deleted and why
  - auditing documentation changes
---

# Removed Sections Protocol

## Overview

When removing obsolete documentation sections, follow this protocol to maintain traceability and prevent accidental re-creation.

## Protocol

1. **Document what's being removed**: Note the section title and brief description
2. **Explain why it's obsolete**: Link to the PR or change that made it obsolete
3. **Check for incoming links**: Grep for references to the removed section
4. **Update or remove links**: Fix any docs that referenced the removed section
5. **Consider tombstone**: For frequently-referenced content, add a brief tombstone note

## Tombstone Format

When content was heavily referenced and might confuse readers looking for it:

```markdown
## [Section Name] (Removed)

This section was removed in PR #XXXX. The functionality it described was replaced by [new feature/pattern]. See [link to new docs].
```

## When to Skip Tombstones

- Content was rarely referenced
- Removal is part of broader reorganization with redirect
- Content was simply wrong (not obsolete)

## Tripwires

- Before deleting doc sections, grep for incoming references
- Consider tombstones for heavily-referenced removed content
```

---

#### 19. Document test exemption criteria

**Location:** `docs/learned/testing/test-exemption-criteria.md`
**Action:** CREATE
**Source:** [PR #8280]

**Draft Content:**

```markdown
---
read-when:
  - deciding whether to write tests
  - reviewing code without tests
  - understanding test policy exceptions
---

# Test Exemption Criteria

## Overview

Erk requires tests for new functionality, but some code legitimately doesn't need dedicated tests. This document defines the exemption criteria.

## Exempt Categories

### 1. Thin Wrappers

Functions that only delegate to a single tested function with no additional logic:

```python
def my_wrapper(x):
    return already_tested_function(x)
```

The underlying function has tests; the wrapper adds nothing testable.

### 2. Type Definitions

TypedDict, dataclass, and other pure type definitions don't need tests:

```python
class MyItem(TypedDict):
    name: str
    value: int
```

Type checkers validate these; runtime tests add no value.

### 3. Configuration Constants

Static configuration values don't need tests:

```python
DEFAULT_TIMEOUT = 30
ALLOWED_LABELS = ["bug", "feature", "docs"]
```

### 4. Re-exports

Modules that only re-export from other modules don't need tests.

## NOT Exempt

- Functions with any conditional logic
- Functions that transform data
- Functions that could fail in non-obvious ways
- Anything with side effects

## Tripwires

- When skipping tests, document which exemption category applies
- If in doubt, write the test
```

---

#### 20. Document batch operation exemplars

**Location:** `docs/learned/cli/batch-operation-exemplars.md`
**Action:** CREATE
**Source:** [PR #8280]

**Draft Content:**

```markdown
---
read-when:
  - creating batch variants of exec commands
  - implementing stdin JSON processing
  - looking for batch command patterns
---

# Batch Operation Exemplars

## Overview

`add_plan_labels.py` and `close_prs.py` are textbook implementations of the batch exec command contract. Use them as reference when creating new batch commands.

## What They Demonstrate

### LBYL Validation

Both implement `_validate_batch_input()` that:
- Checks `isinstance(data, list)` upfront
- Iterates with index tracking for error messages
- Validates each item's type and required fields
- Returns discriminated union: `list[ValidatedItem] | BatchError`

### Frozen Dataclasses for Results

- `BatchLabelResult` / `BatchCloseResult` for success tracking
- `BatchLabelError` / `BatchCloseError` for failure details
- All are frozen dataclasses (immutable after creation)

### Sequential Processing

- Process items one at a time (not parallel)
- Wrap each backend call in try/except
- Append success or failure to results list
- Continue processing even when individual items fail

### Exit Code Semantics

- Always exit 0 (success)
- Encode failures in JSON response
- Top-level `success` field indicates whether ALL items succeeded

## Source Files

- `src/erk/cli/commands/exec/scripts/add_plan_labels.py`
- `src/erk/cli/commands/exec/scripts/close_prs.py`

## Tripwires

- When creating batch commands, follow the patterns in these exemplar files
- When processing multiple plans in a loop, consider creating a batch command instead
```

---

### LOW Priority

#### 21. Update session ID forwarding pattern in exec-script-testing.md

**Location:** `docs/learned/testing/exec-script-testing.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

Add a section on testing session-scoped parameter forwarding:

```markdown
## Session ID Forwarding Tests

When testing exec scripts that accept `--session-id` and forward it to services:

1. Set up fake with session-scoped data:
   ```python
   fake = FakeClaudeInstallation.for_test(
       plans={"test-session-123": "plan content"}
   )
   ```

2. Invoke command with session ID:
   ```python
   result = runner.invoke(my_command, ["--session-id", "test-session-123"])
   ```

3. Verify correct data was retrieved (proves session ID was forwarded correctly)
```

---

#### 22. Update 2 references in cli-push-down.md

**Location:** `docs/learned/developer/agentic-engineering-patterns/cli-push-down.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `issue-title-to-filename`
**Cleanup Instructions:** Replace `issue-title-to-filename` with `plan-title-to-filename` (2 occurrences).

---

#### 23. Update 1 reference in planning/index.md

**Location:** `docs/learned/planning/index.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `setup-impl-from-issue`
**Cleanup Instructions:** Replace `setup-impl-from-issue` with `setup-impl-from-pr` (1 occurrence).

---

#### 24. Update 1 reference in plan-execution-patterns.md

**Location:** `docs/learned/planning/plan-execution-patterns.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `setup-impl-from-issue`
**Cleanup Instructions:** Replace `setup-impl-from-issue` with `setup-impl-from-pr` (1 occurrence).

---

#### 25. Update 2 references in command-composition.md

**Location:** `docs/learned/architecture/command-composition.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `setup-impl-from-issue`
**Cleanup Instructions:** Replace `setup-impl-from-issue` with `setup-impl-from-pr` (2 occurrences).

---

#### 26. Update 1 reference in issue-reference-flow.md

**Location:** `docs/learned/architecture/issue-reference-flow.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `setup-impl-from-issue`
**Cleanup Instructions:** Replace `setup-impl-from-issue` with `setup-impl-from-pr` (1 occurrence).

---

#### 27. Code: TypedDict definitions belong in source

**Location:** N/A (code change, not documentation)
**Action:** CODE_CHANGE
**Source:** [PR #8280]

**Code Change Description:**

The `PlanLabelItem` and `PlanCloseItem` TypedDict definitions in `add_plan_labels.py` and `close_prs.py` are correctly placed in the source code. No documentation needed for type definitions - they are self-documenting through their field names and type annotations.

This item is recorded to confirm the decision: type artifacts belong in code, not in documentation files.

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Documentation Drift After Rename

**What happened:** After renaming 5 exec scripts, 7+ documentation files still referenced the old file names, and multiple behavior descriptions no longer matched actual code.

**Root cause:** No systematic audit step after renaming functions/files. The rename was mechanical (find/replace in source), but documentation wasn't systematically checked.

**Prevention:** After any rename, run the Documentation Audit Protocol: grep all docs, skills, commands, and tests for old names. Update all references before marking the rename complete.

**Recommendation:** TRIPWIRE - Add to `docs/learned/refactoring/tripwires.md`

### 2. Branch Operation Semantic Confusion

**What happened:** Documentation claimed `setup_impl_from_pr()` calls `create_branch()`, but it actually uses `create_tracking_branch()` or `checkout_branch()` depending on branch state.

**Root cause:** BranchManager has three distinct operations with different semantics, but no reference doc explaining when to use each.

**Prevention:** Document the Branch Manager operations reference with clear decision tree.

**Recommendation:** ADD_TO_DOC - Create `docs/learned/architecture/branch-manager-operations-reference.md`

### 3. Detection Pattern Architecture Shift

**What happened:** Docs described branch-name prefix matching for detection, but code now uses `.impl/plan-ref.json` file-based detection.

**Root cause:** Architectural shift happened incrementally without corresponding documentation update.

**Prevention:** When shifting architectural patterns, update all docs that reference the old pattern in the same PR.

**Recommendation:** ADD_TO_DOC - Create `docs/learned/architecture/detection-patterns.md`

### 4. Commit Scope Creep

**What happened:** A staged file (`.impl/plan.md`) was accidentally included in a commit intended for different changes.

**Root cause:** Relying on pre-staged content without verifying before commit.

**Prevention:** Run `git status` before each commit to verify exactly what will be included. Consider `git add <specific-files>` instead of committing pre-staged content.

**Recommendation:** CONTEXT_ONLY - Low severity, agent recovered pragmatically

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. FakeGitHubIssues username=None simulates auth failure

**Score:** 5/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +1)
**Trigger:** Before writing tests for exec scripts that use github_issues
**Warning:** Check FakeGitHubIssues constructor - username=None simulates authentication failure, not "no username"
**Target doc:** `docs/learned/testing/fake-configuration-patterns.md`

This pattern is non-obvious because `username=None` looks like "no user configured" but actually triggers authentication failure mode. Tests expecting success with no username will fail silently or with confusing errors.

### 2. FakeClaudeInstallation.for_test() session-scoped lookup

**Score:** 5/10 (criteria: Non-obvious +2, Cross-cutting +2, External tool quirk +1)
**Trigger:** Before writing tests for exec scripts that use claude_installation
**Warning:** Use FakeClaudeInstallation.for_test(plans={'session_id': 'content'}) - the plans dict is keyed by session ID for get_latest_plan() lookup
**Target doc:** `docs/learned/testing/fake-configuration-patterns.md`

The factory method's plans parameter structure isn't obvious from the name. Tests that don't use the correct key structure will get unexpected None results.

### 3. context_for_test(github_issues=...) not github

**Score:** 4/10 (criteria: Non-obvious +2, Cross-cutting +2)
**Trigger:** Before setting up test context with github_issues
**Warning:** Use context_for_test(github_issues=...) not context_for_test(github=...) - issues is a separate gateway from github
**Target doc:** `docs/learned/testing/fake-configuration-patterns.md`

Easy mistake because "github" seems like it should work. The gateway separation is a design decision that isn't obvious to newcomers.

### 4. Stale references after function/file rename

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Repeated pattern +1, Silent failure +2)
**Trigger:** After renaming functions or files
**Warning:** Grep docs/, .claude/, and tests/ for all references to old names. Update all or documentation will drift silently.
**Target doc:** `docs/learned/refactoring/documentation-audit-protocol.md`

This is the highest-scoring tripwire because documentation drift is silent (no CI failures), affects many files, and has repeated multiple times. The PR that prompted this learn plan found 7+ stale references.

---

## Potential Tripwires

Items with score 2-3 (may warrant tripwire status with additional context):

### 1. Branch operation semantics (create vs checkout vs track)

**Score:** 3/10 (criteria: Non-obvious +2, External tool quirk +1)
**Notes:** Currently addressed via documentation (Branch Manager Operations Reference). May become tripwire if pattern repeats in future implementations. Watch for confusion in future PRs touching branch operations.

### 2. Best-effort branch sync in plan-update

**Score:** 2/10 (criteria: Non-obvious +2)
**Notes:** Command-specific behavior, may not be cross-cutting enough for tripwire. The non-blocking semantics could surprise users expecting sync to be required. Monitor for user confusion.

### 3. Detection pattern shift (branch-name to plan-ref.json)

**Score:** 3/10 (criteria: Non-obvious +2, External tool quirk +1)
**Notes:** Architectural shift worth documenting but may not need tripwire if the Detection Patterns doc is comprehensive enough. Tripwire warranted if agents continue writing branch-name detection code.

---

## Implementation Strategy

Recommended order for addressing gaps:

### Phase 1: Fix Stale References (HIGH priority items 1-8)

- Bulk update all phantom references to old file names
- Fix incorrect behavior descriptions
- Update detection pattern docs
- **Outcome:** Existing docs accurate with current code

### Phase 2: Document Architecture Shifts (HIGH priority items 5-7)

- Planned-PR branch detection
- Branch Manager operations reference
- Detection patterns evolution
- **Outcome:** Architectural decisions documented

### Phase 3: Document New Patterns (MEDIUM priority items 9-16)

- PR review workflows
- Testing patterns
- Parallel tool use
- Fake configuration
- Plan-update branch sync
- **Outcome:** New patterns reusable by future agents

### Phase 4: Process Improvements (MEDIUM priority items 16-20)

- Documentation audit protocol
- Removed sections protocol
- Test exemption criteria
- Batch operation exemplars
- **Outcome:** Process improvements prevent future drift

### Phase 5: Minor Updates (LOW priority items 21-27)

- Individual reference updates in various docs
- **Outcome:** All docs fully accurate
