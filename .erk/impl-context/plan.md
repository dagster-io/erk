# Documentation Plan: Move plan-header metadata block to bottom of PR descriptions

## Context

PR #7934 fundamentally restructures how PR bodies are organized, moving plan metadata from the top to the bottom. This is a significant UX improvement that puts AI-generated summaries front-and-center while relegating internal tracking metadata (plan references, execution metadata) to the end where it doesn't distract reviewers.

The implementation demonstrates exemplary backward compatibility engineering. Rather than breaking existing PRs, the codebase now supports dual-mode extraction: it first looks for headers at the new bottom position, then falls back to legacy top positioning. The `rebuild_pr_body()` function automatically migrates legacy PRs to the new format upon any update, enabling gradual, friction-free migration without manual intervention.

Documentation is critical here because the PR body structure is a cornerstone abstraction in erk. Multiple commands (`pr check`, `submit`, `pr rewrite`, CI update scripts) touch PR bodies. Future agents working on PR-related features need to understand: (1) the new canonical format, (2) how backward compatibility works, (3) when validation will fail (legacy format), and (4) how to detect whether a PR needs migration.

## Raw Materials

PR #7934

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 9     |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 0     |
| Potential tripwires (score2-3) | 5     |

## Documentation Items

### HIGH Priority

#### 1. PR Body Structure and Layout

**Location:** `docs/learned/pr-operations/pr-body-structure.md`
**Action:** CREATE
**Source:** [PR #7934]

**Draft Content:**

```markdown
---
title: PR Body Structure
read_when:
  - "assembling or parsing PR body content"
  - "working with plan headers, metadata blocks, or footers"
  - "investigating PR body validation failures"
tripwires:
  - action: "placing **Plan:** or metadata blocks at the top of PR bodies"
    warning: "Since PR #7934, plan header and metadata appear BELOW content, above footer. New format: summary -> plan details -> header/metadata -> footer. Legacy top-position triggers validation failure."
  - action: "extracting header content assuming top position"
    warning: "Use `extract_header_from_body()` which handles both positions with fallback. Direct line scanning from top will miss new-format PRs."
---

# PR Body Structure

PR bodies follow a defined structure that changed in PR #7934. This document describes the canonical format and backward compatibility behavior.

## New Format (Post-#7934)

See `packages/erk-shared/src/erk_shared/gateway/github/pr_footer.py` for the implementation.

Sections appear in this order:
1. **Main content** — AI-generated summary describing the changes
2. **Plan details** — Collapsible `<details>` section with plan content
3. **Header/Metadata** — `**Plan:** #N` reference and erk metadata YAML block
4. **Footer** — Checkout command and `Closes #N` reference

## Legacy Format (Pre-#7934)

The old format placed header/metadata at the TOP:
1. Header/Metadata (e.g., `**Plan:** #N`)
2. Main content
3. Footer

## Migration Behavior

The `rebuild_pr_body()` function always produces new-format output. When processing a legacy PR:
1. `extract_header_from_body()` finds header at top (fallback path)
2. `rebuild_pr_body()` places header at bottom (new position)
3. Result: Legacy PRs auto-migrate on next CI update

## Separator Handling

When repositioning metadata blocks, strip the `PLAN_CONTENT_SEPARATOR` to prevent double-separator artifacts. See `ci_update_pr_body` and `assemble_pr_body()` implementations.
```

---

#### 2. Update PR Body Assembly Doc

**Location:** `docs/learned/architecture/pr-body-assembly.md`
**Action:** UPDATE
**Source:** [PR #7934]

**Draft Content:**

Add a new section describing the layout change and update the `assemble_pr_body()` documentation:

```markdown
## Layout Change (PR #7934)

Since PR #7934, `assemble_pr_body()` places header and metadata content BELOW the main PR body content, immediately above the footer. This "summary-first" layout improves readability by showing the AI-generated description at the top.

Assembly order:
1. Main content (`pr_body_content`)
2. Header block (if present)
3. Metadata prefix (for draft-PR backend)
4. Footer (checkout command + closing reference)

When metadata blocks contain trailing `PLAN_CONTENT_SEPARATOR`, it is stripped to prevent double separators.

See `src/erk/cli/commands/pr/shared.py` for the implementation.
```

Add tripwire to the frontmatter:

```yaml
tripwires:
  # ... existing tripwires ...
  - action: "placing header or metadata above main content in assemble_pr_body calls"
    warning: "Since PR #7934, header and metadata go BELOW content (above footer). Content-first layout is now canonical."
```

---

#### 3. Header Extraction and Backward Compatibility

**Location:** `docs/learned/architecture/backward-compatibility.md`
**Action:** CREATE
**Source:** [PR #7934]

**Draft Content:**

```markdown
---
title: Backward Compatibility Patterns
read_when:
  - "implementing format changes that must support legacy data"
  - "designing migration strategies for existing resources"
  - "working with PR body parsing or extraction functions"
tripwires:
  - action: "implementing a format change without fallback extraction"
    warning: "Use the fallback scanning pattern: try new format first, fall back to legacy, return empty/default if neither. See PR #7934 header extraction for canonical example."
---

# Backward Compatibility Patterns

This document describes patterns for implementing format changes while maintaining compatibility with existing data.

## Fallback Scanning Pattern

The canonical pattern for handling format evolution:

1. **Try new format first** — Check for data at the expected new location
2. **Fall back to legacy** — If not found, check legacy location(s)
3. **Return empty/default** — If neither found, return appropriate empty value

### Example: Header Extraction (PR #7934)

See `packages/erk-shared/src/erk_shared/gateway/github/pr_footer.py`:

The `extract_header_from_body()` function demonstrates this pattern:
- First scans upward from footer for header lines (new format)
- If not found, calls `_scan_header_from_top()` for legacy format
- Returns empty string if neither location contains a header

## Migration Detection API

When you need to detect whether data is in legacy format:

See `is_header_at_legacy_position()` in the same file. This function returns `True` when:
- Header exists at legacy position (top)
- Header does NOT exist at new position (bottom)

Use cases:
- Validation tooling (`erk pr check` Check 3)
- Dashboards tracking migration progress
- Migration scripts identifying affected resources

## Extract-and-Rebuild Migration

The `rebuild_pr_body()` function always outputs new format, regardless of input format. This enables passive migration:

1. User or CI triggers PR body update
2. Extract functions handle legacy input
3. Rebuild function produces new-format output
4. Legacy PR is now migrated

No explicit migration command needed — updates naturally migrate.
```

---

### MEDIUM Priority

#### 4. Add `erk pr check` Header Position Validation

**Location:** `docs/learned/pr-operations/tripwires.md`
**Action:** UPDATE
**Source:** [PR #7934]

**Draft Content:**

Add this tripwire to the source document that generates the tripwires.md file (likely the frontmatter of a relevant pr-operations doc, or as a standalone entry):

```yaml
- action: "expecting erk pr check to pass with header at top of PR body"
  warning: "Check 3 validates header position. PASS: header at bottom (above footer). FAIL: header at legacy top position. Use is_header_at_legacy_position() for migration detection. See src/erk/cli/commands/pr/check_cmd.py."
```

---

#### 5. CI Update PR Body Logic

**Location:** `docs/learned/ci/tripwires.md`
**Action:** UPDATE
**Source:** [PR #7934]

**Draft Content:**

Add tripwire to the CI tripwires:

```yaml
- action: "modifying ci_update_pr_body metadata block positioning"
  warning: "Since PR #7934, ci_update_pr_body places metadata at bottom (not top). Assembly order: summary -> original_plan_section -> metadata_block -> footer. Strip PLAN_CONTENT_SEPARATOR from metadata_block. See src/erk/cli/commands/exec/scripts/ci_update_pr_body.py."
```

---

#### 6. Migration Detection API Reference

**Location:** `docs/learned/pr-operations/pr-body-structure.md` (section)
**Action:** UPDATE (add section to item #1)
**Source:** [PR #7934]

**Draft Content:**

Add section to the PR Body Structure doc:

```markdown
## Migration Detection

The `is_header_at_legacy_position()` function in `packages/erk-shared/src/erk_shared/gateway/github/pr_footer.py` detects whether a PR uses the legacy format.

**Returns True when:**
- Header block exists at top of body
- Header block does NOT exist at bottom

**Use cases:**
- `erk pr check` validation (Check 3)
- Migration progress monitoring
- Bulk migration tooling
```

---

### LOW Priority

#### 7. Submit Command Initial Format

**Location:** `docs/learned/pr-operations/pr-submission-workflow.md`
**Action:** UPDATE
**Source:** [PR #7934]

**Draft Content:**

Add note to the PR submission workflow doc:

```markdown
## Initial PR Body Format (PR #7934)

The `submit` command creates PRs with `**Plan:**` reference at the bottom position (above footer), not at top. This matches the new canonical format established in PR #7934.

See `src/erk/cli/commands/submit.py` for the implementation.
```

---

#### 8. Plan Backends Metadata Position

**Location:** `docs/learned/planning/plan-backends.md`
**Action:** UPDATE
**Source:** [PR #7934]

**Draft Content:**

Add note clarifying both backends use the same layout:

```markdown
## Metadata Position (PR #7934)

Both backends now position metadata at the bottom of PR bodies:

- **Issue-based:** `**Plan:** #N` reference below content
- **Draft-PR:** `<!-- erk:metadata-block:plan-header -->` YAML block below content

This unified positioning was established in PR #7934 for consistent "summary-first" UX across both backends.
```

---

#### 9. Test Organization for Legacy Format

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [PR #7934]

**Draft Content:**

Add tripwire for test organization pattern:

```yaml
- action: "adding backward compatibility tests without section markers"
  warning: "Use section marker pattern for legacy format tests: '# Legacy <Format> Tests' comment. Separates primary format tests from backward compatibility tests. See test_pr_footer.py for example."
```

---

## Stale Documentation Cleanup

No stale documentation detected requiring removal.

---

## Prevention Insights

### 1. Double-Separator Artifacts

**What happened:** When moving metadata blocks from one position to another, the separator suffix (`PLAN_CONTENT_SEPARATOR`) would appear twice if not stripped.

**Root cause:** Metadata blocks were designed with trailing separators for their original top position. Moving them without cleanup created `---\n---` artifacts.

**Prevention:** Always strip `PLAN_CONTENT_SEPARATOR` when repositioning content blocks. Check both `ci_update_pr_body.py` and `shared.py` for the canonical pattern.

**Recommendation:** ADD_TO_DOC (covered in PR Body Structure doc)

### 2. Validation Without Migration Path

**What happened:** Adding validation (Check 3 for header position) without a corresponding migration mechanism would break existing PRs.

**Root cause:** Potential oversight — validation rules that cannot be automatically satisfied trap users.

**Prevention:** When adding validation rules, always provide either: (1) automatic migration on next update, or (2) explicit migration command. PR #7934 uses approach #1.

**Recommendation:** CONTEXT_ONLY (architectural principle, not tripwire-worthy)

---

## Tripwire Candidates

No items scored 4 or higher on the tripwire criteria. The changes in this PR are significant but have explicit error messages (validation fails clearly) and limited destructive potential (format changes don't lose data).

---

## Potential Tripwires

Items with borderline scores that may warrant promotion with additional context:

### 1. `erk pr check` Header Validation (Score: 3)

**Criteria met:** Non-obvious (+2), Cross-cutting (+1)
**Notes:** The validation rule affects all PR workflows, but the error message is explicit. Users will quickly learn the rule after one failure. Adding as a doc note is sufficient; a tripwire would be excessive.

### 2. `ci_update_pr_body` Metadata Position (Score: 3)

**Criteria met:** Non-obvious (+2), External tool integration (+1)
**Notes:** CI developers working on the update logic need to know this, but the code is self-documenting with clear variable names. Adding tripwire to CI tripwires doc for awareness.

### 3. `assemble_pr_body()` Layout Change (Score: 2)

**Criteria met:** Non-obvious (+2)
**Notes:** Internal function with limited direct usage. The doc update covers this adequately.

### 4. Submit Initial Format (Score: 2)

**Criteria met:** Non-obvious (+2)
**Notes:** Only affects initial PR creation. Low cross-cutting impact.

### 5. Separator Stripping Pattern (Score: 2)

**Criteria met:** Non-obvious (+2)
**Notes:** Prevents cosmetic artifacts but no data loss if missed. Doc coverage sufficient.

---

## Source Pointers

For documentation writers implementing this plan:

### Core Functions
- `extract_header_from_body()`: `packages/erk-shared/src/erk_shared/gateway/github/pr_footer.py` (grep for function name)
- `_scan_header_from_top()`: same file, private helper
- `is_header_at_legacy_position()`: same file
- `extract_main_content()`: same file
- `rebuild_pr_body()`: same file

### CLI Commands
- `pr_check` validation: `src/erk/cli/commands/pr/check_cmd.py` (grep for `is_header_at_legacy_position`)
- `ci_update_pr_body`: `src/erk/cli/commands/exec/scripts/ci_update_pr_body.py` (grep for `metadata_block`)
- `assemble_pr_body()`: `src/erk/cli/commands/pr/shared.py` (grep for function name)
- `submit`: `src/erk/cli/commands/submit.py` (grep for `**Plan:**`)

### Constants
- `PLAN_CONTENT_SEPARATOR`: `packages/erk-shared/src/erk_shared/plan_store/draft_pr_lifecycle.py`
- `HEADER_PATTERNS`: `packages/erk-shared/src/erk_shared/gateway/github/pr_footer.py`
