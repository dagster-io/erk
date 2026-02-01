# Plan: Consolidated Documentation from Learn Plans #6455, #6456, #6457

> **Consolidates:** #6455, #6456, #6457

## Source Plans

| #    | Title                                                                | Items Merged |
| ---- | -------------------------------------------------------------------- | ------------ |
| 6455 | [erk-learn] Plan #6449 - Collapsible Sections in PR Bodies           | 3 items      |
| 6456 | [erk-learn] Token Optimization and Workflow Patterns from /erk:replan | 7 items      |
| 6457 | [erk-learn] Scaffold erkdesk as pnpm Project                         | 7 items      |

## What Changed Since Original Plans

- PR #6450 (collapsible sections) fully merged - all code implemented and tested
- PR #6448 (erkdesk scaffold) fully merged - 16 source files in `erkdesk/`
- PR #6452 consolidated 7 learn plans, creating `docs/learned/architecture/typescript-multi-config.md`
- PR #6454 merged Step 3 into Step 4 in `/erk:replan` - token optimization implemented
- `docs/learned/planning/debugging-patterns.md` already covers validation-through-code-search pattern

## Investigation Findings

### Corrections to Original Plans

- **#6455**: Listed `.claude/commands/erk/objective-create.md` as modified but it was NOT in commit ca46dcbcb. Commit SHA referenced as `280c216b` but actual is `ca46dcbcb`.
- **#6456**: Item #8 (Codebase Search for Validation Rules) already fully documented in `docs/learned/planning/debugging-patterns.md` - remove from plan.
- **#6457**: Plan implied pnpm-workspace.yaml; reality is standalone pnpm project. TypeScript multi-config already fully implemented in #6452.

### Overlap Analysis

- **PR body patterns**: #6455 (plan embedding) and #6456 (PR validation) both touch PR body handling - merged into a single PR operations update
- **Template synchronization**: #6455 discovered this pattern, #6456 references it - documented once
- **erkdesk docs**: #6457 items are independent, no overlap with other plans

## Remaining Gaps

17 documentation items across 3 categories: PR operations, planning patterns, and erkdesk architecture.

## Implementation Steps

### Part A: PR Operations Documentation (from #6455, #6456)

#### Step 1: Update plan-embedding-in-pr.md _(from #6455)_

**File:** `docs/learned/pr-operations/plan-embedding-in-pr.md`

**Changes:**
- Update code example to include `## Implementation Plan` markdown header before `<details>` tag
- Document the two-target body pattern: `pr_body` (plain for git commits) vs `pr_body_for_github` (HTML for GitHub)
- Add reference to `_build_plan_details_section()` at `src/erk/cli/commands/pr/submit_pipeline.py:587-601`
- Note that plan content never reaches commit messages (verified by test at `tests/unit/cli/commands/pr/submit_pipeline/test_finalize_pr.py:291-294`)

**Verification:** Examples in doc match actual function output

#### Step 2: Create template-synchronization.md _(from #6455)_

**File:** `docs/learned/pr-operations/template-synchronization.md`

**Content outline:**
1. Two synchronized files must be byte-identical:
   - `packages/erk-shared/src/erk_shared/gateway/gt/commit_message_prompt.md`
   - `.claude/skills/erk-diff-analysis/references/commit-message-prompt.md`
2. Enforced by `tests/unit/test_file_sync.py:18-55` (assertion at line 49)
3. Tripwire: modifying one file without the other causes CI failure
4. No at-edit-time validation exists; discovered only during CI

**Verification:** Document describes actual test enforcement mechanism

#### Step 3: Create pr-validation-rules.md _(from #6456)_

**File:** `docs/learned/pr-operations/pr-validation-rules.md`

**Content outline:**
1. `has_checkout_footer_for_pr()`: regex `rf"erk pr checkout {pr_number}\b"` at `packages/erk-shared/src/erk_shared/gateway/pr/submit.py:25-38`
2. `has_issue_closing_reference()`: regex `rf"Closes\s+#{issue_number}\b"` (same-repo) or `rf"Closes\s+{escaped_repo}#{issue_number}\b"` (cross-repo)
3. Both use word boundary `\b` and case-insensitive matching
4. Validation orchestrated by `pr_check()` in `src/erk/cli/commands/pr/check_cmd.py`
5. Link to `docs/learned/planning/debugging-patterns.md` for the grep-based resolution pattern

**Verification:** Regex patterns match actual source code

### Part B: Planning Pattern Documentation (from #6456)

#### Step 4: Create token-optimization-patterns.md _(from #6456)_

**File:** `docs/learned/planning/token-optimization-patterns.md`

**Content outline:**
1. Problem: Consolidation with N issues creates N * plan_size tokens in parent context
2. Pattern: Delegate content fetching to child Explore agents (each fetches its own plan)
3. Implementation reference: `.claude/commands/erk/replan.md` Step 3 → Step 4a
4. Result: Parent context O(1) instead of O(n) for plan content
5. When to apply: Any multi-agent workflow handling large data payloads

**Verification:** Pattern matches actual replan command structure

#### Step 5: Create git-force-push-decision-tree.md _(from #6456)_

**File:** `docs/learned/ci/git-force-push-decision-tree.md`

**Content outline:**
1. When `git push` fails with "fetch first":
   - Check `git log origin/branch..HEAD` (outgoing commits)
   - Check `git log HEAD..origin/branch` (incoming commits)
2. Decision tree: incoming empty = safe to force push; incoming non-empty = pull first
3. Common scenario: After `gt submit` squashes commits, divergence is EXPECTED
4. Tripwire: Force pushing with unreviewed incoming commits causes data loss

**Verification:** Decision tree aligns with actual git behavior

#### Step 6: Create step-renumbering-checklist.md _(from #6456)_

**File:** `docs/learned/commands/step-renumbering-checklist.md`

**Content outline:**
1. When merging/removing steps in slash commands: renumber all subsequent steps
2. Update all cross-references ("See Step 4b" must match actual step numbers)
3. Check both forward and backward references
4. Example: replan.md Step 3 removal required updating Steps 4a-4f references

**Verification:** Checklist items match actual replan refactoring changes

#### Step 7: Create metadata-block-fallback.md _(from #6456)_

**File:** `docs/learned/planning/metadata-block-fallback.md`

**Content outline:**
1. Primary: Look for `<!-- erk:metadata-block:plan-body -->` in first comment
2. Fallback: Check issue body directly (handles older issues like #6431)
3. Implementation: `.claude/commands/erk/replan.md` Step 4a
4. Agent pattern: Always try both locations before reporting "no plan content found"

**Verification:** Fallback logic matches replan command instructions

#### Step 8: Create session-id-substitution.md _(from #6456)_

**File:** `docs/learned/commands/session-id-substitution.md`

**Content outline:**
1. In skills/commands: Use `${CLAUDE_SESSION_ID}` string substitution (since Claude Code 2.1.9)
2. In hooks: Session ID comes via stdin JSON, NOT environment variables
3. When generating commands for Claude from hooks: interpolate the actual value
4. Best-effort pattern: `cmd || true` when session ID may be unavailable

**Verification:** Patterns match AGENTS.md documentation

#### Step 9: Create commit-squash-divergence.md _(from #6456)_

**File:** `docs/learned/ci/commit-squash-divergence.md`

**Content outline:**
1. After `gt submit` squashes multiple commits, branch diverges from remote - this is EXPECTED
2. `git push` will fail with "fetch first" - this is NOT an error
3. Safe response: force push (no incoming commits from others)
4. Link to git-force-push-decision-tree.md for general decision framework

**Verification:** Matches observed Graphite workflow behavior

### Part C: erkdesk Documentation (from #6457)

#### Step 10: Create erkdesk-project-structure.md _(from #6457)_

**File:** `docs/learned/desktop-dash/erkdesk-project-structure.md`

**Content outline:**
1. Directory layout: `erkdesk/` with `src/main/`, `src/renderer/`, config files
2. Standalone pnpm project (NOT a pnpm workspace)
3. Three Vite build targets: main (Node.js), preload (bridge), renderer (React)
4. Orchestrated by `forge.config.ts` VitePlugin
5. Makefile targets: `erkdesk-start`, `erkdesk-package`, `erkdesk-make`

**Verification:** Structure matches actual `erkdesk/` directory

#### Step 11: Create pnpm-hoisting-pattern.md _(from #6457)_

**File:** `docs/learned/desktop-dash/pnpm-hoisting-pattern.md`

**Content outline:**
1. `.npmrc` with `node-linker = hoisted` is REQUIRED for Electron
2. Without it: Electron crashes with cryptic errors (silent failure)
3. Default pnpm symlink structure incompatible with Electron module resolution
4. Tripwire: This one-line config prevents ~30min debugging sessions

**Verification:** `.npmrc` file exists with correct content

#### Step 12: Create forge-vite-setup.md _(from #6457)_

**File:** `docs/learned/desktop-dash/forge-vite-setup.md`

**Content outline:**
1. `forge.config.ts` defines three VitePlugin build entries
2. `vite.main.config.ts`: Node.js target, ESM module resolution
3. `vite.preload.config.ts`: External electron, minimal bundle
4. `src/renderer/vite.config.ts`: React plugin, HMR in dev
5. MakerZIP for cross-platform distribution (darwin, linux, win32)

**Verification:** Config descriptions match actual files

#### Step 13: Create main-process-startup.md _(from #6457)_

**File:** `docs/learned/desktop-dash/main-process-startup.md`

**Content outline:**
1. `createWindow()` function with security defaults: `contextIsolation: true`, `nodeIntegration: false`
2. HMR-aware loading: dev server URL vs production file path
3. DevTools auto-open in development only
4. macOS-specific `activate` handler for dock icon clicks
5. Electron-squirrel-startup handler for Windows installer

**Verification:** Code descriptions match `erkdesk/src/main/index.ts`

#### Step 14: Create preload-bridge-patterns.md _(from #6457)_

**File:** `docs/learned/desktop-dash/preload-bridge-patterns.md`

**Content outline:**
1. `contextBridge.exposeInMainWorld("erkdesk", {...})` pattern
2. Currently exposes only version string; reserved for future IPC methods
3. No TypeScript type definitions yet for `window.erkdesk`
4. Security: preload script is the ONLY bridge between renderer and Node.js
5. Link to `docs/learned/desktop-dash/security.md` for broader security patterns

**Verification:** Patterns match `erkdesk/src/main/preload.ts`

### Part D: Update Index Files and Tripwires

#### Step 15: Update category index files

**Files to update:**
- `docs/learned/pr-operations/index.md` - Add entries for template-synchronization.md, pr-validation-rules.md
- `docs/learned/planning/index.md` - Add entries for token-optimization-patterns.md, metadata-block-fallback.md
- `docs/learned/ci/index.md` - Add entries for git-force-push-decision-tree.md, commit-squash-divergence.md
- `docs/learned/commands/index.md` - Add entries for step-renumbering-checklist.md, session-id-substitution.md
- `docs/learned/desktop-dash/index.md` - Add entries for 5 new erkdesk docs

**Note:** Run `erk docs sync` after all changes to regenerate auto-generated files.

#### Step 16: Add tripwires to category tripwire files

**New tripwires:**
- `docs/learned/pr-operations/tripwires.md` (create if not exists): Template sync requirement
- `docs/learned/planning/tripwires.md`: Token optimization delegation pattern
- `docs/learned/ci/tripwires.md`: Force push decision tree
- `docs/learned/desktop-dash/tripwires.md`: pnpm hoisting requirement
- `docs/learned/commands/tripwires.md`: Step renumbering cross-references

**Verification:** Run `erk docs sync` and verify tripwires-index.md counts update

## Attribution

Items by source:

- **#6455**: Steps 1, 2 (+ overlap with #6456 in Step 3)
- **#6456**: Steps 3, 4, 5, 6, 7, 8, 9
- **#6457**: Steps 10, 11, 12, 13, 14
- **Shared**: Steps 15, 16 (index/tripwire updates)