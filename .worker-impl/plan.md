# Plan: Move Real* Tests to `tests/real/`

Part of Objective #7129, Steps 2.1, 2.2, 2.3

## Context

Objective #7129 targets eliminating excessive mocking from unit tests. Steps 2.1-2.3 (Phase 2) involve `tests/unit/test_subprocess.py`, `tests/unit/operations/test_real_git.py`, and `tests/unit/operations/test_real_graphite.py` — all of which test Real* gateway implementations by mocking subprocess.

Rather than refactoring these tests to use fakes (which doesn't make sense — Real* implementations inherently require mocking the external tools they wrap), the solution is organizational: move all Real* tests to a dedicated `tests/real/` directory. This acknowledges they serve a different purpose (verifying command construction and output parsing) than the fake-based unit tests.

## Files to Move

| Source | Destination | Rename Reason |
|--------|------------|---------------|
| `tests/unit/operations/test_real_git.py` | `tests/real/test_real_git.py` | Name unchanged |
| `tests/unit/operations/test_real_graphite.py` | `tests/real/test_real_graphite.py` | Name unchanged |
| `tests/unit/test_subprocess.py` | `tests/real/test_subprocess.py` | Name unchanged |
| `tests/unit/gateways/gt/test_real_ops.py` | `tests/real/test_real_gt_kit.py` | Rename for clarity (matches `RealGtKit`) |
| `tests/unit/agent_docs/test_real.py` | `tests/real/test_real_agent_docs.py` | Rename for clarity (matches `RealAgentDocs`) |

**Total: 5 files, 43 tests**

## Implementation Steps

### Step 1: Create `tests/real/` directory structure

Create:
- `tests/real/__init__.py`
- `tests/real/CLAUDE.md` — brief doc explaining what "real" tests are and when to add tests here

### Step 2: Move and rename files

Use `git mv` to preserve history:
- `git mv tests/unit/operations/test_real_git.py tests/real/test_real_git.py`
- `git mv tests/unit/operations/test_real_graphite.py tests/real/test_real_graphite.py`
- `git mv tests/unit/test_subprocess.py tests/real/test_subprocess.py`
- `git mv tests/unit/gateways/gt/test_real_ops.py tests/real/test_real_gt_kit.py`
- `git mv tests/unit/agent_docs/test_real.py tests/real/test_real_agent_docs.py`

No import changes needed — these files import from `erk_shared` (not relative imports) and have no conftest dependencies.

### Step 3: Clean up empty `tests/unit/operations/` directory

After moving, `tests/unit/operations/` will be empty (only `__init__.py` remains). Remove the directory.

`tests/unit/agent_docs/` and `tests/unit/gateways/gt/` both have other files, so they stay.

### Step 4: Update Makefile

Add `tests/real/` to all targets that currently include `tests/unit/`:

```makefile
test-unit-erk:
	uv run pytest tests/unit/ tests/commands/ tests/core/ tests/real/ -n auto
```

Update all 4 occurrences in the Makefile (lines 37, 87, 102, 118).

### Step 5: Update test documentation

Update `tests/AGENTS.md` (and `tests/CLAUDE.md` which references it):
- Add `tests/real/` to the test directory structure diagram
- Add a "Layer" description for real tests
- Update the layer boundaries diagram

### Step 6: Update `tests/unit/AGENTS.md`

Remove any references to Real* tests from the unit test documentation, since they've moved.

## Verification

1. Run `make test` — should pass with `tests/real/` included
2. Run `pytest tests/real/ -v` — verify all 43 tests pass
3. Run `pytest tests/unit/ -v` — verify no real tests remain
4. Verify `git status` shows clean moves (no untracked files left behind)

## Files Modified

- **Created**: `tests/real/__init__.py`, `tests/real/CLAUDE.md`
- **Moved**: 5 test files (see table above)
- **Edited**: `Makefile` (add `tests/real/` to pytest paths)
- **Edited**: `tests/AGENTS.md` (update directory structure docs)
- **Removed**: `tests/unit/operations/` (empty after move)