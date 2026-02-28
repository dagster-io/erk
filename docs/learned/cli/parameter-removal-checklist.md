---
title: CLI Parameter Removal Checklist
read_when:
  - "removing a CLI parameter or option"
  - "deprecating a CLI flag"
  - "cleaning up unused CLI options"
tripwires:
  - action: "removing a CLI parameter without checking all consumers"
    warning: "When removing a CLI parameter, verify: (1) @click.option decorator, (2) function signature, (3) all call sites, (4) helper functions, (5) ctx.invoke calls. Then run erk-dev gen-exec-reference-docs."
---

# CLI Parameter Removal Checklist

When removing a CLI parameter, five locations must be checked. Missing any one causes runtime errors.

## 5-Step Verification

1. **@click.option decorator** — Remove the `@click.option('--flag-name', ...)` decorator
2. **Function signature** — Remove the parameter from the `def command(*, flag_name: type)` signature
3. **All call sites** — Grep for the parameter name across the codebase: `rg 'flag_name' src/ packages/`
4. **Helper functions** — Check any helper functions that receive the parameter from the command
5. **ctx.invoke calls** — Click `ctx.invoke()` forwards kwargs directly. Any name mismatch causes runtime `TypeError`

## Post-Removal

Run `erk-dev gen-exec-reference-docs` to regenerate reference documentation that may list the removed parameter.

## Example

PR #8130 removed `branch_slug` from `setup_impl`:

- Removed `@click.option('--branch-slug', ...)` from the script
- Removed `branch_slug` from function signature
- Updated all callers in slash commands that passed `--branch-slug`
- Verified no `ctx.invoke` calls referenced it

## Cross-Package Impact

CLI command changes in `src/erk/cli/` can silently break downstream packages:

- `packages/erkbot/` — May invoke CLI commands programmatically

Grep: `rg --type py 'CliRunner.*invoke.*cli' packages/`

Also grep `.github/workflows/*.yml` for stale command references after renames.
