# Introduce `.erk/branch-data/` for Draft PR Backend

## Context

The draft PR backend currently commits `.erk/plan/PLAN.md` to the branch during `plan_save` — a single file to avoid GitHub's empty-branch rejection and enable inline review. The name `.erk/plan/` is narrow; as one-shots, learns, and other workflows adopt the draft PR backend, they'll also need to pass committed data on branches (instructions, learn context, metadata references).

This plan introduces `.erk/branch-data/` as the future-proof committed folder name, replacing `.erk/plan/`. It does NOT touch `.impl/` or `.worker-impl/` — those remain as-is for the issue-based flow.

**Prerequisite**: P7489 (learn migration to PlanBackend) lands first.

## Design

### Folder Structure

```
.erk/branch-data/           # Committed on the branch (replaces .erk/plan/)
├── plan.md                 # Plan content (was .erk/plan/PLAN.md)
└── ref.json                # Plan reference: provider, plan_id, url, objective_id
```

Purely committed data. Runtime files (progress, run state) remain in `.erk/scratch/` and `.impl/` as today.

### What Changes

**`plan_save.py` — draft PR path (`_save_as_draft_pr`):**
- Change `repo_root / ".erk" / "plan"` → `repo_root / ".erk" / "branch-data"`
- Change `plan_dir / "PLAN.md"` → `branch_data_dir / "plan.md"`
- Add: write `ref.json` with plan reference metadata (provider, plan_id, url, objective_id) before push
- Stage `.erk/branch-data/` instead of `.erk/plan/PLAN.md`

**`draft_pr_lifecycle.py` docstring:**
- Update "Branch Files" section: `.erk/branch-data/plan.md` replaces `.erk/plan/PLAN.md`

**`erk implement` — draft PR path (if `.erk/branch-data/` exists on branch):**
- When creating `.impl/`, check if `.erk/branch-data/plan.md` exists on the worktree
- If present, read plan content from the committed file instead of fetching from PR body
- Still create `.impl/plan-ref.json` (can copy from `.erk/branch-data/ref.json`)
- This is an optimization, not a requirement — PR body remains the authoritative source

### Files to Modify

| File | Change |
|------|--------|
| `src/erk/cli/commands/exec/scripts/plan_save.py` | `.erk/plan/PLAN.md` → `.erk/branch-data/plan.md` + `ref.json` |
| `packages/erk-shared/src/erk_shared/plan_store/draft_pr_lifecycle.py` | Update docstring |

### What Does NOT Change

- `.impl/` — remains gitignored, remains the local implementation folder
- `.worker-impl/` — remains the committed folder for issue-based remote implementation
- `impl_folder.py` — no changes
- `worker_impl_folder.py` — no changes
- Submit pipeline — still reads `.impl/plan-ref.json`
- Issue-based workflows — completely untouched

## Objective 7419 Update

Update node 3.4 and add a new node to the roadmap:

**Node 3.4** (rewrite):
> Consolidate committed branch data: rename `.erk/plan/` to `.erk/branch-data/` with `plan.md` + `ref.json`. Implementation reads from committed files on branch instead of fetching from PR body.

**New node 3.5**:
> Eliminate `.worker-impl/` and `.impl/`: after issue-based flow is deleted (3.1-3.3), migrate all consumers to `.erk/branch-data/`. Remove `.worker-impl/` folder, CI copy steps, cleanup commits. Move `.impl/` runtime files to `.erk/scratch/`. Delete `worker_impl_folder.py` and `impl_folder.py`.

## Verification

1. `make fast-ci` passes
2. Draft PR `plan_save`: verify `.erk/branch-data/plan.md` and `ref.json` committed on branch
3. PR "Files Changed" tab shows `.erk/branch-data/plan.md` (inline review works)
4. `erk prepare` on a draft PR plan: worktree has `.erk/branch-data/` files
5. Issue-based workflows: completely unaffected (test `erk plan submit` still uses `.worker-impl/`)