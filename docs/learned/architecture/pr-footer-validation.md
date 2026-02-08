---
title: PR Footer Format Validation
last_audited: "2026-02-08"
audit_result: regenerated
tripwires:
  - action: "modifying PR footer format"
    warning: "Update generator, parser, AND validator in sync. Add support for new format BEFORE deprecating old format. Never break parsing of existing PRs."
read_when:
  - "working with PR metadata footer format"
  - "modifying PR footer generation or parsing"
  - "debugging PR footer extraction errors"
---

# PR Footer Format Validation

## Why Strict Format Matters

PR footers enable automated workflows that depend on reliable parsing. The footer contains:

1. **Closing references** — GitHub auto-closes linked issues when PR merges
2. **Checkout commands** — Copy-paste instructions for `erk pr checkout`
3. **Cross-repo references** — `owner/repo#N` format for plans in external repos

**Strict format enforcement prevents:**

- Silent parser failures (footer exists but data not extracted)
- Workflow breakage (wrong issue closed, checkout command fails)
- Migration confusion (format changes break old PRs)

The format is validated at multiple points: generation, parsing, and when extracting closing references. This defense-in-depth ensures consistency across the entire PR lifecycle.

## The Three-Part Contract

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/pr_footer.py, build_pr_body_footer, extract_footer_from_body, extract_closing_reference -->

Every format change requires updating three synchronized components:

1. **Generator** — Creates footer markdown with correct structure
2. **Parser** — Extracts footer section from full PR body (uses `\n---\n` delimiter)
3. **Validator** — Extracts structured data (issue numbers, repo references) from footer text

**CRITICAL:** Add new format support to parser/validator BEFORE updating generator. This ensures old PRs remain parseable during migration.

See `build_pr_body_footer()`, `extract_footer_from_body()`, and `extract_closing_reference()` in `packages/erk-shared/src/erk_shared/gateway/github/pr_footer.py`.

## Current Format Structure

The footer follows a three-section pattern:

```markdown
---

Closes #123

To checkout this PR in a fresh worktree and environment locally, run:
```

source "$(erk pr checkout 1895 --script)" && erk pr sync --dangerous

```

```

**Key format rules:**

- Footer starts after last `\n---\n` delimiter in PR body
- Closing reference comes first (if present): `Closes #N` or `Closes owner/repo#N`
- Checkout command always includes `&& erk pr sync --dangerous` suffix
- PR number in checkout command must match actual PR number (initially 0, updated after creation)

**Cross-repo variation:** When `plans_repo` is set, closing reference uses `owner/repo#N` format instead of `#N`.

## Migration Strategy: Phase-Zero Detection

<!-- Source: docs/learned/architecture/phase-zero-detection-pattern.md -->

Format changes must support old and new formats simultaneously during transition:

**Phase 0: Add new format support**

- Parser recognizes both old and new delimiters/patterns
- Validator extracts data from both formats
- Zero generator changes yet

**Phase 1: Update generator**

- New PRs use new format
- Old PRs remain parseable via Phase 0 support

**Phase 2: Explicit migration** (optional)

- Update existing PR bodies if needed
- Or leave them in old format (parser handles both)

**Phase 3: Deprecate old format** (optional, after grace period)

- Remove old format support from parser/validator

**Anti-pattern:** Updating generator first breaks parsing of old PRs when code reads them.

## Common Parsing Failures

### Delimiter Mismatch

**Symptom:** `extract_footer_from_body()` returns `None` even though footer exists

**Cause:** Footer delimiter doesn't match `\n---\n` pattern (e.g., `---` without newlines)

**Fix:** Verify delimiter is exactly `\n---\n` with surrounding newlines

### Closing Reference Format Error

**Symptom:** `extract_closing_reference()` returns `None` even though "Closes #N" exists

**Cause:** Extra whitespace, wrong capitalization, or malformed issue reference

**Fix:** Check regex patterns in `extract_closing_reference()`:

- Same-repo: `Closes\s+#(\d+)`
- Cross-repo: `Closes\s+([\w-]+/[\w.-]+)#(\d+)`

### Stale PR Number

**Symptom:** Checkout command references wrong PR number

**Cause:** Generator creates footer with `pr_number=0` initially, update call fails

<!-- Source: src/erk/cli/commands/pr/submit_pipeline.py, _core_submit_flow -->

**Fix:** See two-phase creation in `_core_submit_flow()`:

1. Create PR with `pr_number=0` footer
2. Update footer with actual PR number after creation

## Test Coverage

<!-- Source: packages/erk-shared/tests/unit/github/test_pr_footer.py -->

Comprehensive test suite validates:

- Footer generation with/without issue numbers
- Cross-repo closing reference format
- Header/footer extraction and reconstruction
- Round-trip preservation (extract → rebuild → extract)
- Delimiter handling edge cases

See `test_pr_footer.py` for complete test patterns.

## Related Patterns

- [Phase Zero Detection Pattern](phase-zero-detection-pattern.md) — Add new format before deprecating old
- [Gateway Removal Pattern](gateway-removal-pattern.md) — How to change gateway interfaces safely
- [Parameter Threading Pattern](parameter-threading-pattern.md) — How `plans_repo` flows through submit pipeline
