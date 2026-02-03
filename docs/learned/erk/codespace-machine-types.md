---
title: Codespace Machine Types
read_when:
  - "creating or configuring codespaces"
  - "choosing a machine type for codespace setup"
  - "working with codespace setup command"
---

# Codespace Machine Types

GitHub Codespaces machine types available for erk, with their hardware specifications.

## Available Machine Types

| Machine Name        | CPUs | RAM   | Storage | Notes                     |
| ------------------- | ---- | ----- | ------- | ------------------------- |
| `basicLinux32gb`    | 2    | 8 GB  | 32 GB   | Cheapest option           |
| `standardLinux32gb` | 4    | 16 GB | 64 GB   | Standard dev              |
| `premiumLinux`      | 8    | 32 GB | 64 GB   | Default for erk codespace |
| `largePremiumLinux` | 16   | 64 GB | 64 GB   | Largest available         |

## Default Machine Type

The `erk codespace setup` command defaults to `premiumLinux`. This is defined as `DEFAULT_MACHINE_TYPE` in `src/erk/cli/commands/codespace/setup_cmd.py`.

Override with `--machine`:

```bash
erk codespace setup mybox --machine largePremiumLinux
```

## Machines Endpoint Bug

The GitHub REST API endpoint `GET /repos/{owner}/{repo}/codespaces/machines` returns HTTP 500 for `dagster-io/erk`. This is a GitHub server-side bug. The `erk codespace setup` command works around this by using `POST /user/codespaces` directly instead of `gh codespace create` (which calls the broken machines endpoint for validation).

## Related Documentation

- [Codespace Remote Execution](codespace-remote-execution.md) - Streaming command execution pattern
- [Codespace Gateway](../gateway/codespace-gateway.md) - Gateway ABC for codespace operations
- [Codespace Patterns](../cli/codespace-patterns.md) - `resolve_codespace()` helper usage
