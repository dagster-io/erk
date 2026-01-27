# Plan: Consolidated Documentation for Gateway Migration (Q1 2025)

> **Consolidates:** #6163, #6160, #6158, #6154, #6151, #6147, #6146, #6141, #6137

## Source Plans Summary

| #    | Title                                      | Code Status   | Doc Status |
|------|--------------------------------------------|---------------|------------|
| 6163 | Phase 2B Branch Migration Documentation    | Complete      | 0% done    |
| 6160 | Phase 2A Branch Subgateway Steelthread     | Complete      | 36% (4/11) |
| 6158 | Make delete_branch Idempotent              | Complete      | 0% (0/4)   |
| 6154 | Move TUI Gateways to gateway/              | Complete      | 0% (0/9)   |
| 6151 | CodespaceRegistry Gateway Consolidation    | Complete      | 0% (0/8)   |
| 6147 | Consolidate Gateways Phases 4-7            | Complete      | 27% (3/11) |
| 6146 | GitHub Actions API Reference               | On branch     | 0% (0/1)   |
| 6141 | Move GitHubAdmin Gateway                   | Complete      | 50% (3/6)  |
| 6137 | Public Documentation Quick Fixes           | Partial       | 0% (0/10)  |

---

## Detailed Investigation Findings

### #6163: Phase 2B Branch Migration Documentation

**Codebase State:**
- `git.branch` property EXISTS at `packages/erk-shared/src/erk_shared/gateway/git/abc.py:105-109`
- Added in commit `6198bd723` via PR #6159
- GitBranchOps has 5 mutation methods in `gateway/git/branch_ops/abc.py`:
  - `create_branch()`, `delete_branch()`, `checkout_branch()`, `checkout_detached()`, `create_tracking_branch()`
- 14 query methods remain on Git ABC (not yet migrated): `get_current_branch()`, `detect_trunk_branch()`, `list_local_branches()`, `list_remote_branches()`, `get_branch_head()`, `branch_exists_on_remote()`, `get_ahead_behind()`, `get_branch_last_commit_time()`, `count_commits_ahead()`, `get_all_branch_sync_info()`, `get_commit_message()`, `has_uncommitted_changes()`, `is_branch_diverged_from_remote()`, `get_commit_messages_since()`
- Query migration exists in commit `7df203069` but NOT on master

**Documentation Status:**
- Phase 2A docs exist on branch (commit `a2e2d1e40`) but NOT merged to master
- Gateway inventory (`gateway-inventory.md`) correctly documents GitBranchOps with 5 mutations
- `tripwires.md` has partial coverage for branch mutations (lines 31-37)

**Missing Items:**
- `docs/learned/architecture/flatten-subgateway-pattern.md` - Pattern not formally documented
- `docs/learned/testing/fake-state-linkage.md` - How fakes share state with parent
- Tripwire: "Double .branch.branch" anti-pattern
- Tripwire: "METHOD_NOT_ON_GIT" for subgateway methods

---

### #6160: Phase 2A Branch Subgateway Steelthread

**Codebase State:**
- Implementation complete via PRs #6159 (branch property) and #6156 (idempotent delete)
- 5-layer pattern fully implemented:
  - `abc.py` - abstract property with TYPE_CHECKING guard
  - `real.py` - RealGitBranchOps instance at line 166-169
  - `fake.py` - FakeGitBranchOps with linked mutation tracking at line 330-333
  - `dry_run.py` - DryRunGitBranchOps wrapper
  - `printing.py` - PrintingGitBranchOps wrapper

**Documentation Status (4/11 done):**
- ✅ `tripwires.md` has partial coverage for branch mutation routing
- ✅ `testing.md` has linked mutation tracking
- ✅ `gateway-hierarchy.md` has BranchManager factory documentation
- ⚠️ `gateway-abc-implementation.md` has sub-gateway pattern but **property name mismatch**: docs show `branch_ops`, code uses `branch`

**Missing Items:**
- Flatten subgateway pattern documentation (critical - applies to Phase 2B)
- Git branch subgateway migration guide (before/after examples)
- Tripwire: Subgateway property consistency
- Tripwire: Factory refactoring consistency

**Critical Correction:** Property name is `branch` NOT `branch_ops` - all documentation examples need updating

---

### #6158: Make delete_branch Idempotent

**Codebase State:**
- Implementation COMPLETE in commit `8ffda3f66` (PR #6156)
- Location: `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/real.py:38-59`
- Pattern: LBYL check via `git show-ref --verify refs/heads/{branch_name}` before deletion
- Docstring documents: "Idempotent: if branch doesn't exist, returns successfully."
- Integration test: `tests/integration/test_real_git_branch_ops.py:191-202` - `test_delete_branch_idempotent_when_branch_missing()`
- FakeGitBranchOps already handled idempotency correctly (no changes needed)

**Documentation Status (0/4 done):**
- ❌ `lbyl-gateway-pattern.md` line 106 says "Skip LBYL when operation is idempotent" - CONTRADICTS using LBYL *to implement* idempotency
- ❌ `gateway-abc-implementation.md` has mutation methods section (lines 142-184) but NO idempotent mutations coverage
- ❌ No fake-first verification workflow documentation
- ❌ `tests/integration/AGENTS.md` has no idempotent operation testing pattern

**Missing Items:**
1. Update `lbyl-gateway-pattern.md` - clarify two patterns:
   - Skip LBYL if operation is *already* idempotent
   - Use LBYL *to implement* idempotency for operations that fail on missing resources
2. Add "Idempotent Mutations" section to `gateway-abc-implementation.md` with 5-file verification checklist
3. Add fake-first verification workflow to `testing.md`
4. Add integration testing pattern for idempotent operations to `tests/integration/AGENTS.md`

---

### #6154: Move TUI Gateways to gateway/

**Codebase State:**
- Implementation COMPLETE in commit `a86cdf445` (PR #6153)
- CommandExecutor gateway: `packages/erk-shared/src/erk_shared/gateway/command_executor/` (abc, real, fake, __init__)
- PlanDataProvider gateway: `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/` (abc, real, fake, __init__)
- Imports updated across codebase to new paths

**Documentation Status (0/9 done):**
- ❌ `docs/learned/tui/command-execution.md` exists but has NO import path examples
- ❌ `docs/learned/tui/architecture.md` shows OLD directory structure (`src/erk/tui/commands/executor.py`)
- ❌ `gateway-inventory.md` is MISSING entries for CommandExecutor and PlanDataProvider
- ❌ `docs/learned/testing/shared-test-fakes.md` does NOT exist
- ❌ `docs/learned/tui/import-patterns.md` does NOT exist
- ❌ `docs/learned/architecture/gateway-consolidation.md` does NOT exist
- ❌ `docs/learned/refactoring/import-migration.md` does NOT exist (directory doesn't exist)

**Missing Gateway Inventory Entries:**
```markdown
### CommandExecutor (`gateway/command_executor/`)
TUI command execution abstraction for test isolation.
**Key Methods:** execute(command: list[str]) -> CommandResult
**Fake Features:** Pre-programmed responses, command tracking

### PlanDataProvider (`gateway/plan_data_provider/`)
TUI plan data access abstraction.
**Key Methods:** fetch_plans(), close_plan(), submit_to_queue()
**Properties:** repo_root, clipboard, browser
**Fake Features:** In-memory plan storage, action tracking
```

---

### #6151: CodespaceRegistry Gateway Consolidation

**Codebase State:**
- Implementation COMPLETE in commit `80b36feea` (PR #6150)
- Gateway: `packages/erk-shared/src/erk_shared/gateway/codespace_registry/` (abc, real, fake, __init__)
- Types: `RegisteredCodespace` frozen dataclass with name, gh_name, created_at
- ABC has 4 read-only methods
- Mutation functions: `register_codespace()`, `unregister_codespace()`, `set_default_codespace()`
- Storage: `~/.erk/codespaces.toml`

**Documentation Status (0/8 done):**
- ❌ `docs/learned/gateway/codespace-registry.md` does NOT exist (directory doesn't exist)
- ❌ `gateway-inventory.md` has Codespace (SSH) entry but NO CodespaceRegistry entry
- ❌ `docs/learned/config/codespaces-toml.md` does NOT exist
- ❌ Import sorting tripwire not added (16 I001 violations in PR #6150)
- ❌ CLI command integration docs not created
- ❌ Gateway pattern maturity documentation not created
- ❌ Fake mutation patterns documentation not created

**Critical Gap:** CodespaceRegistry is a fully functional, tested gateway that is NOT documented in the gateway inventory

---

### #6147: Consolidate Gateways Phases 4-7

**Codebase State:**
- Implementation COMPLETE in commit `83a042ff0` (PR #6145)
- All 4 gateways moved to `gateway/` directory:
  - `gateway/branch_manager/` - 6 Python files, factory pattern
  - `gateway/prompt_executor/` - 3-file pattern
  - `gateway/claude_installation/` - 3-file pattern
  - `gateway/live_display/` - 3-file pattern

**Documentation Status (3/11 done, all 3 OUTDATED):**
- ⚠️ `gateway-inventory.md` - lists BranchManager at OLD location "packages/erk-shared/src/erk_shared/" instead of `gateway/branch_manager/`
- ⚠️ `branch-manager-abstraction.md` - paths reference OLD location
- ⚠️ `prompt-executor-gateway.md` - line 16 shows OLD path `prompt_executor/` not `gateway/prompt_executor/`
- ❌ `claude-installation-gateway.md` does NOT exist
- ❌ `live-display-gateway.md` does NOT exist
- ❌ `planning/gateway-consolidation-checklist.md` does NOT exist
- ❌ `refactoring/libcst-systematic-imports.md` does NOT exist (directory doesn't exist)
- ❌ Import relocation checklist not added to `gateway-abc-implementation.md`

**Files Needing Path Updates:**
1. `docs/learned/architecture/gateway-inventory.md` - line ~60
2. `docs/learned/architecture/branch-manager-abstraction.md` - multiple path references
3. `docs/learned/architecture/prompt-executor-gateway.md` - line 16

---

### #6146: GitHub Actions API Reference

**Codebase State:**
- Main deliverable EXISTS on branch `origin/P6142-erk-plan-github-actions-a-01-26-2237`
- File: `docs/learned/reference/github-actions-api.md` (754 lines)
- Commit: `5d732f008` "Add GitHub Actions API reference documentation"
- NOT merged to master

**Content Coverage:**
- 12 REST API categories: Artifacts, Cache, GitHub-hosted runners, OIDC, Permissions, Secrets, Self-hosted runner groups, Self-hosted runners, Variables, Workflow jobs, Workflow runs, Workflows
- Complete workflow YAML DSL reference
- Reusable workflow patterns
- Authentication methods

**Documentation Status (0/1 done):**
- ❌ `docs/learned/reference/index.md` does NOT include github-actions-api.md entry
- ❌ File not merged to master

---

### #6141: Move GitHubAdmin Gateway

**Codebase State:**
- Implementation COMPLETE in commit `6e30e3d69` (PR #6136)
- Gateway: `packages/erk-shared/src/erk_shared/gateway/github_admin/` (abc, real, fake, noop, printing)

**Documentation Status (3/6 done):**
- ✅ `parallel-agent-pattern.md` covers 3-tier learn orchestration pattern
- ✅ `learn-workflow.md` documents agent tier architecture (lines 75-116)
- ✅ `preprocessing.md` documents auto-chunking behavior
- ❌ `docs/learned/planning/learn-plan-validation.md` does NOT exist (cycle prevention)
- ❌ `docs/learned/sessions/remote-session-analysis.md` does NOT exist
- ❌ `gateway-inventory.md` entry for GitHubAdmin needs verification

---

### #6137: Public Documentation Quick Fixes

**Codebase State:**
- CLI uses `erk land` (NOT `erk pr land`) - implemented at `src/erk/cli/commands/land_cmd.py`
- Registered as top-level command in `src/erk/cli/cli.py`

**Documentation Status (0/10 done):**
- ❌ 18 references to deprecated `erk pr land` in docs/learned/:
  1. `erk/branch-cleanup.md` (2 refs)
  2. `architecture/learn-origin-tracking.md` (3 refs)
  3. `glossary.md` (5 refs)
  4. `architecture/erk-architecture.md` (1 ref)
  5. `architecture/markers.md` (2 refs)
  6. `cli/optional-arguments.md` (1 ref)
  7. `architecture/command-boundaries.md` (2 refs)
  8. `architecture/tripwires.md` (1 ref)
  9. `architecture/index.md` (1 ref)
  10. `sessions/raw-session-processing.md` (1 ref)

**Missing New Documentation Files:**
- ❌ `docs/learned/pr/validation-requirements.md` - PR checkout footer validation
- ❌ `docs/learned/documentation/scope-and-audience.md` - audience targeting
- ❌ `docs/learned/ci/devrun-delegation.md` - CI tool routing
- ❌ `docs/learned/development/grep-verification.md` - verification patterns (directory missing)

---

## Overlap Analysis

### Gateway Inventory Updates (6 gateways missing)
From plans: #6154, #6151, #6147, #6141
- CommandExecutor - from #6154
- PlanDataProvider - from #6154
- CodespaceRegistry - from #6151
- GitHubAdmin - from #6141
- ClaudeInstallation - from #6147
- LiveDisplay - from #6147

### Tripwire Documentation (4+ tripwires needed)
From plans: #6163, #6160, #6158, #6151
- "Double .branch.branch" anti-pattern - from #6163
- "METHOD_NOT_ON_GIT" for subgateway methods - from #6163
- "delete_branch should be idempotent" - from #6158
- Import sorting after gateway moves - from #6151
- Subgateway property consistency - from #6160
- Factory refactoring consistency - from #6160

### Import Path Corrections (3+ docs outdated)
From plans: #6147, #6137
- `gateway-inventory.md` - BranchManager path
- `branch-manager-abstraction.md` - multiple paths
- `prompt-executor-gateway.md` - line 16 path

### Flatten Subgateway Pattern (referenced by multiple plans)
From plans: #6163, #6160
- Pattern: `@property def branch(self) -> GitBranchOps: return self._branch_ops`
- Converts `ctx.git_branch_ops.*` to `ctx.git.branch.*`
- Critical for Phase 2B and future subgateways

---

## Implementation Steps

### Phase 1: Critical Pattern Documentation _(from #6163, #6160)_

1. **Create `docs/learned/architecture/flatten-subgateway-pattern.md`**
   - Document the `@property def branch(self) -> GitBranchOps` pattern
   - Show 5-layer implementation examples from `gateway/git/`:
     - `abc.py:105-109` - abstract property with TYPE_CHECKING guard
     - `real.py:166-169` - returns RealGitBranchOps instance
     - `fake.py:330-333` - returns FakeGitBranchOps with linked state
     - `dry_run.py` - wraps with DryRunGitBranchOps
     - `printing.py` - wraps with PrintingGitBranchOps
   - Include factory instantiation pattern from `real.py`
   - Document the TYPE_CHECKING guard pattern for avoiding circular imports

### Phase 2: Gateway Inventory Updates _(from #6154, #6151, #6147, #6141)_

2. **Update `docs/learned/architecture/gateway-inventory.md`**
   - Add CommandExecutor gateway entry (from #6154)
   - Add PlanDataProvider gateway entry (from #6154)
   - Add CodespaceRegistry gateway entry (from #6151)
   - Add GitHubAdmin gateway entry (from #6141)
   - Add ClaudeInstallation gateway entry (from #6147)
   - Add LiveDisplay gateway entry (from #6147)
   - Fix BranchManager path: change "packages/erk-shared/src/erk_shared/" to `gateway/branch_manager/`

### Phase 3: Idempotent Operations Documentation _(from #6158)_

3. **Update `docs/learned/architecture/gateway-abc-implementation.md`**
   - Add "Idempotent Mutations" subsection under "Mutation Methods" section (after line 184)
   - Document the pattern: Check existence → return early if missing → proceed if exists
   - Include 5-file verification checklist for behavioral changes
   - Reference `delete_branch()` implementation at `branch_ops/real.py:38-59`

4. **Update `docs/learned/architecture/lbyl-gateway-pattern.md`**
   - Clarify line 106 ("Skip LBYL when operation is idempotent")
   - Add distinction between two LBYL patterns:
     1. Skip LBYL if operation is *already* idempotent
     2. Use LBYL *to implement* idempotency for operations that fail on missing resources
   - Add decision tree for choosing pattern

### Phase 4: Tripwire Additions _(from #6163, #6160, #6158, #6151)_

5. **Update `docs/learned/architecture/tripwires.md`**
   - Add "Double .branch.branch" tripwire (accessing `ctx.git.branch.branch` by mistake)
   - Add "METHOD_NOT_ON_GIT" tripwire (calling method on Git that moved to subgateway)
   - Add "delete_branch idempotency" tripwire (mutations should check existence first)
   - Add "Import sorting after gateway moves" tripwire (run `ruff --fix` after moving files)
   - Add "Subgateway property consistency" tripwire (ensure all 5 layers implement property)

### Phase 5: New Gateway Reference Docs _(from #6147, #6151)_

6. **Create `docs/learned/architecture/claude-installation-gateway.md`**
   - Document gateway at `gateway/claude_installation/`
   - ABC interface, Real implementation, Fake for testing

7. **Create `docs/learned/architecture/live-display-gateway.md`**
   - Document gateway at `gateway/live_display/`
   - TUI display abstraction

8. **Create `docs/learned/gateway/codespace-registry.md`**
   - Document gateway at `gateway/codespace_registry/`
   - ABC with 4 read-only methods
   - Mutation functions: register, unregister, set_default
   - RegisteredCodespace dataclass fields

9. **Create `docs/learned/config/codespaces-toml.md`**
   - Document `~/.erk/codespaces.toml` schema
   - Configuration options and defaults

### Phase 6: Import Path Corrections _(from #6147, #6137)_

10. **Fix outdated import paths in existing docs:**
    - `branch-manager-abstraction.md` - update all path references to `gateway/branch_manager/`
    - `prompt-executor-gateway.md` - fix line 16 path to `gateway/prompt_executor/`
    - Any other docs with old `erk/` or `erk_shared/` paths that should be `gateway/`

11. **Replace `erk pr land` → `erk land` across docs/learned/ (18 occurrences):**
    - `erk/branch-cleanup.md` (2)
    - `architecture/learn-origin-tracking.md` (3)
    - `glossary.md` (5)
    - `architecture/erk-architecture.md` (1)
    - `architecture/markers.md` (2)
    - `cli/optional-arguments.md` (1)
    - `architecture/command-boundaries.md` (2)
    - `architecture/tripwires.md` (1)
    - `architecture/index.md` (1)
    - `sessions/raw-session-processing.md` (1)

### Phase 7: Index and Reference Updates _(from #6146)_

12. **Add github-actions-api.md entry to `docs/learned/index.md`**
    - Under appropriate category (reference or github)
    - Add read_when conditions for GitHub Actions usage

13. **Ensure github-actions-api.md is on master**
    - Merge branch `P6142-erk-plan-github-actions-a-01-26-2237` if not already done
    - Verify 754-line document is accessible

### Phase 8: Lower Priority Items _(from #6147, #6141)_

14. **Create `docs/learned/planning/gateway-consolidation-checklist.md`**
    - Checklist for future gateway consolidation phases
    - Steps: create directory, move files, update imports, update docs, run ruff

15. **Create `docs/learned/refactoring/libcst-systematic-imports.md`**
    - Guide for using LibCST for systematic import refactoring
    - Patterns from gateway consolidation PRs

16. **Create `docs/learned/planning/learn-plan-validation.md`**
    - Document validation that target issue has erk-plan label, NOT erk-learn
    - Cycle prevention for learn plans

---

## Attribution

| Steps | Source Plans |
|-------|--------------|
| 1 | #6163, #6160 |
| 2 | #6154, #6151, #6147, #6141 |
| 3-4 | #6158 |
| 5 | #6163, #6160, #6158, #6151 |
| 6-9 | #6147, #6151 |
| 10-11 | #6147, #6137 |
| 12-13 | #6146 |
| 14-16 | #6147, #6141 |

---

## Verification

1. `grep -r "erk pr land" docs/learned/` - should return 0 matches after fixes
2. `grep -r "branch_ops" docs/learned/architecture/` - verify property name is `branch` not `branch_ops`
3. Verify all 6 new gateway entries exist in `gateway-inventory.md`
4. Verify all new files exist:
   - `docs/learned/architecture/flatten-subgateway-pattern.md`
   - `docs/learned/architecture/claude-installation-gateway.md`
   - `docs/learned/architecture/live-display-gateway.md`
   - `docs/learned/gateway/codespace-registry.md`
   - `docs/learned/config/codespaces-toml.md`
   - `docs/learned/planning/gateway-consolidation-checklist.md`
   - `docs/learned/refactoring/libcst-systematic-imports.md`
   - `docs/learned/planning/learn-plan-validation.md`
5. Verify index.md has entries for all new docs
6. Run `make docs-check` if available

---

## Related Documentation

- Load `learned-docs` skill before implementing (for frontmatter, categories)
- Reference `docs/learned/architecture/gateway-abc-implementation.md` for 5-layer pattern
- Reference existing `docs/learned/tripwires-index.md` for tripwire format
- Reference `gateway/git/branch_ops/` as canonical 5-layer subgateway implementation
