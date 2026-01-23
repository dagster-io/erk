# Plan: Consolidated Documentation Plan (erk-learn PRs)

> **Consolidates:** #5696, #5695, #5683, #5680

## Source Plans

| # | Title | Status |
|------|-------|--------|
| #5696 | Documentation Plan: Consolidated Documentation Plan [erk-learn] | To be closed |
| #5695 | Documentation Plan: Consolidated Documentation for erk-learn PRs #5688 and #5679 [erk-learn] | To be closed |
| #5683 | Documentation Plan: Multi-Plan Consolidated Replan [erk-learn] | To be closed |
| #5680 | Documentation Plan: Add get-pr-commits and close-issue-with-comment exec commands [erk-learn] | To be closed |

## Investigation Findings

### What Already Exists (Skip These Items)

| Topic | Existing Coverage | Location |
|-------|------------------|----------|
| Learn Workflow 3-Tier Architecture | Comprehensive (Parallel/Sequential tiers, haiku/opus models) | `docs/learned/planning/learn-workflow.md` |
| Graceful Degradation | Error patterns, decision tables, GraphiteDisabled sentinel | `docs/learned/architecture/subprocess-wrappers.md`, `gateway-hierarchy.md` |
| Gateway ABC 5-File Pattern | Comprehensive checklist for abc/real/fake/dry_run/printing | `docs/learned/architecture/gateway-abc-implementation.md` |
| BranchManager Abstraction | Factory pattern, dual-mode operation | `docs/learned/architecture/erk-architecture.md` |
| Session Source Types | `last_session_source`, `gist_url` fields documented | `docs/learned/glossary.md`, `docs/learned/architecture/session-discovery.md` |
| Session Preprocessing | XML format, context optimization | `docs/learned/sessions/preprocessing.md`, `raw-session-processing.md` |
| FakeConsole Pattern | Referenced in `ctx.console.confirm()` pattern | `docs/learned/cli/output-styling.md` |

### Corrections to Original Plans

1. **#5696**: Learn workflow pipeline is already well-documented in `learn-workflow.md` - no expansion needed
2. **#5695**: FakeConsole is already documented via `ctx.console.confirm()` pattern in `output-styling.md`
3. **#5683**: Session preprocessing XML format is already documented in `sessions/preprocessing.md` and `raw-session-processing.md`
4. **#5680**: `get-pr-commits` and `close-issue-with-comment` exec commands exist in source but aren't documented in `erk-exec-commands.md`

### Overlap Analysis

| Items | Plans | Resolution |
|-------|-------|------------|
| Session source type discrimination | #5683, #5680 | Merge - single tripwire |
| Gist URL null check | #5683, #5680 | Merge - single tripwire |
| Exec command documentation | #5695, #5680 | Merge - update erk-exec-commands.md once |
| GitHub API retry patterns | #5696 | Keep - unique gap |
| CI-aware commands | #5696 | Keep - unique gap |
| Branch reuse detection | #5695 | Keep - unique gap |
| No-changes handling | #5695 | Keep - unique gap |
| Multi-plan consolidation format | #5683 | Keep - unique gap |

## Remaining Gaps (Items to Implement)

### HIGH Priority

#### 1. CI-Aware Commands Documentation
**Location:** `docs/learned/cli/ci-aware-commands.md`
**Action:** CREATE
**Source:** #5696

Document:
- CI environment detection via `in_github_actions()` checking `GITHUB_ACTIONS` env var
- When to skip interactive prompts (confirmation, editor launches, stdin reads)
- Testing CI behavior with monkeypatch environment isolation

**Tripwire:** "Before adding user-interactive steps without CI detection" → Read this doc

#### 2. GitHub API Retry Distinction
**Location:** `docs/learned/architecture/github-api-rate-limits.md`
**Action:** UPDATE
**Source:** #5696

Add section distinguishing:
- Rate limits (429 errors): NOT retried - causes waste and abuse detection
- Transient errors (timeouts, connection failures): retried with exponential backoff

**Tripwire:** Clarify in existing tripwire that rate limits are NOT retried

#### 3. Sub-Gateway Extraction Pattern
**Location:** `docs/learned/architecture/gateway-abc-implementation.md`
**Action:** UPDATE
**Source:** #5696

Document:
- Sub-gateway extraction motivation (enforce abstraction boundaries via BranchManager)
- Directory structure: `branch_ops/` subdirectory with full 5-file pattern
- `create_linked_branch_ops()` factory pattern
- When to extract vs keep on main gateway

#### 4. Branch Divergence Detection
**Location:** `docs/learned/architecture/git-graphite-quirks.md`
**Action:** UPDATE
**Source:** #5696

Add:
- Parent branch divergence detection (comparing local vs remote commit heads)
- Impact on plan stacking
- Error messages and recovery strategies

### MEDIUM Priority

#### 5. No-Changes Handling Workflow
**Location:** `docs/learned/planning/no-changes-handling.md`
**Action:** CREATE
**Source:** #5695

Document:
- Why no-changes scenarios occur (documentation-only work, already implemented)
- Detection via `erk exec handle-no-changes`
- GitHub Actions step gating pattern (`has_changes` output variable)
- Recovery strategies

#### 6. Branch Reuse in Plan Submit
**Location:** `docs/learned/planning/submit-branch-reuse.md`
**Action:** CREATE
**Source:** #5695

Document:
- Detection mechanism for existing local branches
- User interaction prompt (reuse or create new)
- Graphite tracking synchronization via `BranchManager.ensure_tracked()`

**Tripwire:** "Before implementing branch reuse detection in plan submit" → ensure Graphite tracking sync

#### 7. Multi-Plan Consolidation Patterns
**Location:** `docs/learned/planning/multi-plan-consolidation.md`
**Action:** CREATE
**Source:** #5683

Document:
- When to consolidate vs batch replan vs objective coordination
- Overlap analysis methodology (parallel Explore agents)
- Merge strategy determination
- Attribution tracking (`[from #123]` syntax)

#### 8. Consolidated Plan Format
**Location:** `docs/learned/planning/plan-schema.md`
**Action:** UPDATE
**Source:** #5683

Add:
- `Consolidates:` header format (vs `Replans:` for single)
- Source plans table format
- Overlap analysis section requirements
- Attribution tracking in implementation steps

### LOW Priority

#### 9. GitHub PR/Issue Operations in erk exec
**Location:** `docs/learned/cli/erk-exec-commands.md`
**Action:** UPDATE
**Source:** #5695, #5680

Add subsections for:
- `get-pr-commits` - Fetch PR commits via REST API
- `close-issue-with-comment` - Two-step workflow (comment then close)
- `handle-no-changes` - Reference to no-changes-handling.md

#### 10. Session Source Tripwires
**Location:** `docs/learned/tripwires.md`
**Action:** UPDATE
**Source:** #5683, #5680

Add:
- "Before downloading remote sessions with `erk exec download-remote-session --gist-url`" → Check `gist_url != null` for legacy artifact sessions
- "Before preprocessing sessions in erk learn workflow" → Inspect `source.source_type` to determine local vs remote access

#### 11. CLI and Planning Index Updates
**Location:** `docs/learned/cli/index.md`, `docs/learned/planning/index.md`
**Action:** UPDATE
**Source:** All

Add navigation links for new documentation files

## Implementation Order

1. **First:** Create `ci-aware-commands.md` (new, referenced by tripwire)
2. **Second:** Update `gateway-abc-implementation.md` (sub-gateway pattern)
3. **Third:** Update `github-api-rate-limits.md` (retry distinction)
4. **Fourth:** Update `git-graphite-quirks.md` (branch divergence)
5. **Fifth:** Create planning docs (`no-changes-handling.md`, `submit-branch-reuse.md`, `multi-plan-consolidation.md`)
6. **Sixth:** Update `plan-schema.md` (consolidated format)
7. **Seventh:** Update `erk-exec-commands.md` (exec command references)
8. **Eighth:** Update `tripwires.md` and indexes
9. **Finally:** Run `erk docs sync` for tripwire sync

## Verification

1. Run `make fast-ci` to ensure no formatting/lint issues
2. Verify all new docs have proper frontmatter with `read_when` conditions
3. Check that index files link to new docs
4. Verify tripwires sync properly with `erk docs sync`

## Summary Statistics

| Metric | Count |
|--------|-------|
| New documentation files | 4 |
| Updated documentation files | 6 |
| Index updates | 2 |
| Tripwires to add | 4 |
| Items skipped (already documented) | 7 |
| Total consolidated from | 4 plans |