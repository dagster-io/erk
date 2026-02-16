---
title: GitHub Actions Claude Integration
read_when:
  - "running Claude in GitHub Actions workflows"
  - "configuring non-interactive Claude execution"
  - "capturing Claude output in CI"
last_audited: "2026-02-05 14:24 PT"
audit_result: edited
---

# GitHub Actions Claude Integration

Running Claude Code in GitHub Actions requires specific flags for non-interactive, permission-skipped execution.

## Required Flags

All Claude-invoking workflows use the same four flags: `--print`, `--verbose`, `--output-format stream-json`, and `--dangerously-skip-permissions`. See `.github/workflows/learn.yml` for a canonical working example.

### Critical: --verbose Is Required for stream-json

The `--output-format stream-json` option **requires** `--verbose`. Without it, the command fails silently or with a cryptic error.

```bash
# WRONG: Fails
claude --print --output-format stream-json ...

# CORRECT: Include --verbose
claude --print --verbose --output-format stream-json ...
```

## Environment Variables

Workflows require `ANTHROPIC_API_KEY` and `GH_TOKEN` (or `GITHUB_TOKEN`). Some workflows also use `CLAUDE_CODE_OAUTH_TOKEN` for authenticated Claude Code access.

## Model Selection

All Claude-invoking workflows default to `claude-opus-4-6`. See [Workflow Model Policy](workflow-model-policy.md) for the standardization rationale, affected workflows, and the distinction between workflow models and review models.

## Common Errors

| Error                            | Cause                                    | Fix                    |
| -------------------------------- | ---------------------------------------- | ---------------------- |
| "stream-json requires --verbose" | Missing `--verbose` flag                 | Add `--verbose`        |
| "Permission denied"              | Missing `--dangerously-skip-permissions` | Add the flag           |
| No output captured               | Missing `--print`                        | Add `--print`          |
| Authentication failed            | Missing `ANTHROPIC_API_KEY`              | Add secret to workflow |

## Exec Script Environment Distinction

Not all Claude usage in workflows is direct `claude` CLI invocation. Exec scripts that internally call Claude via `require_prompt_executor()` need `ANTHROPIC_API_KEY` in their workflow step's environment, even though they don't invoke `claude` directly.

| Usage Type                      | Token Needed                                    | Example                                 |
| ------------------------------- | ----------------------------------------------- | --------------------------------------- |
| Direct `claude` CLI             | `CLAUDE_CODE_OAUTH_TOKEN` + `ANTHROPIC_API_KEY` | `claude --print "..."` in workflow step |
| Exec script with PromptExecutor | `ANTHROPIC_API_KEY`                             | `erk exec generate-pr-address-summary`  |
| Exec script without Claude      | Neither                                         | `erk exec impl-init`                    |

See [Exec Script Environment Requirements](exec-script-environment-requirements.md) for the complete inventory of scripts requiring API keys and the workflow step checklist.

## Related Topics

- [CI Prompt Patterns](prompt-patterns.md) - How to structure prompts for CI
- [Claude CLI Integration](../architecture/claude-cli-integration.md) - General Claude CLI patterns
- [Exec Script Environment Requirements](exec-script-environment-requirements.md) - Environment variables for exec scripts
