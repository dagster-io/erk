# Plan: Rename `erk:system:impl-execute` to `erk:plan-implement`

## Summary

The old command `erk:system:impl-execute` has been moved to `erk:plan-implement` but many references to the old name remain throughout the codebase. This plan renames all occurrences.

## Scope

~70+ references across:
- Source code (`src/`)
- Tests (`tests/`)
- Documentation (`docs/`)
- Claude commands/skills (`.claude/`)
- GitHub workflows (`.github/`)
- Shared packages (`packages/`)
- Docker and config files

## Implementation

### Phase 1: Update Source Code

**Files:**
- `src/erk/cli/commands/implement_shared.py` - 6 occurrences
- `src/erk/cli/commands/docker_executor.py` - 1 occurrence
- `src/erk/cli/commands/artifact/show.py` - 1 occurrence (example)
- `src/erk/cli/commands/exec/scripts/impl_verify.py` - 1 occurrence
- `src/erk/cli/commands/exec/scripts/impl_signal.py` - 1 occurrence
- `src/erk/cli/commands/exec/scripts/impl_init.py` - 2 occurrences
- `src/erk/cli/commands/exec/scripts/check_impl.py` - 2 occurrences
- `src/erk/cli/commands/exec/scripts/exit_plan_mode_hook.py` - 1 occurrence
- `src/erk/cli/commands/exec/scripts/preprocess_session.py` - 1 occurrence
- `src/erk/cli/prompt_hooks_templates/README.md` - 1 occurrence
- `src/erk/core/output_filter.py` - 2 occurrences

### Phase 2: Update Shared Packages

**Files:**
- `packages/erk-shared/src/erk_shared/impl_folder.py` - 1 occurrence
- `packages/erk-shared/src/erk_shared/core/claude_executor.py` - 6 occurrences
- `packages/erk-shared/src/erk_shared/gateway/shell/abc.py` - 1 occurrence

### Phase 3: Update Tests

**Files:**
- `tests/commands/implement/test_flags.py` - 6 occurrences
- `tests/commands/implement/test_execution_modes.py` - 10 occurrences
- `tests/artifacts/test_cli.py` - 2 occurrences
- `tests/artifacts/test_discovery.py` - 2 occurrences
- `tests/core/test_impl_folder.py` - 1 occurrence
- `tests/fakes/claude_executor.py` - 1 occurrence
- `tests/unit/cli/commands/exec/scripts/test_exit_plan_mode_hook.py` - 1 occurrence
- `tests/unit/cli/commands/exec/scripts/test_impl_signal.py` - 1 occurrence
- `tests/unit/cli/commands/exec/scripts/test_impl_init.py` - 1 occurrence
- `tests/unit/cli/commands/test_docker_executor.py` - 6 occurrences
- `tests/integration/cli/commands/exec/scripts/test_check_impl_integration.py` - 2 occurrences

### Phase 4: Update Claude Artifacts

**Files:**
- `.claude/skills/erk-planning/SKILL.md` - 1 occurrence
- `.claude/commands/erk/objective-next-plan.md` - 2 occurrences
- `.claude/commands/local/sessions-list.md` - 1 occurrence (example output)

### Phase 5: Update Documentation

**Files:**
- `docs/user/project-setup.md` - 1 occurrence
- `docs/developer/plan-lifecycle-improvements.md` - 1 occurrence
- `docs/ref/slash-commands.md` - 1 occurrence
- `docs/learned/planning/workflow.md` - 2 occurrences
- `docs/learned/planning/lifecycle.md` - 2 occurrences
- `docs/learned/commands/optimization-patterns.md` - 1 occurrence
- `docs/learned/sessions/raw-session-processing.md` - 2 occurrences
- `docs/learned/hooks/prompt-hooks.md` - 1 occurrence
- `docs/learned/architecture/claude-executor-patterns.md` - 3 occurrences
- `docs/learned/architecture/command-boundaries.md` - 1 occurrence

### Phase 6: Update GitHub Workflow

**Files:**
- `.github/workflows/erk-impl.yml` - 1 occurrence

### Phase 7: Update Config/Docker

**Files:**
- `.erk/docker/Dockerfile` - 1 occurrence

## Verification

1. Run `make fast-ci` to ensure tests pass
2. Grep for any remaining `erk:system:impl-execute` references
3. Verify the skill is recognized: test running `/erk:plan-implement`

## Notes

- This is a mechanical string replacement: `/erk:system:impl-execute` → `/erk:plan-implement`
- Also update `erk:system:impl-execute` (without leading slash) where it appears in artifact names