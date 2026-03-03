# Plan: Consolidate Documentation from 18 erk-learn Plans

> **Consolidates:** #8698, #8692, #8691, #8690, #8685, #8679, #8677, #8672, #8669, #8666, #8665, #8663, #8656, #8650, #8649, #8648, #8647, #8645

All 18 source PRs are fully merged. #8650 superseded by #8669. Five overlap groups identified and merged.

## Implementation Steps

### Step 1: Update activation-scripts.md _(#8698, #8648)_

**File:** `docs/learned/cli/activation-scripts.md`

- Update VIRTUAL_ENV guard section: uv sync/pip install now run OUTSIDE guard (always execute). Guard only protects venv activation, .env loading, shell completion.
- Update tripwire: distinguish "removing guard" (dangerous) from "moving sync outside" (correct)
- Add `force_script_activation` parameter docs (checkout_cmd.py:164)
- Update code example to match current `render_activation_script()` output

### Step 2: Update planning workflow.md _(#8645, #8690, #8692)_

**File:** `docs/learned/planning/workflow.md`

- Update exit plan mode to 4 options: new branch, current branch (hidden on trunk), implement without PR (NEW), view/edit
- Add trunk branch hiding note with warning (#8690)
- Note "In current wt" label (#8692)

### Step 3: Update impl-context.md _(#8669, #8650, #8685)_

**File:** `docs/learned/planning/impl-context.md`

- Add note: `cleanup_impl_for_submit()` runs for ALL branches including plnd/*
- Skip guard was added (#8636) then removed (#8667) because plan-save uses push_to_remote directly
- Reference plan-implement cleanup step (`erk exec cleanup-impl-context`)

### Step 4: Update CI job-ordering-strategy.md _(#8666)_

**File:** `docs/learned/ci/job-ordering-strategy.md`

- Add erk-mcp-tests to Tier 3 diagram and validation jobs table (now 7 jobs)

### Step 5: Create MCP integration doc _(#8665, #8666)_

**File:** `docs/learned/integrations/mcp-integration.md` (NEW)

- Package structure, 3 MCP tools (plan_list, plan_view, one_shot), _run_erk() wrapper
- Configuration (.mcp.json), Makefile targets, CI job

### Step 6: Create threading-patterns.md _(#8672)_

**File:** `docs/learned/architecture/threading-patterns.md` (NEW)

- Daemon thread + holder list pattern from commit_message_generator.py:142-197
- Thread-safe communication, time abstraction, ProgressEvent integration
- Compare: Thread vs ThreadPoolExecutor vs Textual run_worker()

### Step 7: Update dispatch-ref-config.md _(#8656)_

**File:** `docs/learned/erk/dispatch-ref-config.md`

- Add two-stage plan auto-detection: local impl-context first, GitHub API fallback

### Step 8: Create next-steps-output.md _(#8679)_

**File:** `docs/learned/planning/next-steps-output.md` (NEW)

- PlanNextSteps type (replaced IssueNextSteps + PlannedPRNextSteps)
- PlanNumberEvent (replaced IssueNumberEvent), format_plan_next_steps_plain()

### Step 9: Fix dead link _(#8679)_

**File:** `docs/topics/worktrees.md` - Remove dead link to why-github-issues.md (line 10)

### Step 10: Update objective docs _(#8663)_

- Document objectives can exist without roadmap block
- parse_roadmap() returns ([], []) when no block; validate skips checks 3-7

### Step 11: Document slot reuse handling _(#8691)_

- find_inactive_slot() ignores untracked files, checks only staged/modified

### Step 12: Update workspace-activation.md _(#8698)_

- Replace duplicate activation section with cross-ref to activation-scripts.md

### Step 13: Update claude-cli-progress.md _(#8672)_

- Add cross-reference to new threading-patterns.md

### Step 14: Run `erk docs sync` to regenerate index files

## Attribution

- **#8698**: Steps 1, 12 | **#8692**: Step 2 | **#8691**: Step 11 | **#8690**: Step 2
- **#8685**: Step 3 | **#8679**: Steps 8, 9 | **#8677**: none | **#8672**: Steps 6, 13
- **#8669**: Step 3 | **#8666**: Steps 4, 5 | **#8665**: Step 5 | **#8663**: Step 10
- **#8656**: Step 7 | **#8650**: Step 3 | **#8649**: none | **#8648**: Step 1
- **#8647**: none | **#8645**: Step 2
