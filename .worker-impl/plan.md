# Plan: Consolidate Gateways Phases 4-7

**Part of Objective #5930, Steps 4.1-4.3, 5.1-5.3, 6.1-6.3, 7.1-7.4**

## Overview

Move four gateways to `erk_shared/gateway/`:
- Phase 4: BranchManager (27 import sites)
- Phase 5: PromptExecutor (13 import sites)
- Phase 6: ClaudeInstallation (37 import sites)
- Phase 7: LiveDisplay (13 import sites)

Each phase = 1 PR. Total: 4 PRs.

## Design Decisions (from Objective)

- **No backward compatibility**: Update ALL import sites in same PR. No re-exports.
- **Fakes move with ABC**: Fake implementations move to gateway/, not tests/fakes/
- **One gateway per PR**: Minimize merge conflicts

---

## Phase 4: BranchManager Gateway (1 PR)

### Current Location
```
packages/erk-shared/src/erk_shared/branch_manager/
├── __init__.py
├── abc.py           # BranchManager ABC (13 methods)
├── types.py         # PrInfo dataclass
├── fake.py          # FakeBranchManager
├── factory.py       # create_branch_manager()
├── git.py           # GitBranchManager
└── graphite.py      # GraphiteBranchManager
```

### Target Location
```
packages/erk-shared/src/erk_shared/gateway/branch_manager/
├── __init__.py
├── abc.py
├── types.py
├── fake.py
├── factory.py
├── git.py
└── graphite.py
```

### Steps

1. **Move files**: `git mv erk_shared/branch_manager/ erk_shared/gateway/branch_manager/`
2. **Update internal imports**: Fix imports within the moved package
3. **Update 27 external import sites**:
   - `from erk_shared.branch_manager` → `from erk_shared.gateway.branch_manager`
4. **Delete old directory**: Already moved, verify no remnants
5. **Verify**: `make all-ci` passes, `rg "from erk_shared\.branch_manager" --type py` returns nothing

### Files to Modify (Import Updates)
- `src/erk/cli/commands/exec/scripts/exit_plan_mode_hook.py`
- `packages/erk-shared/src/erk_shared/context/helpers.py`
- `packages/erk-shared/src/erk_shared/context/context.py`
- `packages/erk-shared/src/erk_shared/gateway/gt/abc.py`
- `packages/erk-statusline/src/erk_statusline/context.py`
- `tests/unit/gateways/gt/fake_ops.py`
- `tests/unit/fakes/test_fake_branch_manager.py`
- `tests/unit/branch_manager/test_graphite_branch_manager.py`
- `tests/commands/test_create.py`

---

## Phase 5: PromptExecutor Gateway (1 PR)

### Current Location
```
packages/erk-shared/src/erk_shared/prompt_executor/
├── __init__.py
├── abc.py           # PromptExecutor ABC (1 method), PromptResult
├── fake.py          # FakePromptExecutor
└── real.py          # RealPromptExecutor (subprocess + retry)
```

### Target Location
```
packages/erk-shared/src/erk_shared/gateway/prompt_executor/
├── __init__.py
├── abc.py
├── fake.py
└── real.py
```

### Steps

1. **Move files**: `git mv erk_shared/prompt_executor/ erk_shared/gateway/prompt_executor/`
2. **Update internal imports**: Fix imports within the moved package
3. **Update 13 external import sites**:
   - `from erk_shared.prompt_executor` → `from erk_shared.gateway.prompt_executor`
4. **Delete old directory**: Already moved
5. **Verify**: `make all-ci` passes

### Files to Modify (Import Updates)
- `src/erk/cli/commands/exec/scripts/ci_update_pr_body.py`
- `packages/erk-shared/src/erk_shared/context/helpers.py`
- `packages/erk-shared/src/erk_shared/context/context.py`
- `src/erk/core/context.py`
- `packages/erk-shared/tests/` (2 test files)
- `tests/unit/cli/commands/exec/scripts/` (3 test files)

---

## Phase 6: ClaudeInstallation Gateway (1 PR)

### Current Location
```
packages/erk-shared/src/erk_shared/learn/extraction/claude_installation/
├── __init__.py
├── abc.py           # ClaudeInstallation ABC (12+ methods)
├── fake.py          # FakeClaudeInstallation
├── real.py          # RealClaudeInstallation
├── CLAUDE.md
└── AGENTS.md        # Domain documentation
```

### Target Location
```
packages/erk-shared/src/erk_shared/gateway/claude_installation/
├── __init__.py
├── abc.py
├── fake.py
├── real.py
├── CLAUDE.md
└── AGENTS.md
```

### Steps

1. **Move files**: `git mv erk_shared/learn/extraction/claude_installation/ erk_shared/gateway/claude_installation/`
2. **Update internal imports**: Fix imports within the moved package
3. **Update 37 external import sites**:
   - `from erk_shared.learn.extraction.claude_installation` → `from erk_shared.gateway.claude_installation`
4. **Check if erk_shared/learn/extraction/ is empty**: Delete if so
5. **Verify**: `make all-ci` passes

### Files to Modify (Import Updates)
- `packages/erk-shared/src/erk_shared/context/` (3 files)
- `src/erk/core/` (3 files)
- `src/erk/cli/commands/cc/session/` (2 files)
- `src/erk/cli/commands/exec/scripts/` (5 files)
- `src/erk/capabilities/statusline.py`
- `packages/erk-shared/src/erk_shared/` (3 files)
- `tests/` (14 test files)

---

## Phase 7: LiveDisplay Gateway (1 PR)

### Current Location
```
src/erk/core/display/
├── __init__.py
├── abc.py           # LiveDisplay ABC (3 methods)
└── real.py          # RealLiveDisplay (Rich-based)

tests/fakes/live_display.py  # FakeLiveDisplay (separate location!)
```

### Target Location
```
packages/erk-shared/src/erk_shared/gateway/live_display/
├── __init__.py
├── abc.py
├── fake.py          # Moved from tests/fakes/
└── real.py
```

### Steps

1. **Create target directory**: `mkdir -p erk_shared/gateway/live_display/`
2. **Move ABC and real**: From `src/erk/core/display/` to `erk_shared/gateway/live_display/`
3. **Move fake**: From `tests/fakes/live_display.py` to `erk_shared/gateway/live_display/fake.py`
4. **Update internal imports**: Fix imports within the moved package
5. **Update external import sites**:
   - `from erk.core.display` → `from erk_shared.gateway.live_display`
   - `from tests.fakes.live_display` → `from erk_shared.gateway.live_display.fake`
6. **Delete old directories**: `src/erk/core/display/`, `tests/fakes/live_display.py`
7. **Verify**: `make all-ci` passes

### Files to Modify (Import Updates)
- `src/erk/cli/commands/plan/list_cmd.py`
- `tests/fakes/__init__.py` (remove live_display export)
- Test files importing FakeLiveDisplay

---

## Execution Order

Execute phases sequentially (each as separate PR):
1. **Phase 4**: BranchManager - 27 imports
2. **Phase 5**: PromptExecutor - 13 imports
3. **Phase 6**: ClaudeInstallation - 37 imports
4. **Phase 7**: LiveDisplay - 13 imports (cross-package move)

## Verification

After each phase:
1. Run `make all-ci` to verify tests pass
2. Run `rg "from erk_shared\.<old_path>" --type py` to verify no old imports remain
3. Run `ty` to verify type checking passes

## Related Documentation

- Skills: `dignified-python`, `fake-driven-testing`
- Reference: `docs/learned/architecture/gateway-abc-implementation.md`