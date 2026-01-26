# Plan: Move GitHubAdmin Gateway to gateway/github_admin/ (Phase 3 of #5930)

**Objective:** #5930 - Consolidate All Gateways into erk_shared/gateway/
**Step:** 3.1 (Phase 3 complete in one PR - all steps 3.1-3.4 together)

## Goal

Move all GitHubAdmin gateway code to `erk_shared/gateway/github_admin/` and update ALL import sites. No backward compatibility re-exports.

## Files to Create

Create new directory: `packages/erk-shared/src/erk_shared/gateway/github_admin/`

| File | Source | Notes |
|------|--------|-------|
| `__init__.py` | New | Package docstring following github pattern |
| `abc.py` | `erk_shared/github_admin/abc.py` | Move as-is |
| `fake.py` | `erk_shared/github_admin/fake.py` | Update import from `.abc` |
| `real.py` | `src/erk/core/implementation_queue/github/real.py` | Update import from new location |
| `noop.py` | `src/erk/core/implementation_queue/github/noop.py` | Update import from new location |
| `printing.py` | `src/erk/core/implementation_queue/github/printing.py` | Update import from new location |

## Files to Delete

After moving:
- `packages/erk-shared/src/erk_shared/github_admin/` (entire directory)
- `src/erk/core/implementation_queue/github/` (entire directory)

## Import Sites to Update (13 files)

### erk-shared package (4 files)

| File | Old Import | New Import |
|------|-----------|------------|
| `packages/.../context/context.py:44` | `from erk_shared.github_admin.abc import GitHubAdmin` | `from erk_shared.gateway.github_admin.abc import GitHubAdmin` |
| `packages/.../context/testing.py:89` | `from erk_shared.github_admin.fake import FakeGitHubAdmin` | `from erk_shared.gateway.github_admin.fake import FakeGitHubAdmin` |
| `packages/.../context/factories.py:86` | `from erk_shared.github_admin.fake import FakeGitHubAdmin` | `from erk_shared.gateway.github_admin.fake import FakeGitHubAdmin` |

### src/erk (3 files)

| File | Old Import | New Import |
|------|-----------|------------|
| `src/erk/core/context.py:20` | `from erk.core.implementation_queue.github.real import RealGitHubAdmin` | `from erk_shared.gateway.github_admin.real import RealGitHubAdmin` |
| `src/erk/core/context.py:75` | `from erk_shared.github_admin.abc import GitHubAdmin` | `from erk_shared.gateway.github_admin.abc import GitHubAdmin` |
| `src/erk/core/context.py:117,246` | `from erk_shared.github_admin.fake import FakeGitHubAdmin` | `from erk_shared.gateway.github_admin.fake import FakeGitHubAdmin` |
| `src/erk/cli/commands/admin.py:10` | `from erk.core.implementation_queue.github.real import RealGitHubAdmin` | `from erk_shared.gateway.github_admin.real import RealGitHubAdmin` |
| `src/erk/core/health_checks.py:37` | `from erk_shared.github_admin.abc import GitHubAdmin` | `from erk_shared.gateway.github_admin.abc import GitHubAdmin` |

### tests (5 files)

| File | Old Import | New Import |
|------|-----------|------------|
| `tests/fakes/github_admin.py` | `from erk_shared.github_admin.fake import FakeGitHubAdmin` | `from erk_shared.gateway.github_admin.fake import FakeGitHubAdmin` |
| `tests/integration/test_real_github_admin.py` | `from erk.core.implementation_queue.github.real import RealGitHubAdmin` | `from erk_shared.gateway.github_admin.real import RealGitHubAdmin` |
| `tests/commands/admin/test_github_pr_setting.py` | `from tests.fakes.github_admin import FakeGitHubAdmin` | No change (re-export updated) |
| `tests/unit/core/test_health_checks_anthropic_api_secret.py` | `from erk_shared.github_admin.fake import FakeGitHubAdmin` | `from erk_shared.gateway.github_admin.fake import FakeGitHubAdmin` |
| `tests/unit/core/test_health_checks_erk_queue_pat_secret.py` | `from erk_shared.github_admin.fake import FakeGitHubAdmin` | `from erk_shared.gateway.github_admin.fake import FakeGitHubAdmin` |

## Implementation Steps

### Step 1: Create gateway/github_admin/ directory structure
1. Create `packages/erk-shared/src/erk_shared/gateway/github_admin/__init__.py`
2. Copy `abc.py` from `github_admin/` to `gateway/github_admin/`
3. Copy `fake.py` from `github_admin/` to `gateway/github_admin/` (update internal import)
4. Copy `real.py`, `noop.py`, `printing.py` from `src/erk/core/implementation_queue/github/` to `gateway/github_admin/` (update imports)

### Step 2: Update all import sites
Update all 13 files listed above with new import paths.

### Step 3: Delete old directories
1. Delete `packages/erk-shared/src/erk_shared/github_admin/` directory
2. Delete `src/erk/core/implementation_queue/github/` directory

### Step 4: Verification
1. Run `rg "from erk_shared.github_admin" --type py` - should return 0 results
2. Run `rg "from erk.core.implementation_queue.github" --type py` - should return 0 results
3. Run `make all-ci` - all tests pass

## Related Documentation

- Skills: `dignified-python`, `fake-driven-testing`
- Docs: `docs/learned/architecture/gateway-abc-implementation.md`

## Verification

```bash
# Verify no old imports remain
rg "from erk_shared\.github_admin" --type py
rg "from erk_shared import.*github_admin" --type py
rg "from erk\.core\.implementation_queue\.github" --type py

# Run full CI
make all-ci
```