# Plan: Phase 3 — Update CI/Commands/Skills for .erk/impl-context/ consolidation

Part of Objective #8197, Nodes 3.1, 3.2, 3.3, 3.4

## Context

Phase 1 of objective #8197 updated all production code to use `resolve_impl_dir()` which discovers implementation directories from both legacy `.impl/` and branch-scoped `.erk/impl-context/<branch>/`. Phase 2 (tests) is pending. Phase 3 updates CI workflows, commands, and skills to align with the new directory model.

**Key discovery**: `read_run_info()` in `impl_folder.py:395` has zero callers — it's dead code. The `run-info.json` file written by `plan-implement.yml` is never read. This simplifies Node 3.1 significantly.

**Architecture**: Two separate module create impl directories:
- `erk_shared.impl_context.create_impl_context()` — Creates flat `.erk/impl-context/plan.md` (used by CI workflow's `create-impl-context-from-plan`)
- `erk_shared.impl_folder.create_impl_folder()` — Creates branch-scoped `.erk/impl-context/<branch>/plan.md` (used by `setup-impl`)

The CI workflow creates the flat structure for branch sharing; the agent's `setup-impl` re-fetches from GitHub and creates branch-scoped structure via `create_impl_folder`.

## Phase 1: Node 3.1 — plan-implement.yml

**File**: `.github/workflows/plan-implement.yml`

### Change 1: Use `git add -f` (line 161)

```yaml
# Before:
git add .erk/impl-context
# After:
git add -f .erk/impl-context
```

Overcomes `.erk/impl-context/` in `.gitignore`.

### Change 2: Remove "Set up implementation folder" step (lines 195-205)

Delete the entire step that does `cp -r .erk/impl-context .impl` and writes `run-info.json`. The agent's `setup-impl` handles `.impl/` creation. `run-info.json` is dead code.

### Change 3: Change `git rm -rf` to `git rm --cached -rf` (lines 215-217)

```yaml
# Before:
if [ -d .erk/impl-context/ ]; then
  git rm -rf .erk/impl-context/
  NEEDS_CLEANUP=true
fi
# After:
if git ls-files --error-unmatch .erk/impl-context/ >/dev/null 2>&1; then
  git rm --cached -rf .erk/impl-context/
  NEEDS_CLEANUP=true
fi
```

`--cached` removes from git index but keeps files on disk (now gitignored). The agent's `setup-impl --issue N` re-fetches from GitHub anyway, and `cleanup_impl_context` handles final removal.

Update the echo on line 222 accordingly.

### Change 4: Remove `.impl/` grep from "Handle implementation outcome" (line 311)

```yaml
# Before:
UNCOMMITTED=$(git status --porcelain | grep -v '^\s*D.*\.erk/impl-context/' | grep -v '\.impl/' || true)
# After:
UNCOMMITTED=$(git status --porcelain | grep -v '\.erk/impl-context/' || true)
```

No `.impl/` in the CI flow now. Simplify the `.erk/impl-context/` filter too since files are gitignored after `git rm --cached`.

### Change 5: Remove post-implementation cleanup step (lines 398-417)

The "Clean up plan staging dirs after implementation" step is redundant — `cleanup_impl_context` inside `setup-impl` already handles the git rm + commit + push during Step 2d. After `git rm --cached` pre-implementation, the files are gitignored and won't appear in new commits.

## Phase 2: Node 3.2 — one-shot.yml + ci.yml

### one-shot.yml

**File**: `.github/workflows/one-shot.yml`

**Change 1**: Line 252 — `git add .erk/impl-context/` → `git add -f .erk/impl-context/`

The `cp .erk/impl-context/prompt.md .impl/prompt.md` on line 114 stays — in the one-shot flow, `.impl/` is the agent's local scratch space (created by `mkdir -p .impl`), not the implementation directory. The agent reads `.impl/prompt.md` as defined in the one-shot-plan command.

### ci.yml

**File**: `.github/workflows/ci.yml`

**Change 1**: Lines 259-263 — Update the inline `.impl` check in the autofix job to also check `.erk/impl-context/`:

```yaml
# Before:
if [ -d ".impl" ]; then
  echo "Found .impl folder, skipping autofix"
  echo "has_impl_folder=true" >> $GITHUB_OUTPUT
else
  echo "has_impl_folder=false" >> $GITHUB_OUTPUT
fi
# After:
if [ -d ".erk/impl-context" ] || [ -d ".impl" ]; then
  echo "Found implementation folder, skipping autofix"
  echo "has_impl_folder=true" >> $GITHUB_OUTPUT
else
  echo "has_impl_folder=false" >> $GITHUB_OUTPUT
fi
```

The `check-impl-context` action (`.github/actions/check-impl-context/action.yml`) already checks `.erk/impl-context` correctly — no changes needed there.

## Phase 3: Node 3.3 — Command files

Commands reference `.impl/` as agent-facing documentation. Since agents interact via exec commands that use `resolve_impl_dir()`, most references are conceptual. Update where commands hardcode `.impl/` assumptions:

### plan-implement.md

**File**: `.claude/commands/erk/plan-implement.md`

Light text updates — the exec commands handle path resolution:
- Line 61: Update `.erk/impl-context/` cleanup description to mention `git rm --cached` pattern
- Lines referencing `.impl/plan.md` etc. stay as-is since `setup-impl` creates the implementation directory and the agent reads from it

### one-shot-plan.md

**File**: `.claude/commands/erk/one-shot-plan.md`

No changes — `.impl/` is correctly used as local scratch in the one-shot flow.

### Other commands

**No changes needed** for: `pr-submit.md`, `plan-save.md`, `objective-plan.md`, `land.md`, `git-pr-push.md`, `learn.md`, `local/plan-update.md` — these all reference `.impl/` metadata files via exec commands or `resolve_impl_dir()`.

## Phase 4: Node 3.4 — Skill files

### erk-exec/reference.md

**File**: `.claude/skills/erk-exec/reference.md`

Update descriptions for impl-related commands:
- `setup-impl-from-issue`: Update description from "Set up .impl/ folder" to "Set up implementation folder"
- `impl-init`: Update from "validating .impl/ folder" to "validating implementation folder"
- `cleanup-impl-context`: Already correct
- `create-impl-context-from-plan`: Already correct

### erk-planning references

**Files**: `.claude/skills/erk-planning/references/workflow.md`, `.claude/skills/erk-planning/SKILL.md`

Update `.impl/issue.json` references to use generic "implementation directory" or the correct file path since Phase 1 changed the ref format to `ref.json`.

## Dead Code Cleanup

Remove `read_run_info()` and `RunInfo` from `packages/erk-shared/src/erk_shared/impl_folder.py` — zero callers, zero usage. This avoids documenting dead behavior.

## Files Modified

| File | Node | Changes |
|------|------|---------|
| `.github/workflows/plan-implement.yml` | 3.1 | git add -f, remove cp step, git rm --cached, remove .impl grep, remove post-impl cleanup |
| `.github/workflows/one-shot.yml` | 3.2 | git add -f |
| `.github/workflows/ci.yml` | 3.2 | Add .erk/impl-context check to autofix |
| `.claude/commands/erk/plan-implement.md` | 3.3 | Light text updates for cleanup description |
| `.claude/skills/erk-exec/reference.md` | 3.4 | Update impl-related command descriptions |
| `.claude/skills/erk-planning/references/workflow.md` | 3.4 | Update .impl/ references |
| `.claude/skills/erk-planning/SKILL.md` | 3.4 | Update .impl/issue.json reference |
| `packages/erk-shared/src/erk_shared/impl_folder.py` | cleanup | Remove dead `read_run_info`/`RunInfo` |

## Verification

1. **Workflow syntax**: Validate YAML syntax of modified workflow files
2. **Grep audit**: `grep -r '\.impl/' .github/workflows/` should show only legitimate remaining references (one-shot scratch dir)
3. **Grep audit**: `grep -r 'git add .erk' .github/workflows/` should show `-f` flag on all occurrences
4. **Dead code**: Verify `read_run_info` and `RunInfo` are not imported anywhere after removal
5. **CI checks**: Run `make fast-ci` to verify no test breakage from dead code removal
