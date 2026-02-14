# Documentation Plan: Migrate admin.py to Ensure-Based Error Handling

## Context

PR #6860 migrated `admin.py` from manual error handling (`user_output() + SystemExit(1)`) to the Ensure-based pattern (`Ensure.not_none()`, `Ensure.invariant()`, `UserFacingCliError`). This was step 1C.2 of Objective #5185. The migration converted 8 error patterns across two CLI commands (`github_pr_setting` and `test_plan_implement_gh_workflow`), added 9 fake-driven tests in two new test files, and removed the direct `RealGitHubAdmin` import in favor of context-injected `ctx.github_admin`.

The core Ensure/UserFacingCliError/discriminated-union patterns are already well-documented in three existing files: `error-handling-antipatterns.md`, `ensure-ideal-pattern.md`, and `discriminated-union-error-handling.md`. However, those docs contain phantom file references (wrong paths, references to deleted files), the migration status count is stale, and several secondary documentation gaps emerged: admin-specific test patterns with `FakeGitHubAdmin`, multi-line error message conventions, and planning workflow patterns (objective roadmap integration, review PR creation, pre-plan context gathering).

The implementation session also demonstrated effective patterns for plan-mode workflows: parallel context gathering before entering plan mode, marker-based session state management, and the complete plan submission lifecycle (save, review PR, submit for remote implementation). These workflow patterns are undocumented despite being well-established.

## Raw Materials

https://gist.github.com/schrockn/cf52e11185652e38a173ceb2dfb5fb8a

## Summary

| Metric                    | Count |
| ------------------------- | ----- |
| Documentation items       | 8     |
| Contradictions to resolve | 0     |
| Tripwires to add          | 3     |

## Documentation Items

### HIGH Priority

#### 1. Fix phantom references in discriminated-union-error-handling.md

**Location:** `docs/learned/architecture/discriminated-union-error-handling.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Changes needed:

1. Replace reference to `src/erk/cli/commands/land_pipeline.py` — file does not exist.
   Find the actual current location of the land pipeline logic, or remove the reference
   if the example was deleted.

2. Replace `gateway/github/types.py` with correct path:
   `packages/erk-shared/src/erk_shared/github/types.py`

3. Replace `gateway/github/checks.py` — file does not exist after gateway reorganization.
   Find the actual current location or remove the reference.

Audit all <!-- Source: ... --> comments and code examples to verify file paths are current.
```

---

#### 2. Fix phantom references in ensure-ideal-pattern.md

**Location:** `docs/learned/cli/ensure-ideal-pattern.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Changes needed:

1. Replace `gateway/github/types.py` with correct path:
   `packages/erk-shared/src/erk_shared/github/types.py`

2. Replace `gateway/github/checks.py` — file does not exist after gateway reorganization.
   Find the actual current location or remove the reference.

Audit all <!-- Source: ... --> comments and code examples to verify file paths are current.
```

---

#### 3. Update migration status in error-handling-antipatterns.md

**Location:** `docs/learned/cli/error-handling-antipatterns.md`
**Action:** UPDATE
**Source:** [PR #6860]

**Draft Content:**

```markdown
## Current Migration Status

Update the "Current Migration Status" section to reflect PR #6860:

As of PR #6860:
- admin.py converted: 8 error patterns migrated (4 Ensure.not_none, 1 Ensure.invariant,
  3 RuntimeError-to-UserFacingCliError)
- Previous: PR #6353 converted 8 files from RuntimeError to UserFacingCliError
- Cumulative: ~16 files/patterns converted across PRs #6353 and #6860
- Remaining: Audit remaining CLI commands for RuntimeError instances that should
  be UserFacingCliError

Also add the exception chaining pattern demonstrated in PR #6860 if not already present:

### Exception Chaining with `from e`

When converting `RuntimeError` catch blocks to `UserFacingCliError`, always preserve
the exception chain:

\```python
except RuntimeError as e:
    raise UserFacingCliError(str(e)) from e
\```

The `from e` preserves the causal chain for debugging while presenting a clean
user-facing error message.
```

---

#### 4. Add multi-line error message convention to output-styling.md

**Location:** `docs/learned/cli/output-styling.md`
**Action:** UPDATE (add section after "Error Message Guidelines")
**Source:** [PR #6860]

**Draft Content:**

```markdown
### Multi-line Error Messages

For errors that need both a primary message and remediation context, use implicit
string concatenation with `\n`:

\```python
github_id = Ensure.not_none(
    repo.github,
    "Not a GitHub repository\n"
    "This command requires the repository to have a GitHub remote configured.",
)
\```

**Convention:**
- Line 1: Primary error description (concise, specific)
- Newline separator via `\n` at end of first string
- Line 2+: Remediation guidance or additional context

**DO NOT** use `\n\n` (double newline) — the Ensure class already handles
spacing in its error output formatting.

This pattern was established in the admin.py migration (PR #6860) and applies
to all Ensure method calls where the error benefits from remediation context.
```

---

### MEDIUM Priority

#### 5. Document admin command testing patterns with FakeGitHubAdmin

**Location:** `docs/learned/testing/admin-command-testing.md`
**Action:** CREATE
**Source:** [PR #6860]

**Draft Content:**

```markdown
---
title: Admin Command Testing Patterns
read_when:
  - "writing tests for admin CLI commands"
  - "using FakeGitHubAdmin in tests"
  - "testing permission-related CLI commands"
tripwires:
  - action: "testing admin commands that read GitHub settings"
    warning: "Use FakeGitHubAdmin with initial_permissions dict to configure read state.
              Do not mock subprocess calls."
---

# Admin Command Testing Patterns

Testing patterns for `erk admin` subcommands using the fake-driven architecture.

## FakeGitHubAdmin Setup

FakeGitHubAdmin accepts an `initial_permissions` dict to configure read-only state:

\```python
admin = FakeGitHubAdmin(
    initial_permissions={"allow_merge_commit": True, "allow_squash_merge": False}
)
\```

## Testing Display vs Mutation Modes

**Display mode** (read-only): Assert output contains current settings from initial_permissions.

**Mutation mode** (enable/disable): Assert via `admin.set_permission_calls` list which
tracks all mutation calls as `(setting_name, value)` tuples.

\```python
# After running enable command:
assert admin.set_permission_calls == [("allow_merge_commit", True)]
\```

## erk_isolated_fs_env Helper

Use `erk_isolated_fs_env()` to create an isolated environment with:
- Configured git repo with GitHub remote
- Injected fakes (FakeGitHubAdmin, FakeGitGateway, etc.)
- Proper Click context for CLI invocation

\```python
with erk_isolated_fs_env(github_admin=admin, git=fake_git) as env:
    result = env.runner.invoke(cli, ["admin", "github-pr-setting", "--display"])
    assert result.exit_code == 0
\```

## Standard Error Cases

1. **Missing GitHub remote**: Set `repo.github = None` to test Ensure.not_none() path
2. **Detached HEAD**: Configure FakeGitGateway with `current_branch=None`
3. **Permission errors**: FakeGitHubAdmin can raise RuntimeError to test
   UserFacingCliError conversion

## Reference Files

- `tests/unit/cli/commands/test_admin_github_pr_setting.py` — 5 test cases
- `tests/unit/cli/commands/test_admin_test_workflow.py` — 4 test cases
```

---

#### 6. Document objective roadmap integration and review PR workflow

**Location:** `docs/learned/planning/lifecycle.md`
**Action:** UPDATE (add two new sections)
**Source:** [Impl]

**Draft Content:**

```markdown
## Objective Roadmap Integration

When implementing a plan that corresponds to an objective roadmap step, the workflow
includes automatic roadmap updates via markers:

### Marker-Based State Management

1. **Create markers during planning:**
   - `objective-context` marker: stores objective issue number (triggers exit-plan-mode
     hook to suggest correct save command)
   - `roadmap-step` marker: stores step ID (e.g., "1C.2") for automatic roadmap updates

2. **Automatic roadmap update on plan save:**
   - `/erk:plan-save` checks for `roadmap-step` marker
   - If present, runs `erk exec update-roadmap-step` to update the objective's
     roadmap table with the plan issue link
   - Marker is cleared after successful submission

### Lifecycle

\```
Create markers → Save plan → Update roadmap → Create review PR → Submit → Clear markers
\```

## Review PR Workflow

Review PRs enable human review of plans before implementation.

### Purpose

A review PR contains only the `.impl/` plan files, allowing reviewers to comment
on the plan before code is written.

### Workflow: `/erk:plan-review`

1. **Pre-check**: Verify no existing review PR via `erk exec get-plan-metadata <issue> review_pr`
2. **Branch creation**: Create ephemeral branch `plan-review-{issue}-{date}` (e.g.,
   `plan-review-6858-02-11-1122`)
3. **PR creation**: Create PR linking to the plan issue
4. **Branch restoration**: Return to the original branch automatically

### Key Patterns

- **Ephemeral branches**: Review branches are temporary; they exist only to host the PR
- **Branch restoration**: Agent saves current branch, creates review branch, creates PR,
  then returns to original branch
- **Duplicate prevention**: Always check for existing review PRs before creating a new one
- **Defensive checks**: Also check for previous completed reviews to avoid redundancy
```

---

### LOW Priority

#### 7. Document pre-plan context gathering pattern

**Location:** `docs/learned/planning/planning-patterns.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
title: Planning Patterns
read_when:
  - "preparing to enter plan mode"
  - "optimizing plan creation workflow"
  - "delegating tasks during planning"
---

# Planning Patterns

Patterns for effective plan creation and context management.

## Pre-Plan Context Gathering

**Pattern**: Gather ALL necessary context BEFORE entering plan mode.

### Why This Matters

Plan mode is for plan *creation*, not exploration. Entering plan mode early and then
doing extensive file reading, API calls, and exploration wastes the focused planning
context on data gathering.

### The Pattern

1. Parse objective and extract step details
2. Load all relevant documentation (migration guides, API references, prior PRs)
3. Read target files and analyze patterns
4. Enter plan mode with complete context
5. Write plan immediately without further exploration

### Parallel Context Gathering

Use parallel tool calls to load context simultaneously:
- Task agent for structured data (JSON parsing, issue fetching)
- File reads for documentation and source code
- Bash commands for git history and status

### Anti-pattern

Entering plan mode first, then spending multiple turns reading files, fetching issues,
and exploring the codebase. This fragments the planning session with mechanical work.

## Task Agent for Structured Data

Delegate structured data parsing to the Task agent to keep the main conversation
focused on planning logic:

- Fetch and parse issue body
- Validate labels and metadata
- Run JSON commands and format results
- Parse and format structured data

This separation keeps the main conversation clean and planning-focused.
```

---

#### 8. Expand dependency injection documentation for CLI commands

**Location:** `docs/learned/cli/dependency-injection-patterns.md`
**Action:** UPDATE (add section for CLI command context injection)
**Source:** [PR #6860]

**Draft Content:**

```markdown
## CLI Command Context Injection

The dependency injection pattern also applies to CLI commands (not just exec scripts).

### Pattern: Prefer `ctx.<gateway>` Over Direct Construction

**Before (anti-pattern):**
\```python
from erk.gateway.github.admin.real import RealGitHubAdmin

admin = RealGitHubAdmin()
result = admin.get_pr_setting(repo, setting)
\```

**After (correct):**
\```python
admin = ctx.github_admin
result = admin.get_pr_setting(repo, setting)
\```

### Why This Matters

1. **Testability**: Tests inject `FakeGitHubAdmin` via context
2. **Dry-run support**: Dry-run mode can inject `DryRunGitHubAdmin`
3. **Consistency**: Same injection pattern as exec scripts
4. **Import hygiene**: No direct imports of `Real*` implementations in command files

### Migration Pattern

When refactoring a CLI command to use context injection:
1. Remove `from erk.gateway.*.real import Real*` imports
2. Replace `Real*()` construction with `ctx.<gateway>`
3. Verify tests use `erk_isolated_fs_env()` which handles fake injection

This pattern was demonstrated in PR #6860 where `RealGitHubAdmin` was replaced
with `ctx.github_admin` in admin.py.
```

---

## Contradiction Resolutions

No contradictions detected. The existing documentation on Ensure patterns, UserFacingCliError, and discriminated unions is consistent with the patterns implemented in PR #6860. The gap analysis incorrectly stated these docs did not exist; they do, and their content aligns with the migration.

## Prevention Insights

No errors or failed approaches occurred during implementation. The planning session followed a successful linear path. One notable prevention insight from the broader pattern:

### 1. Phantom References in Documentation

**What happened:** Two existing docs (`discriminated-union-error-handling.md`, `ensure-ideal-pattern.md`) contain references to files that no longer exist or have moved (`land_pipeline.py`, `gateway/github/types.py`, `gateway/github/checks.py`).

**Root cause:** Gateway reorganization moved files but documentation was not updated. Docs were written referencing file paths that subsequently changed.

**Prevention:** When reorganizing gateway code or moving files, grep `docs/learned/` for references to the moved paths and update them.

**Recommendation:** TRIPWIRE

## Tripwire Additions

Add these to the frontmatter of relevant documents:

### For `docs/learned/cli/output-styling.md`

```yaml
tripwires:
  - action: "writing multi-line error messages in Ensure method calls"
    warning: "Use implicit string concatenation with \\n at end of first string. Line 1 is the primary error, line 2+ is remediation context. Do NOT use \\n\\n (double newline) — Ensure handles spacing."
```

### For `docs/learned/cli/error-handling-antipatterns.md`

```yaml
tripwires:
  - action: "converting RuntimeError catch blocks to UserFacingCliError"
    warning: "Always preserve exception chain with 'from e'. Pattern: raise UserFacingCliError(str(e)) from e"
```

### For `docs/learned/testing/admin-command-testing.md` (new file)

```yaml
tripwires:
  - action: "testing admin commands that read GitHub settings"
    warning: "Use FakeGitHubAdmin with initial_permissions dict to configure read state. Do not mock subprocess calls."
```