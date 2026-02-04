---
title: Documentation Audit Methodology
last_audited: "2026-02-04 05:48 PT"
audit_result: clean
read_when:
  - auditing documentation for quality
  - cleaning up stale or incorrect docs
  - understanding harmful documentation patterns
tripwires:
  - action: "documenting type definitions without verifying they exist"
    warning: "Type references in docs must match actual codebase types. Run type verification before committing."
  - action: "bulk deleting documentation files"
    warning: "After bulk deletions, run 'erk docs sync' to fix broken cross-references."
  - action: "creating broad exclusion rules in doc-audit classification"
    warning: "Broad exclusion rules need explicit exceptions. Constants and defaults in prose are HIGH VALUE context, not DUPLICATIVE. Add exception rules with rationale."
---

# Documentation Audit Methodology

This document describes the systematic process for auditing learned documentation in `docs/learned/` for quality, correctness, and value. The methodology has been proven through three major audit PRs that cleaned up 20+ documents and removed 553 lines of problematic content.

## Three-Step Audit Process

### Step 1: Type Definition Verification

**Goal**: Ensure documented types actually exist in the codebase.

**Process**:

1. Extract all type references from documentation (class names, dataclass names, enum names)
2. Search for each type in `src/erk/` and `packages/` directories
3. Flag types that don't exist in the codebase
4. Verify field names match actual implementations

**Why it matters**: Documenting phantom types misleads users and creates maintenance burden when the non-existent types can't be found.

**Example violations** (from PR #6660):

- `SessionContext` - documented but never implemented
- `ObjectiveMetadata.steps` - field doesn't exist in actual ObjectiveMetadata
- `PlanStatus` - documented as enum but implementation uses string literals

**Concrete results**: PR #6660 removed 11 phantom type definitions from 10 documents.

### Step 2: Link Validation

**Goal**: Ensure cross-references point to files that exist.

**Process**:

1. Extract all markdown links from documentation
2. Resolve relative paths based on link context
3. Check if target files exist
4. Flag broken links

**Why it matters**: Broken links frustrate readers and signal documentation drift.

**Example violations** (from PRs #6660, #6666):

- Links to deleted files (e.g., `gitlab-ci-integration.md` after GitLab support was removed)
- Wrong directory paths (e.g., `review/reviews.md` instead of `ci/convention-based-reviews.md`)
- Outdated file names after refactoring

**Concrete results**: PRs #6660 and #6666 fixed 40+ broken cross-reference paths.

### Step 3: Path Verification

**Goal**: Ensure documented file paths match actual codebase structure.

**Process**:

1. Extract all file path references from code blocks and inline code
2. Verify paths exist in the repository
3. Check line number references against current files
4. Flag incorrect or outdated paths

**Why it matters**: Wrong paths send readers to non-existent files or wrong locations.

**Example violations**:

- `src/erk/config.py` documented when actual file is `src/erk/config/core.py`
- Line numbers that are off by 10+ lines due to code changes
- References to files that were moved or renamed

**Pattern**: If a path appears in inline code or a code block, verify it exists before merge.

## Harmful Documentation Categories

Documentation can cause harm in three ways:

### Category 1: Drifted Documentation

**Definition**: Documentation that was accurate when written but has become incorrect due to code changes.

**Characteristics**:

- Describes implementation details that have changed
- References file paths or line numbers that are now wrong
- Documents APIs that have been refactored

**Why harmful**: Misleads users with outdated information. They waste time trying code that doesn't work or looking in wrong files.

**Solution**: Remove drifted sections entirely or update with source pointers to current implementation.

**Example** (from PR #6666):

```diff
- The GitContext class (src/erk/git/context.py) provides git operations.
+ Git operations are provided through the GitGateway ABC (see src/erk/gateway/git_gateway.py).
```

### Category 2: Contradictory Documentation

**Definition**: Documentation that directly conflicts with the actual implementation.

**Characteristics**:

- Documents features that don't exist
- Shows function signatures that don't match actual code
- Describes behavior opposite to what code does

**Why harmful**: Actively breaks user trust. When docs say one thing and code does another, users don't know what to believe.

**Solution**: Remove contradictions immediately. Either fix to match reality or delete the section.

**Example** (from PR #6660):

```diff
- The `--parallel` flag runs operations concurrently across worktrees.
  (REMOVED - flag was never implemented)
```

### Category 3: Outdated Documentation

**Definition**: Documentation about features or patterns that no longer exist.

**Characteristics**:

- Documents removed features
- References deprecated commands or APIs
- Describes old workflows that have been replaced

**Why harmful**: Confuses users who try to use features that don't exist. Creates noise in search results.

**Solution**: Delete entirely. Don't leave fossils.

**Example** (from PR #6666):

```diff
- ## GitLab Integration
-
- The GitLab integration allows erk to work with GitLab repositories...
  (REMOVED - GitLab support was removed in favor of GitHub-only)
```

## Source-of-Truth Pattern for Dynamic Content

**Problem**: Some documentation describes content that changes frequently (e.g., list of available commands, configuration options, dataclass fields).

**Anti-pattern**: Manually maintaining these lists in docs. They drift immediately.

**Pattern**: Use source pointers instead of duplication.

### When to Use Source Pointers

Use source pointers (not documentation) for:

1. **Configuration schemas** - Point to Pydantic models

   ```markdown
   See `InteractiveClaudeConfigSchema` in `src/erk_shared/config/schema.py:31` for available fields.
   ```

2. **Dataclass fields** - Point to actual definition

   ```markdown
   See `RoadmapStep` dataclass in `objective_roadmap_shared.py:15-22` for field definitions.
   ```

3. **Command lists** - Point to CLI registration

   ```markdown
   See `src/erk/cli/commands/objective/*.py` for available objective commands.
   ```

4. **Gateway methods** - Point to ABC
   ```markdown
   See `GitGateway` ABC in `src/erk/gateway/git_gateway.py` for required methods.
   ```

### When to Document (Not Point)

Document (don't just point) for:

1. **Why decisions** - Code can't express rationale
2. **Tradeoffs** - Alternatives that were considered
3. **Cross-cutting patterns** - How components interact
4. **Mental models** - Conceptual frameworks for understanding
5. **Usage patterns** - How to use APIs effectively

**Key distinction**: If the information is **derivable from code** (what fields exist, what parameters a function takes), use a pointer. If it's **insight about the code** (why this design, when to use this pattern), write documentation.

## Audit Metrics (Historical)

These metrics demonstrate the audit methodology's effectiveness:

### PR #6637 (First Audit)

- Files modified: 8 docs
- Lines removed: 156
- Issues fixed: Consolidated duplicate learn-pipeline docs, removed outdated session patterns

### PR #6660 (Phantom Types)

- Files modified: 10 docs
- Phantom types removed: 11
- Broken paths fixed: 8
- Lines removed: ~200

### PR #6666 (Doc Simplification)

- Files modified: 10 docs (HIGH/MODERATE priority)
- Lines removed: 197 (from simplification)
- Broken paths fixed: 32
- Content clarified: 10 docs

**Total impact**: 553 lines of problematic documentation removed, 40+ broken references fixed, 20+ documents improved.

## Classification Edge Cases

### Constants and Defaults in Prose

**Classification**: HIGH VALUE, not DUPLICATIVE

**Rationale**: When documentation explains "what value is used by default" or "what constant controls this behavior," it provides scannable context that is hard to extract from code.

**Example**:

```markdown
The default machine type for codespace creation is `basicLinux32gb`.
```

This is HIGH VALUE because:

- Requires grep/search to find in code
- Provides immediate answer to "what's the default?"
- Serves as an index to the codebase, not a duplicate of it

**Key distinction**: Scannability vs code duplication.

- **DUPLICATIVE**: Re-expressing what the code already says clearly (field names, parameter types, class hierarchies)
- **HIGH VALUE**: Surfacing defaults and constants that require navigation to find

**Related**: [Doc Audit Review](../review/doc-audit-review.md) - Constants and defaults exception section

## Integration with Doc Audit Review

The audit methodology pairs with the automated doc-audit review:

1. **Manual audit** (this methodology) - Systematic cleanup of existing docs
2. **Automated review** (doc-audit-review.md) - Prevents new problematic docs at PR time

Together they maintain documentation quality: audits clean up the past, reviews prevent future problems.

## Related Documentation

- [doc-audit-review.md](../review/doc-audit-review.md) - Automated quality checking
- [simplification-patterns.md](simplification-patterns.md) - Specific patterns for reducing duplication
- [learned-docs-review.md](../review/learned-docs-review.md) - Verbatim code detection
- `docs/learned/documentation/tripwires.md` - Tripwires for doc quality
