# Documentation Plan: Add erkbot system prompt module with erk-aware agent instructions

## Context

This plan documents lessons learned from implementing an erkbot system prompt module that teaches the Slack bot agent about erk's commands and workflows. The implementation involved creating a new `prompts.py` module with resource loading and custom override support, integrating it into the erkbot CLI, and fixing several discovered issues including a Click 8.3 breaking change and cross-package CLI command migration impacts.

The sessions revealed critical patterns around third-party dependency breaking changes, cross-package CLI refactoring impacts, and the PR review address workflow. Future agents working with erkbot, Click's CliRunner, or CLI refactoring will benefit from these documented tripwires and patterns. Four high-value tripwires emerged with scores of 4-6, indicating non-obvious, cross-cutting concerns with destructive potential.

Key insights include: (1) Click 8.3 silently changed CliRunner behavior, breaking test mocks that masked the incompatibility; (2) CLI command migrations require checking downstream packages (erkbot, desktop-dash) for hardcoded invocations; (3) TDD discipline catches constructor parameter removal bugs that broad mocks hide; and (4) the complete `/erk:pr-address` workflow was demonstrated end-to-end.

## Raw Materials

PR #8125

## Summary

| Metric | Count |
|--------|-------|
| Documentation items | 17 |
| Contradictions to resolve | 0 |
| Tripwire candidates (score>=4) | 4 |
| Potential tripwires (score 2-3) | 3 |

## Documentation Items

### HIGH Priority

#### 1. Click 8.3 CliRunner Breaking Change

**Location:** `docs/learned/integrations/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] Session 0fda1877, Session 1ac6343e

**Draft Content:**

```markdown
## Click 8.3 CliRunner Breaking Change

Click 8.3 removed the `mix_stderr` parameter from `CliRunner.__init__()`. Code using `CliRunner(mix_stderr=False)` will fail at runtime with a `TypeError`.

**Migration pattern:**
- Remove `mix_stderr=False` from all CliRunner instantiations
- Use `result.output` only (not `result.output + result.stderr`)
- In Click 8.3+, stdout and stderr are mixed into `result.output` by default

**Why test mocks mask this:** If tests mock the entire CliRunner class or constructor, the real constructor never runs and the incompatibility goes undetected. Prefer patching specific methods (like `.invoke()`) so the real constructor executes.

<!-- source: packages/erkbot/src/erkbot/runner.py, grep for CliRunner -->
```

#### 2. LBYL for Bundled Package Resources

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE
**Source:** [PR #8125] PR review thread at prompts.py:12

**Draft Content:**

```markdown
## LBYL for Bundled Package Resources

Even bundled resources that "should always exist" require LBYL existence checks before reading. Package builds can fail, files can be corrupted, and paths can change.

**Pattern:**
```python
def _load_prompt(filename: str) -> str:
    prompt_path = Path(__file__).parent / "resources" / filename
    if not prompt_path.exists():
        msg = f"Bundled resource not found: {prompt_path}"
        raise FileNotFoundError(msg)
    return prompt_path.read_text(encoding="utf-8")
```

**Why:** Defensive programming makes the error explicit and testable. LBYL is erk's standard regardless of file origin.

<!-- source: packages/erkbot/src/erkbot/prompts.py, grep for _load_prompt -->
```

#### 3. CLI Command Migration Cross-Package Impact

**Location:** `docs/learned/cli/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] Session a161c71b, Session f44bc419

**Draft Content:**

```markdown
## CLI Command Migration Cross-Package Impact

When moving or renaming erk CLI commands, downstream packages that invoke CLI via `CliRunner` or subprocess will break with "No such command" errors.

**Locations to check:**
- `packages/erkbot/src/erkbot/runner.py` - CLI invocations
- `packages/erkbot/src/erkbot/resources/` - system prompts with command examples
- `packages/desktop-dash/` - any CLI invocations
- Test files across `packages/*/tests/` with CLI assertions

**Prevention grep:**
```bash
rg --type py 'CliRunner.*invoke.*cli.*\["OLD_COMMAND"' packages/
rg 'erk OLD_COMMAND' packages/
```

<!-- source: packages/erkbot/src/erkbot/runner.py, grep for run_erk_plan_list -->
```

#### 4. encoding="utf-8" Mandatory Parameter

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE
**Source:** [PR #8125] PR review threads

**Draft Content:**

```markdown
## encoding="utf-8" Mandatory for All Text Operations

The `encoding="utf-8"` parameter is mandatory for ALL `read_text()` and `write_text()` calls, including in tests. No exceptions.

**Correct:**
```python
content = path.read_text(encoding="utf-8")
path.write_text(content, encoding="utf-8")
```

**Why:** Explicit encoding prevents platform-dependent behavior and ensures consistent text handling across environments.
```

#### 5. ErkBot Prompt Loading Pattern

**Location:** `docs/learned/integrations/erkbot-prompts.md` (new file)
**Action:** CREATE
**Source:** [Impl] Session 1ac6343e, [Diff] prompts.py, resources/erk_system_prompt.md

**Draft Content:**

```markdown
---
read-when:
  - working with erkbot prompts or system instructions
  - adding prompt loading to new modules
  - implementing custom prompt overrides
---

# ErkBot Prompt Loading Pattern

ErkBot uses a resource loading pattern with custom override support for its system prompt.

## Resource Loading

The `prompts.py` module loads the default prompt from a bundled resource file at module import time, then checks for custom overrides at runtime.

<!-- source: packages/erkbot/src/erkbot/prompts.py -->

## Custom Override Mechanism

Users can override the erkbot system prompt by creating `.erk/prompt-hooks/erk-system-prompt.md` in their repository root. The custom prompt completely replaces the default (no merging).

## Integration

The CLI loads the prompt during bot construction via `get_erk_system_prompt(repo_root=repo_path)`. The prompt is loaded once at startup, not on every request.

<!-- source: packages/erkbot/src/erkbot/cli.py, grep for get_erk_system_prompt -->

## Related Patterns

This pattern mirrors `erk_shared/gateway/gt/prompts.py` which uses the same resource loading and override mechanism for other prompts.
```

### MEDIUM Priority

#### 6. Test Data Migration for Third-Party Breaking Changes

**Location:** `docs/learned/testing/third-party-breaking-changes.md` (new file)
**Action:** CREATE
**Source:** [Impl] Session 0fda1877

**Draft Content:**

```markdown
---
read-when:
  - updating third-party dependencies
  - tests failing after dependency upgrade
  - mocked behavior no longer matches production
---

# Test Data Migration for Third-Party Breaking Changes

When a third-party dependency changes behavior in a minor or patch version, existing test mocks may mask the incompatibility.

## Pattern: Click 8.3 Migration

**Problem:** Click 8.3.1 removed `mix_stderr` parameter and changed output behavior.

**Detection:** Test mocked entire CliRunner class, hiding constructor TypeError until runtime.

**Solution:**
1. Write test that exercises real constructor (not mocked)
2. Update production code to match new API
3. Update all mock data to reflect new behavior (stdout+stderr mixed in `result.output`)
4. Check both unit tests AND integration tests

## General Pattern

1. Check release notes when bumping dependency versions
2. Prefer patching specific methods over entire classes
3. Add tests that exercise real constructors/APIs for critical dependencies
4. Update mock data in ALL test files when behavior changes
```

#### 7. TDD for Constructor Parameter Removal

**Location:** `docs/learned/testing/tdd-constructor-parameter-removal.md` (new file)
**Action:** CREATE
**Source:** [Impl] Session 0fda1877

**Draft Content:**

```markdown
---
read-when:
  - fixing TypeError from removed constructor parameter
  - testing constructor compatibility with third-party classes
  - writing tests that catch API breaking changes
---

# TDD for Constructor Parameter Removal

When a dependency removes a constructor parameter, existing tests may mask the incompatibility if they mock the entire class.

## The Problem

```python
# This test never runs the real CliRunner constructor
@patch("click.testing.CliRunner")
def test_something(self, mock_runner):
    mock_runner.return_value.invoke.return_value = MagicMock(output="test")
    # TypeError from removed parameter never surfaces
```

## TDD Solution

Patch only the method, not the class, so the real constructor runs:

```python
@patch("click.testing.CliRunner.invoke")
def test_constructor_compatibility(self, mock_invoke):
    mock_invoke.return_value = MagicMock(output="test", exit_code=0)
    result = await run_erk_plan_list()  # Real constructor runs here
    # Test will fail if constructor signature incompatible
```

## TDD Flow

1. Write test that exercises real constructor (RED if broken)
2. Fix production code to use compatible API (GREEN)
3. Update other mock data to match new behavior (refactor)
```

#### 8. PR Review Address Workflow

**Location:** `docs/learned/pr-operations/pr-address-workflow.md` (new file or expand existing)
**Action:** CREATE
**Source:** [Impl] Session 0fda1877

**Draft Content:**

```markdown
---
read-when:
  - running /erk:pr-address command
  - addressing PR review comments
  - understanding PR review workflow
---

# PR Review Address Workflow

The `/erk:pr-address` command implements a complete workflow for addressing PR review feedback.

## Phases

### Phase 1: Classify Feedback

Use Task tool (not skill invocation) for the pr-feedback-classifier to ensure proper isolation:

```python
Task(
  subagent_type: "general-purpose",
  model: "haiku",
  description: "Classify PR feedback",
  prompt: "Load and follow .claude/skills/pr-feedback-classifier/SKILL.md..."
)
```

### Phase 2: Execute by Batch

- Group comments by complexity (local, multi-file, architectural)
- Auto-proceed without confirmation for simple batches
- Single commit per batch

### Phase 3: Resolve Threads in Bulk

Use batch command for efficiency:
```bash
erk exec resolve-review-threads  # stdin: JSON array of {thread_id, message}
```

### Phase 4: Reply to Bot Summaries

Bot review summaries are discussion-level comments, not inline threads. Reply to them separately even after inline threads are resolved:
```bash
erk exec reply-to-discussion-comment --comment-id <id> --body "..."
```

### Phase 5: Update PR Description

Generate AI-powered title and body from the full PR diff:
```bash
erk exec update-pr-description --session-id "<session-id>"
```
```

#### 9. Bot Summary Replies

**Location:** `docs/learned/pr-operations/pr-address-workflow.md` (integrate into above)
**Action:** UPDATE
**Source:** [Impl] Session 0fda1877

This item should be integrated into the pr-address-workflow.md document above rather than as a separate file. The key insight: bot review summary comments are discussion-level comments that need replies even when inline threads are resolved.

#### 10. Cross-Package CLI Integration Testing

**Location:** `docs/learned/cli/migration-checklist.md` (expand existing or create)
**Action:** UPDATE
**Source:** [Impl] Session a161c71b

**Draft Content:**

```markdown
## Cross-Package CLI Integration Checklist

When refactoring CLI commands (moving, renaming, changing arguments):

- [ ] Update command implementation in `src/erk/cli/`
- [ ] Grep for CliRunner invocations in `packages/`:
  ```bash
  rg --type py 'CliRunner.*invoke.*cli' packages/
  ```
- [ ] Check system prompts in `packages/erkbot/src/erkbot/resources/`
- [ ] Update test assertions that reference command names
- [ ] Update user-facing messages in Slack handlers
- [ ] Consider adding integration test that invokes real CLI
```

#### 11. Test Code Standards Clarification

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [PR #8125] PR review threads

**Draft Content:**

```markdown
## Test Files Follow Production Standards

Test files follow the same import discipline and coding standards as production code:
- No inline imports (all imports at module level)
- `encoding="utf-8"` required for all text operations
- Same LBYL patterns as production code
```

### LOW Priority

#### 12. setup-impl branch_slug Bug Workaround

**Location:** `docs/learned/planning/setup-impl-bugs.md` (new file)
**Action:** CREATE
**Source:** [Impl] Session 1ac6343e

**Draft Content:**

```markdown
---
read-when:
  - setup-impl failing with TypeError
  - implementing from a plan PR
  - manual implementation setup needed
---

# setup-impl branch_slug Bug

## The Bug

`erk exec setup-impl --issue <number>` crashes with `TypeError: setup_impl_from_issue() got an unexpected keyword argument 'branch_slug'` when implementing from a plan PR.

## Manual Workaround

When setup-impl fails:

1. Fetch the branch from the plan PR:
   ```bash
   git fetch origin <branch-name>
   git checkout <branch-name>
   ```

2. Create .impl/plan.md manually:
   ```bash
   mkdir -p .impl
   gh issue view <issue-number> --json body -q .body > .impl/plan.md
   ```

3. Signal implementation started:
   ```bash
   erk exec signal-impl-started --issue <issue-number>
   ```

## Status

This bug should be fixed by removing branch_slug forwarding in `_handle_issue_setup` or adding the parameter to `setup_impl_from_issue`.
```

#### 13. Graphite Branch Tracking for Manual Branches

**Location:** `docs/learned/planning/manual-impl-setup.md` (integrate into above or separate)
**Action:** UPDATE
**Source:** [Impl] Session 1ac6343e

**Draft Content:**

```markdown
## Graphite Branch Tracking

Manually created branches must be tracked before Graphite submit:

```bash
# After manually checking out a branch
gt track --parent master

# Then submit works normally
gt submit
```

Without tracking, `gt submit` fails with "Cannot perform this operation on untracked branch".
```

#### 14. Monkeypatch Exceptions

**Location:** `docs/learned/testing/monkeypatch-elimination-checklist.md`
**Action:** UPDATE
**Source:** [PR #8125] Discussion comment

**Draft Content:**

```markdown
## Valid Exceptions

`@patch` is allowed when:
- Testing standalone packages that depend on third-party SDKs (e.g., erkbot testing Slack SDK)
- The third-party code cannot be wrapped with erk's fake architecture
- Integration tests would require real API credentials

The general rule (prefer fakes over mocks) still applies within the main erk codebase.
```

#### 15. Test Coverage Expectations

**Location:** `docs/learned/testing/testing.md`
**Action:** UPDATE
**Source:** [PR #8125] Discussion comment

**Draft Content:**

```markdown
## New Source Files Require Tests

When adding new source files:
- New module → new test file (e.g., `prompts.py` → `test_prompts.py`)
- Tests should cover primary functionality, not just existence
- Key phrase validation is acceptable for content tests (e.g., verify prompt mentions expected commands)
```

#### 16. Slack Bot Command Stability Pattern

**Location:** `docs/learned/integrations/slack-command-stability.md` (new file or integrate)
**Action:** CREATE
**Source:** [Impl] Session a161c71b

**Draft Content:**

```markdown
---
read-when:
  - refactoring CLI commands used by Slack bot
  - designing stable Slack command interface
---

# Slack Bot Command Stability Pattern

The Slack bot can present stable user-facing commands while internally mapping to different CLI commands. This decouples Slack UX from CLI refactoring.

**Example:**
- User types: `@erk plan list`
- Bot internally calls: `erk pr list --all-users`

This allows CLI commands to be reorganized without breaking user expectations in Slack.
```

#### 17. Plan Mode User Decision Flow

**Location:** `docs/learned/planning/plan-mode-markers.md`
**Action:** UPDATE
**Source:** [Impl] Session a161c71b

**Draft Content:**

```markdown
## exit-plan-mode-hook.implement-now Marker

The plan mode exit hook presents three options:
1. "Create a plan PR" (recommended) - saves plan to GitHub
2. "Skip PR and implement here" - sets `exit-plan-mode-hook.implement-now` marker
3. "View/Edit the plan" - allows review before decision

The `implement-now` marker signals that the agent should proceed with implementation in the current worktree without creating a plan PR first.
```

## Contradiction Resolutions

No contradictions found. The gap analysis confirmed that:
- No existing documentation covers erkbot system prompt module
- No stale references detected in related docs
- The plan's approach is consistent with existing resource loading patterns

## Stale Documentation Cleanup

No stale documentation requiring cleanup. All referenced code artifacts in related docs were verified to exist.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. TypeError from Removed Constructor Parameter

**What happened:** Click 8.3 removed `mix_stderr` parameter from CliRunner, but existing tests masked this by mocking the entire class.
**Root cause:** Broad test mocking prevented real constructor from running.
**Prevention:** Prefer patching specific methods (like `.invoke()`) over entire classes so real constructors execute.
**Recommendation:** TRIPWIRE

### 2. Test Masks Real Bug by Mocking Too Broadly

**What happened:** Test mocked entire CliRunner class, so `TypeError` only appeared at runtime, not in tests.
**Root cause:** Mock isolation was too complete.
**Prevention:** Add tests that exercise real constructors for critical third-party dependencies.
**Recommendation:** ADD_TO_DOC (testing patterns)

### 3. CLI Command Invocation Fails After Refactor

**What happened:** erkbot's runner.py still called `["plan", "list"]` after command was moved to `["pr", "list"]`.
**Root cause:** Downstream packages use hardcoded CLI arg arrays.
**Prevention:** Before merging CLI refactors, grep for CliRunner invocations in `packages/`.
**Recommendation:** TRIPWIRE

### 4. setup-impl branch_slug Forwarding Bug

**What happened:** `erk exec setup-impl --issue <number>` crashed with TypeError on branch_slug parameter.
**Root cause:** Function signature mismatch between caller and callee in setup_impl.py.
**Prevention:** Fix the bug: remove branch_slug forwarding OR add parameter to callee.
**Recommendation:** ADD_TO_DOC (planning workarounds)

### 5. CliRunner mix_stderr Incompatibility

**What happened:** Runtime error when erkbot tried to construct CliRunner with removed parameter.
**Root cause:** Click 8.3 breaking change not caught during development.
**Prevention:** Update all CliRunner instantiations to parameterless constructor.
**Recommendation:** TRIPWIRE

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Click 8.3 CliRunner Breaking Change

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2)
**Trigger:** Before using Click's CliRunner in tests or runner code
**Warning:** Never use `CliRunner(mix_stderr=False)` - Click 8.3+ removed this parameter. Use `CliRunner()` without arguments. In Click 8.3+, `result.output` contains mixed stdout+stderr.
**Target doc:** `docs/learned/integrations/tripwires.md`

This is tripwire-worthy because the error only manifests at runtime (not import time), test mocks typically hide it, and the fix requires understanding both the constructor change and the output behavior change. Without this tripwire, agents will copy old patterns and create runtime errors.

### 2. LBYL for Bundled Resources

**Score:** 5/10 (Non-obvious +2, Cross-cutting +2, Repeated pattern +1)
**Trigger:** Before reading bundled package resources
**Warning:** Even bundled resources that "should always exist" require LBYL existence checks before `read_text()`. Use: `if not prompt_path.exists(): raise FileNotFoundError(msg)`
**Target doc:** `docs/learned/architecture/tripwires.md`

This is tripwire-worthy because developers assume bundled resources don't need existence checks. The pattern applies to any package with bundled resources, not just erkbot. PR review caught this violation, indicating agents will make this mistake.

### 3. CLI Command Migration Cross-Package Impact

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2)
**Trigger:** Before moving or renaming erk CLI commands
**Warning:** Check downstream packages (erkbot, desktop-dash) that invoke CLI via CliRunner or subprocess. Run: `rg --type py 'CliRunner.*invoke.*cli.*["OLD_COMMAND"' packages/`
**Target doc:** `docs/learned/cli/tripwires.md`

This is tripwire-worthy because CLI refactoring seems like a contained change to `src/erk/cli/` but silently breaks downstream packages. The sessions showed this exact failure pattern, and without the tripwire, agents will make this mistake repeatedly.

### 4. encoding="utf-8" Mandatory Parameter

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)
**Trigger:** Before using `read_text()` or `write_text()`
**Warning:** Always specify `encoding="utf-8"` parameter. This applies to ALL pathlib text operations, including in tests. No exceptions.
**Target doc:** `docs/learned/architecture/tripwires.md`

This is tripwire-worthy because Python's default encoding varies by platform, and omitting it creates subtle cross-platform bugs. PR review caught this violation multiple times, indicating it's a common oversight.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Test Data Mocking for Dependency Changes

**Score:** 3/10 (Non-obvious +2, Repeated pattern +1)
**Notes:** Applies when updating dependencies that change behavior; not frequent enough for cross-cutting status. Could be promoted if more instances of dependency-induced test data staleness are observed.

### 2. Test Code Import Discipline

**Score:** 3/10 (Non-obvious +2, Repeated pattern +1)
**Notes:** Could merge with general import discipline tripwire. Test files are sometimes treated as "less strict" but shouldn't be. May warrant promotion if PR review continues to catch inline imports in tests.

### 3. Bot Summary Replies

**Score:** 2/10 (Non-obvious +2)
**Notes:** Specific to PR workflow, not broadly cross-cutting. Important for PR review workflow documentation but doesn't warrant a standalone tripwire. Better documented in pr-address-workflow.md.
