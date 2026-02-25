---
title: OAuth Secret Management
read_when:
  - "working with erk admin gh-actions-api-key command"
  - "understanding API key vs OAuth token precedence"
  - "adding new secret types to admin commands"
tripwires:
  - action: "adding a new secret type without updating _SecretConfig pattern"
    warning: "Use the _SecretConfig frozen dataclass pattern for parameterized secret behavior. See admin.py for the existing pattern."
---

# OAuth Secret Management

The `erk admin gh-actions-api-key` command manages authentication secrets for GitHub Actions, supporting both API keys and OAuth tokens with clear precedence rules.

## Secret Configuration

The `_SecretConfig` frozen dataclass (`src/erk/cli/commands/admin.py`) parameterizes behavior based on the target secret:

<!-- Source: src/erk/cli/commands/admin.py, _SecretConfig -->

See `_SecretConfig` in `src/erk/cli/commands/admin.py`.

Two configurations exist:

| Config            | `github_secret_name`      | `local_env_var`                      | `other_github_secret_name` |
| ----------------- | ------------------------- | ------------------------------------ | -------------------------- |
| API Key (default) | `ANTHROPIC_API_KEY`       | `GH_ACTIONS_ANTHROPIC_API_KEY`       | `CLAUDE_CODE_OAUTH_TOKEN`  |
| OAuth (`--oauth`) | `CLAUDE_CODE_OAUTH_TOKEN` | `GH_ACTIONS_CLAUDE_CODE_OAUTH_TOKEN` | `ANTHROPIC_API_KEY`        |

## Precedence Rules

When both secrets are set, `ANTHROPIC_API_KEY` takes precedence:

<!-- Source: src/erk/cli/commands/admin.py, _compute_active_label -->

See `_compute_active_label()` in `src/erk/cli/commands/admin.py`. It returns a label indicating which secret takes precedence (`ANTHROPIC_API_KEY` wins when both are set).

## Auto-Switch Behavior

Setting one secret type deletes the other to avoid ambiguity:

- Setting API key deletes OAuth token
- Setting OAuth token deletes API key

This ensures exactly one authentication method is active at any time.

## The `--oauth` Flag

```bash
erk admin gh-actions-api-key set --oauth    # Target OAuth token
erk admin gh-actions-api-key status         # Shows both, marks active
erk admin gh-actions-api-key delete --oauth  # Delete OAuth token
```

The `status` subcommand displays both secrets with an "active" label indicating which takes effect.

## Related Topics

- [erk exec Commands](erk-exec-commands.md) - Full command reference
