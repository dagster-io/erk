# Documentation Plan: Restore --oauth flag and refactor plan listing infrastructure

## Context

PR #7938 implemented a significant enhancement to erk's authentication management by restoring the `--oauth` flag to the `erk admin gh-actions-api-key` command and extending the GitHubAdmin gateway to support GitHub repository variables. The implementation demonstrates several patterns that future agents would benefit from knowing: the 5-place gateway ABC extension pattern, the multi-secret status display pattern with precedence-based active marking, and the enable-deletes-alternative pattern for mutually exclusive configuration options.

Beyond the core OAuth functionality, this PR also introduced the `/local:review` slash command for running code reviews locally, enhanced the pr-address workflow with session tracking capabilities, and improved UX with progress indicators for git lock waiting and workflow polling. The TUI was cleaned up by removing the `copy_implement_local` command that was deemed redundant.

Documentation matters because the gateway extension pattern requires updating 5 places (ABC, Real, Fake, Noop, Printing) and tests - a non-obvious requirement that should be a tripwire. The OAuth flag's precedence behavior (API key takes precedence over OAuth token) and auto-deletion of conflicting secrets are not discoverable from the code alone.

## Raw Materials

Session analysis and diff analysis generated from PR #7938.

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 10    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 2     |
| Potential tripwires (score2-3) | 3     |

## Documentation Items

### HIGH Priority

#### 1. GitHubAdmin Gateway: Repository Variables Support

**Location:** `docs/learned/integrations/github-variables.md`
**Action:** CREATE
**Source:** [PR #7938]

**Draft Content:**

```markdown
---
read-when:
  - adding methods to GitHubAdmin gateway
  - working with GitHub repository variables
  - storing non-sensitive configuration in GitHub repos
tripwires: 1
---

# GitHub Repository Variables

## Overview

GitHub repository variables provide storage for non-sensitive configuration values, distinct from secrets which are for sensitive data like API keys.

## When to Use Variables vs Secrets

- **Variables**: Non-sensitive configuration (feature flags, version numbers, configuration strings)
- **Secrets**: Sensitive data (API keys, tokens, passwords)

## Gateway Methods

The GitHubAdmin gateway provides two methods for variable management:

- `get_variable(repo, name)` - Retrieves a variable's value, returns None on error (graceful degradation)
- `set_variable(repo, name, value)` - Sets or updates a variable's value

## Implementation References

See `packages/erk-shared/src/erk_shared/gateway/github_admin/abc.py` for the ABC definition.
See `packages/erk-shared/src/erk_shared/gateway/github_admin/real.py` for the real implementation using gh CLI.

## 5-Place Update Requirement

CRITICAL: Adding methods to GitHubAdmin requires updating 5 places. See `docs/learned/architecture/gateway-abc-implementation.md` for the complete checklist.
```

---

#### 2. Admin Command: OAuth Token Management

**Location:** `docs/learned/cli/admin-oauth-token.md`
**Action:** CREATE
**Source:** [Impl], [PR #7938]

**Draft Content:**

```markdown
---
read-when:
  - working with erk admin gh-actions-api-key command
  - managing Claude Code authentication in GitHub Actions
  - understanding OAuth vs API key authentication
tripwires: 0
---

# OAuth Token Management

## Overview

The `erk admin gh-actions-api-key` command manages authentication secrets for Claude Code in GitHub Actions. It supports two authentication methods: ANTHROPIC_API_KEY and CLAUDE_CODE_OAUTH_TOKEN.

## The --oauth Flag

The `--oauth` flag switches the command to manage CLAUDE_CODE_OAUTH_TOKEN instead of ANTHROPIC_API_KEY.

## Precedence Rules

When both secrets exist, ANTHROPIC_API_KEY takes precedence over CLAUDE_CODE_OAUTH_TOKEN.

## Enable-Deletes-Alternative Pattern

When enabling one secret type, the command automatically deletes the alternative secret to prevent ambiguity. This is the "enable-deletes-alternative" pattern for mutually exclusive configuration.

## Status Display

The status command shows a table with both secrets, including:
- GitHub secret status (enabled/disabled)
- Local environment variable presence
- Active indicator based on precedence

## Implementation References

See `src/erk/cli/commands/admin.py` for implementation details. Grep for `_SecretConfig` and `_resolve_secret_config`.
```

---

#### 3. Slash Command: /local:review

**Location:** `docs/learned/commands/local-review.md`
**Action:** CREATE
**Source:** [PR #7938]

**Draft Content:**

```markdown
---
read-when:
  - running code reviews locally
  - testing review logic before CI
  - understanding the /local:review command
tripwires: 0
---

# /local:review Command

## Overview

The `/local:review` command replicates the CI code review experience locally, enabling faster iteration on review configurations.

## Three-Phase Workflow

1. **Discover files**: Find all files changed in the current branch
2. **Match reviews**: Determine which review definitions apply to changed files
3. **Run in parallel**: Execute applicable reviews via Task agents

## Output Location

Results are written to `.erk/scratch/<run-id>/`.

## Scope Differences from CI

The local command skips PR-interaction steps:
- No PR comments posted
- No activity logs updated
- Pure review logic execution

## Implementation References

See `.claude/commands/local/review.md` for the command definition.
```

---

### MEDIUM Priority

#### 4. Workflow Enhancement: Remote Implementation Tracking

**Location:** `docs/learned/ci/remote-impl-tracking.md`
**Action:** CREATE
**Source:** [PR #7938]

**Draft Content:**

```markdown
---
read-when:
  - working with pr-address workflow
  - tracking AI agent implementation sessions
  - understanding plan header metadata
tripwires: 0
---

# Remote Implementation Tracking

## Overview

The pr-address workflow tracks AI agent implementation sessions by uploading session files to the branch and updating plan header metadata.

## Captured Data

- Session ID
- Run ID
- Branch name
- Timestamp

## Workflow Steps

1. **Capture session info**: Extract session metadata during implementation
2. **Upload session**: Commit session files to the branch
3. **Update plan header**: Add remote impl metadata to plan header

## Use Case

Enables post-hoc analysis of AI agent implementation sessions and linking completed work back to the implementing agent.

## Implementation References

See `.github/workflows/pr-address.yml` for the workflow definition. Grep for "Capture session ID", "Upload session", "Update plan header".
```

---

#### 5. Multi-Secret Status Display Pattern

**Location:** `docs/learned/cli/multi-secret-display-pattern.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - building CLI commands that show multiple related secrets
  - implementing status displays with precedence indicators
tripwires: 0
---

# Multi-Secret Status Display Pattern

## Overview

A reusable pattern for CLI commands that need to display the status of multiple related secrets or configuration options with precedence rules.

## Table Format

Display multiple secrets in a single table view with columns:
- Secret name
- GitHub status (enabled/disabled)
- Local environment variable (present/absent)
- Active indicator (which one takes effect)

## Precedence Computation

Use a dedicated function (pattern: `_compute_active_label()`) to determine which secret is active based on precedence rules.

## Implementation References

See `src/erk/cli/commands/admin.py` for an example implementation. Grep for `_compute_active_label`.
```

---

#### 6. UX Improvements: Progress Indicators

**Location:** `docs/learned/ux/progress-indicators.md`
**Action:** CREATE
**Source:** [PR #7938]

**Draft Content:**

```markdown
---
read-when:
  - adding long-running operations that may appear to hang
  - debugging reports of "hanging" operations
  - implementing user feedback during waits
tripwires: 0
---

# Progress Indicators

## Overview

Long-running operations should provide user feedback to prevent confusing silent pauses.

## Git Lock Waiting

When waiting for `git index.lock` to be released:
- Print message once: "Waiting for git index.lock to be released..."
- Do not spam repeated messages

See `packages/erk-shared/src/erk_shared/gateway/git/lock.py` for implementation.

## Workflow Trigger Polling

When waiting for a workflow run to start:
- Show attempt count: "Waiting for workflow run... (attempt X/15)"
- Enables user to know progress and total attempts

See `packages/erk-shared/src/erk_shared/gateway/github/real.py` for implementation.

## Pattern

For any operation that may take >5 seconds, provide a one-time message indicating what the system is waiting for.
```

---

#### 7. TUI Removal: copy_implement_local Command

**Location:** `docs/learned/tui/removed-features.md`
**Action:** CREATE
**Source:** [PR #7938]

**Draft Content:**

```markdown
---
read-when:
  - looking for removed TUI commands
  - understanding TUI command evolution
tripwires: 0
---

# Removed TUI Features

## copy_implement_local Command (PR #7938)

**Removed components:**
- `copy_implement_local` command from command palette
- `i` key binding from TUI app
- Related UI elements from plan detail screen

**Rationale:** Command was deemed redundant after workflow changes. The local implementation workflow is now handled through other mechanisms.

## Historical Context

This command previously allowed copying a plan's implementation context for local execution. Its removal reflects the evolution toward more streamlined workflows.
```

---

### LOW Priority

#### 8. .erk/impl-context/ Cleanup Timing

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## .erk/impl-context/ Cleanup

Before starting implementation, verify `.erk/impl-context/` is cleaned up from git tracking:

- **Timing**: Step 2d in setup process, all setup paths converge here
- **Command**: `git rm -rf .erk/impl-context/ && git commit && git push`
- **Idempotency**: Safe to run even if directory doesn't exist
- **Convergence**: Issue-based, file-based, and existing .impl/ paths all require this step
```

---

## Contradiction Resolutions

None detected. All existing documentation is internally consistent and has verified references.

## Stale Documentation Cleanup

None detected. All referenced code artifacts in existing documentation still exist.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Git Push Non-Fast-Forward After Cleanup

**What happened:** Local branch was behind remote after cleanup commits, causing push rejection.
**Root cause:** Cleanup commits were made locally without first syncing with remote.
**Prevention:** Always `git pull --rebase` before pushing after making cleanup commits in plan-implement workflow.
**Recommendation:** ADD_TO_DOC

### 2. Graphite Branch Divergence on PR Submit

**What happened:** `erk pr submit` failed with "diverged branch" error after git operations outside Graphite.
**Root cause:** Rebases or other git operations caused branch to diverge from Graphite tracking.
**Prevention:** Run `gt track --no-interactive <branch>` to re-establish tracking.
**Recommendation:** TRIPWIRE

### 3. Format Check Failure After Manual Line Breaks

**What happened:** After manually breaking long lines to fix ruff E501, format check failed.
**Root cause:** Manual line breaks don't always match ruff's formatting preferences.
**Prevention:** Always run `make format` after manual line-length fixes, before running fast-ci.
**Recommendation:** ADD_TO_DOC

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. GitHubAdmin ABC Extension Requires 5-Place Updates

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Destructive potential +2)
**Trigger:** Before adding methods to GitHubAdmin ABC
**Warning:** CRITICAL: Must update 5 places: (1) ABC definition (abc.py), (2) Real implementation (real.py), (3) Fake implementation (fake.py), (4) Noop wrapper (noop.py), (5) Printing wrapper (printing.py). Plus integration tests. Example: get_variable() and set_variable() in PR #7938.
**Target doc:** `docs/learned/architecture/tripwires.md`

This is tripwire-worthy because forgetting any of the 5 places causes runtime errors or test failures. The pattern is not discoverable from a single file and requires cross-file awareness. PR #7938 demonstrates the complete pattern with the variables support addition.

### 2. Graphite Divergence on PR Submit Requires gt track

**Score:** 5/10 (criteria: Non-obvious +2, Cross-cutting +2, External tool quirk +1)
**Trigger:** When erk pr submit fails with "diverged branch" error
**Warning:** Run `gt track --no-interactive <branch>` to re-establish Graphite tracking. This error is expected after rebases or git operations outside Graphite.
**Target doc:** `docs/learned/erk/tripwires.md`

This is tripwire-worthy because the error message doesn't suggest the solution, and the fix is counterintuitive (tracking an already-tracked branch). It occurs frequently after standard git operations like rebasing.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Rebase vs Merge on Plan Sync

**Score:** 3/10 (criteria: Non-obvious +2, Repeated pattern +1)
**Notes:** When syncing plan branch with remote, use `git pull --rebase` instead of `git pull`. Rebase avoids merge commits and cleans up duplicate commits. The session showed git warning "skipped previously applied commit" during rebase, indicating duplicates were cleaned up. May warrant tripwire if this causes confusion repeatedly.

### 2. Format Check After Manual Line Breaks

**Score:** 2/10 (criteria: Repeated pattern +1, Cross-cutting +1)
**Notes:** After manually fixing ruff E501 line-length violations, always run `make format` to apply consistent formatting. The manual fixes may not match ruff's preferred style. Low score because the error is caught by fast-ci and fix is straightforward.

### 3. .erk/impl-context/ Cleanup Before Implementation

**Score:** 3/10 (criteria: Cross-cutting +2, Repeated pattern +1)
**Notes:** All setup paths converge at the cleanup step for `.erk/impl-context/`. Already documented in planning workflow, but may need more prominent placement if agents skip this step. The command is idempotent so safe to run always.
