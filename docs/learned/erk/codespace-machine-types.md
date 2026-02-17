---
title: Codespace Machine Types
read_when:
  - "creating or configuring codespaces"
  - "choosing a machine type for codespace setup"
  - "debugging codespace creation failures"
tripwires:
  - action: "using `gh codespace create` to create a codespace"
    warning: "The machines endpoint returns HTTP 500 for this repo. Use `POST /user/codespaces` REST API directly. See the workaround section below."
last_audited: "2026-02-17 00:00 PT"
audit_result: clean
---

# Codespace Machine Types

## Why `POST /user/codespaces` Instead of `gh codespace create`

<!-- Source: src/erk/cli/commands/codespace/setup_cmd.py, setup_codespace -->

GitHub's REST endpoint `GET /repos/{owner}/{repo}/codespaces/machines` returns HTTP 500 for certain repositories, including the erk repository. Since `gh codespace create` calls that endpoint for machine type validation before creating anything, the entire command fails. This is a server-side GitHub bug — the endpoint works for some repos but not others, with no documented pattern for which ones fail.

The workaround bypasses validation entirely: `erk codespace setup` posts directly to `POST /user/codespaces` with the machine type as a raw string parameter and the repository's database ID. This means invalid machine type names produce a creation-time error rather than a pre-validation error, but in practice the set of valid machine types rarely changes.

This is one instance of a broader pattern where `gh` CLI subcommands make implicit API calls that fail. See [GitHub CLI Limits](../architecture/github-cli-limits.md) for the general pattern and other affected commands.

## Machine Type Selection

Claude Code agent sessions are memory-intensive — smaller machine types cause OOM kills during long sessions with large context windows. The default is `premiumLinux` for this reason.

| Machine Name        | CPUs | RAM   | Storage | When to use                                  |
| ------------------- | ---- | ----- | ------- | -------------------------------------------- |
| `basicLinux32gb`    | 2    | 8 GB  | 32 GB   | Quick validation only, not agent sessions    |
| `standardLinux32gb` | 4    | 16 GB | 64 GB   | Lightweight tasks without Claude Code        |
| `premiumLinux`      | 8    | 32 GB | 64 GB   | **Default** — standard agent session machine |
| `largePremiumLinux` | 16   | 64 GB | 64 GB   | Parallel agent workloads or large monorepos  |

Override the default via `erk codespace setup --machine <name>`.

## Related Documentation

- [Codespace Remote Execution](codespace-remote-execution.md) — Streaming command execution pattern
- [Codespace Gateway](../gateway/codespace-gateway.md) — Gateway ABC for codespace operations
- [Codespace Patterns](../cli/codespace-patterns.md) — `resolve_codespace()` helper usage
- [GitHub CLI Limits](../architecture/github-cli-limits.md) — Broader pattern of `gh` subcommand failures from implicit API calls
