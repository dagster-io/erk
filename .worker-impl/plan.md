# Plan: Create Objective to Audit All docs/learned/ Documents

## Context

The `/local:audit-scan` found 141 documents in `docs/learned/` that have never been formally audited (`last_audited` field missing from all). A previous objective (#6697) audited 62 high-signal docs, but the audit metadata was subsequently lost. This objective will systematically audit the entire corpus, organized by priority score from the scan.

## Objective Structure

**3 phases, 8 steps, 8 PRs** — organized by priority tier with batch-level granularity.

### Phase 1: HIGH Priority (44 docs, 3 PRs)

| Step | Description | Docs |
|------|-------------|------|
| 1.1 | Audit score 13-14 docs (critical broken paths, highest code block density) | 14 |
| 1.2 | Audit score 11-12 docs | 18 |
| 1.3 | Audit score 10 docs | 12 |

### Phase 2: MODERATE Priority (60 docs, 3 PRs)

| Step | Description | Docs |
|------|-------------|------|
| 2.1 | Audit score 9 docs | 17 |
| 2.2 | Audit score 8 docs | 18 |
| 2.3 | Audit score 6-7 docs | 25 |

### Phase 3: LOW Priority (37 docs, 2 PRs)

| Step | Description | Docs |
|------|-------------|------|
| 3.1 | Audit score 4-5 docs | 22 |
| 3.2 | Audit score 3 docs + 1 redirect stub | 15 |

## Implementation Steps

1. **Draft objective body** — Full markdown with:
   - Goal section describing the end state (100% audited corpus)
   - Design decisions (score-based ordering, batch granularity, auto-apply workflow)
   - Roadmap tables with the 8 steps above
   - Per-step doc lists (extracted from scan results) in expandable `<details>` blocks
   - Test criteria per phase (verify `last_audited` field present on all docs in batch)

2. **Create GitHub issue** — Use `gh api` REST endpoint (not GraphQL per tripwire) with label `erk-objective`

## Per-Step Workflow (for future implementers)

Each step follows this process:
1. Run `/local:audit-doc --auto-apply` on each doc in the batch
2. Review changes, fix anything needing manual attention
3. Commit and submit PR
4. Update objective roadmap with PR number

## Verification

- `gh issue view <number>` confirms issue exists with `erk-objective` label
- `erk objective check <number>` validates roadmap format
- Roadmap shows 8 pending steps across 3 phases