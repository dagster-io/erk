# Documentation Plan: Remove plan_backend from GlobalConfig, use only ERK_PLAN_BACKEND env var

## Context

This implementation simplified erk's configuration architecture by removing the `plan_backend` field from `GlobalConfig` and `GlobalConfigSchema`, consolidating backend selection to rely solely on the `ERK_PLAN_BACKEND` environment variable. The change moved from a 3-tier resolution model (env var > config file > default) to a simpler 2-tier model (env var > default), reducing configuration complexity while maintaining all functionality.

The refactoring touched 24 files across core implementation, CLI commands, statusline, and tests. It required updating 24 call sites, rewriting unit tests to validate 2-tier resolution, and deleting 128 lines of integration tests that validated config file persistence. This PR demonstrates a complete pattern for removing config fields from erk's configuration system.

Future agents benefit from documenting: (1) the specific pattern for removing config fields (a 12-step checklist), (2) when to use 2-tier vs 3-tier configuration resolution, (3) test patterns for env-var-driven behavior, and (4) erk's policy on breaking changes. Additionally, the implementation sessions exposed gaps in GitHub API rate limit handling and command output verification that warrant tripwires.

## Raw Materials

See PR #7772 diff and associated session analyses.

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 13    |
| Contradictions to resolve      | 2     |
| Tripwire candidates (score>=4) | 3     |
| Potential tripwires (score2-3) | 4     |

## Documentation Items

### HIGH Priority

#### 1. Update backend selection documentation to reflect 2-tier resolution

**Location:** `docs/learned/planning/draft-pr-plan-backend.md`
**Action:** UPDATE
**Source:** [Impl] [PR #7772]

**Draft Content:**

```markdown
## Backend Selection (Updated)

Backend selection uses a **two-tier resolution** model:

1. **Environment variable** (`ERK_PLAN_BACKEND`): If set to "draft_pr" or "github", use that value
2. **Default**: "github"

The previous three-tier model (env var > GlobalConfig.plan_backend > default) was removed in PR #7772 to simplify configuration.

### When to Use ERK_PLAN_BACKEND

- CI workflows that need draft PR backend: `ERK_PLAN_BACKEND=draft_pr erk ...`
- Local development experiments: `export ERK_PLAN_BACKEND=draft_pr`
- Test isolation: `monkeypatch.setenv("ERK_PLAN_BACKEND", "draft_pr")`

### Migration Note

Config files containing `plan_backend` field are silently ignored (no error, no warning). Users must switch to environment variable.

See `get_plan_backend()` in `packages/erk-shared/src/erk_shared/plan_store/__init__.py`.
```

---

#### 2. Delete obsolete tripwire about GlobalConfig.plan_backend precedence

**Location:** `docs/learned/planning/draft-pr-plan-backend.md` (Tripwire #14)
**Action:** DELETE_STALE_ENTRY
**Source:** [Impl] [PR #7772]

**Cleanup Instructions:**

Remove tripwire #14 which states: "Backend detection precedence: when GlobalConfig.plan_backend is available via context, use it. Never fall back to re-reading env vars inside inner functions if global_config is already in scope."

This tripwire is obsolete because GlobalConfig.plan_backend no longer exists. The general principle about not re-reading env vars when context provides values may be documented elsewhere, but this specific tripwire about plan_backend precedence must be deleted.

---

#### 3. GitHub API rate limit handling patterns

**Location:** `docs/learned/architecture/github-api-rate-limits.md` (new file)
**Action:** CREATE
**Source:** [Impl] (session-1ea0b05f, session-e40b3d81)

**Draft Content:**

```markdown
---
read-when: calling gh commands repeatedly, implementing retry logic for GitHub API, encountering rate limit errors
tripwires: 1
---

# GitHub API Rate Limit Handling

## Overview

GitHub's API has separate rate limits for GraphQL and REST APIs. When implementing commands that make repeated API calls, use these patterns to handle rate limits gracefully.

## Detection

Rate limit errors appear as:
- Exit code 1 from `gh` commands
- Message containing "API rate limit already exceeded for user ID"

## Prevention Strategies

### Exponential Backoff

Simple fixed delays (e.g., `sleep 5`) are insufficient. Implement exponential backoff:

- Initial delay: 5 seconds
- Subsequent delays: 10s, 20s, 40s
- Maximum retries: 3-4 attempts

### REST API Fallback

GraphQL and REST APIs have separate rate limits. If GraphQL is rate-limited, REST may still work:

```bash
# GraphQL (may be rate-limited)
gh pr view --json title,body

# REST fallback (separate quota)
gh api repos/{owner}/{repo}/pulls/{number}
```

### Caching

Cache PR metadata locally when feasible to reduce API calls.

## Tripwires

- Before calling gh commands repeatedly in workflows like `/erk:pr-address`: Implement exponential backoff or REST API fallback for metadata queries to avoid rate limits
```

---

#### 4. Config field removal checklist

**Location:** `docs/learned/refactoring/config-field-removal-checklist.md` (new file)
**Action:** CREATE
**Source:** [Impl] [PR #7772]

**Draft Content:**

```markdown
---
read-when: removing a field from GlobalConfig or GlobalConfigSchema, simplifying configuration
tripwires: 1
---

# Config Field Removal Checklist

Complete checklist for removing a field from erk's configuration system, using PR #7772 (plan_backend removal) as reference implementation.

## Prerequisites

- [ ] Confirm the field can be removed (alternative mechanism in place)
- [ ] Document migration path for users (env var, default behavior, etc.)

## Schema Layer

1. [ ] Remove field from `GlobalConfigSchema` in `packages/erk-shared/src/erk_shared/config/schema.py`
2. [ ] Remove field from `GlobalConfig` dataclass in `packages/erk-shared/src/erk_shared/context/types.py`
3. [ ] Remove field parameter from `GlobalConfig.test()` factory method

## Gateway Layer

4. [ ] Remove field parsing in `load_config()` in `packages/erk-shared/src/erk_shared/gateway/erk_installation/real.py`
5. [ ] Remove field persistence in `save_config()` in `packages/erk-shared/src/erk_shared/gateway/erk_installation/real.py`

## Consumer Layer

6. [ ] Update function signatures that consumed the field (e.g., `get_plan_backend()`)
7. [ ] Update all call sites that passed the field value (grep for field name)

## Test Layer

8. [ ] Update test fixtures (`context_for_test()`) to remove the parameter
9. [ ] Update all test call sites to stop passing the parameter
10. [ ] **DELETE** integration tests that validated config persistence of the field (don't try to update them)
11. [ ] Rewrite unit tests to test new resolution logic

## Documentation Layer

12. [ ] Update docs referencing the removed field
13. [ ] Remove any tripwires about the field

## Verification

- [ ] Run full CI: `make all-ci`
- [ ] Grep codebase for field name to ensure no orphaned references

## Tripwires

- Before removing a field from GlobalConfig: Follow this 12-step config field removal checklist
```

---

#### 5. Empty command output verification tripwire

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] (session-e40b3d81)

**Draft Content:**

```markdown
## Command Output Verification

### Empty Output After State-Changing Commands

When `erk exec` commands return empty output, verify the state change actually occurred by re-querying state.

**Problem**: Commands like `erk exec update-pr-description` may return empty output on both success and failure.

**Solution**: After running state-changing commands, verify the change:

```bash
# After updating PR description
gh pr view --json title,body

# After resolving threads
gh pr view --json reviewThreads
```

**Tripwire**: After running erk exec commands with empty output, verify state change occurred by re-querying state (e.g., `gh pr view --json`)
```

---

### MEDIUM Priority

#### 6. Test fixture monkeypatch pattern for env vars

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] [PR #7772]

**Draft Content:**

```markdown
## Test Fixture Monkeypatch Pattern

### When Fixtures Accept Env-Var-Driven Parameters

When test fixtures previously accepted a parameter to control env-var-driven behavior, replace the parameter with `monkeypatch.setenv()`.

**Before (PR #7772 pattern)**:
```python
# Fixture accepted plan_backend parameter
def context_for_test(plan_backend: PlanBackendType = "github") -> GlobalConfig:
    ...
```

**After**:
```python
# Fixture reads from env var; tests use monkeypatch
def context_for_test() -> GlobalConfig:
    # Internally calls get_plan_backend() which reads ERK_PLAN_BACKEND

# In tests:
def test_draft_pr_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ERK_PLAN_BACKEND", "draft_pr")
    ctx = context_for_test()
    # Now get_plan_backend() returns "draft_pr"
```

**Why**: Better isolation. Each test controls its own environment without fixture parameter threading.

See `context_for_test()` in `packages/erk-shared/src/erk_shared/context/testing.py` and usage examples in `packages/erk-statusline/tests/test_statusline.py`.

**Tripwire**: When test fixtures accept env-var-driven parameters, replace parameter with `monkeypatch.setenv()` for better isolation
```

---

#### 7. Integration test deletion after config field removal

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] [PR #7772]

**Draft Content:**

```markdown
## Integration Test Deletion Pattern

### When Removing Config Fields

When removing a config field, **DELETE** (not update) integration tests that validated config file parsing/persistence for that field.

**Example from PR #7772**:
- Removed `plan_backend` field from `GlobalConfig`
- Deleted 128 lines from `tests/integration/test_real_global_config.py`
- Tests deleted:
  - `test_real_config_store_loads_plan_backend_draft_pr`
  - `test_real_config_store_loads_plan_backend_default`
  - `test_real_config_store_loads_plan_backend_invalid_fallback`

**Why delete instead of update**: These tests validated config-based behavior that no longer exists. There's nothing to update them to test.

**What to keep**: Unit tests for the new resolution logic (e.g., env-var-based resolution).

**Tripwire**: When removing a config field, DELETE integration tests for config persistence — don't try to update them
```

---

#### 8. 2-tier vs 3-tier configuration resolution

**Location:** `docs/learned/configuration/resolution-tiers.md` (new file)
**Action:** CREATE
**Source:** [Impl] [PR #7772]

**Draft Content:**

```markdown
---
read-when: designing configuration resolution, deciding whether to add config file backing for a setting
---

# Configuration Resolution Tiers

## Overview

Erk uses two resolution patterns for configuration:

| Pattern | Resolution Order | Use Case |
|---------|------------------|----------|
| 2-tier | env var > default | Backend selection, feature flags, CI overrides |
| 3-tier | env var > config file > default | User preferences persisting across sessions |

## 2-Tier Resolution (Env Var > Default)

Use when:
- Value changes frequently (CI, experiments)
- No need to persist across sessions
- Simplicity preferred over flexibility

Example: `ERK_PLAN_BACKEND` (removed from config file in PR #7772)

See `get_plan_backend()` in `packages/erk-shared/src/erk_shared/plan_store/__init__.py`.

## 3-Tier Resolution (Env Var > Config > Default)

Use when:
- Value is a user preference that should persist
- User explicitly sets it once and expects it to remain
- Override capability needed for CI/scripts

Examples: `use_graphite`, `shell_setup_complete`

## Decision Framework

Ask these questions:

1. **Does the user set this once and forget?** → 3-tier
2. **Does this change per-command or per-CI-run?** → 2-tier
3. **Is this primarily for developer experimentation?** → 2-tier
4. **Would users be surprised if it reset after restart?** → 3-tier
```

---

#### 9. Breaking change migration pattern

**Location:** `docs/learned/refactoring/breaking-changes.md` (new file)
**Action:** CREATE
**Source:** [Impl] [PR #7772]

**Draft Content:**

```markdown
---
read-when: removing features, changing behavior, considering backwards compatibility
---

# Breaking Changes in Erk

## Policy

Erk follows a "break and migrate immediately" policy:

- **No backwards compatibility shims**
- **No deprecation warnings** (in most cases)
- **No legacy code paths**

This is intentional: erk is unreleased private software where breaking changes have minimal impact.

## PR #7772 Example: Silent Field Ignore

When `plan_backend` was removed from `GlobalConfig`:

- Users with `plan_backend` in config files see **no error**
- The field is silently ignored
- Default behavior applies (`github` backend)

**Why no error?** The field is removed entirely from schema parsing. Unknown fields in TOML are ignored by default.

## When This Pattern Applies

- **Removing config fields**: Silent ignore is acceptable
- **Changing CLI flags**: May warrant deprecation message
- **Removing CLI commands**: May warrant helpful error message

## When to Add Migration Help

Consider adding a migration message when:
- Change affects workflow significantly
- Users won't discover the change until something breaks
- Alternative requires non-obvious action

Example: If removing a CLI command, the command could remain as a stub printing "This command is removed. Use X instead."
```

---

#### 10. Automated review process documentation

**Location:** `docs/learned/ci/automated-review-process.md` (new file)
**Action:** CREATE
**Source:** [PR #7772]

**Draft Content:**

```markdown
---
read-when: understanding CI bot comments, working with automated review feedback
---

# Automated Review Process

## Overview

Erk PRs receive automated review from several bots that post comments with findings.

## Review Bots

| Bot | Purpose | Comment Structure |
|-----|---------|-------------------|
| test-coverage | Coverage deltas | Status badge, file-level coverage changes |
| dignified-python | Python standards | LBYL violations, type issues |
| dignified-code-simplifier | Code simplification | Redundant code, consolidation opportunities |
| tripwires | Documentation requirements | Pattern matches triggering tripwire warnings |

## Two-Tier Tripwire Checking

1. **Tier 1 (Mechanical)**: Regex-based pattern matching against diff
2. **Tier 2 (Semantic)**: LLM-based analysis for non-obvious violations

## Bot Comment Structure

Standard elements across all bots:
- Status badge (pass/fail/warnings)
- Timestamp of last check
- Findings section with actionable items
- Activity log showing resolution history

## Handling Bot Comments

- **Actionable findings**: Address in code, bot will re-check
- **Top-level summary comments**: Informational only, no response needed
- **False positives**: Resolve thread with explanation
```

---

#### 11. Preview-only command pattern

**Location:** `docs/learned/cli/preview-command-pattern.md` (new file)
**Action:** CREATE
**Source:** [Impl] (session-7ad45e71)

**Draft Content:**

```markdown
---
read-when: creating read-only preview commands, implementing commands that show what would happen
---

# Preview-Only Command Pattern

## Purpose

Preview commands show what actions would be taken without executing them. They provide visibility before committing to changes.

## Examples

- `/erk:pr-preview-address`: Shows PR review feedback classification without resolving threads

## Implementation Checklist

- [ ] Command name includes "preview" to signal read-only nature
- [ ] Documentation states explicitly: "This command does NOT make any changes"
- [ ] Command MUST NOT:
  - Resolve review threads
  - Commit code
  - Push to remote
  - Modify any state
- [ ] Output clearly indicates "preview" vs "actual" mode

## Documentation Pattern

Include explicit warnings:

```markdown
**WARNING**: This is a preview-only command. It does NOT:
- Resolve threads
- Make code changes
- Push to remote

To actually address feedback, use `/erk:pr-address`.
```

## Tripwire

When implementing preview commands, add explicit warnings that the command must NOT make any changes (resolve threads, commit code, push to remote).
```

---

#### 12. OAuth token vs API key decision tree

**Location:** `docs/learned/capabilities/authentication.md` (new or update existing)
**Action:** UPDATE
**Source:** [Impl] (session-7ad45e71)

**Draft Content:**

```markdown
## OAuth Token vs API Key (Feb 2026 Policy)

### Policy Change

As of February 2026, OAuth tokens generated via `claude setup-token` are restricted:
- **Allowed**: Claude Code, Claude.ai
- **NOT allowed**: Third-party integrations, CI/CD pipelines

### Decision Tree

**Are you using Claude Code or Claude.ai directly?**
- Yes → OAuth token via `claude setup-token`
- No → API key from console.anthropic.com

**Are you building CI/CD integration?**
- Yes → API key (store in GitHub Secrets)
- No → OAuth token may work

**Are you building a third-party tool?**
- Yes → API key required
- No → Either may work; prefer OAuth for local development
```

---

### LOW Priority

#### 13. Verify monkeypatch examples in environment-variable-isolation.md

**Location:** `docs/learned/testing/environment-variable-isolation.md`
**Action:** UPDATE
**Source:** [Impl] [PR #7772]

**Draft Content:**

Verify existing examples match the monkeypatch pattern used in PR #7772:

```python
def test_draft_pr_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ERK_PLAN_BACKEND", "draft_pr")
    # ... test code
```

Update any outdated examples that use fixture parameters instead of monkeypatch.

---

## Contradiction Resolutions

### 1. Backend Selection Resolution Mechanism

**Existing doc:** `docs/learned/planning/draft-pr-plan-backend.md`
**Conflict:** Document describes three-tier resolution (env var > GlobalConfig.plan_backend > default), but PR #7772 changed to two-tier (env var > default).
**Resolution:** Update the Backend Selection section to reflect two-tier resolution and remove all references to GlobalConfig.plan_backend field. See Documentation Item #1.

### 2. Env Var Re-reading Tripwire (Obsolete)

**Existing doc:** `docs/learned/planning/draft-pr-plan-backend.md` (Tripwire #14)
**Conflict:** Tripwire references GlobalConfig.plan_backend which no longer exists.
**Resolution:** Delete this tripwire entirely. See Documentation Item #2.

## Stale Documentation Cleanup

Existing docs with phantom references requiring action:

### 1. Obsolete plan_backend tripwire

**Location:** `docs/learned/planning/draft-pr-plan-backend.md`
**Action:** DELETE_STALE_ENTRY
**Phantom References:** Tripwire #14 references `GlobalConfig.plan_backend` (removed in PR #7772)
**Cleanup Instructions:** Remove tripwire #14 about plan_backend precedence. The field no longer exists, making the precedence rule obsolete.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. GitHub API Rate Limit Exhaustion

**What happened:** Session 1ea0b05f was interrupted by GitHub API rate limit errors. Agent attempted `gh pr view --json` but received "API rate limit already exceeded for user ID".

**Root cause:** Repeated GraphQL API calls in rapid succession exhausted hourly quota. Previous sessions had also made many `gh` calls.

**Prevention:** Implement exponential backoff (5s, 10s, 20s, 40s) instead of simple fixed delays. Consider REST API fallback since GraphQL and REST have separate rate limits.

**Recommendation:** TRIPWIRE - See Tripwire Candidate #1

### 2. Simple Sleep Retry Insufficient

**What happened:** Agent in session e40b3d81 attempted `sleep 5 && gh pr view` after rate limit, but user interrupted. The 5-second delay was insufficient.

**Root cause:** GitHub rate limits reset hourly, not after seconds. Fixed short delays don't help.

**Prevention:** Detect rate limit reset time from API response headers if available, or use exponential backoff with longer initial delay.

**Recommendation:** ADD_TO_DOC - Covered in GitHub API rate limits documentation

### 3. Empty Command Output Not Verified

**What happened:** In session e40b3d81, `erk exec update-pr-description` returned empty output. Agent proceeded without verifying the PR was actually updated.

**Root cause:** State-changing commands may return empty output on both success and failure.

**Prevention:** After running state-changing commands with empty output, re-query state to verify the change occurred.

**Recommendation:** TRIPWIRE - See Tripwire Candidate #2

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. GitHub API Rate Limit Handling

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before calling gh commands repeatedly in workflows like `/erk:pr-address`
**Warning:** Implement exponential backoff or REST API fallback for metadata queries to avoid rate limits
**Target doc:** `docs/learned/architecture/github-api-rate-limits.md`

This tripwire is critical because rate limit failures are silent until the command fails, they affect any workflow making multiple GitHub API calls, and recovery requires waiting (potentially an hour) or switching to alternative APIs. Two implementation sessions (1ea0b05f and e40b3d81) encountered this issue, demonstrating it's a recurring problem.

### 2. Empty Command Output Verification

**Score:** 5/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +2, but LOW destructive potential -1)
**Trigger:** After running erk exec commands that return empty output
**Warning:** Verify state change occurred by re-querying state (e.g., `gh pr view --json`)
**Target doc:** `docs/learned/architecture/tripwires.md`

Commands returning empty output create ambiguity about success vs failure. Without verification, agents may report success when the operation silently failed. This is cross-cutting because many `erk exec` commands can return empty output.

### 3. Config Field Removal Checklist

**Score:** 4/10 (criteria: Cross-cutting +2, Destructive potential +2)
**Trigger:** Before removing a field from GlobalConfig or GlobalConfigSchema
**Warning:** Follow the 12-step config field removal checklist
**Target doc:** `docs/learned/refactoring/config-field-removal-checklist.md`

Config field removal touches multiple layers (schema, gateway, consumers, tests, docs). Missing any step leaves orphaned references that cause runtime errors or test failures. PR #7772 demonstrates the complete pattern.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Test Fixture Monkeypatch Pattern

**Score:** 3/10 (criteria: Cross-cutting +2, Repeated pattern +1)
**Notes:** Affects all tests using `context_for_test()` with env-var-driven behavior. Didn't meet threshold because it's more of a best practice than a foot-gun; wrong approach causes test failures, not silent bugs.

### 2. Integration Test Deletion Pattern

**Score:** 3/10 (criteria: Non-obvious +2, Repeated pattern +1)
**Notes:** Not immediately clear that tests should be deleted vs updated when removing config fields. Didn't meet threshold because attempting to update tests causes obvious failures, guiding toward deletion.

### 3. 2-Tier vs 3-Tier Resolution Decision

**Score:** 2/10 (criteria: Cross-cutting +2)
**Notes:** Architectural decision, but consequences are not destructive. Wrong choice leads to user confusion, not runtime errors.

### 4. Breaking Changes Silent Field Ignore

**Score:** 3/10 (criteria: Non-obvious +2, Silent failure +1)
**Notes:** Users affected by silent field ignore is a rare scenario (most users don't customize config files). Would promote if erk becomes public software with more config file users.
