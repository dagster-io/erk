---
title: erk pr summarize Command
read_when:
  - "generating AI commit messages for existing commits"
  - "amending commit messages with plan context"
  - "understanding pr summarize vs pr submit"
---

# erk pr summarize Command

Generates an AI-powered commit message and amends the current commit. This is the local-only variant of `erk pr submit` - it updates your commit message without creating or updating a PR.

## Why This Command Exists

**Problem**: You've made a commit but the message is generic or doesn't capture the full context. You want an AI-generated message that incorporates plan context, but you're not ready to push yet.

**Solution**: `pr summarize` analyzes your branch's diff against its parent, generates a commit message (with plan context if available), and amends your current commit.

## Usage Pattern

```bash
# Must have exactly 1 commit ahead of parent
erk pr summarize

# With debug output
erk pr summarize --debug
```

**Pre-requisite**: Exactly one commit ahead of parent branch. If you have multiple commits, run `gt squash` first.

<!-- Source: src/erk/cli/commands/pr/summarize_cmd.py, _execute_pr_summarize -->

The command enforces single-commit state at summarize_cmd.py:80-90. This constraint matches Graphite's stack model - one commit per PR.

## Three-Phase Execution

The command mirrors `pr submit`'s structure but stops before pushing:

### Phase 1: Get Diff

Extracts the diff between current branch and parent using the shared `execute_diff_extraction` pipeline. Sets `pr_number=0` as a placeholder since no PR exists yet (see summarize_cmd.py:186).

### Phase 2: Generate Commit Message

Uses `CommitMessageGenerator` with identical context priority to `pr submit`:

1. **Plan context** - From linked erk-plan issue (highest priority)
2. **Objective context** - From parent objective if plan is linked
3. **Commit messages** - Not used in summarize (only in submit with multiple commits)

<!-- Source: src/erk/core/commit_message_generator.py, CommitMessageGenerator._build_context_section -->

The generator places plan content before commit messages in the prompt (commit_message_generator.py:207-227), making it the primary source of truth for WHY the changes exist.

### Phase 3: Amend Commit

Combines title and body into a single commit message and amends the current commit via `git.commit.amend_commit()`.

## Plan Context Integration

<!-- Source: src/erk/cli/commands/pr/summarize_cmd.py, plan context feedback (lines 120-131) -->

When a branch follows the `P{issue_number}-{slug}` naming convention, the command automatically fetches plan context from the linked erk-plan issue.

**Feedback styling:**

- Plan found: Green text showing issue number and optional objective
- No plan: Dimmed text "No linked plan found"

This feedback pattern is standardized across `pr summarize` and `pr submit` - both commands use identical styling when incorporating plan context.

## Context Priority Decision

<!-- Source: src/erk/core/commit_message_generator.py, _build_context_section -->

**Why plan context takes priority over commit messages:**

When both exist, the plan is placed first in the prompt to Claude (commit_message_generator.py:207-227). This ordering reflects reality: the plan describes the intended outcome, while commit messages describe incremental implementation steps.

For `pr summarize`, commit messages are never included in the request (summarize_cmd.py:140 passes `commit_messages=None`). This is correct - you're amending the single commit, so its current message is being replaced, not incorporated.

## Anti-Pattern: Summarizing Multi-Commit Branches

**WRONG**: Running `pr summarize` with multiple commits ahead of parent

**WHY**: The command can only amend the most recent commit. If you have 3 commits, it would generate a message describing all changes but only amend the last commit, creating a mismatch.

**CORRECT**: Run `gt squash` first to combine commits, then `pr summarize`.

<!-- Source: src/erk/cli/commands/pr/summarize_cmd.py, lines 86-90 -->

The enforcement at summarize_cmd.py:86-90 prevents this anti-pattern. It suggests `gt squash` explicitly in the error message.

## Relationship to pr submit

| Aspect                   | pr summarize        | pr submit                     |
| ------------------------ | ------------------- | ----------------------------- |
| Creates PR               | ❌ No               | ✅ Yes                        |
| Amends commit            | ✅ Yes              | ✅ Yes (before pushing)       |
| Accepts multiple commits | ❌ No (enforced)    | ✅ Yes (squashes them)        |
| Plan context             | ✅ Yes              | ✅ Yes                        |
| Commit message context   | ❌ No (passes None) | ✅ Yes (includes all commits) |

Both commands use the same `CommitMessageGenerator` and `PlanContextProvider` classes. The difference is what happens after generation:

- `pr summarize` stops after amending
- `pr submit` continues to push and create/update PR

## When to Use Which Command

| Scenario                                      | Use                                   |
| --------------------------------------------- | ------------------------------------- |
| Want AI commit message, not ready to push     | `pr summarize`                        |
| Ready to create PR on Graphite                | `pr submit`                           |
| PR already exists, want to update description | `pr submit` (it updates existing PRs) |
| Just want to fix typo in commit message       | `git commit --amend` (no need for AI) |

## Related Documentation

- [PR Submit Phases](../../pr-operations/pr-submit-phases.md) - Full workflow for PR creation
- [Commit Message Generation](../../pr-operations/commit-message-generation.md) - How context priority works
- [Plan Context Integration](../../architecture/plan-context-integration.md) - How PlanContextProvider extracts plan content
