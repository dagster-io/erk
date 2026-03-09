# Plan: Integrate npx skills into erk init and install

## Context

This PR added the `SkillsCli` gateway wrapping `npx skills` from vercel-labs/skills. The gateway is wired into `ErkContext` but not yet used. This change integrates it into `erk init` and `erk init --upgrade` to **replace** the bundled skill file-copy sync with `npx skills add`.

The erk repo itself serves as the skills source. Skills install to `.agents/skills/` (the standard skills directory per the skills CLI convention) instead of `.claude/skills/`.

## Changes

### 1. Add `cwd` parameter to SkillsCli gateway

The skills CLI installs relative to CWD. We need `cwd` so init can direct installation to the target repo root.

**`packages/erk-shared/src/erk_shared/gateway/skills_cli/abc.py`** — Add `cwd: Path | None` to `add_skills()` and `remove_skills()`.

**`packages/erk-shared/src/erk_shared/gateway/skills_cli/real.py`** — Pass `cwd` through to `run_subprocess_with_context()` (which already supports it).

**`packages/erk-shared/src/erk_shared/gateway/skills_cli/fake.py`** — Add `cwd` to `AddSkillsCall` / `RemoveSkillsCall` dataclasses. Record in tracking.

**`packages/erk-shared/src/erk_shared/gateway/skills_cli/types.py`** — Add `backend_to_skills_agent()` mapping:
- `"claude"` → `"claude-code"`
- `"codex"` → `"codex"`

### 2. Add `skip_skills` to `ArtifactSyncConfig`

**`src/erk/artifacts/sync.py`**:
- Add `skip_skills: bool` field to `ArtifactSyncConfig` (line 47)
- Update `create_artifact_sync_config()` to accept `skip_skills` parameter
- Wrap skills sync block (lines 762-770) in `if not config.skip_skills:`
- Wrap skills hash block in `_compute_source_artifact_state()` (lines 541-544) similarly

### 3. Add skills source path utility

**`src/erk/artifacts/paths.py`** — Add `get_skills_source_path() -> Path | None`:
- Editable installs: returns erk repo root (`_get_erk_package_dir().parent.parent`)
- Wheel installs: returns `None` (not yet supported — fall back to bundled sync)

### 4. Wire npx skills into `run_init()`

**`src/erk/cli/commands/init/main.py`**:

Add helper function `_install_skills_via_npx(skills_cli, *, repo_root, backend) -> bool`:
1. LBYL: `skills_cli.is_available()` — if False, warn and return False
2. LBYL: `get_skills_source_path()` — if None (wheel install), warn and return False
3. Get skill names from `bundled_skills().keys()`
4. Map backend via `backend_to_skills_agent()`
5. Call `skills_cli.add_skills(source=..., skill_names=..., agents=[...], cwd=repo_root)`
6. Return True on success, False on failure (caller falls back to bundled sync)

Wire into both init paths:
- **Fresh init** (~line 628): Call before `sync_artifacts`, set `skip_skills=npx_success`
- **Upgrade** (~line 551): Same pattern
- **Skip when `in_erk_repo`**: Skills already exist at source in dogfooding mode

### 5. Add `skills_cli` param to `context_for_test()`

**`src/erk/core/context.py`** — Add `skills_cli: SkillsCli | None = None` parameter to `context_for_test()` (line 210). Default to `FakeSkillsCli(available=True)` when None.

### 6. Update tests

**Update existing**:
- `tests/artifacts/test_sync.py` — Add `skip_skills=False` to all 10 `ArtifactSyncConfig(...)` constructions. Add one test for `skip_skills=True`.
- `tests/artifacts/test_orphan_cleanup.py` — Add `skip_skills=False` to the 1 construction.
- `tests/unit/fakes/test_fake_skills_cli.py` — Add `cwd=None` to `add_skills`/`remove_skills` calls.
- `tests/integration/test_skills_cli.py` — Replace `os.chdir` hack with `cwd=temp_project` parameter.

**New test file** `tests/commands/setup/init/test_npx_skills.py`:
1. `test_npx_skills_unavailable` — FakeSkillsCli(available=False) → returns False, no calls made
2. `test_npx_skills_success` — verify add_calls has correct source, skill_names, agents, cwd
3. `test_npx_skills_failure` — add_result with success=False → returns False
4. `test_npx_skills_no_source` — wheel install (mock `get_skills_source_path` → None) → returns False

**New test** `tests/unit/gateway/test_skills_cli_types.py`:
- `test_backend_to_skills_agent_claude` — "claude" → "claude-code"
- `test_backend_to_skills_agent_codex` — "codex" → "codex"

## Critical files

| File | Change |
|------|--------|
| `packages/erk-shared/src/erk_shared/gateway/skills_cli/abc.py` | Add `cwd` param |
| `packages/erk-shared/src/erk_shared/gateway/skills_cli/real.py` | Thread `cwd` to subprocess |
| `packages/erk-shared/src/erk_shared/gateway/skills_cli/fake.py` | Track `cwd` in call records |
| `packages/erk-shared/src/erk_shared/gateway/skills_cli/types.py` | Add `backend_to_skills_agent()` |
| `src/erk/artifacts/paths.py` | Add `get_skills_source_path()` |
| `src/erk/artifacts/sync.py` | Add `skip_skills` to config and sync |
| `src/erk/cli/commands/init/main.py` | Add `_install_skills_via_npx`, wire into both paths |
| `src/erk/core/context.py` | Add `skills_cli` to `context_for_test()` |

## Known spike limitations

- **Wheel installs**: No skills source path available. Falls back to bundled artifact sync.
- **Dual directories**: Skills now install to `.agents/skills/` (npx) alongside existing `.claude/skills/` (bundled). Future work to clean up.
- **npx speed**: First run downloads from npm. Acceptable for init (one-time cost).

## Verification

1. Run `uv run pytest tests/artifacts/test_sync.py` — existing sync tests pass with new field
2. Run `uv run pytest tests/unit/fakes/test_fake_skills_cli.py` — fake tests pass with cwd
3. Run `uv run pytest tests/commands/setup/init/` — init tests pass
4. Run `uv run pytest tests/unit/gateway/test_skills_cli_types.py` — mapping tests pass
5. Manual: `erk init --no-interactive` in a test repo shows npx skills output
6. `uv run ruff check` and `uv run ty check` pass
