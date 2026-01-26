# Plan: Consolidated Documentation Updates from erk-learn Plans

> **Consolidates:** #6134, #6131, #6130, #6125, #6120
> **Type:** erk-learn (documentation plan)

## Source Plans

| # | Title | Items Merged | Status |
|---|-------|--------------|--------|
| 6134 | Replace Haiku Plan Generation with Full Claude Planning Sessions | 10 items | Partial overlap |
| 6131 | Remote Execution Implementation Documentation | 7 items | Minimal overlap |
| 6130 | Complete howto/planless-workflow.md | 5 gaps + patterns | Unique |
| 6125 | Add CIRunner Gateway to Eliminate subprocess.run Mocks | 13 items | Minimal overlap |
| 6120 | Fix PR Review Discovery for Large PRs | 5 items | Unique |

## What Changed Since Original Plans

- PR #6110 merged removing Haiku-based plan generation (2,827 lines deleted)
- CIRunner gateway fully implemented (`packages/erk-shared/src/erk_shared/gateway/ci_runner/`)
- PR #6119 fixed discover-reviews for large PRs using REST API pagination
- Several doc files still exist but need updates (not creation)

## Investigation Findings

### Overlap Analysis

**High Overlap (Merge into single items):**
- Session preprocessing docs (#6134 + #6131) → One comprehensive update to `preprocessing.md`
- Learn workflow architecture (#6134 + #6125) → Combine into single `learn-workflow-architecture.md`

**No Overlap (Keep separate):**
- Planless workflow gaps (#6130) - unique topic
- GitHub API limits (#6120) - unique topic
- CIRunner gateway docs (#6125) - unique topic

### Corrections to Original Plans

- **#6134**: `prompt-executor-gateway.md` still references Haiku - confirmed needs update
- **#6131**: `preprocessing.md` exists (81 lines) - needs UPDATE not CREATE
- **#6130**: Pattern templates don't exist anywhere - confirmed CREATE needed
- **#6125**: `subprocess-testing.md` exists and documents FakeCIRunner - just needs CIRunner example added
- **#6120**: Fix is implemented but no documentation was added - confirmed CREATE needed

## Remaining Documentation Items

### HIGH Priority (Blocking future agents)

#### 1. UPDATE: Remove Haiku Default Reference
**File:** `docs/learned/architecture/prompt-executor-gateway.md`
**Action:** Remove/update Haiku-as-default statements; clarify model selection varies by subsystem

#### 2. UPDATE: Add CIRunner to Gateway Inventory
**File:** `docs/learned/architecture/gateway-inventory.md`
**Action:** Add CIRunner section with CICheckResult dataclass fields (`passed`, `error_type`)

#### 3. CREATE: GitHub CLI Limitations
**File:** `docs/learned/architecture/github-cli-limits.md`
**Action:** Document `gh pr diff` HTTP 406 error on 300+ files; REST API pagination alternative

#### 4. ADD TRIPWIRE: gh pr diff Size Limits
**File:** `docs/learned/universal-tripwires.md`
**Action:** Add tripwire warning about `gh pr diff --name-only` failing on large PRs

### MEDIUM Priority (Improves efficiency)

#### 5. UPDATE: Session Preprocessing Metrics
**File:** `docs/learned/sessions/preprocessing.md`
**Action:** Add compression metrics table (84% reduction), chunking algorithm, part naming convention

#### 6. CREATE: Plan-Implement Workflow
**File:** `docs/learned/cli/plan-implement.md`
**Action:** Document 4-phase execution pattern, timing, cleanup discipline for `.worker-impl/`

#### 7. CREATE: PR Discovery Fallback
**File:** `docs/learned/planning/pr-discovery.md`
**Action:** Document fallback when `branch_name` missing; git history investigation pattern

#### 8. CREATE: Session ID Availability
**File:** `docs/learned/cli/session-management.md`
**Action:** Document context-dependent `${CLAUDE_SESSION_ID}` availability; expected failures

#### 9. UPDATE: Investigation Findings Purpose
**File:** `docs/learned/planning/lifecycle.md`
**Action:** Add section explaining investigation findings are mandatory corrections, not suggestions

### LOW Priority (Pattern documentation)

#### 10. CREATE: Dependency Injection in Exec Scripts
**File:** `docs/learned/cli/dependency-injection-patterns.md`
**Action:** Document gateway injection pattern using `ci_verify_autofix.py` as example

#### 11. CREATE: Monkeypatch Elimination Checklist
**File:** `docs/learned/testing/monkeypatch-elimination-checklist.md`
**Action:** Checklist for migrating from monkeypatch to gateway fakes

#### 12. UPDATE: Add Devrun Read-Only Design
**File:** `docs/learned/testing/devrun-agent.md` (or create if missing)
**Action:** Document forbidden prompt patterns, required patterns, iteration workflow

#### 13. COMPLETE: Planless Workflow Guide
**File:** `docs/howto/planless-workflow.md`
**Action:** Fill 7 skeleton sections; address 5 gaps (troubleshooting, stacking, CI, collaboration, learn)

#### 14. CREATE: Documentation Pattern Templates
**Files:** `docs/learned/documentation/when-to-switch-pattern.md`, `two-option-template.md`
**Action:** Create reusable templates for decision-point documentation

## Implementation Steps

### Phase 1: Contradiction Resolution (1 file)
1. Edit `docs/learned/architecture/prompt-executor-gateway.md`
   - Remove "Default 'haiku' for speed/cost" statement
   - Add note about model selection varying by subsystem

### Phase 2: Critical Tripwires and Limits (2 files)
2. Edit `docs/learned/universal-tripwires.md`
   - Add tripwire: "Before using `gh pr diff` in production code → Use REST API for PRs with 300+ files"
3. Create `docs/learned/architecture/github-cli-limits.md`
   - Document HTTP 406 error, REST API alternative, pagination pattern

### Phase 3: Gateway Documentation (2 files)
4. Edit `docs/learned/architecture/gateway-inventory.md`
   - Add CIRunner section with dataclass fields and fake configuration
5. Edit `docs/learned/testing/subprocess-testing.md`
   - Add FakeCIRunner example with `failing_checks`/`missing_commands`

### Phase 4: Session and Planning Docs (4 files)
6. Edit `docs/learned/sessions/preprocessing.md`
   - Add compression metrics table, chunking explanation
7. Create `docs/learned/cli/plan-implement.md`
   - 4-phase pattern, timing, cleanup discipline
8. Create `docs/learned/planning/pr-discovery.md`
   - Fallback strategies when branch_name missing
9. Create `docs/learned/cli/session-management.md`
   - Context availability table, expected failures

### Phase 5: Workflow and Pattern Docs (4 files)
10. Edit `docs/learned/planning/lifecycle.md`
    - Add investigation findings section
11. Edit or create `docs/learned/testing/devrun-agent.md`
    - Read-only design, forbidden patterns
12. Create `docs/learned/cli/dependency-injection-patterns.md`
    - Gateway injection example
13. Create `docs/learned/testing/monkeypatch-elimination-checklist.md`

### Phase 6: Planless and Patterns (3 files)
14. Complete `docs/howto/planless-workflow.md`
    - Fill all 7 sections, address 5 identified gaps
15. Create `docs/learned/documentation/when-to-switch-pattern.md`
16. Create `docs/learned/documentation/two-option-template.md`

## Files to Modify

| File | Action |
|------|--------|
| `docs/learned/architecture/prompt-executor-gateway.md` | Edit - remove Haiku default |
| `docs/learned/universal-tripwires.md` | Edit - add gh pr diff tripwire |
| `docs/learned/architecture/github-cli-limits.md` | Create |
| `docs/learned/architecture/gateway-inventory.md` | Edit - add CIRunner |
| `docs/learned/testing/subprocess-testing.md` | Edit - add FakeCIRunner example |
| `docs/learned/sessions/preprocessing.md` | Edit - add metrics |
| `docs/learned/cli/plan-implement.md` | Create |
| `docs/learned/planning/pr-discovery.md` | Create |
| `docs/learned/cli/session-management.md` | Create |
| `docs/learned/planning/lifecycle.md` | Edit - add investigation section |
| `docs/learned/testing/devrun-agent.md` | Create or edit |
| `docs/learned/cli/dependency-injection-patterns.md` | Create |
| `docs/learned/testing/monkeypatch-elimination-checklist.md` | Create |
| `docs/howto/planless-workflow.md` | Edit - complete skeleton |
| `docs/learned/documentation/when-to-switch-pattern.md` | Create |
| `docs/learned/documentation/two-option-template.md` | Create |

## Verification

1. Run `make format` to ensure markdown formatting passes
2. Run `erk docs sync` to update auto-generated indexes
3. Verify all new files have proper frontmatter with `read_when` conditions
4. Verify tripwires have proper `action` and `warning` fields
5. Check internal links work (reference existing docs correctly)

## Attribution

Items by source:
- **#6134**: Items 1, 5 (partial), 9
- **#6131**: Items 5 (partial), 6, 7, 8, 9, 12
- **#6125**: Items 2, 4, 5 (partial), 10, 11, 12
- **#6120**: Items 3, 4
- **#6130**: Items 13, 14, 15, 16

## Related Documentation

**Skills to load:**
- `learned-docs` - For documentation authoring patterns
- `dignified-python` - For any code examples in docs

**Existing docs to reference:**
- `docs/learned/architecture/gateway-abc-implementation.md` - Gateway pattern reference
- `docs/learned/testing/fake-infrastructure-patterns.md` - Fake patterns (if exists)
- `docs/learned/documentation/divio-documentation-system.md` - Doc structure guidance