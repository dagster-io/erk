---
title: dispatch_ref Configuration
read_when:
  - "configuring which branch workflow_dispatch targets"
  - "working with .erk/config.toml dispatch settings"
  - "debugging workflow dispatch targeting the wrong branch"
  - "using --ref CLI option to override dispatch branch per run"
  - "using --ref-current to dispatch against current branch"
tripwires:
  - action: "assuming dispatch_ref is project-level config"
    warning: "dispatch_ref is repo-level config (.erk/config.toml), overridable at local level (.erk/config.local.toml). It is not project-level."
  - action: "passing both --ref and --ref-current to a dispatch command"
    warning: "--ref and --ref-current are mutually exclusive. resolve_dispatch_ref() raises UsageError if both are provided."
---

# dispatch_ref Configuration

Override the default branch used for GitHub Actions `workflow_dispatch` events. By default, erk dispatches workflows against the repository's default branch (usually `master`). The `dispatch_ref` config allows targeting a different branch.

## Configuration

Top-level key in `.erk/config.toml`:

```toml
dispatch_ref = "my-custom-branch"
```

Can be overridden per-user in `.erk/config.local.toml`:

```toml
dispatch_ref = "my-dev-branch"
```

## Type Definition

<!-- Source: packages/erk-shared/src/erk_shared/context/types.py, LoadedConfig -->

`LoadedConfig` is a frozen dataclass with a `dispatch_ref: str | None` field. When `None`, the GitHub gateway calls `_get_default_branch()` via REST API to determine the repository's default branch. The result is cached per `repo_root` for the session.

## Config Loading

<!-- Source: src/erk/cli/config.py -->

Config loading reads `dispatch_ref` from TOML data, converting to `str` if present. Merge behavior: local config takes precedence over repo config when both are set.

## CLI `--ref` Override

All five dispatch commands accept a `--ref` option for per-run branch override:

```bash
erk one-shot "fix the auth bug" --ref my-feature-branch
erk launch pr-address --pr 123 --ref my-feature-branch
erk pr dispatch 456 --ref my-feature-branch
erk workflow smoke-test --ref my-feature-branch
erk objective plan 42 --one-shot --ref my-feature-branch
```

**Priority chain:** `--ref` CLI flag > config `dispatch_ref` > repository default branch

<!-- Source: src/erk/cli/commands/ref_resolution.py -->

All five commands use the shared `resolve_dispatch_ref()` function at `src/erk/cli/commands/ref_resolution.py` to resolve the ref once before dispatching.

## CLI `--ref-current` Convenience Flag

All five dispatch commands also accept `--ref-current` to dispatch against the currently checked-out branch:

```bash
erk one-shot "fix the auth bug" --ref-current
erk launch pr-address --pr 123 --ref-current
```

This is a shorthand for `--ref $(git branch --show-current)`. It reads the current branch via `ctx.git.branch.get_current_branch()`.

**Mutual exclusivity:** `--ref` and `--ref-current` cannot be used together. `resolve_dispatch_ref()` raises `UsageError` if both are provided.

**Detached HEAD:** Using `--ref-current` in a detached HEAD state raises a `UsageError` with a descriptive message, since there is no current branch to resolve.

## Call Sites

`dispatch_ref` is consumed at 5 locations, all using `resolve_dispatch_ref()` from `src/erk/cli/commands/ref_resolution.py` and passing the resolved ref to `github.trigger_workflow(ref=ref)`:

| Command                         | Context                                             |
| ------------------------------- | --------------------------------------------------- |
| `erk pr dispatch`               | Dispatching plans for remote implementation         |
| `erk one-shot`                  | Triggering one-shot workflows                       |
| `erk launch`                    | Triggering pr-fix-conflicts, pr-address, pr-rewrite |
| `erk workflow smoke-test`       | Testing workflow dispatch connectivity              |
| `erk objective plan --one-shot` | Dispatching objective-driven one-shot plans         |

## Gateway Integration

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/real.py -->

In `_dispatch_workflow_impl()`, if `ref` is provided it's used directly, bypassing the REST API call. When `None`, the gateway calls `_get_default_branch()` to fetch and cache the default branch.

## Two-Stage Plan Auto-Detection

When `erk pr dispatch` is called without explicit plan numbers, it detects the plan via two-stage fallback:

<!-- Source: src/erk/cli/commands/pr/dispatch_cmd.py, _detect_plan_number_from_context -->

See `_detect_plan_number_from_context()` in `src/erk/cli/commands/pr/dispatch_cmd.py` for the implementation.

**Stage 1**: Check local `.erk/impl-context/<branch>/ref.json` (no network). Fast path — works when a plan has been set up locally.

**Stage 2**: Call `resolve_plan_id_for_branch()` on the plan backend (GitHub API). Matches the branch name against open plan PRs. Used when no local impl-context exists (e.g., dispatching from a raw branch).

This two-stage pattern matches the `implement` and `land` commands for consistency.

## Related Documentation

- [Remote Workflow Template](remote-workflow-template.md) - How dispatched workflows execute
