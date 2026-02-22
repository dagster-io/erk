# Documentation Plan: Add --oauth flag to manage dual authentication secrets in GitHub Actions

## Context

This PR (#7768) implements a `--oauth` flag for the `erk admin gh-actions-api-key` command, enabling management of dual authentication secrets in GitHub Actions. The key architectural decision is that API keys and OAuth tokens are mutually exclusive: enabling one automatically deletes the other to prevent authentication ambiguity. The precedence rule states that when both exist (a transitional state), the API key takes precedence.

The implementation introduces user guidance in interactive prompts, specifically instructing users to run `claude setup-token` when obtaining OAuth tokens. This UX pattern addresses a gap identified during the session: users need actionable instructions, not just bare prompts asking for credentials.

Documentation matters here because the dual-secret model has subtle behaviors (automatic cleanup, precedence rules) that users and future agents need to understand. Additionally, the session revealed that CI authentication failures are often misidentified as code problems when they're actually infrastructure issues (missing GitHub secrets).

## Raw Materials

Associated with PR #7768

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 8     |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 2     |
| Potential tripwires (score2-3) | 3     |

## Documentation Items

### HIGH Priority

#### 1. Dual-Secret Authentication Model

**Location:** `docs/learned/integrations/dual-secret-authentication.md`
**Action:** CREATE
**Source:** [Impl], [PR #7768]

**Draft Content:**

```markdown
---
title: Dual-Secret Authentication Model
read_when:
  - "configuring GitHub Actions authentication for Claude"
  - "understanding ANTHROPIC_API_KEY vs CLAUDE_CODE_OAUTH_TOKEN"
  - "troubleshooting authentication in CI workflows"
---

# Dual-Secret Authentication Model

GitHub Actions Claude integration supports two authentication methods: API keys and OAuth tokens. These are mutually exclusive by design.

## Overview

Erk manages two GitHub Actions secrets for Claude authentication:
- `ANTHROPIC_API_KEY` - API key for direct Claude API access
- `CLAUDE_CODE_OAUTH_TOKEN` - OAuth token for Claude Code CLI access

## Precedence Rule

When both secrets exist (a transitional state), `ANTHROPIC_API_KEY` takes precedence. The CLI displays this with `<- active (takes precedence)` indicator.

## Automatic Cleanup Behavior

Enabling one authentication method automatically deletes the other. This prevents ambiguity about which authentication is active.

See `src/erk/cli/commands/admin.py` function `_enable_secret` for implementation.

## When to Use Each

| Method | Use When |
|--------|----------|
| API Key | Direct Claude API calls, exec scripts with PromptExecutor |
| OAuth Token | Claude Code CLI invocations in workflows |

See [Exec Script Environment Requirements](../ci/exec-script-environment-requirements.md) for detailed usage matrix.

## Obtaining Credentials

- **API Key**: Generate from Anthropic Console
- **OAuth Token**: Run `claude setup-token` to obtain

## Related Topics

- [GitHub Actions Claude Integration](../ci/github-actions-claude-integration.md)
- [Exec Script Environment Requirements](../ci/exec-script-environment-requirements.md)
```

---

#### 2. Exception Logging in Non-Fatal Operations

**Location:** `docs/learned/architecture/exception-handling.md`
**Action:** UPDATE (or CREATE if not exists)
**Source:** [PR #7768]

**Draft Content:**

```markdown
## Logging Non-Fatal Exceptions

Even non-fatal or optional operations must log failures. Silent exception swallowing (bare `except: pass`) is prohibited.

### Pattern

For operations that may fail but shouldn't stop execution:

```python
try:
    optional_operation()
except RuntimeError:
    logger.debug("Optional operation failed: %s", e)
```

### Why This Matters

Silent failures make debugging impossible. The PR #7768 review caught a case where secret deletion failures were silently swallowed. The fix converted `except RuntimeError: pass` to a logged debug message.

See `src/erk/cli/commands/admin.py` function `_enable_secret` for the corrected pattern.
```

---

#### 3. CI Authentication Failures as Infrastructure Issues

**Location:** `docs/learned/ci/tripwires.md`
**Action:** UPDATE (add tripwire)
**Source:** [Impl]

**Draft Content:**

Add this tripwire to the existing tripwires.md file:

```markdown
**When CI code-reviews fail with authentication errors** -> Check error message for "Invalid API key - Please run /login". This indicates missing GitHub Actions secrets (ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN), not a code problem. Verify secrets are set in repository settings before debugging code.
```

---

### MEDIUM Priority

#### 4. OAuth Flag Usage Pattern

**Location:** `docs/learned/integrations/dual-secret-authentication.md` (add section)
**Action:** UPDATE (merge into item #1)
**Source:** [Impl], [PR #7768]

**Draft Content:**

```markdown
## CLI Usage

The `erk admin gh-actions-api-key` command manages both authentication methods:

### Status Display

```bash
# Show current authentication status
erk admin gh-actions-api-key
```

### Managing API Keys

```bash
# Enable API key
erk admin gh-actions-api-key --enable

# Disable API key
erk admin gh-actions-api-key --disable
```

### Managing OAuth Tokens

```bash
# Enable OAuth token
erk admin gh-actions-api-key --oauth --enable

# Disable OAuth token
erk admin gh-actions-api-key --oauth --disable
```

See `src/erk/cli/commands/admin.py` for implementation.
```

---

#### 5. OAuth Token Setup Workflow

**Location:** `docs/learned/ci/github-actions-claude-integration.md`
**Action:** UPDATE (add section)
**Source:** [Impl]

**Draft Content:**

Add a new section "Setting Up Authentication Secrets":

```markdown
## Setting Up Authentication Secrets

### Obtaining Credentials

| Secret | How to Obtain |
|--------|---------------|
| `ANTHROPIC_API_KEY` | Generate from Anthropic Console |
| `CLAUDE_CODE_OAUTH_TOKEN` | Run `claude setup-token` in terminal |

### Initial Setup

Use the `erk admin gh-actions-api-key` command to configure secrets:

```bash
# Set up API key authentication
erk admin gh-actions-api-key --enable

# Or set up OAuth token authentication
erk admin gh-actions-api-key --oauth --enable
```

See [Dual-Secret Authentication Model](../integrations/dual-secret-authentication.md) for the precedence rules and automatic cleanup behavior.
```

---

#### 6. User Guidance in OAuth Prompts (Tripwire)

**Location:** `docs/learned/cli/tripwires.md`
**Action:** UPDATE (add tripwire)
**Source:** [Impl]

**Draft Content:**

Add this tripwire to the existing tripwires.md:

```markdown
**When adding OAuth authentication to CLI commands** -> Always provide actionable guidance in prompts when asking for credentials. Example: "Run 'claude setup-token' to obtain your OAuth token" rather than just "Enter OAuth token:". Users need to know HOW to get the credential being requested.
```

---

### LOW Priority

#### 7. SHOULD_BE_CODE: _display_auth_status() Docstring

**Location:** `src/erk/cli/commands/admin.py`
**Action:** CODE_CHANGE
**Source:** [Impl]

Add docstring to `_display_auth_status()` function explaining:
- The dual-secret status display logic
- How precedence is indicated (`<- active (takes precedence)`)
- The four display states: both set, only API key, only OAuth, neither

---

#### 8. SHOULD_BE_CODE: _enable_secret() Docstring

**Location:** `src/erk/cli/commands/admin.py`
**Action:** CODE_CHANGE
**Source:** [Impl]

Add docstring to `_enable_secret()` function explaining:
- Automatic deletion of the "other" secret before setting the new one
- Why this prevents authentication ambiguity
- The error handling for cleanup failures (log but don't fail)

---

## Contradiction Resolutions

None found. Existing documentation does not conflict with new insights.

## Stale Documentation Cleanup

None found. All file references in existing docs were verified and confirmed to exist.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. CI Authentication Misidentification

**What happened:** CI code-reviews workflow failed with "Invalid API key - Please run /login" error.
**Root cause:** Missing GitHub Actions secrets (ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN) in the repository.
**Prevention:** When encountering this error, check repository secrets configuration first rather than debugging code.
**Recommendation:** TRIPWIRE (implemented in item #3)

### 2. Silent Exception Swallowing

**What happened:** PR review bot flagged `except RuntimeError: pass` as a coding standard violation.
**Root cause:** Non-fatal operations were silently swallowing exceptions without any logging.
**Prevention:** Always log exceptions, even for optional operations that shouldn't stop execution. Use `logger.debug()` for non-critical failures.
**Recommendation:** ADD_TO_DOC (implemented in item #2)

### 3. Missing User Guidance in Prompts

**What happened:** Initial implementation asked for OAuth token without explaining how to obtain one.
**Root cause:** User requested explicit guidance on running `claude setup-token`.
**Prevention:** When prompting for credentials, always include actionable instructions on how to obtain them.
**Recommendation:** TRIPWIRE (implemented in item #6)

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. CI Authentication Failures Misidentified as Code Issues

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before debugging CI code-reviews failures showing "Invalid API key" errors
**Warning:** Check for missing GitHub Actions secrets (ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN) before debugging code. This is an infrastructure issue, not a code problem.
**Target doc:** `docs/learned/ci/tripwires.md`

This tripwire is essential because the error message "Invalid API key - Please run /login" doesn't clearly indicate that GitHub repository secrets are missing. Agents may waste significant time debugging code when the fix is simply configuring secrets in repository settings.

### 2. Missing User Guidance in OAuth Prompts

**Score:** 5/10 (criteria: Non-obvious +2, Cross-cutting +2, Repeated pattern +1)
**Trigger:** Before adding OAuth or credential prompts to CLI commands
**Warning:** Include actionable guidance on how to obtain the credential being requested (e.g., "Run 'claude setup-token' to obtain your OAuth token").
**Target doc:** `docs/learned/cli/tripwires.md`

This pattern applies beyond just OAuth tokens to any credential prompt. Users need to know not just what to enter, but how to obtain what they need to enter.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Exception Logging in Non-Fatal Operations

**Score:** 3/10 (criteria: Non-obvious +2, Repeated pattern +1)
**Notes:** Pattern was caught by automated review bot, suggesting it may appear elsewhere in codebase. Could be promoted if additional instances are found during code review.

### 2. Automatic Secret Switching Deletes Other Secret

**Score:** 3/10 (criteria: Non-obvious +2, Destructive potential +1)
**Notes:** UX surprise but not data loss - secrets can be re-enabled. Better addressed through documentation than tripwire since the behavior is intentional and documented.

### 3. Skip-PR Workflow Marker Creation

**Score:** 2/10 (criteria: Cross-cutting +2)
**Notes:** Specific to planning workflow implementation. May evolve as planning system matures.

## Existing Documentation Updates

The gap analysis revealed that some items identified as "new documentation needed" are actually updates to existing, well-documented features:

### Automated Review System (Already Documented)

The gap analysis identified "Automated PR review system" as needing new documentation, but `docs/learned/ci/automated-review-system.md` already provides comprehensive coverage of:
- Review bots overview (test-coverage, dignified-python, code-simplifier, tripwires, audit-pr-docs)
- How reviews are triggered
- Re-review triggers
- Bot thread inflation

**Action:** No new documentation needed. The existing doc is comprehensive.

### PR Address Workflow (Already Documented)

The gap analysis identified "PR address workflow" as needing documentation, but `docs/learned/erk/pr-address-workflows.md` already provides comprehensive coverage of:
- Local vs remote workflow decision matrix
- Usage patterns for `/erk:pr-address` and `erk launch pr-address`
- Plan review mode details
- Operational procedures

**Action:** No new documentation needed. The existing doc is comprehensive and recently audited (2026-02-16).
