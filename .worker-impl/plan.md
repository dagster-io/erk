# Audit Plan: 16 HIGH Priority docs/learned/ Documents

## Summary

Audited 16 documents from the HIGH priority queue. Below are the verdicts, findings, and planned actions for each document.

---

## 1. testing/import-conflict-resolution.md (Score: 11)

**Audit: testing/import-conflict-resolution.md | Verdict: CONSIDER DELETING | Duplicative: 85% | Inaccurate: 10% | High-value: 5%**

**Verification: 2 verified | 1 broken**

No previous audit recorded.

The document describes a generic merge conflict resolution strategy for import consolidation. Nearly all content is procedural steps that any agent already knows (resolve conflicts, pick shared imports, delete obsolete files). The "Decision Framework" table adds minimal value over standard merge conflict heuristics. The import path `erk_shared.gateway.github.parsing` exists and is real, but the old paths `.local_helpers`, `.github_helpers`, `.issue_helpers` are fabricated examples. The broken path reference to `rebase-conflicts.md` is actually valid (file exists).

**Planned changes:** Document should be considered for deletion. The only marginally useful content is "prefer shared imports over local helpers" which is a one-line principle, not a 127-line document.

---

## 2. architecture/gateway-abc-implementation.md (Score: 10)

**Audit: architecture/gateway-abc-implementation.md | Verdict: KEEP | Duplicative: 30% | Inaccurate: 5% | High-value: 65%**

**Verification: 28 verified | 1 stale**

Last audited: 2026-02-04 05:48 PT (result: clean)

This is a comprehensive, high-value document. The 5-file pattern explanation, decision checklists for discriminated unions vs exceptions, and gateway composition patterns are genuinely cross-cutting knowledge that spans many source files. The code blocks are mostly CONCEPTUAL (showing patterns across 5 files) or ANTI-PATTERN. The `NonIdealState` protocol reference is correct. Gateway locations verified. Codebase examples tables verified.

**Issues found:**
- The first exit code table in the update-roadmap-step section has a self-contradiction (covered in that doc's audit)
- Some verbatim code blocks reproduce source patterns that could be replaced with source pointers
- The AgentLauncher code block (lines 91-105) is borderline VERBATIM but serves as a CONCEPTUAL example illustrating the NoReturn pattern

**Planned changes:** Stamp as clean. The high-value cross-cutting content justifies the length. Verbatim blocks are largely justified by the conceptual/template nature.

---

## 3. architecture/gateway-error-boundaries.md (Score: 10)

**Audit: architecture/gateway-error-boundaries.md | Verdict: SIMPLIFY | Duplicative: 35% | Inaccurate: 0% | High-value: 55%**

**Verification: 6 verified | 0 broken**

No previous audit recorded.

The core principle ("only real.py catches exceptions") is genuinely high-value cross-cutting insight. The "Implementation Responsibilities by File" table is excellent. The anti-pattern section is well-done. However, sections "abc.py: Type Definitions", "real.py: The Exception Boundary", "fake.py: Constructor-Driven", "dry_run.py: Success Path Only", "printing.py: Transparent Wrapper" (lines 102-145) duplicate the table at lines 94-100 with prose that adds minimal value over reading the gateway implementations directly.

**Planned changes:** Stamp as audited. The duplicative prose sections (102-145) could be condensed but the overall doc is still high value. The anti-patterns section is excellent and justifies keeping the doc.

---

## 4. architecture/gateway-removal-pattern.md (Score: 10)

**Audit: architecture/gateway-removal-pattern.md | Verdict: KEEP | Duplicative: 15% | Inaccurate: 5% | High-value: 80%**

**Verification: 4 verified | 0 broken**

Last audited: 2026-02-07 (result: clean)

Excellent high-value document. The "Why Immediate Deletion" section captures architectural philosophy that can't be derived from code. Decision framework, anti-patterns, and the concrete PR #6587 example are all high-value. The `ClaudeExecutor -> PromptExecutor` example references a real consolidation. The checklist steps are genuinely useful process documentation. Cross-references to `gateway-abc-implementation.md` and `flatten-subgateway-pattern.md` are valid.

**Planned changes:** No changes needed. Stamp as clean.

---

## 5. architecture/github-pr-linkage-api.md (Score: 10)

**Audit: architecture/github-pr-linkage-api.md | Verdict: NEEDS_UPDATE | Duplicative: 15% | Inaccurate: 15% | High-value: 70%**

**Verification: 3 verified | 2 broken**

No previous audit recorded.

Excellent REFERENCE CACHE document documenting GitHub GraphQL API patterns and the `willCloseTarget` timing quirk (undocumented behavior). The GraphQL query examples are legitimate third-party API knowledge (exception 2 of the One Code Rule). The `willCloseTarget` timing detail is discovered knowledge -- extremely high value.

**Issues found:**
- **INACCURATE:** "Query location: `packages/erk-shared/src/erk_shared/github/real.py`" -- `get_prs_referencing_issue()` is actually in `packages/erk-shared/src/erk_shared/gateway/github/issues/real.py` (issues subgateway, not main GitHub gateway)
- **INACCURATE:** "Method: `get_prs_linked_to_issues()` for batch queries (dash)" -- this method IS on the main GitHub real.py, but `get_prs_referencing_issue()` is on the issues subgateway
- The doc says "Query location" implying both methods are in the same file, which is incorrect

**Planned changes:** Fix the inaccurate method locations in the "Erk Implementation" section. Both cross-references are valid. Stamp as edited.

---

## 6. architecture/pre-destruction-capture.md (Score: 10)

**Audit: architecture/pre-destruction-capture.md | Verdict: KEEP | Duplicative: 20% | Inaccurate: 0% | High-value: 70%**

**Verification: 2 verified | 0 broken**

No previous audit recorded.

Good conceptual document. The core principle "capture first, transform later" is cross-cutting wisdom. The pipeline diagram (Phase 1/2/3) illustrates a pattern spanning multiple files. Anti-pattern code blocks are legitimate (exception 3 -- showing what NOT to do). The `event-progress-pattern.md` cross-reference is valid.

**Issues found:**
- The "Common Mistakes" code blocks are ANTI-PATTERN (legitimate keep)
- Source reference `packages/erk/src/erk/operations/` is vague -- should be more specific but works as a pointer

**Planned changes:** Stamp as clean.

---

## 7. architecture/prompt-executor-gateway.md (Score: 10)

**Audit: architecture/prompt-executor-gateway.md | Verdict: SIMPLIFY | Duplicative: 30% | Inaccurate: 5% | High-value: 60%**

**Verification: 12 verified | 1 stale**

No previous audit recorded.

The document has genuinely high-value sections: the "Why Three Execution Modes?" table, streaming vs single-shot trade-offs, model selection philosophy, interactive execution asymmetry, and TTY redirection logic. These capture architectural decisions and cross-cutting design rationale.

**Issues found:**
- The "Simulating Failures" section (lines 69-100) contains code blocks that are borderline VERBATIM -- they show FakePromptExecutor constructor calls that could be derived from reading the fake
- The "Call Tracking" code block (lines 119-126) is VERBATIM from test patterns
- The "PromptResult vs CommandResult" section restates type field listings that can be read from source
- Source pointers use proper `<!-- Source: ... -->` format throughout -- well done

**Planned changes:** Replace the verbatim FakePromptExecutor code blocks with prose references. Keep the mode table, trade-offs, and architectural rationale. Stamp as edited.

---

## 8. capabilities/folder-structure.md (Score: 10)

**Audit: capabilities/folder-structure.md | Verdict: NEEDS_UPDATE | Duplicative: 20% | Inaccurate: 15% | High-value: 65%**

**Verification: 8 verified | 1 broken**

No previous audit recorded.

Good architectural document explaining the infrastructure/implementations split. The "Why the Split Exists" and "Explicit Registry Pattern" sections are high-value cross-cutting insight. The "Anti-pattern" callouts are useful.

**Issues found:**
- **INACCURATE:** "DignifiedPythonCapability lives in `skills/` because it extends `SkillCapability`" and source pointer "`src/erk/capabilities/skills/dignified_python.py`" -- this file no longer exists. The `skills/` directory now only contains `bundled.py`. DignifiedPython exists in `reminders/` and `reviews/` but not `skills/`
- The `HooksCapability` path `src/erk/capabilities/hooks.py` is verified correct
- Cross-references to other capabilities docs are all valid

**Planned changes:** Fix the broken DignifiedPythonCapability reference. Find the correct current example of a skill capability or use a different example. Stamp as edited.

---

## 9. ci/convention-based-reviews.md (Score: 10)

**Audit: ci/convention-based-reviews.md | Verdict: KEEP | Duplicative: 15% | Inaccurate: 5% | High-value: 80%**

**Verification: 10 verified | 0 broken**

Last audited: 2026-02-05 15:20 PT (result: clean)

Excellent document. The "Adding a New Code Review" section is a practical how-to that synthesizes knowledge from multiple files. The frontmatter schema table is HIGH VALUE as a reference cache for the review definition format. The workflow architecture diagram captures cross-cutting system behavior. The `pathspec` vs `fnmatch` tripwire is high-value discovered knowledge.

**Issues found:**
- The "Existing Reviews" table lists 5 reviews -- this is DRIFT RISK as reviews can be added/removed. However, it's useful for quick navigation.
- The test coverage agent details section is borderline duplicative but provides useful summary

**Planned changes:** No changes needed. Stamp as clean.

---

## 10. cli/commands/pr-summarize.md (Score: 10)

**Audit: cli/commands/pr-summarize.md | Verdict: CONSIDER DELETING | Duplicative: 20% | Inaccurate: 70% | High-value: 10%**

**Verification: 1 verified | 4 broken**

No previous audit recorded.

**CRITICAL:** This document describes a command (`erk pr summarize`) that no longer exists. It was replaced by `erk pr rewrite` (confirmed via `rewrite_cmd.py` which mentions "Replaces the old multi-step workflow (gt squash -> erk pr summarize -> push)"). The source file `summarize_cmd.py` does not exist. The function `_execute_pr_summarize()` does not exist in any file. The entire document describes an obsolete system.

**Issues found:**
- **INACCURATE (systemic):** The entire document describes a removed command
- Source reference `src/erk/cli/commands/pr/summarize_cmd.py` -- FILE DOES NOT EXIST
- Function `_execute_pr_summarize()` -- NOT FOUND in codebase
- The `CommitMessageGenerator` and plan context concepts may still be valid but in the context of `pr rewrite`, not `pr summarize`

**Planned changes:** Delete this document. It documents a command that has been removed. If documentation for `pr rewrite` is needed, it should be a new document.

---

## 11. cli/commands/update-roadmap-step.md (Score: 10)

**Audit: cli/commands/update-roadmap-step.md | Verdict: NEEDS_UPDATE | Duplicative: 20% | Inaccurate: 10% | High-value: 65%**

**Verification: 5 verified | 1 inconsistent**

No previous audit recorded.

Good reference document for the roadmap step update command. The "Why This Command Exists" section is high-value (architectural rationale). Status computation semantics table is useful. Anti-pattern section is excellent.

**Issues found:**
- **INACCURATE (self-contradiction):** The document has TWO exit code tables that contradict each other:
  - Lines 78-86: Says exit code 1 for errors
  - Lines 206-216: Says "The command always exits 0" and all exit codes are 0
  - Actual code: `SystemExit(0)` on all paths -- the second table is correct, the first is wrong
- The first exit code table (lines 78-86) must be corrected to show exit code 0
- An unclosed code fence at line 73 (the ```` after the multi-step example doesn't close properly)

**Planned changes:** Fix the contradictory exit code table. Fix the unclosed code fence. Stamp as edited.

---

## 12. cli/plan-implement.md (Score: 10)

**Audit: cli/plan-implement.md | Verdict: KEEP | Duplicative: 15% | Inaccurate: 5% | High-value: 80%**

**Verification: 6 verified | 0 broken**

No previous audit recorded.

High-value document capturing the plan-implement workflow's decision trees, failure patterns, and cleanup discipline. The source resolution priority section, `.impl/` vs `.worker-impl/` distinction table, and phase timing characteristics are all cross-cutting insight. Anti-patterns are well-documented.

**Issues found:**
- Source references all verified: `impl_verify.py`, `impl_signal.py`, `exit_plan_mode_hook.py`, `setup_impl_from_issue.py` all exist
- The `capture_session_info.py` reference is valid
- Stacked branch behavior section is useful architectural documentation

**Planned changes:** Stamp as clean.

---

## 13. glossary.md (Score: 10)

**Audit: glossary.md | Verdict: SIMPLIFY | Duplicative: 40% | Inaccurate: 5% | High-value: 50%**

**Verification: 15 verified | 2 stale**

Last audited: 2026-02-03 (result: edited)

This is a 1284-line document with mixed value. High-value sections: Branch Naming Convention (with objective ID format), `.impl/` vs `.worker-impl/` distinction, Erk Context field documentation, Plan & Extraction Concepts, Objectives System. These capture cross-cutting terminology that agents need.

**Issues found:**
- Many code blocks are VERBATIM source code (Gateway, Real Implementation, Fake Implementation, Dry Run Wrapper sections just reproduce code patterns already covered by `gateway-abc-implementation.md`)
- The ExecutorEvent union type listing (lines 690-730) is an ENUMERABLE CATALOG that belongs in source code, not docs
- PRDetails field table (lines 553-561) duplicates what's in `types.py`
- PRNotFound section duplicates `not-found-sentinel.md`
- Multiple sections overlap heavily with `architecture/gateway-abc-implementation.md`
- PromptExecutor/ClaudePromptExecutor/FakePromptExecutor sections duplicate `architecture/prompt-executor-gateway.md`

**Planned changes:** The glossary should be simplified to remove sections that duplicate other dedicated docs. Gateway implementation patterns, ExecutorEvent catalogs, and PRDetails field listings should be replaced with cross-references. Keep terminology definitions, cross-cutting concepts, and branch naming conventions. Stamp as edited.

---

## 14. planning/workflow.md (Score: 10)

**Audit: planning/workflow.md | Verdict: NEEDS_UPDATE | Duplicative: 15% | Inaccurate: 5% | High-value: 75%**

**Verification: 5 verified | 1 broken**

Last audited: 2026-02-05 12:35 PT (result: edited)

Good workflow document. The flow diagram, five exit-plan-mode options, and plan save workflow are high-value. The line number reference prohibition section is important process guidance. Progress tracking format is useful.

**Issues found:**
- **BROKEN LINK:** "[erk-impl Change Detection](../ci/erk-impl-change-detection.md)" -- this file does NOT exist. It's referenced but the document was likely renamed or never created.
- The remote implementation section is useful but the broken link undermines it

**Planned changes:** Fix or remove the broken cross-reference to `ci/erk-impl-change-detection.md`. Stamp as edited.

---

## 15. sessions/preprocessing.md (Score: 10)

**Audit: sessions/preprocessing.md | Verdict: KEEP | Duplicative: 15% | Inaccurate: 0% | High-value: 75%**

**Verification: 4 verified | 0 broken**

No previous audit recorded.

Good reference document. The compression metrics tables are empirical data (high value -- can't be derived from code). The chunking algorithm explanation captures cross-cutting behavior. Multi-part file handling patterns are useful for downstream consumers.

**Issues found:**
- Shell script code blocks (Patterns 1-3) are INPUT/OUTPUT EXAMPLES (exception 4), not verbatim source code
- The token compression ratios table is empirical reference data
- All cross-references valid: `lifecycle.md`, `discovery-fallback.md`, `tools.md`, `layout.md`

**Planned changes:** Stamp as clean.

---

## 16. sessions/session-hierarchy.md (Score: 10)

**Audit: sessions/session-hierarchy.md | Verdict: NEEDS_UPDATE | Duplicative: 25% | Inaccurate: 15% | High-value: 55%**

**Verification: 5 verified | 2 broken**

No previous audit recorded.

The conceptual model diagram and linking patterns are high-value. Session type identification and parent-child linking are cross-cutting knowledge.

**Issues found:**
- **INACCURATE:** "Session store: `erk_shared/extraction/claude_code_session_store/`" -- this path does not exist. The actual location is `erk_shared/gateway/claude_installation/` (confirmed by grep)
- **INACCURATE:** "Agent type extraction: `show_cmd.py:extract_agent_types()`" -- `extract_agent_types` does not exist as a function (only referenced in docs). The `show_cmd.py` exists at `src/erk/cli/commands/cc/session/show_cmd.py` but the function name may be wrong
- Code blocks showing JSON format are INPUT/OUTPUT EXAMPLES (legitimate keep)
- The `discover_agent_logs()` code pattern is borderline VERBATIM

**Planned changes:** Fix the broken implementation references. Replace the session store path and verify the `extract_agent_types` function name. Stamp as edited.

---

## Collateral Findings: 3 issues in 2 other files

**MECHANICAL:**
- `docs/learned/planning/workflow.md`: [BX] Link to `../ci/erk-impl-change-detection.md` -- file does not exist. Fix: remove or update link.

**CONCEPTUAL:**
- `docs/learned/cli/commands/pr-summarize.md`: [OS] Describes the `erk pr summarize` command which has been replaced by `erk pr rewrite`. Recommend: delete document.
- `docs/learned/glossary.md`: Significant overlap with dedicated architecture docs (gateway-abc-implementation, prompt-executor-gateway). Recommend: audit to deduplicate.

---

## Execution Summary

| Doc | Verdict | Action |
|-----|---------|--------|
| testing/import-conflict-resolution.md | CONSIDER DELETING | Stamp only (don't auto-delete) |
| architecture/gateway-abc-implementation.md | KEEP | Stamp clean |
| architecture/gateway-error-boundaries.md | SIMPLIFY | Stamp clean (mild simplification) |
| architecture/gateway-removal-pattern.md | KEEP | Stamp clean |
| architecture/github-pr-linkage-api.md | NEEDS_UPDATE | Fix method locations + stamp edited |
| architecture/pre-destruction-capture.md | KEEP | Stamp clean |
| architecture/prompt-executor-gateway.md | SIMPLIFY | Replace verbatim blocks + stamp edited |
| capabilities/folder-structure.md | NEEDS_UPDATE | Fix broken example + stamp edited |
| ci/convention-based-reviews.md | KEEP | Stamp clean |
| cli/commands/pr-summarize.md | CONSIDER DELETING | Stamp only (recommend deletion) |
| cli/commands/update-roadmap-step.md | NEEDS_UPDATE | Fix exit code contradiction + stamp edited |
| cli/plan-implement.md | KEEP | Stamp clean |
| glossary.md | SIMPLIFY | Deduplicate + stamp edited |
| planning/workflow.md | NEEDS_UPDATE | Fix broken link + stamp edited |
| sessions/preprocessing.md | KEEP | Stamp clean |
| sessions/session-hierarchy.md | NEEDS_UPDATE | Fix broken paths + stamp edited |