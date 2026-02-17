---
title: Agent Schema Enforcement
read_when:
  - "processing JSON output from AI agents"
  - "normalizing agent-produced data before validation"
  - "designing schemas for agent-to-tool communication"
  - "debugging tripwire candidate JSON drift"
tripwires:
  - action: "trusting agent-produced JSON without normalization"
    warning: "Agents drift from expected schemas over time. Always normalize at the boundary before validation. See normalize_tripwire_candidates.py for the pattern."
  - action: "adding a new field to agent-produced JSON without updating normalization"
    warning: "Add the field to CANONICAL_FIELDS and any aliases to FIELD_ALIASES in the normalization script. Without this, the field may be stripped during normalization."
---

# Agent Schema Enforcement

AI agents produce JSON that drifts from expected schemas. This document describes the defense-in-depth approach erk uses to handle schema drift at system boundaries.

## The Problem

When agents produce structured JSON (tripwire candidates, plan metadata, etc.), the output frequently diverges from the expected schema:

- **Root key drift**: `tripwire_candidates` instead of `candidates`
- **Field name drift**: `description` instead of `warning`, `title` or `name` instead of `action`
- **Extra fields**: Agents add fields not in the schema (`trigger_pattern`, `severity`, etc.)
- **Missing fields**: Required fields omitted entirely

This drift is not a bug in any single agent — it's a property of LLM-based systems. Prompts can reduce drift but cannot eliminate it.

## Decision Framework

Three approaches exist for handling agent schema drift:

| Approach                | Pros                         | Cons                                 |
| ----------------------- | ---------------------------- | ------------------------------------ |
| Inline schema in prompt | Prevents drift at source     | Bloats prompts, agents still drift   |
| Normalize at boundary   | Handles drift after the fact | Doesn't prevent drift, adds code     |
| Validate and reject     | Strict correctness           | High failure rate, wastes agent work |

The recommended approach is **normalize + validate** (defense-in-depth): normalize common drift patterns at the boundary, then validate the normalized output. This maximizes the success rate while maintaining schema correctness.

## The Normalize Pattern

<!-- Source: src/erk/cli/commands/exec/scripts/normalize_tripwire_candidates.py:25-106 -->

The `normalize-tripwire-candidates` exec script demonstrates the canonical pattern:

### Root Key Normalization

<!-- See ROOT_KEY_ALIASES in src/erk/cli/commands/exec/scripts/normalize_tripwire_candidates.py:28-30 -->

Maps non-canonical root keys (e.g., `tripwire_candidates`) to the canonical key (`candidates`). If the canonical root key is missing, check for known aliases and rename.

### Field Name Normalization

<!-- See FIELD_ALIASES in src/erk/cli/commands/exec/scripts/normalize_tripwire_candidates.py:33-38 -->

Maps non-canonical field names (e.g., `description`, `title`, `name`, `trigger_pattern`) to their canonical equivalents (`warning`, `action`). For each entry, copy canonical fields first, then fill missing canonical fields from aliases. This gives canonical field names precedence — if both `action` and `title` are present, `action` wins.

### Extra Field Stripping

Only `CANONICAL_FIELDS` (`action`, `warning`, `target_doc_path`) are kept. Extra fields are silently removed. This prevents downstream code from depending on fields that may or may not appear.

## The Three-Layer Architecture

For critical agent-produced data, use all three layers:

1. **Inline schema in prompt** — include the expected format in the agent's instructions to reduce drift frequency
2. **Normalize at boundary** — run normalization before validation to recover from common drift patterns
3. **Validate normalized output** — reject entries that are still invalid after normalization

The `store_tripwire_candidates.py` script validates after normalization, ensuring only well-formed entries are stored.

## Current Implementation

The tripwire extraction pipeline uses this pattern:

1. Agent produces `tripwire-candidates.json` (may have drift)
2. `erk exec normalize-tripwire-candidates` normalizes in-place
3. `erk exec store-tripwire-candidates` validates and stores

The normalization step is idempotent — running it on already-correct JSON produces no changes. The `normalized` flag in the response indicates whether any changes were made.

## Related Documentation

- [Frontmatter and Tripwire Format](../documentation/frontmatter-tripwire-format.md) — The target schema tripwire candidates must match
