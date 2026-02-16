---
title: GitHub API Diagnostics
last_audited: "2026-02-07 00:00 PT"
audit_result: clean
read_when:
  - debugging GitHub API failures
  - investigating repository-specific API issues
  - GitHub CLI commands returning unexpected errors
tripwires:
  - action: "assuming GitHub API failures are transient without repository-specific testing"
    warning: "Test with a control repository first. Some GitHub bugs affect specific repos but not others. Follow the 3-step diagnostic methodology."
---

# GitHub API Diagnostics

When GitHub API calls fail, the root cause isn't always what it seems. This document explains why repository-specific bugs exist, how to diagnose them, and what makes them different from transient failures.

## The Insight: Repository-Specific Bugs Are Real

GitHub's API can fail for **one repository** while working perfectly for others. This isn't network issues or rate limiting—it's bugs in GitHub's backend that only trigger under specific repository conditions (size, age, configuration, or unknown internal state).

**Why this matters**: The failure appears consistent (not transient), credentials work fine, and the GitHub status page shows no incidents. Without testing against a control repository, you'll waste time debugging your own code or retrying the same API call.

## Three-Step Diagnostic Methodology

### Step 1: Isolate from Erk Code

Use `gh api` directly to prove the failure is in GitHub's API, not erk's implementation:

```bash
# Example: Codespace machines endpoint
gh api "/repos/OWNER/REPO/codespaces/machines" --jq '.machines'
```

**Decision tree**:

- ✅ Success → Bug is in erk's code (proceed with standard debugging)
- ❌ HTTP 500/400 → Potential repository-specific GitHub bug (proceed to Step 2)
- ❌ HTTP 401/403 → Credential/permission issue (fix auth first)
- ❌ HTTP 404 → Endpoint doesn't exist or repository name is wrong

### Step 2: Test Control Repository

Create or use a minimal test repository and run the identical API call:

```bash
# Create test repo (or reuse existing small repo)
gh repo create test-repo-api-debug --private --confirm

# Try identical API call against test repo
gh api "/repos/YOUR_USERNAME/test-repo-api-debug/codespaces/machines" --jq '.machines'
```

**Decision tree**:

- ✅ Success on test repo + ❌ Failure on original repo → **Repository-specific bug confirmed**
- ❌ Failure on both → General API issue (check GitHub status, rate limits, auth)

### Step 3: Find REST API Workaround

Repository-specific bugs often affect **high-level convenience commands** (like `gh codespace create`) while **lower-level REST endpoints** still work. This is because convenience commands may use different API paths or aggregate multiple calls.

**Search strategy**:

1. Check GitHub REST API docs for alternative endpoints that accomplish the same operation
2. Try direct POST/GET with explicit parameters instead of convenience wrappers
3. Check if the operation can be decomposed into multiple API calls

## Why High-Level Commands Fail While REST Works

**The pattern**: GitHub CLI convenience commands (like `gh codespace create`) often:

1. Fetch metadata from one endpoint (e.g., list available machines)
2. Use that metadata to make the actual operation call

When **Step 1 is broken** (e.g., machines endpoint returns HTTP 500), the entire convenience command fails—even though the **actual creation endpoint works fine**.

**Workaround pattern**: Skip the broken metadata fetch and provide the required parameters directly to the operation endpoint.

<!-- Source: src/erk/cli/commands/codespace/setup_cmd.py, setup_codespace() and _get_repo_id() -->

**Example from erk codebase**: See `setup_codespace()` in `src/erk/cli/commands/codespace/setup_cmd.py`, which uses `POST /user/codespaces` with `repository_id` parameter instead of `gh codespace create` (which fails because the machines endpoint is broken for certain repositories).

## Repository-Specific Bug Catalog

### Machines Endpoint HTTP 500

**Symptoms**:

- `gh codespace create` fails with HTTP 500
- `GET /repos/{owner}/{repo}/codespaces/machines` returns HTTP 500
- Same call works fine on test repositories

**Workaround**: Use `POST /user/codespaces` with `repository_id` parameter instead of repository name.

**Why it works**: The creation endpoint doesn't depend on the broken machines endpoint—you provide the machine type directly.

### Large PR Diff Failures

**Symptoms**:

- `gh pr diff` returns HTTP 406 for PRs with >300 files
- Works fine on small PRs

**Workaround**: Use `GET /repos/{owner}/{repo}/pulls/{number}/files` with `--paginate` flag.

**Why it works**: The REST API supports pagination, splitting large responses into manageable chunks.

**Reference**: [GitHub CLI Limits](github-cli-limits.md)

### Large Repository GraphQL Timeouts

**Symptoms**:

- GraphQL queries timeout for repositories with >10k issues/PRs
- Same query structure works on smaller repositories

**Workaround**: Use REST API with pagination instead of GraphQL.

**Why it works**: REST API endpoints are optimized for large result sets with cursor-based pagination.

## When to Use This Methodology

Use the three-step diagnostic when **all of these are true**:

- ✅ GitHub API call fails consistently (not intermittent)
- ✅ Credentials and permissions are correct
- ✅ GitHub status page shows no incidents
- ✅ The same code/command works in other repositories

**Do NOT use this methodology for**:

- Transient network failures (retry instead)
- Auth/permission errors (fix credentials)
- Known API limits (use documented workarounds)

## Prevention: Test with Multiple Repositories

When implementing new GitHub API integrations:

1. **Test with diverse repositories** - Small repos, large repos, old repos, repos with unusual configurations
2. **Prefer REST over convenience commands** - REST APIs have better rate limits, pagination support, and fewer abstraction layers where bugs can hide
3. **Implement fallbacks early** - Don't wait for production failures to discover the need for workarounds
4. **Document discovered bugs** - Add to [GitHub CLI Limits](github-cli-limits.md) when repository-specific bugs are confirmed

## Related Documentation

- [GitHub CLI Limits](github-cli-limits.md) - Known gh command limitations and REST API workarounds
- [Codespace Patterns](../cli/codespace-patterns.md) - Codespace implementation patterns in erk
