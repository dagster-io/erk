# Plan: Consolidate documentation from 10 erk-learn plans

> **Consolidates:** #8935, #8934, #8933, #8930, #8929, #8927, #8926, #8924, #8921, #8919

## Context

10 erk-learn plans accumulated from recent implementation sessions. All underlying PRs are merged and fully implemented. This plan consolidates their documentation needs into actionable steps, fixing outdated docs and capturing new patterns.

## Source Plans

| # | Title | Items Merged |
|---|-------|-------------|
| #8935 | Rename cmux-checkout-workspace to cmux-open-pr | 2 items (merged with #8933) |
| #8934 | Clarify test helper function exemptions | 1 item |
| #8933 | Remove --sync from checkout, add --script/--sync to teleport | 2 items (merged with #8935) |
| #8930 | Implement RemoteGitHub read operations (Phase 1 & 2) | 3 items |
| #8929 | Fix slow unit tests + codespace gateway extension | 2 items |
| #8927 | Disable UV cache pruning in remote setup | 1 item |
| #8926 | Create /local:check-superceded command | 1 item |
| #8924 | Drop uv pip install from activation scripts | 2 items |
| #8921 | Add Check 8 for roadmap table sync validation | 1 item |
| #8919 | Update rebase skill + misc fixes | 2 items |

## Overlap Analysis

- **#8935 and #8933** cover identical source PRs (#8897, #8932). Merged into single set of doc items.
- **#8924 and #8927** both relate to CI/build infrastructure (uv/cache). Kept separate but grouped in implementation order.

## Corrections to Original Plans

- **#8935/#8933**: File is still named `cmux_checkout_workspace.py` (Python module name unchanged); only the Click command name changed to `cmux-open-pr`
- **#8919**: Rebase skill file was subsequently renamed from `rebase.md` to `pr-rebase.md` in PR #8925
- **#8924**: `workspace-activation.md` is stale — still describes the removed `uv pip install` line
- **#8921**: `validate_objective()` docstring lists 7 checks but implementation has 8

## Implementation Steps

### Step 1: Fix outdated workspace-activation.md _(from #8924)_

**File:** `docs/learned/erk/workspace-activation.md`

- Remove or rewrite the "Package Refresh" section (lines ~21-25) that describes the removed `uv pip install --no-deps` behavior
- Update to explain that `uv sync --quiet` handles workspace package installation
- **Source:** Investigation found `activation.py` line 211 only has `uv sync --quiet`
- **Verification:** `grep -r "uv pip install" docs/learned/erk/workspace-activation.md` returns nothing

### Step 2: Remove dead tripwire for uv pip install _(from #8924)_

**File:** `docs/learned/erk/tripwires.md`

- Remove tripwire at line ~47 that warns against "removing the uv pip install --no-deps line from activation" — the line is already removed
- **Verification:** No stale tripwire references to removed code

### Step 3: Update validate_objective() docstring _(from #8921)_

**File:** `src/erk/cli/commands/objective/check_cmd.py`

- Update docstring for `validate_objective()` (lines 111-118) to include Check 8: "Roadmap table sync (rendered table matches YAML source)"
- Also update the brief docstring for `check_objective()` command (lines 271-272)
- **Verification:** Docstring lists all 8 checks matching implementation

### Step 4: Document checkout/teleport refactoring _(from #8935, #8933)_

**File:** `docs/learned/cli/checkout-teleport-split.md` (NEW)

**Content outline:**
1. Problem: checkout was overloaded with both local and remote (Graphite sync) concerns
2. Solution: checkout is lightweight (local-only), teleport is heavyweight (remote + sync)
3. Key files: `checkout_cmd.py`, `teleport_cmd.py`, `cmux_checkout_workspace.py`
4. cmux-open-pr command: `--mode` flag selects checkout vs teleport
5. TUI integration: separate registry entries, keybindings, and async workers

**Frontmatter:**
- category: cli
- read_when: "working with erk pr checkout or erk pr teleport commands"
- tripwires: "adding --sync to checkout" → "checkout is local-only; use teleport for sync"

**Verification:** Document accurately describes current command signatures

### Step 5: Document RemoteGitHub gateway pattern _(from #8930)_

**File:** `docs/learned/architecture/remote-github-gateway.md` (NEW)

**Content outline:**
1. Purpose: REST API-based GitHub operations without local git/gh CLI
2. ABC location: `packages/erk-shared/src/erk_shared/gateway/remote_github/abc.py`
3. 7 read methods + 2 mutation methods documented
4. Shared `--repo` infrastructure: `repo_resolution.py` with `resolve_owner_repo()`, `get_remote_github()`, `is_remote_mode()`, `repo_option`
5. Real implementation uses HttpClient; Fake uses constructor injection + mutation tracking
6. Pattern: Remote mode vs local mode branching in PR commands

**Frontmatter:**
- category: architecture
- read_when: "working with RemoteGitHub, adding --repo support, or implementing remote PR operations"
- tripwires: "calling gh CLI for GitHub API operations" → "use RemoteGitHub gateway instead"

**Verification:** All 7 read methods listed match abc.py

### Step 6: Document test migration patterns _(from #8929)_

**File:** `docs/learned/testing/test-layer-migration.md` (NEW)

**Content outline:**
1. When to migrate: Tests that call real `create_context()`, scan filesystem trees, or use real git operations belong in integration, not unit
2. Migration process: Extract tests, verify no real I/O remains in unit layer
3. Concrete example: `test_forward_references.py` moved to integration; 3 context tests extracted
4. Codespace gateway extension as example of maintaining the 5-place pattern (abc, real, fake, dry_run, printing)

**Frontmatter:**
- category: testing
- read_when: "moving tests between unit and integration layers"
- tripwires: "unit test calling create_context() or scanning real filesystem" → "move to integration"

**Verification:** Test files exist at documented paths

### Step 7: Document CI cache management _(from #8927)_

**File:** `docs/learned/ci/uv-cache-management.md` (NEW)

**Content outline:**
1. Problem: `astral-sh/setup-uv@v7` post-job cache pruning can timeout (~5min)
2. Solution: `prune-cache: false` in setup-uv action config
3. Rationale: Ephemeral CI runners don't benefit from pruning
4. Location: `.github/actions/erk-remote-setup/action.yml` lines 30-32

**Frontmatter:**
- category: ci
- read_when: "debugging slow CI jobs or GitHub Actions cache issues"
- tripwires: "CI job timing out in post-job cleanup" → "check if UV cache pruning is enabled"

**Verification:** action.yml has `prune-cache: false`

### Step 8: Document check-superceded command _(from #8926)_

**File:** `docs/learned/cli/local-commands.md` (UPDATE)

- Verify `check-superceded` entry exists and is accurate (may already be updated from PR #8913)
- If entry is stale, update with: 9 phases, 5 match types, 4 verdict categories
- **Verification:** Entry matches `.claude/commands/local/check-superceded.md`

### Step 9: Document test helper exemption pattern _(from #8934)_

**File:** `docs/learned/testing/testing.md` (UPDATE)

- Add a section or note about the test helper default parameter exemption
- Clarify: functions in `test_*.py`, `conftest.py`, and Fake classes are exempt from the no-default-parameters rule
- Reference: `.claude/skills/dignified-python/references/api-design.md` line 61
- **Verification:** Testing docs mention the exemption

### Step 10: Document AskUserQuestion in skills pattern _(from #8919)_

**File:** `docs/learned/commands/skill-patterns.md` (UPDATE or NEW)

- Document the pattern of using AskUserQuestion in slash command skills for user-facing decisions
- Example: pr-rebase.md Step 8 offering push options (Graphite, git, manual)
- Also note: prompt_executor naming convention (replaces llm_caller)
- **Verification:** Pattern matches `.claude/commands/erk/pr-rebase.md` lines 58-61

### Step 11: Run `erk docs sync` to regenerate indices

- After all doc changes, run `erk docs sync` to update auto-generated index files
- **Verification:** `docs/learned/index.md` includes new documents; tripwires-index.md updated

## Attribution

| Steps | Source Plans |
|-------|------------|
| 1-2 | #8924 |
| 3 | #8921 |
| 4 | #8935, #8933 |
| 5 | #8930 |
| 6 | #8929 |
| 7 | #8927 |
| 8 | #8926 |
| 9 | #8934 |
| 10 | #8919 |
| 11 | All |

## Verification

1. `grep -r "uv pip install" docs/learned/erk/` — no stale references
2. All new docs have valid frontmatter with read_when and tripwires
3. `erk docs sync` completes without errors
4. New tripwires appear in category tripwires.md files
