---
title: Exec Script Environment Requirements
read_when:
  - "adding or modifying exec scripts that call Claude"
  - "debugging missing API key errors in CI workflows"
  - "adding new workflow steps that run exec scripts"
tripwires:
  - action: "adding or modifying exec scripts that use require_prompt_executor()"
    warning: "Ensure workflow step has ANTHROPIC_API_KEY in environment. See exec-script-environment-requirements.md"
  - action: "adding new Claude-dependent exec scripts to workflows"
    warning: "Check workflow environment: ANTHROPIC_API_KEY, GH_TOKEN, CLAUDE_CODE_OAUTH_TOKEN"
---

# Exec Script Environment Requirements

Exec scripts that call Claude need specific environment variables in their workflow steps. Missing variables cause silent failures or cryptic errors.

## The Core Rule

When an exec script calls `require_prompt_executor()`, its workflow step **must** have `ANTHROPIC_API_KEY` in its environment. This applies even if the script doesn't invoke `claude` directly -- the PromptExecutor abstraction handles the API call internally.

## Scripts Requiring ANTHROPIC_API_KEY

> **Note:** This table may be incomplete. To find the current list, run:
> `grep -rl 'require_prompt_executor' src/erk/cli/commands/exec/scripts/`

| Script                               | Command Name                      | Uses                        |
| ------------------------------------ | --------------------------------- | --------------------------- |
| `generate_pr_address_summary.py`     | `generate-pr-address-summary`     | `require_prompt_executor()` |
| `rebase_with_conflict_resolution.py` | `rebase-with-conflict-resolution` | `require_prompt_executor()` |
| `ci_update_pr_body.py`               | `ci-update-pr-body`               | `require_prompt_executor()` |
| `run_review.py`                      | `run-review`                      | `require_prompt_executor()` |

## Workflow Step Checklist

When adding a workflow step that runs an exec script:

| Variable                  | When Needed                                           | Source                                                     |
| ------------------------- | ----------------------------------------------------- | ---------------------------------------------------------- |
| `ANTHROPIC_API_KEY`       | Script calls `require_prompt_executor()`              | `${{ secrets.ANTHROPIC_API_KEY }}`                         |
| `GH_TOKEN`                | Script calls `require_github()` or `require_issues()` | `${{ github.token }}` or `${{ secrets.ERK_QUEUE_GH_PAT }}` |
| `CLAUDE_CODE_OAUTH_TOKEN` | Direct `claude` CLI invocation in workflow            | `${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}`                   |

**Distinction:** `ANTHROPIC_API_KEY` is for exec scripts that use the PromptExecutor abstraction. `CLAUDE_CODE_OAUTH_TOKEN` is for steps that invoke the `claude` CLI binary directly. Both may be needed in the same workflow but typically in different steps.

## Context Dependency Pattern

Exec scripts use typed dependency injection via Click context helpers in `packages/erk-shared/src/erk_shared/context/helpers.py`:

```python
@click.command()
@click.pass_context
def my_exec_script(ctx: click.Context) -> None:
    executor = require_prompt_executor(ctx)  # needs ANTHROPIC_API_KEY
    repo_root = require_repo_root(ctx)       # needs git repo
    backend = require_plan_backend(ctx)      # needs GH_TOKEN
    time = require_time(ctx)                 # no external deps
```

Each `require_*` helper checks `ctx.obj` is initialized and returns a typed dependency. If the required environment variable is missing, the context initialization fails with a clear error.

## Workflow Examples

**Correct -- exec script with API key:**

```yaml
- name: Generate summary
  env:
    GH_TOKEN: ${{ github.token }}
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
  run: |
    git diff "$PRE_HEAD"..HEAD | erk exec generate-pr-address-summary \
      --pr-number "$PR_NUMBER" --model-name "$MODEL_NAME"
```

**Correct -- setup action passes key:**

```yaml
- uses: ./.github/actions/erk-remote-setup
  with:
    erk-pat: ${{ secrets.ERK_QUEUE_GH_PAT }}
    anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
    claude-code-oauth-token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
```

## Workflows Using ANTHROPIC_API_KEY

To find the current list of workflows using this key:

```bash
grep -rl 'ANTHROPIC_API_KEY' .github/workflows/
```

## Related Topics

- [GitHub Actions Claude Integration](github-actions-claude-integration.md) -- direct Claude CLI invocation patterns
- [Exec Script Testing](../testing/exec-script-testing.md) -- testing exec scripts with fakes
