# Plan: Update .impl/ references to .erk/impl-context/ (Objective #8365 Nodes 4.1 + 4.2)

## Context

Objective #8365 ("Eliminate .impl/ Folder — Unify on .erk/impl-context/") is migrating all implementation context from the legacy `.impl/` folder to `.erk/impl-context/`. Phases 1-3 (code paths, CI workflows, command/skill files) are in progress via PRs #8366-#8371. **Nodes 4.1 and 4.2 are the final documentation sweep** — updating docstrings, user-facing strings, and docs/learned/ files to reference the new canonical location.

**Scope:** ~42 Python source files + ~70 docs/learned/ files + AGENTS.md = ~113 files total. All changes are textual (docstrings, comments, help text, markdown). No code logic changes.

## Strategy: Rename-Swarm

Use the `/rename-swarm` skill to parallelize updates across all files using haiku agents. Each agent gets one file and clear replacement rules.

### Replacement Rules (for all agents)

```
.impl/              → .erk/impl-context/
.impl/plan.md       → .erk/impl-context/plan.md
.impl/plan-ref.json → .erk/impl-context/plan-ref.json
.impl/ref.json      → .erk/impl-context/ref.json
.impl/issue.json    → (remove or note as legacy — this file no longer exists)
.impl/progress.md   → .erk/impl-context/progress.md
.impl/local-run-state.json → .erk/impl-context/local-run-state.json
"the .impl folder"  → "the implementation context folder" or ".erk/impl-context/"
"the .impl/ directory" → "the .erk/impl-context/ directory"
"dot-impl"          → ".erk/impl-context"
```

### Boundary Constraints (what NOT to change)

- **DO NOT** modify `.gitignore` entries (node 4.3 handles this separately)
- **DO NOT** modify actual code paths (`Path` operations, variable assignments like `cwd / ".impl"`) — those are phase 1 territory
- **DO NOT** change import statements or function/variable names containing `impl`
- **DO NOT** change CLI command names (`check-impl`, `setup-impl`, etc.) — only their docstrings
- **DO NOT** change file names — only file contents

## Execution Steps

### Step 1: Load rename-swarm skill

Load `/rename-swarm` for the agent prompt template and wave orchestration pattern.

### Step 2: Fresh grep to identify all files

Before launching agents, grep for the current state (phases 1-3 PRs may have merged by then):

```bash
grep -rl '\.impl' src/erk/ --include='*.py' --include='*.md' | sort
grep -rl '\.impl' docs/learned/ --include='*.md' | sort
grep -n '\.impl' AGENTS.md
```

### Step 3: Wave 1 — Source files (Node 4.1)

Launch haiku agents for all ~42 source files, sub-batched into groups of 15:
- Batch 1A: First 15 source files
- Batch 1B: Next 15 source files
- Batch 1C: Remaining ~12 source files

Each agent prompt:
```
In the file `{file_path}`:

Update all textual references from `.impl/` to `.erk/impl-context/`.

This includes:
- Module docstrings and function docstrings
- Comments referencing .impl/ paths
- User-facing output strings (click.echo, print, f-strings shown to users)
- Help text for CLI options/arguments
- Example output in docstrings

DO NOT modify:
- Actual code paths (Path operations like `cwd / ".impl"`)
- Variable names or function names containing "impl"
- Import statements
- CLI command names (check-impl, setup-impl, etc.)
- .gitignore entries

Replacement mapping:
- `.impl/` → `.erk/impl-context/`
- `.impl/plan.md` → `.erk/impl-context/plan.md`
- `.impl/plan-ref.json` → `.erk/impl-context/plan-ref.json`
- `.impl/ref.json` → `.erk/impl-context/ref.json`
- `.impl/issue.json` → remove reference or note as legacy
- `.impl/progress.md` → `.erk/impl-context/progress.md`
- `.impl/local-run-state.json` → `.erk/impl-context/local-run-state.json`
- "the .impl folder" → "the .erk/impl-context/ folder"

Read the file first, then apply all changes using the Edit tool.
```

### Step 4: Verify Wave 1

- Grep source files for remaining `.impl` in docstrings/strings (code path refs are expected)
- Run `ty` type checker via devrun agent

### Step 5: Wave 2 — Documentation files (Node 4.2)

Launch haiku agents for all ~70 docs/learned/ files + AGENTS.md + `src/erk/cli/commands/exec/scripts/AGENTS.md`, sub-batched into groups of 15:
- Batch 2A: First 15 docs files
- Batch 2B: Next 15 docs files
- Batch 2C: Next 15 docs files
- Batch 2D: Next 15 docs files
- Batch 2E: Remaining ~10 docs files + AGENTS.md + exec AGENTS.md

Each agent prompt:
```
In the file `{file_path}`:

Update all references from `.impl/` to `.erk/impl-context/`. This is part of
a migration to eliminate the legacy `.impl/` folder.

Replacement mapping:
- `.impl/` → `.erk/impl-context/`
- `.impl/plan.md` → `.erk/impl-context/plan.md`
- `.impl/plan-ref.json` → `.erk/impl-context/plan-ref.json`
- `.impl/ref.json` → `.erk/impl-context/ref.json`
- `.impl/issue.json` → remove or note as legacy
- `.impl/progress.md` → `.erk/impl-context/progress.md`
- "the .impl folder" → "the .erk/impl-context/ folder"
- Code examples showing `.impl/` paths → update to `.erk/impl-context/`

DO NOT modify:
- CLI command names (check-impl, setup-impl, etc.)
- References that are explicitly documenting the migration history

Preserve the meaning and flow of the documentation.
Read the file first, then apply all changes using the Edit tool.
```

### Step 6: Verify Wave 2

- Grep all docs for remaining `.impl` references
- Run `prettier` via devrun agent to ensure markdown formatting

### Step 7: Final verification

- Full grep across repo: `grep -rn '\.impl' src/ docs/ AGENTS.md` to confirm only code-path refs remain
- Run `make fast-ci` via devrun agent

## Key Files

### Source files (Node 4.1) — heaviest hitters:
- `src/erk/cli/commands/exec/scripts/check_impl.py` — module docstring
- `src/erk/cli/commands/exec/scripts/setup_impl.py` — module docstring
- `src/erk/cli/commands/exec/scripts/setup_impl_from_pr.py` — module docstring + function docstrings
- `src/erk/cli/commands/exec/scripts/impl_init.py` — module docstring
- `src/erk/cli/commands/wt/create_cmd.py` — help text
- `src/erk/cli/commands/branch/checkout_cmd.py` — docstrings
- `src/erk/cli/commands/learn/learn_cmd.py` — docstrings + user output
- `src/erk/agent_docs/operations.py` — category descriptions
- `src/erk/status/collectors/impl.py` — docstring
- `src/erk/core/health_checks.py` — required entries list

### Documentation files (Node 4.2) — heaviest hitters:
- `docs/learned/cli/plan-implement.md` — 27 references
- `docs/learned/planning/lifecycle.md` — 22 references
- `docs/learned/planning/workflow.md` — 14 references
- `docs/learned/glossary.md` — 13 references
- `docs/learned/planning/worktree-cleanup.md` — 12 references
- `docs/learned/erk/issue-pr-linkage-storage.md` — 9 references
- `AGENTS.md` — 3 references (lines 107, 108, 176)

## Verification

1. `grep -rn '\.impl/' src/erk/ docs/ AGENTS.md` — only code-path refs should remain in source
2. `make fast-ci` — all tests pass, type checker clean, lint clean
3. Spot-check 3-4 heavy files manually to ensure replacements read naturally
