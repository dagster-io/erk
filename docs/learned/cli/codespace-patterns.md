---
audit_result: edited
last_audited: '2026-02-08'
read_when:
- implementing CLI commands that use codespaces
- handling codespace name resolution with optional defaults
- bypassing GitHub API endpoint bugs
title: Codespace Patterns
---

# Codespace Patterns

Cross-cutting patterns for codespace CLI commands in erk.

## Resolution Pattern: Named vs Default

<!-- Source: src/erk/cli/commands/codespace/resolve.py, resolve_codespace() -->

The `resolve_codespace()` helper provides **three-way error messaging** that distinguishes between:

1. **Named lookup failure** — user requested a specific codespace that doesn't exist
2. **Default lookup failure** — a default is configured but the codespace was deleted
3. **No default set** — user didn't specify a name and no default exists

**Why three cases matter**: Users need different recovery paths. Missing named codespace → check spelling. Deleted default → old registration needs cleanup. No default → first-time setup flow.

See `resolve_codespace()` in `src/erk/cli/commands/codespace/resolve.py` for the implementation.

### Anti-Pattern: Generic "Not Found" Error

**WRONG:**

```
Error: Codespace not found
```

This forces users to guess whether they typed the name wrong, the registry is stale, or they haven't set up any codespaces yet.

**CORRECT:** Match the error to the specific resolution path (named lookup vs default lookup vs no default).

## Field Separation: name vs gh_name

<!-- Source: packages/erk-shared/src/erk_shared/gateway/codespace_registry/abc.py, RegisteredCodespace -->

The `RegisteredCodespace` type has two name fields:

- `name` — friendly identifier chosen by user (e.g., "my-codespace")
- `gh_name` — GitHub-assigned identifier (e.g., "user-codespace-abc123")

**Why the split**: GitHub generates opaque names for codespaces. Users need memorable names for CLI operations. The registry maps friendly names to GitHub names.

**Usage rule**: Always use `gh_name` for GitHub API calls (`gh codespace ssh -c {gh_name}`). Use `name` for user-facing output and registry lookups.

See `RegisteredCodespace` dataclass in `packages/erk-shared/src/erk_shared/gateway/codespace_registry/abc.py`.

## REST API Creation Workaround

<!-- Source: src/erk/cli/commands/codespace/setup_cmd.py, setup_codespace() -->

The `erk codespace setup` command creates codespaces via `POST /user/codespaces` with `repository_id` instead of using `gh codespace create`.

**Why bypass gh CLI**: The `gh codespace create` command internally calls the `/repositories/{repo}/codespaces/machines` endpoint, which returns HTTP 500 for certain repositories (GitHub API bug). The REST API accepts `repository_id` as an alternative parameter, skipping the broken endpoint entirely.

**Implementation**: Fetch repo ID via `gh api repos/{owner}/{repo} --jq .id`, then POST to `/user/codespaces` with `repository_id` in the payload.

See `setup_codespace()` in `src/erk/cli/commands/codespace/setup_cmd.py` for the full flow.

**Related**: [GitHub CLI Limits](../architecture/github-cli-limits.md) — Documents the machines endpoint bug in detail.

## Optional Codespace Flag Pattern

Commands that operate on codespaces typically accept an optional `--codespace` flag with fallback to default:

```python
@click.option("--codespace", "-c", "name", default=None, help="Codespace name.")
def my_command(ctx: ErkContext, name: str | None) -> None:
    codespace = resolve_codespace(ctx.codespace_registry, name)
    # Use codespace.gh_name for API calls, codespace.name for display
```

**Why optional with default**: Most users have a single codespace and don't want to type the name repeatedly. Power users with multiple codespaces can override with `--codespace`.

**Anti-pattern**: Required codespace argument forces users to type the name even when they only have one registered.

See usage in `src/erk/cli/commands/codespace/connect_cmd.py` and `src/erk/cli/commands/codespace/remove_cmd.py`.

## SSH Interactive Execution

<!-- Source: src/erk/cli/commands/codespace/connect_cmd.py, connect_codespace() -->

The `connect` command uses `exec_ssh_interactive()` to replace the erk process with an SSH session.

**Why exec, not subprocess**: The SSH session needs to take over stdin/stdout for interactive TUI usage (Claude Code's interactive mode). Using `subprocess.run()` would create a nested TTY environment with broken signal handling.

**Remote command construction**: The entire remote command string must be a single SSH argument. SSH concatenates multiple arguments with spaces, which breaks shell quoting.

```bash
# CORRECT: Single argument with bash -l -c
ssh codespace "bash -l -c 'git pull && claude'"

# WRONG: Multiple arguments lose grouping
ssh codespace bash -l -c 'git pull && claude'  # SSH runs: bash -l -c git pull && claude
```

See `connect_codespace()` in `src/erk/cli/commands/codespace/connect_cmd.py`.

## Related Documentation

- [GitHub CLI Limits](../architecture/github-cli-limits.md) — Machines endpoint HTTP 500 bug and workaround
- [GitHub API Diagnostics](../architecture/github-api-diagnostics.md) — Repository-specific API diagnostic methodology
- [Composable Remote Commands](../architecture/composable-remote-commands.md) — Template for remote commands using resolve_codespace()
