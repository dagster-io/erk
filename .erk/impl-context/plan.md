# Plan: Consolidate documentation from Mar 1 learn sessions (batch 2)

> **Consolidates:** #8561, #8558, #8557, #8556, #8554, #8553, #8552, #8543, #8538, #8537, #8536, #8535, #8533, #8532

## Context

14 erk-learn plans were generated from Mar 1 implementation sessions. All source implementations are merged. This plan captures documentation insights across all 14, deduplicating overlap and skipping plans where existing documentation is already sufficient.

## Source Plans

| # | Title | Doc Action |
| --- | --- | --- |
| 8561 | Create `cli-push-down` skill | SKIP - skill IS the doc |
| 8558 | Dispatch uses existing worktree | NEW doc |
| 8557 | Fix double activation (direnv) | UPDATE existing doc |
| 8556 | `erk doctor workflow` + rename deps columns | NEW doc |
| 8554 | Restructure review prompt | SKIP - 2 docs already exist |
| 8553 | Gitignore handling for plan-only PRs | UPDATE existing doc |
| 8552 | Improve cmux skill | SKIP - skill IS the doc |
| 8543 | Sync CHANGELOG | SKIP - mechanical, no insights |
| 8538 | External docs repository via config | NEW doc |
| 8537 | Session accumulation via XML on git branches | NEW doc |
| 8536 | `erk pr submit` silent hang fix | NEW doc |
| 8535 | Fix duplicate `gt submit` in cmux | SKIP - covered by activation-scripts.md |
| 8533 | Break up app.py into subpackage | UPDATE existing doc |
| 8532 | Untrack stub branches from Graphite | NEW doc |

**Result:** 3 updates to existing docs + 6 new docs = 9 documentation items

## Implementation Steps

### Step 1: Update `docs/learned/cli/activation-scripts.md` _(from #8557)_

**File:** `docs/learned/cli/activation-scripts.md`

**Action:** Add new section "## VIRTUAL_ENV Idempotency Guard" after the existing content.

**Content outline:**
- Problem: `erk pr checkout --script` with direnv triggers double activation (direnv sources `.erk/activate.sh`, then temp script runs same activation)
- Solution: Guard `if [ "$VIRTUAL_ENV" != "{worktree_path}/.venv" ]; then` wraps expensive operations
- Guard scope: venv creation, uv sync, uv pip install, .env loading, shell completion are INSIDE guard
- Post-activation commands (`gt submit`) always run OUTSIDE guard
- Implementation: `render_activation_script()` at `src/erk/cli/activation.py:198`
- Add tripwire: "removing the VIRTUAL_ENV guard" → "Guard prevents double activation when direnv and temp script both source activation. Removing it causes duplicate package installs."

**Verification:** Read `src/erk/cli/activation.py:193-229` to confirm guard structure

### Step 2: Update `docs/learned/tui/architecture.md` _(from #8533)_

**File:** `docs/learned/tui/architecture.md`

**Action:** Update the directory structure section to reflect the mixin decomposition. Add new "## Mixin Architecture" section.

**Content outline:**
- Updated directory tree showing `operations/` and `actions/` subpackages
- MRO: `ErkDashApp(NavigationActionsMixin, FilterActionsMixin, PaletteActionsMixin, StreamingOperationsMixin, BackgroundWorkersMixin, App)`
- Critical constraint: Textual's `_MessagePumpMeta` scans `class.__dict__` for `@on` decorators - event handlers MUST stay on concrete class
- TYPE_CHECKING import pattern for mixin type safety: `if TYPE_CHECKING: from erk.tui.app import ErkDashApp`
- Module responsibilities: operations/types.py (14 lines), operations/logic.py (42 lines), operations/streaming.py (77 lines), operations/workers.py (428 lines), actions/navigation.py (305 lines), actions/filter_actions.py (164 lines), actions/palette.py (264 lines)
- Add tripwire: "moving @on decorated event handlers to a mixin" → "Textual's _MessagePumpMeta only scans class.__dict__, not inherited methods. Event handlers on mixins are silently ignored."

**Verification:** Read `src/erk/tui/app.py:1-20` to confirm MRO

### Step 3: Update `docs/learned/ci/gitignored-directory-commit-patterns.md` _(from #8553)_

**File:** `docs/learned/ci/gitignored-directory-commit-patterns.md`

**Action:** Add a "## Agent Instruction Cross-References" section noting that `pr-address.md` Step 3 includes the `git add -f` note for plan-only PRs.

**Content outline:**
- The pr-address command is the only command that directly edits and commits `.erk/impl-context/` files
- Line 209 of `.claude/commands/erk/pr-address.md` contains the git add -f note
- Real-world trigger: PR #8544 (plan-only PR) caused agent to waste 2 turns discovering `git add -f`
- Pattern: Document gitignore exceptions in the command instructions that touch gitignored paths

**Verification:** Read `.claude/commands/erk/pr-address.md:205-215`

### Step 4: Create `docs/learned/architecture/worktree-dispatch-detection.md` _(from #8558)_

**File:** `docs/learned/architecture/worktree-dispatch-detection.md`

**Content outline:**

```yaml
---
title: Worktree Detection in Dispatch
read_when:
  - "modifying dispatch command logic"
  - "working with worktree branch detection"
tripwires:
  - action: "assuming plan branch is always in root worktree"
    warning: "Branch may already be checked out in a slot worktree. Use find_worktree_for_branch() to detect."
---
```

- Problem: `erk pr dispatch` assumed it could checkout the plan branch in root worktree, but branch may already be in a slot
- Solution: LBYL pattern using `find_worktree_for_branch(repo_root, branch)` returns `Path | None`
- Implementation: `src/erk/cli/commands/pr/dispatch_cmd.py:226-247`
- `work_dir` variable: toggles between root and existing worktree for all git operations
- Graphite `retrack` uses `repo.root` (repo-global operation) while git ops use `work_dir`
- Conditional branch restoration: only restores to original branch if `checked_out_in_root`
- Gateway: `find_worktree_for_branch()` in `packages/erk-shared/src/erk_shared/gateway/git/worktree/{abc,real,fake}.py`

**Verification:** Read `src/erk/cli/commands/pr/dispatch_cmd.py:226-290`

### Step 5: Create `docs/learned/sessions/session-accumulation.md` _(from #8537)_

**File:** `docs/learned/sessions/session-accumulation.md`

**Content outline:**

```yaml
---
title: Session Accumulation Architecture
read_when:
  - "working with push-session or fetch-sessions exec commands"
  - "modifying the learn pipeline session discovery"
  - "debugging session data on async-learn branches"
tripwires:
  - action: "modifying manifest format without updating version field"
    warning: "Manifest includes a version field for forward compatibility. Increment on schema changes."
  - action: "assuming sessions are stored locally"
    warning: "Sessions are accumulated on git branches (async-learn/<plan-id>). Use fetch-sessions to download."
---
```

- Architecture: Sessions preprocessed (JSONL → XML, ~84% compression) and accumulated on git branches
- Branch naming: `async-learn/<plan-id>` per plan
- Manifest format: `{"version": 1, "plan_id": N, "sessions": [...]}`
- Each session entry: `{session_id, stage, source, uploaded_at, files: ["stage-sessionid.xml"]}`
- Idempotency: duplicate session_id entries replaced, not appended
- Three lifecycle stages: planning, impl, address
- Two source types: local (Claude Code), remote (GitHub Actions)
- Key commands: `erk exec push-session`, `erk exec fetch-sessions`
- Integration points: plan-save (Step 5), plan-implement (Step 10), pr-address (Phase 6), learn.md (Step 3)
- Gateway enhancement: `read_file_from_ref()` reads files from git refs without checkout
- Graceful degradation: push failures return `{"uploaded": false, "reason": "..."}`, never hard-fail

**Verification:** Read `src/erk/cli/commands/exec/scripts/push_session.py:1-50` for architecture overview

### Step 6: Create `docs/learned/cli/doctor-workflow.md` _(from #8556)_

**File:** `docs/learned/cli/doctor-workflow.md`

**Content outline:**

```yaml
---
title: Doctor Workflow Subcommand
read_when:
  - "modifying doctor command or workflow diagnostics"
  - "adding health checks to doctor"
tripwires:
  - action: "adding doctor subcommand without invoke_without_command=True"
    warning: "Doctor uses Click group with invoke_without_command=True so bare 'erk doctor' preserves original behavior."
---
```

- Architecture: `erk doctor` converted to Click group, `erk doctor workflow` is a subgroup
- Subcommands: `check` (static health checks), `smoke-test` (production dispatch), `cleanup` (smoke test artifacts), `list` (installed workflows)
- Health checks: GitHub auth, queue PAT, API secret, workflow permissions, CLAUDE_ENABLED variable, workflow artifacts
- Smoke test: dispatches through production one-shot code path with configurable `--wait`
- Cleanup: removes `plnd/smoke-test-*` branches and associated PRs
- Key types: `SmokeTestResult`, `SmokeTestError`, `CleanupItem` (all frozen dataclasses)
- Files: `src/erk/cli/commands/doctor_workflow.py` (360 lines), `src/erk/core/workflow_smoke_test.py` (165 lines)
- Also documents deps column rename: `objective_head_state` → `objective_deps_display`, `objective_head_plans` → `objective_deps_plans`

**Verification:** Read `src/erk/cli/commands/doctor_workflow.py:1-30`

### Step 7: Create `docs/learned/cli/piped-output-flushing.md` _(from #8536)_

**File:** `docs/learned/cli/piped-output-flushing.md`

**Content outline:**

```yaml
---
title: Piped Output Flushing Pattern
read_when:
  - "debugging silent CLI commands in piped environments"
  - "adding progress messages to long-running commands"
tripwires:
  - action: "adding click.echo() without sys.stdout.flush() in pipeline commands"
    warning: "Python buffers stdout when piped. Without explicit flush, users see no output until command completes or buffer fills."
---
```

- Problem: `erk pr submit` appeared to hang with no output when piped (e.g., captured by CI or automation)
- Root cause: Python's stdout buffering in non-TTY environments
- Solution pattern: `sys.stdout.flush()` after banner and after each pipeline step
- Progress messages: dim-styled messages for silent phases (`"Resolving branch and plan context..."`, `"Checking for existing PR..."`)
- Timeout protection: 15-second timeouts on external subprocess calls (`gt auth`, `gt branch info`) with graceful degradation
- Graceful defaults: `check_auth_status()` returns `(False, None, None)` on timeout; `is_branch_tracked()` returns `False`
- Files: `src/erk/cli/commands/pr/submit_cmd.py:171-173`, `src/erk/cli/commands/pr/submit_pipeline.py:136-138,225-226,968,1005`
- Graphite gateway timeouts: `packages/erk-shared/src/erk_shared/gateway/graphite/real.py:169-179,283-295`

**Verification:** Read `src/erk/cli/commands/pr/submit_cmd.py:170-175`

### Step 8: Create `docs/learned/config/external-docs-path.md` _(from #8538)_

**File:** `docs/learned/config/external-docs-path.md`

**Content outline:**

```yaml
---
title: External Docs Path Configuration
read_when:
  - "configuring docs path in .erk/config.local.toml"
  - "adding new configurable paths to the config system"
tripwires:
  - action: "setting docs.path at global config level"
    warning: "docs_path is REPO_ONLY in RepoConfigSchema. Per-user paths go in .erk/config.local.toml (gitignored)."
---
```

- Feature: `[docs] path` in `.erk/config.local.toml` points erk docs commands to external repository
- Config format: `[docs]\npath = "/path/to/external/repo"`
- Schema: `docs_path: str | None` on `LoadedConfig`, `REPO_ONLY` level in `RepoConfigSchema`
- Resolver: `resolve_docs_project_root(repo_root=, docs_path=)` in `src/erk/agent_docs/operations.py:31-42`
- Error: `click.ClickException` if configured path doesn't exist
- Merge precedence: local config overrides repo config; None defaults to repo_root
- Integration: `erk docs sync`, `erk docs validate`, `erk docs check` all use resolver
- No changes to AgentDocs ABC needed (resolver sits at CLI layer)
- Test coverage: 8 config tests + 3 resolver tests

**Verification:** Read `src/erk/agent_docs/operations.py:31-42`

### Step 9: Create `docs/learned/erk/stub-branch-lifecycle.md` _(from #8532)_

**File:** `docs/learned/erk/stub-branch-lifecycle.md`

**Content outline:**

```yaml
---
title: Stub Branch Lifecycle
read_when:
  - "working with slot pool or branch cleanup"
  - "debugging Graphite branch tracking"
tripwires:
  - action: "deleting stub branches without untracking from Graphite first"
    warning: "Stub branches tracked by Graphite pollute gt log output. Untrack with gt branch untrack before deletion."
---
```

- What: `__erk-slot-N-br-stub__` branches are internal placeholders created during slot pool operations
- Problem: These branches get tracked by Graphite and pollute `gt log` output
- Solution: Auto-untrack during `audit-branches` Phase 1, Step 8
- Implementation: `grep -oE '__erk-slot-[0-9]+-br-stub__'` + `gt branch untrack "$stub" --no-interactive --force`
- Location: `.claude/commands/local/audit-branches.md` Phase 1, Step 8
- Note: Original plan #8530 also proposed blocking slot auto-unassignment, but only stub untracking was implemented

**Verification:** Read `.claude/commands/local/audit-branches.md` and search for "stub"

### Step 10: Update `docs/learned/index.md` and category indexes

**Action:** Run `erk docs sync` after creating all new docs to regenerate the index files and ensure all new documents appear in the navigation.

**Verification:** `erk docs check` should pass with no errors

## Overlap Analysis

| Theme | Plans | Resolution |
| --- | --- | --- |
| Shell activation patterns | #8557, #8535 | #8557 updates activation-scripts.md; #8535 already covered |
| Review workflow | #8554 | Already has 2 docs in docs/learned/review/ |
| Skill creation | #8561, #8552 | Skills ARE the documentation |
| CHANGELOG | #8543 | Mechanical, no documentation needed |
| Worktree management | #8558, #8532 | Separate docs: dispatch detection vs stub lifecycle |
| Session system | #8537 | Standalone doc (complex architecture) |

## Attribution

Items by source:
- **#8557**: Step 1 (activation idempotency)
- **#8533**: Step 2 (TUI architecture update)
- **#8553**: Step 3 (gitignore cross-reference)
- **#8558**: Step 4 (worktree dispatch detection)
- **#8537**: Step 5 (session accumulation)
- **#8556**: Step 6 (doctor workflow)
- **#8536**: Step 7 (piped output flushing)
- **#8538**: Step 8 (external docs config)
- **#8532**: Step 9 (stub branch lifecycle)
- **#8543, #8552, #8561, #8535, #8554**: No steps (SKIP - already documented)

## Verification

1. All new docs have valid YAML frontmatter with `title`, `read_when`, and `tripwires`
2. `erk docs sync` regenerates indexes without errors
3. `erk docs check` passes
4. Each doc references specific file paths and line numbers verified against current codebase
