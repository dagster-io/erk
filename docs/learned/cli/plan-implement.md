---
title: Plan-Implement Workflow
read_when:
  - "understanding the /erk:plan-implement command"
  - "implementing plans from GitHub issues"
  - "working with .impl/ folders"
  - "debugging plan execution failures"
tripwires:
  - action: "editing or deleting .impl/ folder during implementation"
    warning: ".impl/plan.md is immutable during implementation. Never edit it. Never delete .impl/ folder - it must be preserved for user review. Only .worker-impl/ should be auto-deleted."
  - action: "committing .impl/ folder to git"
    warning: ".impl/ lives in .gitignore and should never be committed. Only .worker-impl/ (remote execution artifact) gets committed and later removed."
  - action: "skipping session upload after local implementation"
    warning: "Local implementations must upload session via capture-session-info + upload-session. This enables async learn workflow. See session upload section below."
---

# Plan-Implement Workflow

The `/erk:plan-implement` command orchestrates plan execution from setup through PR submission. Understanding its decision trees and cleanup discipline prevents common failure modes.

## Core Execution Pattern

The command follows a priority-based source resolution pattern that determines where the plan comes from:

### Source Resolution Priority

**Priority 1: Explicit argument**

- Issue number → Fetch from GitHub, create branch, setup `.impl/`
- File path → Local plan, create branch from file, no issue tracking
- Empty → Fall through to Priority 2

**Priority 2: Existing `.impl/` folder**

- Valid folder → Skip setup, proceed directly to implementation
- Invalid folder → Fall through to Priority 3

**Priority 3: Current plan mode session**

- Save plan to GitHub issue → Setup from new issue → Implement

This priority order prevents destructive operations (saving plans when `.impl/` exists) and enables flexible workflow restart.

## `.impl/` vs `.worker-impl/` Distinction

The system uses two folders with fundamentally different lifecycles:

| Aspect         | `.impl/`                      | `.worker-impl/`                  |
| -------------- | ----------------------------- | -------------------------------- |
| **Context**    | Local + remote (Claude reads) | Remote only (GitHub Actions)     |
| **Git Status** | In `.gitignore`, never staged | Committed, then auto-deleted     |
| **Lifecycle**  | Preserved forever for review  | Transient, deleted after CI pass |
| **Cleanup**    | Manual user action only       | Automatic after validation       |

**Why this matters:** Agents commonly violate the preservation contract by deleting `.impl/` during implementation. The `impl-verify` command exists as a guardrail to catch this violation.

### Remote Execution Flow

In GitHub Actions workflow:

1. `.worker-impl/` is committed to branch (for git-based transport)
2. Workflow copies `.worker-impl/` → `.impl/` (Claude's read location)
3. Claude executes with `.impl/` folder
4. After CI passes, workflow removes `.worker-impl/` in separate commit
5. `.impl/` is never committed (stays local-only in workflow runner)

<!-- Source: src/erk/cli/commands/exec/scripts/impl_verify.py, impl_verify() -->

The distinction exists because `.worker-impl/` is a git-based transport mechanism while `.impl/` is Claude's working directory.

## Session Upload for Async Learn

Local implementations must upload the session to enable `erk learn --async`. This isn't optional — it's what makes the learn workflow work for local PRs.

### Why Session Upload Exists

Without session upload:

- Learn workflow requires manual session file handling
- No consistent session storage location
- Async learn can't find the session for locally-implemented PRs

With session upload:

- Session stored in GitHub Gist (linked to issue)
- Learn workflow finds session via issue metadata
- Local and remote implementations treated uniformly

### Implementation Pattern

<!-- Source: .claude/commands/erk/plan-implement.md, Step 10b -->

The command uses `capture-session-info` to extract session ID and file path from Claude's project directory, then uploads via `upload-session` with issue linking:

See `capture_session_info()` in `src/erk/cli/commands/exec/scripts/capture_session_info.py` for session discovery logic.

**Critical detail:** Session upload happens **after** implementation completes but **before** `.worker-impl/` cleanup. This ensures the session capture reflects the complete implementation.

## Common Failure Patterns

### File-Based Plans Lack Issue Tracking

When implementing from a markdown file (not a GitHub issue), `impl-init` returns `has_issue_tracking: false`. This means:

- No PR-to-issue linking (`get-closing-text` returns empty)
- No GitHub comments (impl-signal silently no-ops)
- PR won't auto-close an issue on merge

This is **by design** — file-based plans are for throwaway experiments, not tracked work.

### Skipped Setup Phase Confusion

When `.impl/` already exists and is valid, the command skips directly to implementation. This causes confusion when:

- User expects fresh plan fetch from GitHub (stale `.impl/plan.md`)
- Issue was updated but `.impl/` contains old version
- Branch name doesn't match current issue

**Solution:** Delete `.impl/` folder to force setup phase re-execution.

### Hook Overrides for CI

The post-implementation CI phase checks for `.erk/prompt-hooks/post-plan-implement-ci.md`. If present, it replaces the default AGENTS.md CI instructions. This allows per-project customization of CI validation.

<!-- Source: .claude/commands/erk/plan-implement.md, Step 12 -->

Hook-based CI override exists because different projects need different validation sequences (some skip integration tests, others require specific linters).

## Phase Timing Characteristics

Different phases have vastly different completion times:

| Phase                 | Typical Duration | Blocking Factor                  |
| --------------------- | ---------------- | -------------------------------- |
| Setup (issue fetch)   | 2-5 seconds      | GitHub API latency               |
| Setup (branch create) | <1 second        | Local git operation              |
| Implementation        | 5 mins - 2 hours | Plan complexity, codebase size   |
| CI verification       | 2-10 minutes     | Test suite size, iteration count |
| PR creation           | 5-10 seconds     | GitHub API latency               |

**Why this matters:** When debugging hangs, knowing expected phase duration helps identify where to investigate (network vs code execution vs test infrastructure).

## Cleanup Discipline Anti-Patterns

### Anti-Pattern: Deleting `.impl/` After CI Passes

**WRONG:**

```bash
git rm -rf .impl/
git commit -m "Clean up after implementation"
```

**Why wrong:** `.impl/` is in `.gitignore` (never staged), so this command fails. More importantly, `.impl/` must be preserved for user review of what-was-planned vs what-was-implemented.

**Correct:** Only delete `.worker-impl/` (committed artifact), never `.impl/` (gitignored artifact).

### Anti-Pattern: Committing `.impl/` for "Documentation"

**WRONG:**

```bash
git add -f .impl/plan.md  # Force-add ignored file
git commit -m "Add implementation plan"
```

**Why wrong:** `.impl/` is agent working state, not documentation. Plans live in GitHub issues. Forcing gitignored files into commits creates confusion about source of truth.

**Correct:** Link PR body to plan issue (`**Plan:** #123`). Issue is the documentation.

## Signal Events and Plan File Lifecycle

The `impl-signal started` command has a side effect that's easy to miss: it deletes the Claude plan file from `~/.claude/plans/`.

<!-- Source: src/erk/cli/commands/exec/scripts/impl_signal.py, _delete_claude_plan_file() -->

This happens because:

1. Plan content has been saved to GitHub issue (permanent storage)
2. Plan content has been snapshotted to `.erk/scratch/` (backup)
3. Keeping the file could cause confusion if user tries to re-save

The deletion is **intentional cleanup**, not data loss.

## Stacked Branch Behavior

When implementing from a feature branch (not trunk), the new branch is stacked on the current branch:

```
main
  └── feature-a (current)
        └── feature-b (new plan implementation)
```

<!-- Source: src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py, _is_trunk_branch() -->

This is determined by trunk detection: branches named "main" or "master" are trunk, everything else is a feature branch. Stacking happens automatically — no configuration needed.

**Implication:** Plan implementation from feature branches creates Graphite-compatible stacks. The branch manager abstraction handles Graphite tracking automatically.

## Related Documentation

- [Plan Lifecycle](../planning/lifecycle.md) - Complete plan states and transitions across all phases
- [Planning Workflow](../planning/workflow.md) - `.impl/` folder structure and file contracts
- [Branch Manager Abstraction](../architecture/branch-manager-abstraction.md) - How branch creation delegates to Graphite when available
