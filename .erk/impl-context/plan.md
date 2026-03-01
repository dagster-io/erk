# External Learned Docs Repository

## Context

A user wants to experiment with learned docs on a project without anyone in the main repo knowing. The docs live in a completely separate repository that the user manages independently. The main project repo stays 100% untouched — no symlinks, no gitignore changes, no new directories.

The user discovers docs at runtime via personal `~/.claude/projects/<project>/CLAUDE.md` with `@` references pointing to the external repo's docs.

## Approach: Project Root Override

All three `erk docs` commands (`sync`, `validate`, `check`) start with `project_root = ctx.repo_root`. The feature adds a `[docs] path` config that overrides this to point at the external repo's local path.

**Config** (in `.erk/config.local.toml`, which is gitignored and per-user):
```toml
[docs]
path = "/Users/me/code/my-docs-repo"
```

The external repo has `docs/learned/` at its root (mirroring project layout). All existing operations work unchanged — they just resolve files from the external path instead of the main repo.

**What stays untouched:**
- `AgentDocs` ABC and all implementations — unchanged
- `operations.py` (866 lines) — unchanged
- Gateway, models, frontmatter parsing — unchanged
- The main project repo — zero modifications

## Implementation Steps

### 1. Add `docs_path` field to `LoadedConfig`

**File:** `packages/erk-shared/src/erk_shared/context/types.py`

Add `docs_path: str | None` to `LoadedConfig` (after `dispatch_ref`). Update `LoadedConfig.test()` factory to accept optional `docs_path` defaulting to `None`.

### 2. Add `docs_path` to config schema

**File:** `packages/erk-shared/src/erk_shared/config/schema.py`

Add to `RepoConfigSchema`:
```python
docs_repo: str | None = Field(
    description="Local path to external repository containing docs/learned/",
    json_schema_extra={"level": ConfigLevel.REPO_ONLY, "cli_key": "docs.path"},
)
```

### 3. Parse `[docs] path` from config files

**File:** `src/erk/cli/config.py`

In `_parse_config_file()`, add after the `[plans]` section parsing:
```python
docs = data.get("docs", {})
docs_path = docs.get("path")
if docs_path is not None:
    docs_path = str(docs_path)
```

Pass `docs_path` to `LoadedConfig` constructor. Thread through:
- `_parse_config_file()` return value
- `load_config()` and `load_local_config()` default returns
- `merge_configs()` — `docs_path` is repo-level only, pass through from `repo_config`
- `merge_configs_with_local()` — local overrides base if set

### 4. Create `resolve_docs_project_root()` helper

**File:** `src/erk/agent_docs/operations.py`

Add at the top of the module (after imports):
```python
def resolve_docs_project_root(*, repo_root: Path, docs_path: str | None) -> Path:
    """Resolve the project root for docs operations.

    When docs_path is configured, docs operations target the external
    repo instead of the main project repo.
    """
    if docs_path is None:
        return repo_root
    path = Path(docs_path)
    if not path.exists():
        raise click.ClickException(
            f"Configured docs.path does not exist: {docs_path}"
        )
    return path
```

### 5. Use `resolve_docs_project_root()` in CLI commands

**Files:**
- `src/erk/cli/commands/docs/sync.py` — line 41
- `src/erk/cli/commands/docs/validate.py` — line 37
- `src/erk/cli/commands/docs/check.py` — line 31

Change from:
```python
project_root = ctx.repo_root
```
To:
```python
project_root = resolve_docs_project_root(
    repo_root=ctx.repo_root,
    docs_path=ctx.local_config.docs_path,
)
```

## Files Modified

| File | Change |
|------|--------|
| `packages/erk-shared/src/erk_shared/context/types.py` | Add `docs_path` to `LoadedConfig` |
| `packages/erk-shared/src/erk_shared/config/schema.py` | Add `docs_path` to `RepoConfigSchema` |
| `src/erk/cli/config.py` | Parse `[docs] path`, thread through merge functions |
| `src/erk/agent_docs/operations.py` | Add `resolve_docs_project_root()` helper |
| `src/erk/cli/commands/docs/sync.py` | Use `resolve_docs_project_root()` |
| `src/erk/cli/commands/docs/validate.py` | Use `resolve_docs_project_root()` |
| `src/erk/cli/commands/docs/check.py` | Use `resolve_docs_project_root()` |

## No New Files

The entire feature is ~30 lines of new code across existing files.

## Verification

1. **Config parsing:** Set `[docs] path = "/tmp/test-docs"` in `.erk/config.local.toml`, verify `erk config keys` shows `docs.path`
2. **Setup external repo:** Create a test repo with `docs/learned/` containing a doc with valid frontmatter
3. **Sync:** Run `erk docs sync` — should operate on the external repo
4. **Validate:** Run `erk docs validate` — should validate external repo docs
5. **Check:** Run `erk docs check` — should check external repo
6. **Error handling:** Configure a non-existent path, verify clear error message
7. **No config:** Remove `[docs]` section, verify commands fall back to `ctx.repo_root`
8. **Tests:** Add config parsing test for `docs_path`; test `resolve_docs_project_root()` with both None and configured paths
