# Plan: Audit Top 20 HIGH/MODERATE-Priority Docs

## Summary

An audit-scan of 375 `docs/learned/` documents (skipping 25 auto-generated, excluding 16 recently audited) scored each doc on heuristic signals: no prior audit (+3), line count >200 (+2) / >100 (+1), 3+ code blocks (+2), 5+ file path refs (+2), broken paths (+3), imports in code blocks (+1). All 13 HIGH-priority docs scored 10, and 7 MODERATE docs scored 9. This plan audits these top 20.

Full scan results exported to `.erk/scratch/audit-scan-results.md`.

## Context

- **350 of 375 docs have never been audited** — no `last_audited` frontmatter
- **0 broken paths detected** by heuristic scan (but heuristic only checks 3 per doc)
- **Common risk pattern**: large docs with many code blocks and file path references are most prone to drift
- **Audit command**: Each doc is audited using `/local:audit-doc <path>` which does deep analysis

## Execution Strategy

Run `/local:audit-doc` on each document. For each doc:
1. Read the full document
2. Check every file path reference against the actual codebase
3. Check every code block against the actual source (imports, function signatures, class names)
4. Check for phantom content (fabricated APIs, types, or commands that don't exist)
5. Check for duplicative content (verbatim source code restated in docs)
6. If issues found → apply rewrite + stamp `last_audited` with today's date and `audit_result: edited`
7. If clean → stamp `last_audited` with today's date and `audit_result: clean`

**Batch execution**: Run 10 docs in parallel per batch, 2 batches total.

## Batch 1: HIGH Priority (10 docs)

Process these 10 documents in parallel using `subagent_type=general-purpose` agents, each running `/local:audit-doc`:

### Doc 1: `docs/learned/architecture/discriminated-union-error-handling.md`
- **Score**: 10 | **Lines**: 783 | **Code blocks**: 70 | **Path refs**: 11 | **Imports**: 1
- **Risk**: Extremely high code block count (70!) — many examples that could drift from actual gateway error handling patterns
- **Audit focus**: Verify all code examples match current `src/erk/` patterns, check import paths, verify discriminated union types still exist

### Doc 2: `docs/learned/architecture/erk-architecture.md`
- **Score**: 10 | **Lines**: 1039 | **Code blocks**: 26 | **Path refs**: 20 | **Imports**: 8
- **Risk**: Largest architecture doc, 20 file path references — high chance some paths have moved
- **Audit focus**: Verify all 20 path references exist, check that architecture descriptions match current code structure, verify import examples

### Doc 3: `docs/learned/architecture/flatten-subgateway-pattern.md`
- **Score**: 10 | **Lines**: 280 | **Code blocks**: 11 | **Path refs**: 8 | **Imports**: 4
- **Risk**: Gateway refactoring is ongoing — patterns may have changed
- **Audit focus**: Verify gateway paths, check that flatten pattern examples match current gateway hierarchy

### Doc 4: `docs/learned/architecture/gateway-abc-implementation.md`
- **Score**: 10 | **Lines**: 991 | **Code blocks**: 34 | **Path refs**: 18 | **Imports**: 5
- **Risk**: Second largest doc, 34 code blocks showing ABC implementation — very drift-prone during gateway changes
- **Audit focus**: Verify all ABC class examples, check that implementation checklist steps match current patterns, verify test file paths

### Doc 5: `docs/learned/architecture/git-graphite-quirks.md`
- **Score**: 10 | **Lines**: 413 | **Code blocks**: 24 | **Path refs**: 13 | **Imports**: 2
- **Risk**: Git/Graphite integration has many edge cases documented — quirks may be fixed or changed
- **Audit focus**: Verify quirk descriptions still apply, check command examples, verify referenced source files

### Doc 6: `docs/learned/cli/output-styling.md`
- **Score**: 10 | **Lines**: 821 | **Code blocks**: 28 | **Path refs**: 10 | **Imports**: 5
- **Risk**: Large CLI styling reference with many code examples — CLI patterns evolve frequently
- **Audit focus**: Verify styling helper functions exist, check import paths, verify output formatting examples match current CLI output

### Doc 7: `docs/learned/hooks/erk.md`
- **Score**: 10 | **Lines**: 470 | **Code blocks**: 23 | **Path refs**: 26 | **Imports**: 5
- **Risk**: 26 file path references — highest path ref count in the batch. Hook system has been actively refactored
- **Audit focus**: Verify all 26 path references (critical), check hook registration examples, verify marker patterns

### Doc 8: `docs/learned/planning/gateway-consolidation-checklist.md`
- **Score**: 10 | **Lines**: 205 | **Code blocks**: 12 | **Path refs**: 26 | **Imports**: 10
- **Risk**: 26 path refs + 10 imports — the most reference-dense doc by ratio. Gateway consolidation may be complete
- **Audit focus**: Check if consolidation is done (doc may be obsolete), verify all gateway paths, check import examples

### Doc 9: `docs/learned/testing/cli-testing.md`
- **Score**: 10 | **Lines**: 483 | **Code blocks**: 19 | **Path refs**: 5 | **Imports**: 3
- **Risk**: Test patterns doc with many code examples — testing infrastructure evolves
- **Audit focus**: Verify test helper imports, check that CLI test patterns match current `tests/` structure

### Doc 10: `docs/learned/testing/testing.md`
- **Score**: 10 | **Lines**: 748 | **Code blocks**: 35 | **Path refs**: 26 | **Imports**: 16
- **Risk**: Master testing reference doc — 35 code blocks and 16 imports. Most import-heavy doc in the scan
- **Audit focus**: Verify all import paths, check that fake/gateway test patterns match current architecture, verify test file locations

## Batch 2: HIGH + MODERATE Priority (10 docs)

Process these 10 documents in parallel after Batch 1 completes:

### Doc 11: `docs/learned/reference/interactive-claude-config.md`
- **Score**: 10 | **Lines**: 235 | **Code blocks**: 9 | **Path refs**: 8 | **Imports**: 1
- **Audit focus**: Verify Claude config paths and settings still valid

### Doc 12: `docs/learned/testing/exec-script-testing.md`
- **Score**: 10 | **Lines**: 461 | **Code blocks**: 17 | **Path refs**: 9 | **Imports**: 5
- **Audit focus**: Verify exec script test patterns, check Path.home() alternatives

### Doc 13: `docs/learned/testing/rebase-conflicts.md`
- **Score**: 10 | **Lines**: 580 | **Code blocks**: 27 | **Path refs**: 39 | **Imports**: 3
- **Risk**: 39 path refs — absolute highest in entire scan. Rebase conflict resolution code may have moved
- **Audit focus**: Verify all 39 path references (critical priority), check conflict resolution examples

### Doc 14: `docs/learned/cli/command-group-structure.md`
- **Score**: 9 | **Lines**: 114 | **Code blocks**: 8 | **Path refs**: 13 | **Imports**: 7
- **Audit focus**: Verify CLI command group paths and import statements match current `src/erk/cli/` structure

### Doc 15: `docs/learned/glossary.md`
- **Score**: 9 | **Lines**: 1328 | **Code blocks**: 11 | **Path refs**: 5 | **Imports**: 0
- **Risk**: Largest doc in entire scan (1328 lines). Terminology may have drifted
- **Audit focus**: Check for stale terminology, verify definitions match current codebase concepts

### Doc 16: `docs/learned/planning/context-preservation-in-replan.md`
- **Score**: 9 | **Lines**: 316 | **Code blocks**: 8 | **Path refs**: 6 | **Imports**: 0
- **Audit focus**: Verify replan context patterns, check referenced planning files

### Doc 17: `docs/learned/planning/context-preservation-patterns.md`
- **Score**: 9 | **Lines**: 409 | **Code blocks**: 14 | **Path refs**: 13 | **Imports**: 0
- **Audit focus**: Verify context preservation code examples and file paths

### Doc 18: `docs/learned/planning/debugging-patterns.md`
- **Score**: 9 | **Lines**: 228 | **Code blocks**: 16 | **Path refs**: 10 | **Imports**: 0
- **Audit focus**: Verify debugging examples and referenced source files

### Doc 19: `docs/learned/planning/lifecycle.md`
- **Score**: 9 | **Lines**: 1101 | **Code blocks**: 23 | **Path refs**: 8 | **Imports**: 0
- **Risk**: Third largest doc (1101 lines). Plan lifecycle is core to erk — high value if accurate, high cost if stale
- **Audit focus**: Verify lifecycle state transitions, check code examples against current implementation

### Doc 20: `docs/learned/refactoring/libcst-systematic-imports.md`
- **Score**: 9 | **Lines**: 284 | **Code blocks**: 24 | **Path refs**: 12 | **Imports**: 0
- **Audit focus**: Verify LibCST patterns, check referenced file paths for import refactoring

## Verification

After both batches complete:
1. Grep `docs/learned/` for `last_audited: "2026-02-03"` — should find 20 entries
2. Check `git diff --stat` to see which files were modified
3. Any doc stamped `audit_result: edited` was rewritten — review the diffs
4. Any doc stamped `audit_result: clean` passed audit with no changes needed

## Post-Audit

- Run `/local:audit-scan` again to verify the top 20 no longer appear in HIGH/MODERATE tiers
- The remaining 330+ unaudited docs can be addressed in follow-up plans, prioritized by the scan results in `.erk/scratch/audit-scan-results.md`