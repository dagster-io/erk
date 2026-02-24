# Inference hoisting: exec script error-first patterns and doc workflow gaps

## Context

This plan implements documentation and process improvements discovered while refactoring three exec scripts (`plan_save.py`, `setup_impl_from_issue.py`, `plan_migrate_to_draft_pr.py`) to eliminate nested LLM calls. The core pattern documentation (inference-hoisting.md) was already created and merged as part of PR #8002, establishing the critical architectural boundary where all LLM reasoning must happen in the skill orchestration layer, not in exec scripts.

The primary work of this learn plan focuses on **process improvements to the documentation and testing workflows themselves**. The PR review cycle revealed systematic gaps: silent frontmatter validation failures caused confusion, test coverage requirements for new CLI parameters were not enforced, and documentation quality checks (completeness verification, verbatim code detection) caught issues late in the review cycle. These meta-improvements will prevent similar friction in future sessions.

Why does this documentation matter? Future agents working with exec scripts, documentation workflows, or testing patterns will benefit from explicit tripwires and workflow guidance. The "error-first over fallback" philosophy discovered during PR review is a cross-cutting principle that applies beyond inference hoisting to all exec script development.

## Raw Materials

PR #8002

## Summary

| Metric | Count |
|--------|-------|
| Documentation items | 7 |
| Contradictions to resolve | 0 |
| Tripwire candidates (score >= 4) | 3 |
| Potential tripwires (score 2-3) | 3 |

## Documentation Items

### HIGH Priority

#### 1. Silent fallback prohibition in exec scripts

**Location:** `docs/learned/universal-tripwires.md`
**Action:** UPDATE
**Source:** [PR #8002]

The reviewer explicitly rejected deterministic fallbacks: "do NOT encourage deterministic fallback. prefer clear error messages on llm failures." This is a universal principle affecting all exec scripts. Violating it prevents agents from learning correct patterns and makes debugging harder.

**Draft Content:**

```markdown
## Exec Script Error-First Requirements

### FORBIDDEN: Silent fallbacks on missing LLM inputs

When exec scripts receive optional parameters that should come from LLM-generated values (e.g., branch slugs, plan summaries), they must NOT silently fall back to deterministic alternatives.

**Why**: Silent transformation masks mistakes and prevents agents from learning correct patterns. The skill layer should generate these values; if they're missing, it indicates a workflow problem that should be surfaced, not hidden.

**Pattern**: Error with clear remediation instructions:

See `src/erk/cli/commands/exec/scripts/plan_save.py` for implementation - grep for `if not branch_slug:` to find the error handling pattern.

**Related**: See `docs/learned/architecture/inference-hoisting.md` and `docs/learned/architecture/agent-backpressure-gates.md` for the full philosophy.
```

#### 2. Test coverage requirement for CLI parameters

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [PR #8002]

PR review automation flagged missing test coverage multiple times. This is a cross-cutting pattern: all new CLI parameters need comprehensive test cases.

**Draft Content:**

```markdown
## CLI Parameter Test Coverage

### REQUIRED: Both "provided" and "missing/error" test cases

When adding new CLI options (Click parameters) to exec scripts or commands, you must add test cases for both:

1. **Provided case** (`test_*_<param>_provided`): Parameter is passed, verify it's used correctly
2. **Missing/error case** (`test_*_missing_errors`): Parameter is missing when required, verify clear error message

**Why**: Ensures both happy path and error handling are tested. The error path is particularly important for exec scripts that require LLM-generated inputs.

**Example naming pattern**:
- `test_plan_save_branch_slug_provided`
- `test_plan_save_branch_slug_missing_errors`

See test files in `tests/unit/cli/commands/exec/scripts/` for examples - grep for `--branch-slug` to find the test patterns.
```

#### 3. Error-first philosophy cross-reference

**Location:** `docs/learned/architecture/agent-backpressure-gates.md`
**Action:** UPDATE
**Source:** [Impl]

The inference hoisting work provides a concrete example of the backpressure gates philosophy. Add a cross-reference to strengthen the connection between the abstract principle and concrete implementation.

**Draft Content:**

```markdown
## Concrete Examples

### Inference Hoisting (PR #8002)

The refactoring in `src/erk/cli/commands/exec/scripts/plan_save.py` (and related scripts) demonstrates backpressure gates in action:

- **Before**: Scripts silently fell back to `sanitize_worktree_name()` when `--branch-slug` was missing
- **After**: Scripts error with clear remediation: "Branch slug must be provided via --branch-slug. Generate it in the skill layer."

This teaches agents to include slug generation in skills, rather than silently producing suboptimal branch names.

See `docs/learned/architecture/inference-hoisting.md` for the full pattern.
```

### MEDIUM Priority

#### 4. Frontmatter validation workflow

**Location:** `docs/learned/documentation/frontmatter-validation.md`
**Action:** CREATE
**Source:** [Impl]

Session 2f3441d0 discovered that `erk docs sync` silently skips documents with invalid frontmatter. This non-obvious behavior caused confusion when a new document didn't appear in indexes.

**Draft Content:**

```markdown
---
title: Frontmatter Validation Workflow
read_when:
  - creating new documents in docs/learned/
  - running erk docs sync
  - document not appearing in generated indexes
tripwires:
  - action: "running erk docs sync after creating a new doc"
    warning: "Always run 'erk docs validate' immediately after creating a new doc in docs/learned/. Invalid frontmatter causes sync to silently skip the document."
    score: 4
last_audited: "2026-02-24 00:00 PT"
audit_result: clean
---

# Frontmatter Validation Workflow

## The Problem

`erk docs sync` silently skips documents with invalid frontmatter. This is intentional - it allows sync to continue processing valid documents - but it means invalid frontmatter causes documents to be silently omitted from indexes and tripwire files.

## The Workflow

When creating a new document in `docs/learned/`:

1. **Create the document** with frontmatter
2. **Immediately run `erk docs validate`** to check frontmatter validity
3. **Fix any validation errors** (the command shows specific issues)
4. **Then run `erk docs sync`** to regenerate indexes and tripwire files
5. **Verify the document appears** in the appropriate index.md

## Date/Time Format Requirements

The `last_audited` field requires format `YYYY-MM-DD HH:MM PT`, not just `YYYY-MM-DD PT`.

**Correct**: `last_audited: "2026-02-24 00:00 PT"`
**Incorrect**: `last_audited: "2026-02-24 PT"`

Use `00:00` for the time component if the exact audit time is unknown.

## Detecting Silent Skips

Check the `erk docs sync` output for:
- "Skipped N doc(s) with invalid frontmatter"

If documents are skipped, run `erk docs validate` to see detailed error messages.
```

#### 5. Completeness verification in documentation

**Location:** `docs/learned/documentation/tripwires.md`
**Action:** UPDATE
**Source:** [PR #8002]

PR review caught incomplete skill listings - the documentation claimed "all skills" but missed two of three. This undermines documentation trustworthiness.

**Draft Content:**

```markdown
## Documentation Accuracy

### REQUIRED: Verify "all X" claims

When documenting "all occurrences" of a pattern (e.g., "all skills that use this pattern", "all commands that accept this flag"), use grep/glob to verify completeness before writing.

**Why**: Inaccurate "all X" claims undermine documentation trustworthiness. Readers may miss important cases if the list is incomplete.

**Process**:
1. Before writing "all X", run a grep to find all occurrences
2. List them explicitly rather than saying "all"
3. If the list is dynamic, document how to find current occurrences

**Example**: When documenting "all skills with BRANCH_SLUG generation", grep for the pattern rather than manually listing.
```

#### 6. Verbatim code block detection

**Location:** `docs/learned/documentation/tripwires.md`
**Action:** UPDATE
**Source:** [PR #8002]

PR review flagged multiple instances of verbatim code copying into documentation. This causes drift when implementation changes.

**Draft Content:**

```markdown
### AVOID: Verbatim code blocks in docs/learned/

Before merging documentation PRs, grep for code blocks in `docs/learned/`. Prefer source pointers over verbatim code.

**Why**: Code blocks copied into documentation drift from the actual implementation. When code changes, the documentation becomes stale.

**Instead**: Use source pointers as documented in `docs/learned/documentation/source-pointers.md`:
- Prose describing what the code does
- File path references: "See `path/to/file.py`"
- grep patterns: "grep for `pattern` to find examples"
- Short illustrative snippets (5 lines max) are acceptable for patterns

**Enforcement**: Run `rg '```(python|bash)' docs/learned/` before merging doc PRs to identify potential drift risks.
```

#### 7. LLM turn optimization cross-reference

**Location:** `docs/learned/cli/slash-command-llm-turn-optimization.md`
**Action:** UPDATE
**Source:** [Impl]

The inference hoisting pattern is closely related to LLM turn optimization. Add a cross-reference for discoverability.

**Draft Content:**

```markdown
## Related Patterns

### Inference Hoisting

For the specific pattern of moving LLM calls from exec scripts to skills, see `docs/learned/architecture/inference-hoisting.md`. This is a concrete instance of turn optimization applied to the exec script architecture.

Key insight: Skills run within the Claude Code session context and can leverage LLM reasoning. Exec scripts run as subprocesses and cannot make nested LLM calls.
```

### LOW Priority

None - all items above MEDIUM were either covered by higher-priority items or already documented in the PR.

## Stale Documentation Cleanup

None identified. All referenced files in existing documentation were verified as present and current.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Silent frontmatter validation failures

**What happened:** New document created in `docs/learned/architecture/inference-hoisting.md` didn't appear in generated indexes after running `erk docs sync`. The `last_audited` field used format `2026-02-23 PT` instead of `2026-02-23 00:00 PT`.

**Root cause:** `erk docs sync` silently skips documents with invalid frontmatter. It reports "Skipped N doc(s)" but this is easy to miss.

**Prevention:** Run `erk docs validate` immediately after creating any new document in `docs/learned/`. This catches frontmatter issues before sync.

**Recommendation:** TRIPWIRE - Score 4, added to documentation/tripwires.md

### 2. Test coverage gaps for new CLI parameters

**What happened:** New `--branch-slug` options were added to three exec scripts, but test files weren't consistently updated. PR review automation flagged missing coverage.

**Root cause:** No explicit requirement for test cases when adding new CLI parameters.

**Prevention:** Require both "provided" and "missing/error" test cases for all new CLI options.

**Recommendation:** TRIPWIRE - Score 5, added to testing/tripwires.md

### 3. Silent fallbacks masking incorrect agent behavior

**What happened:** Initial implementation used `branch_slug if branch_slug else sanitize_worktree_name(title)` - a deterministic fallback when the LLM-generated slug was missing.

**Root cause:** Common Python pattern (provide sensible defaults) conflicts with agent backpressure philosophy.

**Prevention:** Exec scripts must error with clear remediation when LLM-generated inputs are missing. Never silently fall back.

**Recommendation:** TRIPWIRE - Score 7, added to universal-tripwires.md

### 4. Incomplete "all X" claims in documentation

**What happened:** Documentation said "the plan-save skill uses this pattern" but two other skills (plan-implement, migrate-plan-to-draft-pr) also used it and were missed.

**Root cause:** Manual listing without verification.

**Prevention:** Use grep to verify completeness before documenting "all occurrences" of any pattern.

**Recommendation:** TRIPWIRE - Score 3, added to documentation/tripwires.md

### 5. Verbatim code blocks drifting from implementation

**What happened:** PR review flagged multiple instances where code was copied verbatim into documentation. When implementation changes, these blocks become stale.

**Root cause:** Common documentation pattern (show the code) conflicts with erk's source-pointer philosophy.

**Prevention:** Use source pointers (prose + file paths) instead of verbatim code blocks. Follow `docs/learned/documentation/source-pointers.md`.

**Recommendation:** TRIPWIRE - Score 3, added to documentation/tripwires.md

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Silent fallback prohibition in exec scripts

**Score:** 7/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2, Repeated pattern +1)
**Trigger:** Before using fallback logic in exec scripts when optional parameters are missing
**Warning:** "Exec scripts must error with clear remediation instructions when LLM-generated inputs are missing. Never silently fall back to deterministic alternatives. Read agent-backpressure-gates.md and inference-hoisting.md."
**Target doc:** `docs/learned/universal-tripwires.md`

This principle was explicitly stated by the reviewer: "do NOT encourage deterministic fallback." It's the most important cross-cutting insight from this PR because it affects the design of all exec scripts that receive LLM-generated values. Without this tripwire, future implementations will default to the "sensible fallback" pattern that Python training data encourages.

### 2. Test coverage for new CLI parameters

**Score:** 5/10 (Cross-cutting +2, Repeated pattern +1, Non-obvious +2)
**Trigger:** Before merging new CLI command or option
**Warning:** "New CLI parameters require test coverage for both 'provided' and 'missing/error' cases. Use naming pattern: test_*_<param>_provided and test_*_<param>_missing_errors."
**Target doc:** `docs/learned/testing/tripwires.md`

PR automation caught this multiple times across three test files. The pattern is consistent enough to warrant a tripwire that reminds implementers to add both test cases.

### 3. Frontmatter validation workflow

**Score:** 4/10 (Non-obvious +2, Silent failure +2)
**Trigger:** Before running erk docs sync after creating a new doc
**Warning:** "Always run 'erk docs validate' immediately after creating a new doc in docs/learned/. Invalid frontmatter causes sync to silently skip the document."
**Target doc:** `docs/learned/documentation/tripwires.md`

The session spent multiple iterations debugging why the new document didn't appear in indexes. Running validate first would have caught the issue immediately.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Completeness verification

**Score:** 3/10 (Repeated pattern +1, Non-obvious +2)
**Notes:** Caught by PR automation but easy to miss during manual review. Could be promoted if more instances are found. The challenge is that "all X" claims are natural language patterns that are hard to detect automatically.

### 2. Verbatim code blocks in docs

**Score:** 3/10 (Cross-cutting +2, Repeated pattern +1)
**Notes:** The source-pointer pattern is already documented in `docs/learned/documentation/source-pointers.md`. This tripwire is about enforcement rather than documentation. Could be promoted if a pre-commit hook or CI check is added to detect code blocks in docs/learned/.

### 3. Nested LLM calls in exec scripts

**Score:** 3/10 (Non-obvious +2, Repeated pattern +1)
**Notes:** The inference-hoisting.md document already has score-9 tripwires for specific patterns (`PromptExecutor`, `generate_slug_or_fallback`, `BranchSlugGenerator`). This analysis identified that the *concept* of nested LLM calls is broader than those specific patterns, but the existing tripwires provide adequate coverage for the current codebase.

## Process Quality Observations

### What Worked Well

1. **Parallel exploration in planning session**: Session 8ade693d launched two Task agents simultaneously to understand implementation and documentation structure, reducing round trips.

2. **Validation-driven debugging**: Session 2f3441d0 ran `erk docs validate` when sync didn't work, identifying the exact frontmatter issue rather than guessing.

3. **Systematic file reading**: Implementation session read all related docs before writing, ensuring consistency.

4. **PR review automation**: Bot caught 13+ issues (code copying, test gaps, inaccurate claims) that human review might have missed.

5. **Clear reviewer guidance**: Explicit rejection of deterministic fallbacks clarified the design philosophy early enough to fix before merge.

### Process Gaps Addressed

All four gaps identified in the sessions have documentation solutions in this plan:

1. **Frontmatter validation not in standard workflow** - Item #4 creates the workflow doc
2. **Test coverage not enforced for new CLI params** - Item #2 adds testing tripwire
3. **Completeness verification not standard** - Item #5 adds documentation tripwire
4. **Code block drift not prevented** - Item #6 adds documentation tripwire

## Attribution Summary

| Source | Key Insights |
|--------|--------------|
| Session 2f3441d0 (implementation) | Frontmatter validation workflow, date format requirements, validation-first debugging |
| Session 5864ad33 (PR addressing) | Error-first philosophy, source pointer pattern, test coverage requirements |
| Session 8ade693d (planning) | Inference hoisting pattern, parallel exploration efficiency |
| Diff analysis | Complete inventory of changes (28 items, all accounted for) |
| PR comment analysis | Silent fallback rejection, completeness verification, code block drift |
