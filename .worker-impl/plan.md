# Plan: Audit Phase 1 Docs (Objective #6697, Steps 1.1-1.10)

Part of Objective #6697, Steps 1.1-1.10

## Goal

Run `/local:audit-doc` on all 10 critical score 10-12 docs from Phase 1 of the audit objective. Each doc gets adversarial analysis, recommended rewrites applied, and `last_audited` frontmatter stamped. Broken paths in steps 1.1 and 1.3 are fixed.

## Docs to Audit

1. `docs/learned/planning/agent-delegation.md` (score 12: 822L, 27cb, 5refs, 2broken)
2. `docs/learned/architecture/github-parsing.md` (score 10: 217L, 8cb, 6refs, 2imp)
3. `docs/learned/architecture/phase-zero-detection-pattern.md` (score 10: 277L, 5cb, 1broken)
4. `docs/learned/architecture/plan-file-sync-pattern.md` (score 10: 204L, 4cb, 7refs, 1imp)
5. `docs/learned/architecture/protocol-vs-abc.md` (score 10: 483L, 15cb, 12refs, 3imp)
6. `docs/learned/architecture/state-derivation-pattern.md` (score 10: 313L, 9cb, 8refs, 2imp)
7. `docs/learned/ci/ci-iteration.md` (score 10: 360L, 8cb, 9refs, 1imp)
8. `docs/learned/ci/convention-based-reviews.md` (score 10: 245L, 3cb, 6refs, 1imp)
9. `docs/learned/cli/pr-operations.md` (score 10: 349L, 5cb, 7refs, 1imp)
10. `docs/learned/desktop-dash/backend-communication.md` (score 10: 308L, 11cb, 6refs, 2imp)

## Implementation

### Phase 1: Run audits

Run `/local:audit-doc <path>` sequentially on each of the 10 docs. For each doc:
1. The command performs adversarial analysis (reads doc, reads referenced source code, classifies sections)
2. It generates a report with verdict and recommended rewrites
3. Select "Apply rewrites and mark audited" when offered actions
4. The command updates frontmatter with `last_audited` and `audit_result`

Order: Start with 1.1 (highest score, 2 broken paths) to handle the most critical doc first.

### Phase 2: Commit and submit PR

After all 10 docs are audited:
1. Create a feature branch
2. Commit all changes
3. Submit PR with Graphite referencing objective #6697

## Verification

- All 10 docs have `last_audited` frontmatter field set
- Broken paths in docs 1.1 and 1.3 are fixed
- `erk docs sync` runs clean (if tripwires were modified)