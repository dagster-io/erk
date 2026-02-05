# Plan: Audit Phase 2 Docs (Objective #6697, Steps 2.1-2.10)

> **Replans:** #6704

## What Changed Since Original Plan

**Status**: Plan created 2026-02-04 but **NO implementation progress** yet (0/10 documents audited).

**Codebase Changes**:
- Phase 1 (10 docs) successfully completed via PR #6731 (merged 2026-02-04 17:27:35)
- Phase 1 demonstrated proven execution pattern: sequential `/local:audit-doc` → metadata stamped → single PR
- No changes to audit command architecture or document structure since plan creation

**Path Status Update**:
- Original plan noted "1 broken path" in step 2.4 (`objectives/roadmap-mutation-patterns.md`)
- Current verification: **all 4 cross-references are valid** (see Investigation Notes comment on #6704)
- Likely fixed between scan time and now, or scan data was conservative

## Investigation Findings

### Document Status: All Ready for Audit

All 10 Phase 2 documents exist at expected paths with **NO audit metadata yet**:

| Step | File Path | Lines | Blocks | Refs | Status |
|------|-----------|-------|--------|------|--------|
| 2.1 | `docs/learned/desktop-dash/erkdesk-project-structure.md` | 228 | 6 | 5 | ✓ EXISTS, NO audit |
| 2.2 | `docs/learned/desktop-dash/split-pane-implementation.md` | 223 | 7 | 5 | ✓ EXISTS, NO audit |
| 2.3 | `docs/learned/integrations/bundled-artifacts.md` | 220 | 3 | 8 | ✓ EXISTS, NO audit |
| 2.4 | `docs/learned/objectives/roadmap-mutation-patterns.md` | 215 | 7 | 4 | ✓ EXISTS, NO audit |
| 2.5 | `docs/learned/planning/learn-workflow.md` | 405 | 8 | 7 | ✓ EXISTS, NO audit |
| 2.6 | `docs/learned/planning/workflow.md` | 366 | 6 | 8 | ✓ EXISTS, NO audit |
| 2.7 | `docs/learned/reference/github-actions-api.md` | 754 | 8 | 6 | ✓ EXISTS, NO audit |
| 2.8 | `docs/learned/testing/session-log-fixtures.md` | 396 | 12 | 5 | ✓ EXISTS, NO audit |
| 2.9 | `docs/learned/workflows/commit-messages.md` | 378 | 8 | 5 | ✓ EXISTS, NO audit |
| 2.10 | `docs/learned/architecture/capability-system.md` | 211 | 3 | 8 | ✓ EXISTS, NO audit |

### Corrections to Original Plan

1. **Broken Path (Step 2.4)**: Plan assumed 1 broken path, but current state shows all paths valid. Audit will confirm.

2. **Line Counts**: All accurate (verified ±1 line)

### Additional Details Discovered

#### Audit Command Architecture (`/local:audit-doc`)

**Location**: `.claude/commands/local/audit-doc.md`

**7-Phase Workflow**:
1. Resolve path, read doc, extract frontmatter
2. Extract code references from doc
3. Read referenced source code
4. Adversarial analysis (6 value categories: DUPLICATIVE, DRIFT RISK, HIGH VALUE, CONTEXTUAL, EXAMPLES, CONTRADICTS)
5. Generate brief report with verdict (KEEP/SIMPLIFY/DELETE)
6. Auto-apply based on verdict + CI detection (`$CI` or `$GITHUB_ACTIONS` env vars)
7. Execute actions, update frontmatter with `last_audited: "YYYY-MM-DD HH:MM PT"` and `audit_result: clean|edited`

#### Phase 1 Success Pattern (PR #6731)

Proven execution model:
- 10 documents audited sequentially with `/local:audit-doc`
- 2 documents received major rewrites (260 and 313 lines condensed)
- All metadata stamped correctly
- Verification: "All 10 docs have `last_audited` frontmatter field. Broken paths in 1.1 and 1.3 are fixed."

#### Document Risk Profiles

- **Highest Risk (2.7)**: `reference/github-actions-api.md` (754L) - largest doc, heavy API reference
- **Most Complex (2.8)**: `testing/session-log-fixtures.md` (12 code blocks, 2 implementation examples)
- **Balanced (2.1-2.3, 2.10)**: Desktop/Integrations/Architecture docs (211-228L)

## Remaining Gaps

**All 10 documents need audit execution** - no implementation started yet.

Current state: 0/10 documents have `last_audited` or `audit_result` frontmatter fields.

## Implementation Steps

### Step 1: Execute Audit on All 10 Documents

Run `/local:audit-doc` sequentially on each Phase 2 document:

**2.1 Desktop Dash: Erkdesk Project Structure**
```bash
/local:audit-doc docs/learned/desktop-dash/erkdesk-project-structure.md
```
- **Verify**: Frontmatter updated with `last_audited` and `audit_result`
- **Check**: If verdict = SIMPLIFY, confirm rewrite applied; if KEEP, confirm metadata added
- **File**: `docs/learned/desktop-dash/erkdesk-project-structure.md:1-5` (frontmatter)

**2.2 Desktop Dash: Split Pane Implementation**
```bash
/local:audit-doc docs/learned/desktop-dash/split-pane-implementation.md
```
- **Verify**: Frontmatter updated
- **File**: `docs/learned/desktop-dash/split-pane-implementation.md:1-5`

**2.3 Integrations: Bundled Artifacts**
```bash
/local:audit-doc docs/learned/integrations/bundled-artifacts.md
```
- **Verify**: Frontmatter updated
- **File**: `docs/learned/integrations/bundled-artifacts.md:1-5`

**2.4 Objectives: Roadmap Mutation Patterns**
```bash
/local:audit-doc docs/learned/objectives/roadmap-mutation-patterns.md
```
- **Verify**: Frontmatter updated
- **Check**: Confirm all 4 cross-references still valid (lines 212-215) after any rewrites
- **File**: `docs/learned/objectives/roadmap-mutation-patterns.md:1-5`, `:212-215`

**2.5 Planning: Learn Workflow**
```bash
/local:audit-doc docs/learned/planning/learn-workflow.md
```
- **Verify**: Frontmatter updated (largest planning doc at 405L)
- **File**: `docs/learned/planning/learn-workflow.md:1-5`

**2.6 Planning: Workflow**
```bash
/local:audit-doc docs/learned/planning/workflow.md
```
- **Verify**: Frontmatter updated
- **File**: `docs/learned/planning/workflow.md:1-5`

**2.7 Reference: GitHub Actions API**
```bash
/local:audit-doc docs/learned/reference/github-actions-api.md
```
- **Verify**: Frontmatter updated (largest doc in phase at 754L)
- **Check**: Monitor for token usage (cf. PR #6717 context explosion fix)
- **File**: `docs/learned/reference/github-actions-api.md:1-5`

**2.8 Testing: Session Log Fixtures**
```bash
/local:audit-doc docs/learned/testing/session-log-fixtures.md
```
- **Verify**: Frontmatter updated (most code blocks: 12)
- **File**: `docs/learned/testing/session-log-fixtures.md:1-5`

**2.9 Workflows: Commit Messages**
```bash
/local:audit-doc docs/learned/workflows/commit-messages.md
```
- **Verify**: Frontmatter updated
- **File**: `docs/learned/workflows/commit-messages.md:1-5`

**2.10 Architecture: Capability System**
```bash
/local:audit-doc docs/learned/architecture/capability-system.md
```
- **Verify**: Frontmatter updated (score 9, lowest in phase but still audit-worthy)
- **File**: `docs/learned/architecture/capability-system.md:1-5`

---

### Step 2: Final Verification

After all 10 audits complete, verify all metadata is present:

```bash
# Check all 10 docs have last_audited field
for doc in \
  docs/learned/desktop-dash/erkdesk-project-structure.md \
  docs/learned/desktop-dash/split-pane-implementation.md \
  docs/learned/integrations/bundled-artifacts.md \
  docs/learned/objectives/roadmap-mutation-patterns.md \
  docs/learned/planning/learn-workflow.md \
  docs/learned/planning/workflow.md \
  docs/learned/reference/github-actions-api.md \
  docs/learned/testing/session-log-fixtures.md \
  docs/learned/workflows/commit-messages.md \
  docs/learned/architecture/capability-system.md
do
  echo "Checking $doc..."
  grep -E "^last_audited:" "$doc" || echo "  ❌ MISSING last_audited"
  grep -E "^audit_result:" "$doc" || echo "  ❌ MISSING audit_result"
done
```

**Expected Output**: All 10 documents should show `last_audited` and `audit_result` fields.

**Cross-Reference Check (Step 2.4)**:
```bash
# Verify all 4 cross-references in roadmap-mutation-patterns.md still valid
grep -A 4 "## Related Documentation" docs/learned/objectives/roadmap-mutation-patterns.md
```
- Confirm paths at lines 212-215 resolve correctly

---

### Step 3: Submit PR

Create single PR with all 10 audit results:

```bash
/erk:pr-submit
```

**Commit Message Template**:
```
Audit Phase 2 Docs (Objective #6697, Steps 2.1-2.10)

Run /local:audit-doc on 10 Phase 2 documents (score 9-10).
Apply audit verdicts and stamp all docs with metadata.

Documents audited:
- desktop-dash/erkdesk-project-structure.md (228L, 6 blocks)
- desktop-dash/split-pane-implementation.md (223L, 7 blocks)
- integrations/bundled-artifacts.md (220L, 3 blocks)
- objectives/roadmap-mutation-patterns.md (215L, 7 blocks)
- planning/learn-workflow.md (405L, 8 blocks)
- planning/workflow.md (366L, 6 blocks)
- reference/github-actions-api.md (754L, 8 blocks)
- testing/session-log-fixtures.md (396L, 12 blocks)
- workflows/commit-messages.md (378L, 8 blocks)
- architecture/capability-system.md (211L, 3 blocks)

All 10 docs now have last_audited and audit_result frontmatter.

Resolves #<NEW_ISSUE_NUMBER> (replan of #6704)
Part of Objective #6697 (Phase 2 of 7)
```

**PR Checks**:
- ✓ All 10 docs have `last_audited` field
- ✓ All 10 docs have `audit_result: clean` or `audit_result: edited`
- ✓ No broken cross-references introduced
- ✓ CI passes (docs build, no format errors)

---

## Critical Files

**Audit Command**:
- `.claude/commands/local/audit-doc.md` - 7-phase audit workflow

**Documents to Audit** (10 total):
- `docs/learned/desktop-dash/erkdesk-project-structure.md`
- `docs/learned/desktop-dash/split-pane-implementation.md`
- `docs/learned/integrations/bundled-artifacts.md`
- `docs/learned/objectives/roadmap-mutation-patterns.md`
- `docs/learned/planning/learn-workflow.md`
- `docs/learned/planning/workflow.md`
- `docs/learned/reference/github-actions-api.md`
- `docs/learned/testing/session-log-fixtures.md`
- `docs/learned/workflows/commit-messages.md`
- `docs/learned/architecture/capability-system.md`

**Reference Implementation**:
- PR #6731 (Phase 1) - proven success pattern for batch audit execution

**Objective Context**:
- Issue #6697 (62 docs across 7 phases)
- `.erk/scratch/audit-scan-20260204-1200/batch-2.md` - scan data for Phase 2

---

## Verification

### End-to-End Test

1. **Pre-Check**: Verify 0/10 docs have audit metadata
   ```bash
   grep -L "^last_audited:" docs/learned/desktop-dash/erkdesk-project-structure.md docs/learned/desktop-dash/split-pane-implementation.md docs/learned/integrations/bundled-artifacts.md docs/learned/objectives/roadmap-mutation-patterns.md docs/learned/planning/learn-workflow.md docs/learned/planning/workflow.md docs/learned/reference/github-actions-api.md docs/learned/testing/session-log-fixtures.md docs/learned/workflows/commit-messages.md docs/learned/architecture/capability-system.md
   ```
   Expected: All 10 files listed

2. **Execute Audits**: Run `/local:audit-doc` on all 10 documents sequentially

3. **Post-Check**: Verify 10/10 docs have audit metadata
   ```bash
   grep "^last_audited:" docs/learned/desktop-dash/erkdesk-project-structure.md docs/learned/desktop-dash/split-pane-implementation.md docs/learned/integrations/bundled-artifacts.md docs/learned/objectives/roadmap-mutation-patterns.md docs/learned/planning/learn-workflow.md docs/learned/planning/workflow.md docs/learned/reference/github-actions-api.md docs/learned/testing/session-log-fixtures.md docs/learned/workflows/commit-messages.md docs/learned/architecture/capability-system.md | wc -l
   ```
   Expected: `10` (all documents stamped)

4. **Cross-Reference Check**: Verify step 2.4 paths still valid
   ```bash
   # All 4 paths in roadmap-mutation-patterns.md should resolve
   ls docs/learned/architecture/roadmap-mutation-semantics.md
   ls docs/learned/objectives/roadmap-status-system.md
   ls docs/learned/cli/commands/update-roadmap-step.md
   ls docs/learned/architecture/discriminated-union-error-handling.md
   ```
   Expected: All 4 files exist

5. **PR Submission**: Verify commit message includes all 10 documents and correct objective reference

### Success Criteria

- ✓ All 10 documents audited with `/local:audit-doc`
- ✓ All 10 documents have `last_audited` and `audit_result` frontmatter
- ✓ No broken paths introduced or detected
- ✓ Single PR submitted with comprehensive commit message
- ✓ Objective #6697 progresses to 2/7 phases complete

---

## Notes

**Execution Pattern**: Mirror Phase 1 approach - sequential audits, single PR, metadata verification

**Risk Mitigation**: Step 2.7 (754L) is the largest doc; monitor token usage during audit (audit command handles large docs but worth tracking)

**Objective Progress**: After this plan completes, Objective #6697 will be 2/7 phases complete (20/62 documents audited total)