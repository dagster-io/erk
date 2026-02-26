# Documentation Plan: Complete CLI consolidation: move erk plan subcommands under erk pr

## Context

This PR completes Phase 4 of the CLI consolidation journey, moving all `erk plan` subcommands under `erk pr`. The work touched 44 files across the documentation tree, updating command references, file paths, flag syntax, and help text. No new functionality was added—this is purely a documentation synchronization effort following the code reorganization completed in prior phases.

The implementation session revealed two significant patterns worth documenting. First, a critical shell escaping issue emerged when piping JSON to `erk exec` commands: the common `echo '[...]' | command` pattern silently fails due to shell interpretation of special characters. The HEREDOC solution (`cat <<'JSONEOF'`) prevents these parse errors. Second, the PR review surfaced 7 documentation violations from stale references—functions that were renamed during refactoring but still referenced in docs. This 64% violation rate from a single root cause suggests a systematic gap in the post-refactoring workflow.

Future agents benefit most from understanding: (1) the HEREDOC pattern for piping complex JSON, (2) the post-refactoring documentation audit workflow that would have prevented 7 of 11 review threads, and (3) the complete command mapping for the consolidated CLI structure. The CLI consolidation itself is now complete and documented in-place; the learn work focuses on cross-cutting patterns that apply beyond this specific migration.

## Raw Materials

PR #8226 - Complete CLI consolidation: move erk plan subcommands under erk pr

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 11     |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4)  | 2     |
| Potential tripwires (score 2-3) | 3     |

## Stale Documentation Cleanup

Existing docs with phantom references requiring immediate action:

### 1. Phantom Command Reference in Ambiguity Resolution

**Location:** `docs/learned/cli/ambiguity-resolution.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `erk plan co` (command no longer exists)
**Cleanup Instructions:** Replace all occurrences of `erk plan co` with `erk pr checkout` or `erk pr co`. The command namespace migration is complete; the old `plan` namespace no longer exists.

### 2. Outdated Command in CLI Tripwires

**Location:** `docs/learned/cli/tripwires.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** "plan list" without proper namespace
**Cleanup Instructions:** Update to `erk pr list` for consistency with the consolidated CLI structure. Search for any remaining `plan` command references and update to the `erk pr` namespace.

## Documentation Items

### HIGH Priority

#### 1. Post-Refactoring Documentation Audit Checklist

**Location:** `docs/learned/refactoring/post-refactor-documentation-audit.md`
**Action:** CREATE
**Source:** [PR #8226] - 7 of 11 review threads stemmed from stale documentation references

**Draft Content:**

```markdown
---
title: Post-Refactoring Documentation Audit
read_when:
  - completing a refactoring that renames, moves, or deletes code
  - finishing any PR that changes function names, file paths, or command names
  - reviewing documentation before submitting a refactoring PR
tripwires:
  - action: "completing a refactoring that renames, moves, or deletes code"
    warning: "Run documentation audit checklist: grep for stale references, update source pointers, verify all paths resolve. See post-refactor-documentation-audit.md"
---

# Post-Refactoring Documentation Audit

After any refactoring that changes identifiers (file paths, function names, command names, class names), run this systematic audit to prevent stale documentation references.

## Why This Matters

In PR #8226, 64% of review violations (7 of 11) stemmed from stale documentation references—functions renamed during refactoring but still referenced in docs. A 10-minute audit would have prevented these.

## Audit Checklist

### Step 1: Identify Changed Identifiers

Before auditing, list all identifiers that changed:
- File paths (moved or renamed files)
- Function/method names (renamed functions)
- Class names (renamed classes)
- Command names (CLI commands that changed)
- Flag names (CLI flags that changed syntax)

### Step 2: Grep Documentation for Old Identifiers

For each changed identifier:

```bash
# File paths
rg "old/path/name" docs/

# Function names
rg "old_function_name" docs/

# Source comments (critical - these are machine-checked)
rg "<!-- Source:.*old_identifier" docs/
```

### Step 3: Update Found References

For each match:
1. Verify the new identifier exists
2. Update the reference to the new identifier
3. If using source pointers, update both HTML comment AND prose reference

### Step 4: Verify No Stale References Remain

```bash
# Final verification - should return no results
rg "old_identifier" docs/
```

## Common Pitfalls

- **Partial updates**: Updating prose but forgetting HTML source comments
- **Skills overlooked**: `.claude/skills/` contains documentation that also needs updating
- **Help text**: `src/erk/cli/` error messages and help text reference other commands
- **Test fixtures**: Test data may contain documentation that needs updating

## Related Documentation

See `docs/learned/documentation/source-pointers.md` for the source pointer format.
See `docs/learned/commands/command-rename-pattern.md` for CLI-specific migration patterns.
```

---

#### 2. HEREDOC JSON Piping Pattern

**Location:** `docs/learned/pr-operations/json-piping-patterns.md`
**Action:** CREATE
**Source:** [Impl] - Session discovered this after JSON parse failure

**Draft Content:**

```markdown
---
title: JSON Piping Patterns for Erk Exec
read_when:
  - piping JSON data to erk exec commands
  - using erk exec resolve-review-threads
  - encountering JSON parse errors with erk exec
tripwires:
  - action: "piping JSON data to erk exec commands via echo"
    warning: "Use HEREDOC syntax (cat <<'JSONEOF') instead of echo to prevent shell escaping issues. See json-piping-patterns.md"
---

# JSON Piping Patterns for Erk Exec

When piping JSON data to `erk exec` commands, shell escaping can silently corrupt the input. This document explains the HEREDOC pattern that prevents these failures.

## The Problem

The intuitive approach fails silently:

```bash
# WRONG - shell escaping corrupts JSON with complex data
echo '[{"thread_id": "abc", "comment": "Fixed in commit abc123"}]' | erk exec resolve-review-threads
```

When JSON contains nested quotes, special characters, or multi-line strings, the shell interprets these before the command receives them. The result: the command receives empty or malformed input and may appear to succeed while doing nothing.

## The Solution: HEREDOC Syntax

Use the HEREDOC pattern to preserve JSON exactly:

```bash
cat <<'JSONEOF' | erk exec resolve-review-threads
[
  {"thread_id": "abc123", "comment": "Fixed in commit abc123"},
  {"thread_id": "def456", "comment": "Updated per review feedback"}
]
JSONEOF
```

Key points:
- The `'JSONEOF'` quotes prevent shell variable expansion
- Multi-line JSON is preserved exactly
- No escaping of internal quotes required

## When to Use HEREDOC

| Input Type | Recommendation |
|------------|----------------|
| Simple string, no special chars | `echo` is fine |
| JSON with nested quotes | Use HEREDOC |
| Multi-line JSON | Use HEREDOC |
| JSON with `$` or backticks | Use HEREDOC (quoted delimiter) |

## Debugging JSON Parse Errors

If you see `Expecting value: line 1 column 1 (char 0)`, the command received empty input. This means shell escaping consumed the data. Switch to HEREDOC.
```

---

#### 3. CLI Command Organization Update

**Location:** `docs/learned/cli/command-organization.md`
**Action:** UPDATE
**Source:** [PR #8226] - All plan commands now under `erk pr`

**Draft Content:**

Update the existing document to reflect the consolidated structure. Key changes:

1. **Update command hierarchy table**: All plan-related operations are now under `erk pr`:
   - `erk pr list` (was `erk plan list`)
   - `erk pr check` (was `erk plan check`)
   - `erk pr co` / `erk pr checkout` (was `erk plan co`)
   - `erk pr close` (was `erk plan close`)
   - `erk pr dispatch` (was `erk plan submit`)

2. **Add consolidation rationale**: The `erk plan` namespace was removed because:
   - Plans are stored as GitHub issues, managed via PR-like workflows
   - Reducing command surface area improves discoverability
   - Single namespace for all PR/issue operations reduces confusion

3. **Update decision framework examples**: Replace references to split namespaces with consolidated examples

4. **Add historical note**: Document that the consolidation completed in PR #8226 as part of Objective #7978

---

#### 4. Source Path Update Pattern

**Location:** `docs/learned/documentation/source-path-updates.md`
**Action:** CREATE
**Source:** [PR #8226] - 40+ files required file path updates

**Draft Content:**

```markdown
---
title: Source Path Updates During Refactoring
read_when:
  - refactoring that moves source files to new directories
  - updating documentation after file path changes
  - planning a multi-file refactoring
tripwires:
  - action: "moving source files to new directories"
    warning: "Documentation references file paths in two places: source pointer HTML comments and prose references. Both need updating. See source-path-updates.md"
---

# Source Path Updates During Refactoring

When refactoring moves source files, documentation path references need systematic updating. This is distinct from command name changes—path updates affect developer-facing documentation while command changes affect user-facing documentation.

## Scope of Path References

Documentation references paths in:

1. **Source pointer HTML comments**: `<!-- Source: old/path/file.py, ClassName -->`
2. **Prose references**: "See `ClassName` in `old/path/file.py`"
3. **Import examples**: `from erk.old.path import something`
4. **Directory structure diagrams**: ASCII trees showing file organization

## Grep Strategy for Path Updates

```bash
# Find all references to old directory
rg "old/path/" docs/

# Find source pointer comments specifically
rg "<!-- Source:.*old/path" docs/

# Find import statements
rg "from erk\.old\.path" docs/
```

## The Two-Step Update

For each source pointer, update BOTH parts:

1. **HTML comment**: `<!-- Source: new/path/file.py, ClassName -->`
2. **Prose reference**: "See `ClassName` in `new/path/file.py`"

Updating only one creates a mismatch that confuses both automated tools and human readers.

## Case Study: CLI Commands Consolidation (PR #8226)

Path change: `src/erk/cli/commands/plan/` → `src/erk/cli/commands/pr/`
Test path: `tests/commands/plan/` → `tests/commands/pr/`

This required updating 40+ documentation files across architecture, CLI, planning, and reference categories.

## Validation

After updating, verify no stale paths remain:

```bash
# Should return no results
rg "commands/plan/" docs/
```
```

---

#### 5. Fix Phantom Command References (Stale Cleanup)

**Location:** `docs/learned/cli/ambiguity-resolution.md`, `docs/learned/cli/tripwires.md`
**Action:** UPDATE_REFERENCES
**Source:** [PR #8226] - Stale reference warnings from existing docs checker

**Cleanup Instructions:**

1. In `ambiguity-resolution.md`: Replace `erk plan co` with `erk pr checkout` or `erk pr co`
2. In `tripwires.md`: Update "plan list" to `erk pr list`
3. Grep for any remaining `erk plan` command references in these files and update to `erk pr` namespace

---

### MEDIUM Priority

#### 6. PlanContext Field Name Confusion

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Source:** [PR #8226] - Field name violation in output-styling.md

**Draft Content:**

Add a tripwire entry to prevent common field name confusion:

```markdown
- action: "accessing plan_context issue number"
  warning: "Use plan_context.plan_id, NOT plan_context.issue_number. The correct field is plan_id. See PlanContext dataclass in src/erk/core/plan_context.py"
```

---

#### 7. CLI File Naming Convention

**Location:** `docs/learned/cli/tripwires.md`
**Action:** UPDATE
**Source:** [PR #8226] - view.py vs view_cmd.py violation

**Draft Content:**

Strengthen the existing file naming convention:

```markdown
- action: "creating a new command file in src/erk/cli/commands/"
  warning: "All command files MUST use *_cmd.py suffix (e.g., view_cmd.py, not view.py). This distinguishes command modules from support modules."
```

---

#### 8. Verbatim Code Signature Drift Examples

**Location:** `docs/learned/documentation/tripwires.md`
**Action:** UPDATE
**Source:** [PR #8226] - 2 review threads about missing parameters in code examples

**Draft Content:**

Add a "Common Violations" subsection:

```markdown
## Common Verbatim Code Violations

### Signature Drift

Method signatures change but documentation examples still show old signatures:

- **Symptom**: Code example shows `foo(a, b)` but actual method is `foo(a, b, *, verbose: bool)`
- **Root cause**: Copied the signature when documenting, then signature evolved
- **Prevention**: Use source pointers instead of copying signatures

### Detection Pattern

Any documentation code block containing a function call to erk source should be a source pointer. Grep for code blocks with `def ` or method calls to erk modules.
```

---

#### 9. Batch Thread Resolution Workflow

**Location:** `docs/learned/pr-operations/thread-resolution.md`
**Action:** CREATE or UPDATE (check if exists)
**Source:** [Impl] - Complete workflow executed in session

**Draft Content:**

```markdown
---
title: Batch Thread Resolution Workflow
read_when:
  - addressing PR review comments
  - using /erk:pr-address command
  - resolving multiple review threads at once
---

# Batch Thread Resolution Workflow

This document describes the complete workflow for addressing PR review comments efficiently using batch operations.

## The /erk:pr-address Workflow

1. **Load skill**: `pr-operations` skill provides thread resolution context
2. **Classify feedback**: Use classifier to group threads by complexity
3. **Display execution plan**: Review batches before making changes
4. **Read affected files**: Understand context for each fix
5. **Make fixes**: Apply all changes for each batch
6. **Run CI checks**: Verify formatting and lint
7. **Commit changes**: Single commit for all fixes in batch
8. **Batch resolve threads**: Use `erk exec resolve-review-threads` with HEREDOC (see json-piping-patterns.md)
9. **Reply to discussion comments**: Address non-actionable comments
10. **Update PR description**: Reflect completed work
11. **Verify**: Run classifier again to confirm zero remaining threads

## Batch Resolution Command

Use HEREDOC for the JSON array:

```bash
cat <<'JSONEOF' | erk exec resolve-review-threads
[
  {"thread_id": "...", "comment": "Fixed in commit abc123"},
  {"thread_id": "...", "comment": "Updated per feedback"}
]
JSONEOF
```

See `json-piping-patterns.md` for why HEREDOC is required.
```

---

#### 10. Plan Terminology Clarification

**Location:** `docs/learned/glossary.md`
**Action:** UPDATE
**Source:** [PR #8226] - Terminology confusion after consolidation

**Draft Content:**

Add or update glossary entries to clarify:

```markdown
## Plan

A GitHub issue containing an implementation specification created through erk's planning workflow. Plans are backend-agnostic concepts—the planning workflow applies regardless of which AI agent executes the implementation.

**Note**: Prior to the CLI consolidation (PR #8226), plans were managed via `erk plan` commands. All plan operations are now under `erk pr` (e.g., `erk pr list`, `erk pr dispatch`). The CLI namespace changed but the underlying concept remains the same.

## erk pr

The CLI command group for managing GitHub issues and pull requests, including plan operations. This is the command namespace, not the conceptual domain.

Commands: `erk pr list`, `erk pr check`, `erk pr checkout`, `erk pr close`, `erk pr dispatch`
```

---

### LOW Priority

#### 11. Source Comment Validation Pattern

**Location:** `docs/learned/documentation/tripwires.md`
**Action:** UPDATE
**Source:** [Impl] - Documentation source auditing pattern discovered

**Draft Content:**

Add to existing "One Code Rule" or documentation tripwires:

```markdown
- action: "refactoring functions referenced in documentation source comments"
  warning: "After refactoring, grep docs/ for `<!-- Source:` comments and validate all referenced functions/files still exist"
```

Include validation command:

```bash
# After refactoring, validate source comments
rg "<!-- Source:" docs/ | while read line; do
  # Extract path and verify it exists
  path=$(echo "$line" | sed 's/.*Source: \([^,]*\).*/\1/')
  if [[ ! -f "$path" ]]; then
    echo "STALE: $line"
  fi
done
```

---

## Contradiction Resolutions

**No contradictions found.**

The existing documentation consistently described the pre-consolidation state (`erk plan` commands). The consolidation represents an architectural evolution, not a contradiction with existing guidance. The primary update is to `docs/learned/cli/command-organization.md` to reflect the new consolidated structure.

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. JSON Parse Failure with Echo Piping

**What happened:** `echo '[{...}]' | erk exec resolve-review-threads` produced JSON parse error "Expecting value: line 1 column 1 (char 0)"

**Root cause:** Shell escaping consumed special characters in the JSON string before the command received it. The command received empty input.

**Prevention:** Always use HEREDOC syntax (`cat <<'JSONEOF'`) for piping JSON to erk exec commands

**Recommendation:** TRIPWIRE - This is a silent failure pattern that affects all erk exec commands accepting JSON input

### 2. Model Fallback Error (haiku to sonnet)

**What happened:** Task tool called with `model: "haiku"` returned 404 error for model "sonnet"

**Root cause:** Model ID mapping changed or model unavailable in current environment

**Prevention:** When Task tool fails with 404 model error, immediately retry with `model: "sonnet"`

**Recommendation:** SHOULD_BE_CODE - This belongs in capabilities configuration, not documentation. The model selection logic should handle fallbacks automatically.

### 3. Stale Documentation References After Refactoring

**What happened:** 7 of 11 PR review threads flagged stale function/path references in documentation

**Root cause:** Functions were renamed during refactoring but documentation `<!-- Source:` comments and prose references weren't updated

**Prevention:** Run documentation audit checklist after completing any refactoring

**Recommendation:** TRIPWIRE - This is a systematic gap in the post-refactoring workflow affecting all documentation

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. HEREDOC JSON Piping Pattern

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before piping JSON data to erk exec commands
**Warning:** Use HEREDOC syntax (`cat <<'JSONEOF'`) instead of echo to prevent shell escaping issues. See json-piping-patterns.md
**Target doc:** `docs/learned/pr-operations/tripwires.md`

This is tripwire-worthy because the failure is completely silent—the command appears to succeed but processes empty input. The error message ("Expecting value: line 1 column 1") doesn't clearly indicate shell escaping as the cause. This pattern affects all erk exec commands that accept JSON input, making it cross-cutting.

### 2. Post-Refactoring Documentation Audit

**Score:** 5/10 (Non-obvious +2, Cross-cutting +2, Repeated pattern +1)
**Trigger:** After completing a refactoring that renames, moves, or deletes code
**Warning:** Run documentation audit checklist: grep for stale references, update source pointers, verify all paths resolve. See post-refactor-documentation-audit.md
**Target doc:** `docs/learned/refactoring/tripwires.md`

This is tripwire-worthy because it's easy to forget documentation when focused on code changes, yet 64% of review violations in this PR stemmed from this single cause. The pattern applies to all refactoring work across the codebase.

---

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. PlanContext Field Name Confusion

**Score:** 3/10 (Non-obvious +2, Repeated pattern +1)
**Notes:** Specific to planning domain; may not be cross-cutting enough for a general tripwire. Consider promoting if confusion recurs in future sessions. Currently documented as a planning-specific tripwire in `docs/learned/planning/tripwires.md`.

### 2. CLI File Naming Convention

**Score:** 3/10 (Non-obvious +2, Repeated pattern +1)
**Notes:** Specific to CLI module structure. Good candidate for CLI-specific tripwire (already appropriate for that category). Not cross-cutting enough for universal tripwires.

### 3. Source Comment Validation

**Score:** 3/10 (Cross-cutting +2, Repeated pattern +1)
**Notes:** Overlaps significantly with the post-refactoring audit tripwire. Better as an enhancement to existing documentation tripwires rather than a separate tripwire. The audit checklist covers this case.

---

## Implementation Sequence

**Recommended order:**

1. **FIRST** - Fix stale references (items in Stale Documentation Cleanup) - prevents confusion, 5 minutes
2. **SECOND** - Create post-refactoring checklist (item #1) - highest impact, 15 minutes
3. **THIRD** - Document HEREDOC pattern (item #2) - prevents high-severity errors, 15 minutes
4. **FOURTH** - Update CLI command organization (item #3) - primary architectural doc, 15 minutes
5. **FIFTH** - Create source path update pattern (item #4) - complements audit checklist, 15 minutes
6. **SIXTH** - Medium priority tripwire updates (items #6-10) - incremental improvements, 45 minutes
7. **LAST** - Low priority enhancement (item #11) - polish existing docs, 10 minutes

**Cross-document dependencies:**
- Post-refactoring checklist should reference `docs/learned/commands/command-rename-pattern.md`
- HEREDOC pattern should be added to `docs/learned/pr-operations/tripwires.md`
- CLI organization update should note migration history (link to PR #8226)
- Terminology clarification in glossary should link to updated `command-organization.md`

---

## Verification Checklist

After implementing this plan:

- [ ] No phantom references remain (grep for `erk plan co`, check tripwires.md)
- [ ] HEREDOC pattern document created with working example
- [ ] Post-refactoring checklist validated against PR #8226 scope
- [ ] CLI organization doc reflects consolidated structure with rationale
- [ ] Source path update pattern includes grep examples
- [ ] All tripwire additions include concrete trigger phrases
- [ ] Frontmatter updated for new docs (category, read-when, tripwires)
- [ ] Run `erk docs sync` to regenerate indices
