# Documentation Plan: Update CI/Commands/Skills for .erk/impl-context/ consolidation

## Context

This PR (#8326) represents Phase 3 of objective #8197, which consolidates erk's implementation directory model. The broader effort replaces the legacy `.impl/` directory pattern with branch-scoped `.erk/impl-context/<branch>/` directories, enabling transparent resolution via `resolve_impl_dir()`. The PR updates 18 test files and one skill file to use the new directory model, while related PRs (#8328, #8279, #7901) handle CI workflows and exec scripts.

Documentation matters here because agents implementing future plans need to understand: (1) the new branch-scoped directory model and its discovery strategy, (2) the test helper patterns for working with implementation directories, and (3) critical CI patterns discovered during this work (force-adding gitignored directories, triaging pre-existing failures). The existing `docs/learned/planning/impl-context.md` contains phantom references to a file that no longer exists, which will actively mislead agents attempting to understand the lifecycle.

Key insights from this implementation include the grep audit pattern for systematic refactoring verification, the regex-over-literal lesson for pattern matching, and the distinction between "files exist on disk" vs "files exist in git tracking" that underlies the two-phase cleanup pattern.

## Raw Materials

PR #8326

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 12    |
| Contradictions to resolve      | 1     |
| Tripwire candidates (score>=4) | 3     |
| Potential tripwires (score 2-3)| 2     |

## Stale Documentation Cleanup

Existing docs with phantom references requiring action:

### 1. setup_impl_from_issue.py Phantom Reference

**Location:** `docs/learned/planning/impl-context.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py` (lines 43, 48, 68, 72, 202)
**Cleanup Instructions:** The file `setup_impl_from_issue.py` does not exist in the codebase. All five references should point to `src/erk/cli/commands/exec/scripts/setup_impl.py`, which contains the consolidated logic. Verify that the "deliberate non-deletion" pattern (the comment about deferring deletion to Step 2d) still exists at the correct location in the actual file, and update line number references accordingly.

## Documentation Items

### HIGH Priority

#### 1. Implementation Directory Model Consolidation

**Location:** `docs/learned/planning/impl-context.md`
**Action:** UPDATE
**Source:** [PR #8326]

**Draft Content:**

```markdown
---
title: Implementation Directory Model
read_when:
  - "working with .erk/impl-context/ files"
  - "debugging plan content missing from implementation"
  - "understanding how plans transfer content to implementation directories"
  - "writing tests that create implementation directories"
tripwires:
  # existing tripwires plus:
  - action: "hardcoding .impl/ path in tests"
    warning: "Use get_impl_dir(tmp_path, branch_name=BRANCH) helper for branch-scoped paths. Never hardcode .impl/ in new tests."
---

# Implementation Directory Model

[Update existing content to reflect:]

## Directory Resolution Strategy

<!-- Source: packages/erk-shared/src/erk_shared/impl_folder.py, resolve_impl_dir -->

The implementation directory is resolved via `resolve_impl_dir()`, which searches for existing directories in priority order:
1. Branch-scoped: `.erk/impl-context/<branch>/`
2. Legacy: `.impl/`

For creating new directories, use `get_impl_dir()` which constructs the branch-scoped path.

See `resolve_impl_dir()` and `get_impl_dir()` in `packages/erk-shared/src/erk_shared/impl_folder.py`.

## Metadata Files

The implementation directory contains:
- `plan.md` - The plan content (immutable during implementation)
- `ref.json` - Plan reference metadata (migrated from `plan-ref.json`)

Schema for `ref.json`: `{provider, plan_id, plan_url, title, labels, objective_id}`

[Continue with existing lifecycle content, updating file paths...]
```

---

#### 2. CI Force-Add Gitignored Directories (Tripwire)

**Location:** `docs/learned/ci/tripwires.md`
**Action:** UPDATE (add to frontmatter of a source file, then run `erk docs sync`)
**Source:** [PR #8328]

**Draft Content:**

This tripwire should be added to an appropriate CI doc's frontmatter (likely `plan-implement-workflow-patterns.md` or `workflow-gating-patterns.md`):

```yaml
tripwires:
  - action: "staging gitignored directories in CI workflows"
    warning: "Use `git add -f` to force-add. Without `-f`, git silently skips gitignored files and the commit appears to succeed but content is missing."
    score: 6
```

The `.erk/impl-context/` directory is gitignored by default. When CI workflows need to commit this directory for branch sharing, they must use `git add -f .erk/impl-context` rather than `git add .erk/impl-context`. The failure mode is silent: git skips the gitignored files, the commit succeeds with no error, but the content is missing from the commit.

---

#### 3. Pre-existing CI Failure Triage (Tripwire)

**Location:** `docs/learned/ci/tripwires.md`
**Action:** UPDATE (add to `ci-iteration.md` frontmatter, then run `erk docs sync`)
**Source:** [Impl]

**Draft Content:**

Add to `ci-iteration.md` frontmatter:

```yaml
tripwires:
  - action: "debugging a CI failure"
    warning: "ALWAYS run `git diff --name-only HEAD` first to distinguish new issues from pre-existing failures. Cross-reference failure file paths against changed files before debugging."
    score: 4
```

When CI fails, the failure may be from pre-existing issues in the codebase, not from the current changes. Before debugging, compare the failing file paths against `git diff --name-only HEAD` to determine if the failures are in changed files. In this PR, Prettier failures in `docs/learned/integrations/github-review-decision.md` and `docs/learned/tui/status-indicators.md` were correctly identified as pre-existing issues unrelated to the current work.

---

### MEDIUM Priority

#### 4. Test Pattern for Implementation Directories

**Location:** `docs/learned/testing/impl-directory-testing.md`
**Action:** CREATE
**Source:** [PR #8326]

**Draft Content:**

```markdown
---
title: Implementation Directory Testing
read_when:
  - "writing tests that create implementation directories"
  - "migrating tests from hardcoded .impl/ to branch-scoped paths"
  - "understanding get_impl_dir() test helper"
tripwires:
  - action: "hardcoding .impl/ path in new tests"
    warning: "Use get_impl_dir(tmp_path, branch_name=BRANCH) for branch-scoped paths. The helper constructs .erk/impl-context/<branch>/ paths consistently."
---

# Implementation Directory Testing

Tests that create implementation directories should use the `get_impl_dir()` helper for consistent branch-scoped path construction.

## The Test Helper Pattern

<!-- Source: packages/erk-shared/src/erk_shared/impl_folder.py, get_impl_dir -->

See `get_impl_dir()` in `packages/erk-shared/src/erk_shared/impl_folder.py`.

### Key patterns:
- Use `get_impl_dir(tmp_path, branch_name=BRANCH)` to construct paths
- Call `impl_dir.mkdir(parents=True)` - branch-scoped paths require nested directory creation
- Write `ref.json` (not `plan-ref.json`) for plan reference metadata

## Dry-Run Test Pattern

For dry-run tests that verify no directories are created:

```python
# Assert the parent directory doesn't exist
assert not (env.cwd / ".erk" / "impl-context").exists()
```

This verifies that dry-run mode doesn't create any implementation directories.

## Related Documentation

- [Implementation Directory Model](../planning/impl-context.md) - Directory resolution strategy
```

---

#### 5. Ref.json Migration

**Location:** `docs/learned/planning/ref-json-format.md`
**Action:** CREATE
**Source:** [PR #8326]

**Draft Content:**

```markdown
---
title: Ref.json Format
read_when:
  - "working with plan reference metadata"
  - "migrating from plan-ref.json to ref.json"
  - "understanding the ref.json schema"
---

# Ref.json Format

`ref.json` is the plan reference metadata file stored in implementation directories. It was migrated from the earlier `plan-ref.json` naming convention.

## Schema

<!-- Source: packages/erk-shared/src/erk_shared/impl_folder.py, save_plan_ref -->

See `save_plan_ref()` and `read_plan_ref()` in `packages/erk-shared/src/erk_shared/impl_folder.py`.

The file contains:
- `provider` - The plan backend provider (e.g., "github")
- `plan_id` - Unique identifier for the plan
- `plan_url` - URL to the plan issue/PR
- `title` - Plan title
- `labels` - List of labels applied to the plan
- `objective_id` - (optional) Associated objective ID

## Migration from plan-ref.json

Tests and code that previously used `plan-ref.json` should be updated to use `ref.json`. The file content schema is unchanged; only the filename changed.
```

---

#### 6. Grep Audit Pattern for Refactoring

**Location:** `docs/learned/testing/verification-patterns.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
title: Verification Patterns
read_when:
  - "verifying a refactoring is complete"
  - "checking that all instances of a pattern were updated"
  - "auditing code for stale references"
tripwires:
  - action: "verifying pattern removal with literal string searches"
    warning: "Use regex patterns (e.g., `git add.*\\.erk`) not literal strings. Literal searches miss variations."
---

# Verification Patterns

Systematic approaches for verifying refactoring completeness.

## Grep Audit Pattern

When refactoring patterns across a codebase, use parallel grep searches to verify:
1. **Old pattern is gone**: Search for the pattern being removed
2. **New pattern is present**: Search for the replacement pattern

### Use Regex, Not Literal Strings

Literal string searches miss variations. In PR #8326, the initial search for `git add .erk` missed `git add -f .erk`. The correct approach:

```bash
# Wrong: misses variations
grep -r "git add .erk" .

# Right: catches all variations
grep -r "git add.*\.erk" .
```

### Parallel Search Pattern

Run both searches in parallel for efficiency:
1. Search for old pattern (should return 0 results)
2. Search for new pattern (should return expected locations)

## Comment Consistency

When refactoring, also grep for comments referencing old patterns. Code might be updated but comments can lag behind.
```

---

#### 7. Auto-Generated Reference Doc Workflow

**Location:** `docs/learned/documentation/auto-generated-docs.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
title: Auto-Generated Documentation
read_when:
  - "editing a file marked AUTO-GENERATED"
  - "updating CLI command help text"
  - "regenerating reference documentation"
tripwires:
  - action: "editing auto-generated files directly"
    warning: "Check file header for `<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->`. If found, locate source of truth and generation command in the header comments."
---

# Auto-Generated Documentation

Some documentation files are generated from source code and should never be edited directly.

## Identification

Auto-generated files contain a header comment:

```html
<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
```

The header also specifies the source of truth and regeneration command.

## Update Workflow

1. **Find the source**: Look at the header to find what generates this file
2. **Update the source**: For CLI references, update Click command help text
3. **Regenerate**: Run the generation command (e.g., `erk-dev gen-exec-reference-docs`)
4. **Never edit directly**: Changes to generated files will be overwritten

## Examples

- `.claude/skills/erk-exec/reference.md` - Generated from exec script Click decorators
- `docs/learned/*/tripwires.md` - Generated from frontmatter via `erk docs sync`
```

---

#### 8. Session ID Substitution with Stderr Redirects

**Location:** `docs/learned/commands/session-id-substitution.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

The existing doc already covers session ID substitution well. Add this to the tripwires section:

```yaml
tripwires:
  # existing tripwires plus:
  - action: "using ${CLAUDE_SESSION_ID} with stderr redirect (2>/dev/null)"
    warning: "Stderr redirects may interfere with session ID substitution in some contexts. If session ID is non-critical, use `|| true` to suppress errors. If critical, test without redirect first."
```

Add a note to the "Best-Effort Pattern" section explaining that the stderr redirect combined with session ID substitution was observed to fail in some CI contexts.

---

### LOW Priority

#### 9. Dead Code Removal Verification

**Location:** `docs/learned/refactoring/feature-removal-checklist.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

Add to the checklist:

```markdown
## Pre-Removal Verification

Before removing code as "dead":

- [ ] Grep entire codebase (including tests, docs, markdown files) for the symbol name
- [ ] Verify only the definition appears, with zero usage sites
- [ ] Check `docs/learned/` for documentation references
- [ ] Check `.claude/` for skill/command references
```

---

#### 10. Comment Consistency During Refactoring

**Location:** `docs/learned/refactoring/systematic-terminology-renames.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

Add to the tripwires:

```yaml
tripwires:
  # existing tripwires plus:
  - action: "completing a refactoring without grepping for comments"
    warning: "Grep for comments referencing old patterns. Code might be updated but comments can lag behind (e.g., `# Update .impl/ folder` after migration to .erk/impl-context/)."
```

---

#### 11. Regex Grep for Completeness

**Location:** `docs/learned/testing/verification-patterns.md` (same as item #6)
**Action:** UPDATE (consolidate with item #6)
**Source:** [Impl]

This is covered in item #6 above. The key insight is documented in the tripwire: use regex patterns for verification, not literal strings.

---

#### 12. Implementation Terminology Migration

**Location:** `docs/learned/planning/impl-context.md` (same as item #1)
**Action:** UPDATE (consolidate with item #1)
**Source:** [PR #8326]

Update terminology from `.impl/` to "implementation folder" or "implementation directory" where referring to the generic concept. Keep specific paths when discussing legacy support.

---

## Contradiction Resolutions

### 1. setup_impl_from_issue.py Reference

**Existing doc:** `docs/learned/planning/impl-context.md`
**Conflict:** References `src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py` at lines 43, 48, 68, 72, and 202, but this file does not exist
**Resolution:** This is a phantom reference, not a contradiction between two valid sources. The file was consolidated into `setup_impl.py` during the objective #8197 work. Update all five references to point to `src/erk/cli/commands/exec/scripts/setup_impl.py` and verify the referenced content (the "deliberate non-deletion" comment) exists in the correct location.

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Literal Search Miss

**What happened:** Initial grep for `git add .erk` found 0 results, suggesting the pattern had been fully migrated.
**Root cause:** Literal string search missed `git add -f .erk` (the correct pattern with force flag).
**Prevention:** Use regex patterns for verification: `git add.*\.erk` catches all variations.
**Recommendation:** ADD_TO_DOC (covered in verification-patterns.md)

### 2. Pre-Existing Prettier Failures

**What happened:** CI failed on Prettier formatting for 3 files: `.impl/plan.md`, `docs/learned/integrations/github-review-decision.md`, `docs/learned/tui/status-indicators.md`.
**Root cause:** The first is immutable per erk conventions; the other two were pre-existing issues not introduced by this PR.
**Prevention:** Cross-reference CI failure paths against `git diff --name-only HEAD` before debugging.
**Recommendation:** TRIPWIRE (covered in ci-iteration.md tripwire addition)

### 3. Session ID Signal Failure

**What happened:** `impl-signal started` failed with `session-id-required` error.
**Root cause:** `${CLAUDE_SESSION_ID}` substitution potentially affected by stderr redirect context.
**Prevention:** Non-blocking in this case (marked with `|| true`). If critical, test without redirects.
**Recommendation:** CONTEXT_ONLY (already documented in session-id-substitution.md)

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. CI Force-Add Gitignored Directories

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before staging gitignored directories in CI workflows
**Warning:** "Use `git add -f` to force-add. Without `-f`, git silently skips gitignored files and the commit appears to succeed but content is missing."
**Target doc:** `docs/learned/ci/plan-implement-workflow-patterns.md`

This is highly tripwire-worthy because the failure is completely silent. The `git add` command succeeds, the commit succeeds, everything appears to work - but the gitignored files are simply not included. The only symptom is missing content in the resulting commit, which can take significant debugging to trace back to the missing `-f` flag.

### 2. Pre-Existing CI Failure Triage

**Score:** 4/10 (criteria: Non-obvious +2, Cross-cutting +2)
**Trigger:** When CI fails
**Warning:** "ALWAYS run `git diff --name-only HEAD` first to distinguish new issues from pre-existing failures. Cross-reference failure file paths against changed files."
**Target doc:** `docs/learned/ci/ci-iteration.md`

This pattern is valuable because agents can waste significant time debugging failures that have nothing to do with their changes. The simple check of comparing failure paths against changed files immediately filters out inherited problems.

### 3. Session ID Substitution with Stderr Redirects

**Score:** 4/10 (criteria: Non-obvious +2, External tool quirk +1, Repeated pattern +1)
**Trigger:** When using ${CLAUDE_SESSION_ID} with stderr redirects
**Warning:** "Stderr redirects may interfere with session ID substitution. If non-critical, use `|| true`. If critical, test without redirect first."
**Target doc:** `docs/learned/commands/session-id-substitution.md`

The existing doc covers session ID substitution well, but this specific interaction with stderr redirects was discovered during this implementation and warrants a tripwire note.

---

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Dead Code Removal Verification

**Score:** 3/10 (criteria: Non-obvious +2, Repeated pattern +1)
**Notes:** The pattern of grepping the entire codebase before removing "dead" code is good practice but not cross-cutting enough to warrant a tripwire. It's refactoring-specific. Could elevate if the pattern repeats as a source of problems.

### 2. Regex Grep for Verification Completeness

**Score:** 2/10 (criteria: Non-obvious +2)
**Notes:** This is a testing/verification pattern that was learned from one failed attempt. It's valuable documentation but not yet proven to be a recurring problem worthy of tripwire status.
