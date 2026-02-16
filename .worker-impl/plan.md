# Audit 26 Score-10 docs/learned/ Documents

## Context

This is step 1.3 of objective #7132 ("Audit All docs/learned/ Documents"). The objective works through all documents by audit-scan priority score, starting with the highest. Step 1.1 (PR #7134) audited 7 score 11-12 documents. Step 1.2 (PR #7147) audited 6 score-11 documents. This step audits the next tier: 26 documents at score 10.

The audit-scan scoring rubric (defined in `.claude/commands/local/audit-scan.md`) assigns points based on: missing audit metadata (+3), large line count (+1/+2), code blocks (+2), file path references (+2), broken paths (+3), imports (+1), step sequences (+1), behavioral claim density (+2), line number references (+1), with deductions for redirects (-2) and recently-edited status (-1).

**Batch size note:** This is 26 documents — significantly larger than previous batches (7 and 6). The implementer should work through them methodically, grouping by category for efficiency since documents in the same category often reference similar source files.

## Documents to Audit

### Recently Audited (Re-stamp candidates — 3 docs)

These were audited by steps 1.1 or 1.2 (within the last 7 days). They still appear at score 10 due to other scoring factors. The implementer should verify they are still accurate and re-stamp with current date.

| # | Document | Lines | last_audited | audit_result |
|---|----------|-------|-------------|--------------|
| 1 | `ci/claude-code-docker.md` | 158 | 2026-02-16 | edited |
| 2 | `cli/exec-command-patterns.md` | 158 | 2026-02-16 | edited |
| 3 | `hooks/hooks.md` | 554 | 2026-02-16 | edited |

### Previously Audited (Re-audit — 7 docs)

These have prior audit dates but are older (>7 days). Full re-audit needed.

| # | Document | Lines | last_audited | audit_result |
|---|----------|-------|-------------|--------------|
| 4 | `architecture/discriminated-union-error-handling.md` | 296 | 2026-02-07 | clean |
| 5 | `architecture/fail-open-patterns.md` | 255 | 2026-02-07 | clean |
| 6 | `cli/batch-exec-commands.md` | 307 | 2026-02-08 | clean |
| 7 | `cli/dependency-injection-patterns.md` | 187 | 2026-02-08 | clean |
| 8 | `documentation/source-pointers.md` | 94 | 2026-02-08 | edited |
| 9 | `hooks/pretooluse-implementation.md` | 93 | 2026-02-08 | edited |
| 10 | `sessions/tools.md` | 275 | 2026-02-05 | edited |

### Older Audits (Re-audit — 2 docs)

These have audit dates from 2026-02-03 (13+ days old). Full re-audit needed.

| # | Document | Lines | last_audited | audit_result |
|---|----------|-------|-------------|--------------|
| 11 | `testing/cli-testing.md` | 486 | 2026-02-03 | edited |
| 12 | `testing/exec-script-testing.md` | 438 | 2026-02-03 | edited |

### Never Audited (First audit — 14 docs)

These have no `last_audited` field. Full first-time audit needed.

| # | Document | Lines | Notes |
|---|----------|-------|-------|
| 13 | `architecture/gateway-signature-migration.md` | 130 | Migration guide for gateway signatures |
| 14 | `architecture/github-api-rate-limits.md` | 176 | GitHub API rate limiting patterns |
| 15 | `architecture/lbyl-gateway-pattern.md` | 102 | LBYL pattern for gateways |
| 16 | `architecture/tripwires.md` | 253 | Auto-generated (check if auto-gen filter applies) |
| 17 | `architecture/type-safety-patterns.md` | 111 | Type safety patterns |
| 18 | `ci/github-commit-indexing-timing.md` | 109 | GitHub commit indexing timing |
| 19 | `ci/prompt-patterns.md` | 127 | CI prompt patterns |
| 20 | `cli/slash-command-exec-migration.md` | 87 | Migration guide |
| 21 | `cli/tripwires.md` | 135 | Auto-generated (check if auto-gen filter applies) |
| 22 | `documentation/frontmatter-tripwire-format.md` | 130 | Frontmatter/tripwire format spec |
| 23 | `erk/remote-workflow-template.md` | 103 | Remote workflow template patterns |
| 24 | `hooks/reminder-consolidation.md` | 114 | Reminder consolidation patterns |
| 25 | `planning/pr-discovery.md` | 68 | PR discovery patterns |
| 26 | `testing/erkdesk-component-testing.md` | 205 | Component testing patterns |

## Changes

### Prerequisites

Before starting any audits:

1. Load the `learned-docs` skill (read `.claude/skills/learned-docs/learned-docs-core.md`)
2. Read `docs/learned/documentation/audit-methodology.md` for classification guidance
3. Read `docs/learned/documentation/source-pointers.md` for source pointer format

### Per-Document Audit Process

For each of the 26 documents, apply the `/local:audit-doc` methodology:

1. **Read the document** fully and extract frontmatter
2. **Extract code references** — identify all `src/`, `tests/`, `.claude/` paths and symbols
3. **Read referenced source code** — verify functions/classes exist, capture collateral findings
4. **Verify system descriptions** — confirm workflows, behaviors, imports, symbols, types match reality
5. **Adversarial analysis** — classify each section as DUPLICATIVE, INACCURATE, DRIFT RISK, HIGH VALUE, CONTEXTUAL, REFERENCE CACHE, or EXAMPLES
6. **Code block triage** — classify each code block as ANTI-PATTERN, CONCEPTUAL, VERBATIM, REFERENCE TABLE, or TEMPLATE
7. **Generate verdict** — produce brief summary with planned changes
8. **Apply changes**:
   - **KEEP / STAMP ONLY** → Update `last_audited` date and set `audit_result: clean`
   - **NEEDS_UPDATE** → Fix issues, update `last_audited` date, set `audit_result: edited`
   - **SIMPLIFY** → Rewrite sections, update `last_audited` date, set `audit_result: edited`
   - **CONSIDER DELETING** → Stamp only (do not delete in audit PR), set `audit_result: clean`
9. **Apply collateral fixes** — fix mechanical issues (stale comments, broken links) in other files when discovered

### Recommended Processing Order

Process documents grouped by category for efficiency (shared source file reads):

**Batch A — Architecture (7 docs):**
Documents #4, #5, #13, #14, #15, #16, #17
- Many reference `src/erk/gateway/` and `src/erk/` core modules
- `architecture/tripwires.md` (#16) is AUTO-GENERATED — check for `<!-- AUTO-GENERATED FILE -->` header. If present, STAMP ONLY (do not modify content)

**Batch B — CLI (5 docs):**
Documents #6, #7, #2, #20, #21
- Reference `src/erk/cli/` modules extensively
- `cli/tripwires.md` (#21) is AUTO-GENERATED — STAMP ONLY if auto-generated

**Batch C — CI (3 docs):**
Documents #1, #18, #19
- Reference `.github/workflows/` and CI infrastructure

**Batch D — Testing (3 docs):**
Documents #11, #12, #26
- Reference `tests/` directory patterns
- `testing/cli-testing.md` (#11) and `testing/exec-script-testing.md` (#12) are large (486 and 438 lines) — expect significant audit work

**Batch E — Hooks (3 docs):**
Documents #3, #9, #24
- Reference `.claude/hooks/` and `src/erk/hooks/`

**Batch F — Documentation (2 docs):**
Documents #8, #22
- Self-referential — describe docs/learned/ conventions

**Batch G — Remaining (3 docs):**
Documents #10, #23, #25
- Mixed categories: sessions, erk workflows, planning

### Document-Specific Pre-Audit Notes

#### Recently Audited (Quick Re-stamp)

**#1 `ci/claude-code-docker.md`** — Audited 2026-02-16 as `edited`. Was marked as historical during step 1.2 audit. Quick verification that historical framing is still appropriate, then re-stamp.

**#2 `cli/exec-command-patterns.md`** — Audited 2026-02-16 as `edited`. Simplified code examples and added source references in step 1.2. Verify source references still valid, then re-stamp.

**#3 `hooks/hooks.md`** — Audited 2026-02-16 as `edited`. Expanded hook types and lifecycle events in step 1.1. Large file (554 lines). Verify recent expansions are still accurate, then re-stamp.

#### Architecture Docs

**#4 `architecture/discriminated-union-error-handling.md`** (296 lines) — Previously clean. Contains critical error handling patterns. Verify `GatewayResult`, `OpResult` types still match implementation. This is a universal tripwire doc — extra care needed.

**#5 `architecture/fail-open-patterns.md`** (255 lines) — Previously clean. Verify fail-open gateway patterns against current `src/erk/gateway/` code.

**#13 `architecture/gateway-signature-migration.md`** (130 lines) — Never audited. Migration guide — check if migration is complete (may be historical). Verify referenced function signatures exist.

**#14 `architecture/github-api-rate-limits.md`** (176 lines) — Never audited. Verify rate limit constants and retry patterns against `src/erk/gateway/github_gateway.py`.

**#15 `architecture/lbyl-gateway-pattern.md`** (102 lines) — Never audited. Verify LBYL patterns match current gateway implementations.

**#16 `architecture/tripwires.md`** (253 lines) — Never audited. **AUTO-GENERATED** — check for `<!-- AUTO-GENERATED FILE -->`. If present, STAMP ONLY. Verify generation source is correct.

**#17 `architecture/type-safety-patterns.md`** (111 lines) — Never audited. Verify type patterns match current codebase.

#### CI Docs

**#18 `ci/github-commit-indexing-timing.md`** (109 lines) — Never audited. Verify GitHub Actions timing patterns are still relevant.

**#19 `ci/prompt-patterns.md`** (127 lines) — Never audited. Verify CI prompt patterns match current `.github/workflows/` content.

#### CLI Docs

**#6 `cli/batch-exec-commands.md`** (307 lines) — Previously clean. Large file with batch command contract documentation. Verify 5-step contract against actual exec scripts.

**#7 `cli/dependency-injection-patterns.md`** (187 lines) — Previously clean. Verify DI patterns against current CLI command structure.

**#20 `cli/slash-command-exec-migration.md`** (87 lines) — Never audited. Migration guide — check if migration is complete.

**#21 `cli/tripwires.md`** (135 lines) — Never audited. **AUTO-GENERATED** — STAMP ONLY if auto-generated.

#### Documentation Docs

**#8 `documentation/source-pointers.md`** (94 lines) — Previously edited. Verify source pointer format still matches current conventions.

**#22 `documentation/frontmatter-tripwire-format.md`** (130 lines) — Never audited. Verify frontmatter schema matches `AgentDocFrontmatter` in `src/erk/agent_docs/models.py`.

#### Erk Docs

**#23 `erk/remote-workflow-template.md`** (103 lines) — Never audited. Verify remote workflow patterns against `.github/workflows/`.

#### Hooks Docs

**#9 `hooks/pretooluse-implementation.md`** (93 lines) — Previously edited. Verify PreToolUse hook patterns against `.claude/hooks/`.

**#24 `hooks/reminder-consolidation.md`** (114 lines) — Never audited. Verify reminder consolidation patterns against hook implementations.

#### Planning Docs

**#25 `planning/pr-discovery.md`** (68 lines) — Never audited. Small file. Verify PR discovery patterns against `src/erk/` code.

#### Sessions Docs

**#10 `sessions/tools.md`** (275 lines) — Previously edited. Verify session tool patterns against current implementation.

#### Testing Docs

**#11 `testing/cli-testing.md`** (486 lines) — Previously edited. Large file. Verify CLI testing patterns against current `tests/` structure. Check if Click testing patterns are still current.

**#12 `testing/exec-script-testing.md`** (438 lines) — Previously edited. Large file. Universal tripwire doc. Verify Path.home() alternatives and monkeypatch patterns are still accurate.

**#26 `testing/erkdesk-component-testing.md`** (205 lines) — Never audited. Verify component testing patterns against `tests/` directory.

## Files NOT Changing

- No source code files (`src/`, `tests/`) should be modified unless collateral fixes are discovered during auditing (e.g., stale comments or broken links in source files that are referenced by docs)
- Auto-generated files (`index.md`, `guide.md`) should not have content modified — only frontmatter stamped
- `CHANGELOG.md` — never modify

## Verification

After all 26 documents are audited:

1. **Frontmatter check**: Every audited document should have `last_audited` set to today's date and `audit_result` set to either `clean` or `edited`
2. **Run CI checks**: `make lint` and `make test` to ensure no regressions
3. **PR summary**: Include per-document verdicts in the PR description, following the pattern from PR #7134 and PR #7147:
   - List each document with its verdict (STAMP ONLY, KEEP, NEEDS_UPDATE, SIMPLIFY)
   - Note any collateral fixes made to source files
   - Summarize key changes