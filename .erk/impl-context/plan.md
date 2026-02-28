# Add `dispatch_ref` config to override workflow dispatch branch

## Context

When erk dispatches GitHub Actions workflows (plan-implement, one-shot, pr-address, pr-fix-conflicts, pr-rewrite, learn), it always resolves `ref` to the repository's default branch (master). This means GitHub runs the workflow YAML from master — not from a feature branch. If you're developing erk workflows on a branch, your changes are invisible until merged.

This change adds a `dispatch_ref` config key so consumers can override which branch's workflow YAML is used for all dispatches.

## Changes

### 1. Add `dispatch_ref` to `LoadedConfig`

**File:** `packages/erk-shared/src/erk_shared/context/types.py`

- Add `dispatch_ref: str | None` field to `LoadedConfig` (line ~285, alongside `prompt_learn_on_land`)
- Add parameter to `LoadedConfig.test()` factory with `None` default

### 2. Parse `dispatch_ref` from config

**File:** `src/erk/cli/config.py`

In `_parse_config_file()` (line 43-93):
- Parse `dispatch_ref = data.get("dispatch_ref")` as a top-level key (same pattern as `prompt_learn_on_land`)
- Pass to `LoadedConfig` constructor

In `merge_configs()` (line 243):
- Thread through: `dispatch_ref=repo_config.dispatch_ref` (repo-level only, no project override)

In `merge_configs_with_local()` (line 284):
- Local overrides base: `dispatch_ref = local_config.dispatch_ref if local_config.dispatch_ref is not None else base_config.dispatch_ref`

### 3. Pass `dispatch_ref` to workflow callers

All 4 call sites change `ref=None` → `ref=ctx.local_config.dispatch_ref`:

| File | Line | Current |
|------|------|---------|
| `src/erk/cli/commands/launch_cmd.py` | 38 | `_trigger_workflow` helper |
| `src/erk/cli/commands/launch_cmd.py` | 250 | learn workflow trigger |
| `src/erk/cli/commands/pr/dispatch_cmd.py` | 304 | plan dispatch |
| `src/erk/cli/commands/one_shot_dispatch.py` | 338 | one-shot dispatch |

The gateway's existing fallback handles the rest: `ref_value = ref if ref is not None else self._get_default_branch(repo_root)`. When `dispatch_ref` is `None` (unset), behavior is unchanged.

### 4. Config format

Top-level key in `.erk/config.toml` (same pattern as `prompt_learn_on_land`):

```toml
dispatch_ref = "update-erk-0.9.0"
```

Overridable in `.erk/config.local.toml` for per-user settings.

## Files modified

1. `packages/erk-shared/src/erk_shared/context/types.py` — add field
2. `src/erk/cli/config.py` — parse + merge
3. `src/erk/cli/commands/launch_cmd.py` — 2 call sites
4. `src/erk/cli/commands/pr/dispatch_cmd.py` — 1 call site
5. `src/erk/cli/commands/one_shot_dispatch.py` — 1 call site

## Verification

1. `make fast-ci` — unit tests + lint + type check
2. Set `dispatch_ref = "test-branch"` in `.erk/config.toml`, run `erk pr dispatch` with `--dry-run`, verify the ref value in dry-run output
3. Remove `dispatch_ref`, verify default branch behavior is unchanged
