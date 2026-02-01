# Plan: Consolidated Documentation from 7 Learn Plans

> **Consolidates:** #6445, #6444, #6443, #6440, #6437, #6431, #6422

## Source Plans

| #    | Title                                                            | Items Merged |
| ---- | ---------------------------------------------------------------- | ------------ |
| 6445 | Add --description to roadmap update + skill instructions         | 2 tripwires  |
| 6444 | Scaffold erkdesk Electron + React + TypeScript App               | 4 items      |
| 6443 | Add Progress Logging to Learn Workflow                           | 2 items      |
| 6440 | Add erk exec dash-data Command                                   | 1 item       |
| 6437 | Fix: gh codespace start does not exist                           | 4 items      |
| 6431 | Desktop Dashboard Research Documentation Patterns                | 2 items      |
| 6422 | Remote Objective Next-Plan Execution via GitHub Codespaces       | 4 items      |

## What Changed Since Original Plans

- PR #6432 (gh codespace start fix) merged to master
- PR #6433 (dash-data command) merged to master
- PR #6439 (progress logging) merged to master
- PR #6408 (codespace run objective next-plan) merged to master
- Several docs proposed by plans already exist (pr-discovery.md, session-preprocessing.md, plan-metadata-fields.md, learn-workflow.md, formatter-tools.md)
- Branch P6424 has desktop-dash docs, branch P6435 has erkdesk scaffold, branch P6441 has --description flag — all NOT yet merged

## Investigation Findings

### Corrections to Original Plans

- **#6443**: 3 of 5 proposed docs already exist (pr-discovery.md, session-preprocessing.md, plan-metadata-fields.md)
- **#6440**: json-serialization-patterns.md partially covered by existing json-schema.md
- **#6437**: integration-testing-patterns.md already exists (plan proposed integration-tests.md separately)
- **#6437**: subprocess-testing.md already exists with gateway patterns
- **#6431**: Frontmatter standards and auto-generated indexes already documented in architecture/generated-files.md
- **#6431**: Prettier CI tripwire already exists in ci/tripwires.md
- **#6444**: 38 items proposed but plan is documentation-heavy for desktop feature still on branches

### Overlap Analysis

1. **Desktop/erkdesk docs** (#6444 + #6431): Both propose desktop-dash documentation; #6431 proposes WebContentsView and performance baseline docs that complement #6444's security and bridge docs
2. **Codespace docs** (#6437 + #6422): Both touch codespace gateway; #6437 focuses on gh CLI limits, #6422 on remote execution pattern
3. **CI/formatting docs** (#6443 + #6431): Both reference Prettier formatting patterns; #6431's tripwire already exists
4. **Tripwires** (#6445 + #6443 + #6431 + #6437): Multiple plans propose tripwires; need deduplication

## Remaining Documentation Gaps

After filtering out what already exists, these are the actual gaps:

### Category A: Codespace & Gateway (from #6437, #6422)

1. **Update github-cli-limits.md** — Add `gh codespace start` REST API section + GH-API-AUDIT convention
2. **Create codespace-remote-execution.md** — Fire-and-forget pattern with build_codespace_run_command()
3. **Create codespace-gateway.md** — 3-place gateway pattern for codespace ABC
4. **Create composable-remote-commands.md** — Template for adding new remote commands
5. **Create codespace-patterns.md** — resolve_codespace() helper documentation

### Category B: CI & Tooling (from #6443, #6445)

6. **Create edit-tool-formatting.md** — Edit tool multiline string handling pattern
7. **Create formatting-workflow.md** — Decision tree: Python→ruff, Markdown→prettier
8. **Add tripwire: Auto-generated file regeneration** — After CLI changes, run gen-exec-reference-docs
9. **Add tripwire: CLI options validation** — Check validation logic when adding new flags

### Category C: Desktop Dashboard (from #6444, #6431)

10. **Create erkdesk/security.md** — Context bridge security pattern
11. **Create architecture/typescript-multi-config.md** — Multi-config TypeScript project checking
12. **Create tui/dual-handler-pattern.md** — Context-agnostic command handler pattern
13. **Create objectives/research-documentation-integration.md** — Objective-linked research workflow

### Category D: Exec Script Patterns (from #6440)

14. **Create json-serialization-patterns.md** — Datetime, tuple, dataclass serialization for JSON

## Implementation Steps

### Step 1: Update github-cli-limits.md _(from #6437)_

**File:** `docs/learned/architecture/github-cli-limits.md`

Add sections:
- `## gh codespace start Does Not Exist` — Document that `gh codespace start` is not a real command; use REST API `/user/codespaces/{name}/start` via `gh api --method POST`
- `## GH-API-AUDIT Annotation Convention` — Document the `# GH-API-AUDIT: [REST/GraphQL] - [operation]` format used in 66 places across gateway code

**Verification:** grep for "GH-API-AUDIT" in the updated doc

### Step 2: Create codespace documentation _(from #6422)_

**File:** `docs/learned/erk/codespace-remote-execution.md`
- Fire-and-forget semantics
- `build_codespace_run_command()` in `src/erk/core/codespace_run.py`
- Environment setup: git pull, uv sync, venv activation
- Output logging to `/tmp/erk-run.log`
- Debugging guidance

**File:** `docs/learned/gateway/codespace-gateway.md`
- 3-place pattern (abc, real, fake — no dry-run/print)
- `start_codespace()`, `run_ssh_command()`, `exec_ssh_interactive()`
- ABC at `packages/erk-shared/src/erk_shared/gateway/codespace/abc.py`

**File:** `docs/learned/architecture/composable-remote-commands.md`
- Template for new remote commands using `build_codespace_run_command()`
- `resolve_codespace()` usage from `src/erk/cli/commands/codespace/resolve.py`
- Existing example: `erk codespace run objective next-plan`

**File:** `docs/learned/cli/codespace-patterns.md`
- `resolve_codespace(registry, name)` helper function documentation
- Error handling patterns (name not found, default not set)
- Usage in existing commands

**Verification:** All 4 files have proper `read_when` frontmatter; `erk docs sync` succeeds

### Step 3: Create CI documentation _(from #6443, #6445)_

**File:** `docs/learned/ci/edit-tool-formatting.md`
- Edit tool preserves exact indentation without auto-formatting
- Pattern: always run `make format` after editing Python with multiline strings
- Tripwire in frontmatter

**File:** `docs/learned/ci/formatting-workflow.md`
- Decision tree: `.py` → `make format`, `.md` → `make prettier`, unclear → both
- The Prettier Trap: Prettier silently does nothing on Python files
- Standard CI iteration sequence

**Add tripwires to `docs/learned/cli/tripwires.md`:**
- Auto-generated file regeneration after CLI changes (run `erk-dev gen-exec-reference-docs`)
- CLI options validation coverage when adding new flags

**Verification:** Files pass `make prettier`; tripwires appear in regenerated tripwires.md after `erk docs sync`

### Step 4: Create desktop/erkdesk documentation _(from #6444, #6431)_

**File:** `docs/learned/erkdesk/security.md`
- Context isolation architecture (contextIsolation: true, nodeIntegration: false)
- Preload script and context bridge pattern
- GitHub token isolation (stays in Python layer)
- FORBIDDEN patterns

**File:** `docs/learned/architecture/typescript-multi-config.md`
- Problem: `tsc --noEmit` from root breaks subdirectory configs
- Solution: `tsc -p <path> --noEmit` for each config
- erkdesk example with 3 configs (root, main, renderer)

**File:** `docs/learned/tui/dual-handler-pattern.md`
- Context-agnostic commands operating on selected plan
- CommandRegistry dispatches same handler from list and detail contexts
- Implications for desktop implementation

**File:** `docs/learned/objectives/research-documentation-integration.md`
- When to create research documentation during objectives
- Documentation creation workflow (read_when frontmatter, erk docs sync)
- Objective linking workflow (bidirectional references)

**Verification:** All files have proper `read_when` frontmatter; `erk docs sync` succeeds

### Step 5: Create JSON serialization patterns _(from #6440)_

**File:** `docs/learned/cli/json-serialization-patterns.md`
- Datetime → `.isoformat()` for ISO 8601
- Tuple → `list()` for JSON compatibility
- Pure helper function pattern (`_serialize_plan_row()` example)
- Reference: `src/erk/cli/commands/exec/scripts/dash_data.py`

**Verification:** File has proper frontmatter; referenced code paths are accurate

### Step 6: Run erk docs sync and make prettier

- Run `erk docs sync` to regenerate all index and tripwire files
- Run `make prettier` to format all new markdown files
- Verify no formatting errors remain

**Verification:** `make prettier` reports no changes; `erk docs sync` is idempotent

## Attribution

Items by source:

- **#6445**: Steps 3 (2 tripwires)
- **#6444**: Steps 4 (security.md, typescript-multi-config.md)
- **#6443**: Step 3 (edit-tool-formatting.md, formatting-workflow.md)
- **#6440**: Step 5 (json-serialization-patterns.md)
- **#6437**: Steps 1, 2 (github-cli-limits update, codespace-gateway.md)
- **#6431**: Step 4 (dual-handler-pattern.md, research-documentation-integration.md)
- **#6422**: Step 2 (codespace-remote-execution.md, composable-remote-commands.md, codespace-patterns.md)