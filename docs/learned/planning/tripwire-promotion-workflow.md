---
title: Tripwire Promotion Workflow
read_when:
  - "implementing tripwire candidate extraction"
  - "promoting tripwire candidates to frontmatter"
  - "understanding the learn-to-tripwire pipeline"
---

# Tripwire Promotion Workflow

How tripwire candidates flow from learn sessions to active tripwires.

## Pipeline Overview

1. **Session Analysis**: Agent errors/patterns identified in session logs
2. **Learn Plan**: Tripwire candidates described in prose (Tripwire Candidates section)
3. **Extraction**: Tripwire Extractor agent extracts structured candidates
4. **Storage**: `store-tripwire-candidates` saves to PR comment as metadata block
5. **Promotion**: `promote_tripwire_to_frontmatter()` adds entries to doc YAML
6. **Index Generation**: `erk docs sync` regenerates `tripwires.md` from all frontmatter

## Key Components

### TripwireCandidate Dataclass

Location: `packages/erk-shared/src/erk_shared/github/metadata/tripwire_candidates.py`

Fields:

- `action`: The action pattern to detect (e.g., "calling os.chdir()")
- `warning`: Warning message explaining what to do instead
- `target_doc_path`: Relative path within `docs/learned/` for this tripwire

### Tripwire Extractor Agent

Location: `.claude/agents/learn/tripwire-extractor.md`

Reads learn plan and gap analysis docs, extracts structured tripwire candidates with action/warning/target_doc_path. Outputs JSON to `.erk/scratch/sessions/${session}/learn-agents/tripwire-candidates.json`.

### Storage Command

Command: `erk exec store-tripwire-candidates --issue <N> --candidates-file <path>`

Posts candidates to GitHub issue as a metadata comment with key `tripwire-candidates`.

### Promotion Function

Location: `packages/erk-shared/src/erk_shared/learn/tripwire_promotion.py`

Function: `promote_tripwire_to_frontmatter(project_root, target_doc_path, action, warning)`

Returns: `PromotionResult` dataclass with `success`, `target_doc_path`, `error` fields.

Features:

- Reads target doc's YAML frontmatter
- Adds tripwire entry to `tripwires:` list
- Deduplicates by action string (skips if same action exists)
- Returns error if doc not found or no frontmatter

## Quality Criteria for Tripwires

- **Action patterns should be specific**: "calling os.chdir()" not "changing directories"
- **Warnings should be actionable**: "Use context.time.sleep() for testability" not "Be careful"
- **Target docs must exist**: Only reference docs that exist in `docs/learned/`
- **Prefer fewer, high-quality candidates**: 2-3 precise tripwires better than 10 vague ones

## Related Topics

- [Tripwire Worthiness Criteria](tripwire-worthiness-criteria.md) - Scoring tripwire candidates
- [Learn Workflow](learn-workflow.md) - Full learn workflow with agent tiers
- [Metadata Blocks](../architecture/metadata-blocks.md) - How metadata is stored in GitHub comments
