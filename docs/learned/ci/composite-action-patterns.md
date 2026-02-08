---
title: Composite Action Patterns
read_when:
  - creating reusable GitHub Actions setup steps
  - using erk-remote-setup composite action
  - understanding GitHub Actions composite patterns
tripwires:
  - "NEVER use the curl | bash install script for Claude Code in CI — it hangs unpredictably. Use direct GCS download via setup-claude-code action."
  - "NEVER duplicate secret validation across workflows — use erk-remote-setup's consolidated validation."
  - "NEVER skip cache keys for downloaded binaries — cache saves 10-20s per workflow run."
last_audited: "2026-02-08"
audit_result: regenerated
---

# Composite Action Patterns

GitHub Actions composite actions encapsulate reusable setup steps. Erk uses them to avoid duplicating 7-step setup sequences across remote AI workflows.

## Why Composite Actions Over Repeated Steps

**Problem**: Before erk-remote-setup, every remote workflow (plan-implement, pr-address, learn) duplicated the same 7 setup steps. Changes required editing 6+ workflow files.

**Solution**: Composite actions extract common setup into `.github/actions/*/action.yml`. Workflows call the composite action with secrets, getting consistent setup everywhere.

**Trade-off**: Composite actions can't access repository secrets directly — workflows must pass secrets as inputs. This is GitHub's security model: secrets live at workflow scope, not action scope.

<!-- Source: .github/actions/erk-remote-setup/action.yml, steps 1-7 -->

See the complete 7-step sequence in `.github/actions/erk-remote-setup/action.yml`.

## Secret Validation Pattern: Fail Fast with Context

Standard GitHub Actions workflow errors are opaque: "Secret not found" doesn't tell you which secret or which step failed.

**Pattern**: Validate all required secrets in the first composite action step with explicit error titles.

<!-- Source: .github/actions/erk-remote-setup/action.yml, Validate secrets step -->

Benefits:
- **Fails within 5 seconds** instead of after 2 minutes of setup
- **Clear error titles** in GitHub UI (visible without expanding logs)
- **Named secrets** make it obvious which credential is missing

This pattern is cheap (bash string check) and saves 2+ minutes when credentials are misconfigured.

## Claude Code Installation: Why Not curl | bash

The standard Claude Code install method (`curl -fsSL https://claude.ai/install.sh | bash`) hangs in CI environments, sometimes for hours before timeout.

**Root causes** (from GitHub issue triage):
1. Install script spawns subprocesses that hang indefinitely
2. Lock files at `~/.local/state/claude/locks/` persist after timeout
3. No built-in timeout or retry in install script

**Solution**: Download the binary directly from GCS, bypassing the install script entirely.

<!-- Source: .github/actions/setup-claude-code/action.yml, WHY DIRECT DOWNLOAD comment -->

The action:
1. Fetches stable version from `https://storage.googleapis.com/.../stable`
2. Downloads platform-specific binary (linux-x64 or linux-arm64)
3. Cleans stale lock files before installation
4. Caches binary with runner OS/arch key

This approach is proven by the community (alonw0/cc-versions) and eliminates the most common CI hang in erk workflows.

**Why native binary**: Anthropic is releasing features that require the native binary installation (not npm package). Future-proofing by using the GCS distribution now.

## Caching Pattern: Binary Downloads

GitHub Actions cache saves 10-20 seconds per workflow run by avoiding repeated downloads.

**Key structure**: `tool-name-${{ runner.os }}-${{ runner.arch }}-v1`

The cache key includes:
- **Runner OS**: `linux` vs `darwin` (though erk only uses linux runners)
- **Runner arch**: `x64` vs `arm64` (GitHub provides both)
- **Version suffix**: `-v1` for cache busting when the binary changes

<!-- Source: .github/actions/setup-claude-code/action.yml, Cache Claude Code binary step -->

**Cache miss behavior**: Download only when `steps.cache.outputs.cache-hit != 'true'`. This conditional prevents redundant downloads when cache hits.

**Why not version in key**: Claude Code's "stable" version changes frequently. Using a static `-v1` suffix means the cache stays warm across version bumps. When a breaking change requires cache invalidation, bump the suffix to `-v2`.

## Worker Implementation Check: CI Skip Pattern

Erk's remote workflows create `.worker-impl/` folders during AI implementation. CI should skip these branches until implementation completes.

**Pattern**: Composite action with conditional output.

<!-- Source: .github/actions/check-worker-impl/action.yml, Check for worker implementation folder step -->

Workflow usage:

```yaml
- uses: ./.github/actions/check-worker-impl
  id: worker-check

- name: Run tests
  if: steps.worker-check.outputs.skip != 'true'
  run: pytest
```

**Why this works**: The output is a string (`"true"` or `"false"`), not a boolean. GitHub Actions requires string comparison for step outputs.

**Why not a single workflow-level condition**: Some steps (git operations, metadata collection) should run even when `.worker-impl/` exists. The granular `if:` conditions let workflows choose which steps to skip.

## Conditional Erk Installation: Package vs Tool Mode

Erk runs in two installation modes depending on repository structure:
- **Package mode**: `packages/erk-shared/` exists → editable install with shared packages
- **Tool mode**: No shared packages → sync dev dependencies to `.venv/`

<!-- Source: .github/actions/erk-remote-setup/action.yml, Install erk step -->

**Why the branch**: Package mode uses `uv tool install -e` to make erk globally available. Tool mode uses `uv sync` and adds `.venv/bin` to PATH. The shared package scenario requires editable installs to pick up local changes.

This pattern handles both erk's own CI (which has erk-shared) and external projects that depend on erk (which don't).

## Composite Action Anti-Patterns

### DON'T: Return Computed Values via Outputs

Composite actions **can't** run conditional logic that agents need. They return strings, not structured data.

**WRONG**: Action that parses workflow state and returns "should_skip" or "safe_to_deploy"
**CORRECT**: Action that returns raw data (folder exists, file hash) — let workflow decide what to do

Agents can't introspect composite action internals during implementation. If the decision logic lives in the action, agents can't reason about it when debugging workflow behavior.

### DON'T: Chain Composite Actions with Implicit Dependencies

If action B depends on action A's PATH modifications, **document the dependency explicitly** in action B's description.

**WRONG**: setup-claude-erk silently assumes claude binary exists in PATH
**CORRECT**: setup-claude-erk description says "assumes uv/claude exist" and erk-remote-setup calls actions in required order

GitHub Actions doesn't validate composite action dependencies. Undocumented dependencies cause silent failures when actions are reused in new contexts.

### DON'T: Duplicate Setup Across Actions

If two actions both need Python, **don't** run setup-python twice. Create a setup-python-uv action that other actions depend on.

Duplication wastes CI minutes and creates version skew when one action updates Python version but another doesn't.

## Creating New Actions: Decision Checklist

Before creating a new composite action:

1. **Is this setup used in 3+ workflows?** → If no, inline the steps
2. **Will this setup change together?** → If no, keep separate (e.g., Python vs Claude Code)
3. **Can this fail independently?** → If yes, separate action for better error messages

Composite actions add indirection. Only extract when the DRY benefits outweigh the debugging cost.

## Related Documentation

- [GitHub Actions Workflow Patterns](github-actions-workflow-patterns.md) — Workflow-level patterns
- [Containerless CI](containerless-ci.md) — Why erk uses direct installs instead of containers
- [Plan Implement Customization](plan-implement-customization.md) — How workflows consume these actions
