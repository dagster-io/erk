# Plan: Audit Phase 2 Docs (Objective #6697, Steps 2.1-2.10)

Part of Objective #6697, Step 2.1 (batch covers 2.1-2.10)

## Goal

Run `/local:audit-doc` on all 10 Phase 2 documents, apply recommended actions, and submit as a single PR.

## Documents

| Step | Path | Score | Notes |
|------|------|-------|-------|
| 2.1 | `desktop-dash/erkdesk-project-structure.md` | 10 | Preliminary: likely clean |
| 2.2 | `desktop-dash/split-pane-implementation.md` | 10 | |
| 2.3 | `integrations/bundled-artifacts.md` | 10 | |
| 2.4 | `objectives/roadmap-mutation-patterns.md` | 10 | 1 broken path |
| 2.5 | `planning/learn-workflow.md` | 10 | 406L |
| 2.6 | `planning/workflow.md` | 10 | |
| 2.7 | `reference/github-actions-api.md` | 10 | 755L, largest |
| 2.8 | `testing/session-log-fixtures.md` | 10 | 12cb, 2imp |
| 2.9 | `workflows/commit-messages.md` | 10 | |
| 2.10 | `architecture/capability-system.md` | 9 | |

## Steps

1. **Run `/local:audit-doc` on each doc sequentially** (all 10, one at a time)
   - Per verdict: KEEP -> mark clean, REVISE -> apply rewrite + mark edited, REMOVE -> delete/redirect
   - Fix broken path in step 2.4

2. **Verify all 10 docs have audit frontmatter**
   ```yaml
   last_audited: "2026-02-04 HH:MM PT"
   audit_result: clean | edited
   ```

3. **Commit and submit PR** referencing Objective #6697

## Verification

- All 10 docs have `last_audited` frontmatter after audit
- Step 2.4 broken path is resolved
- No new broken cross-references introduced by any rewrites