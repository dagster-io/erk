---
title: Documentation Simplification Patterns
read_when:
  - auditing or cleaning up documentation
  - removing duplication from docs
  - understanding what makes docs maintainable
tripwires:
  - action: "documenting implementation details that are derivable from code"
    warning: "Use source pointers instead of duplication. See simplification-patterns.md for patterns on replacing static docs with dynamic references."
last_audited: "2026-02-05"
audit_result: edited
---

# Documentation Simplification Patterns

This document captures three proven patterns for simplifying documentation, derived from audit PRs #6637, #6660, and #6666 which removed 553 lines of problematic content.

## Pattern 1: Static → Dynamic Replacement

**Problem**: Documentation duplicates information that already exists in code.

**Solution**: Replace static duplication with dynamic source pointers.

### Example 1: Configuration Fields

**Before** (static duplication):

```markdown
## Configuration Options

The config system supports these fields:

- `erk_root`: Root directory for erk data
- `use_graphite`: Enable Graphite integration
- `github_planning`: Enable GitHub issues integration
- `interactive_claude.verbose`: Show verbose output
- `interactive_claude.permission_mode`: Permission mode
- `interactive_claude.dangerous`: Skip permission prompts
```

**After** (dynamic pointer):

````markdown
## Configuration Options

See `GlobalConfigSchema` and `InteractiveClaudeConfigSchema` in `packages/erk-shared/src/erk_shared/config/schema.py:31-89` for all available fields and descriptions.

For field-level documentation, run:

```bash
erk config keys
```
````

**Why it's better**:

- Code is source of truth (no drift)
- Users get current fields via CLI
- Documentation focuses on concepts, not data

**Savings**: 6 lines of static docs → 1 line pointer + CLI command

### Example 2: Dataclass Fields

**Before** (static duplication):

```markdown
The RoadmapStep dataclass contains:

- `step_id: str` - Step identifier (e.g., "1.1")
- `description: str` - What the step does
- `status: str` - One of: pending, done, in_progress, blocked, skipped
- `pr: str | None` - PR reference or None
```

**After** (dynamic pointer):

```markdown
See `RoadmapStep` dataclass in `objective_roadmap_shared.py:10-17` for field definitions.
```

**Why it's better**:

- Field names can't drift (pointing to actual code)
- Type annotations are authoritative
- Less surface area to maintain

**Savings**: 5 lines of duplication → 1 line pointer

### Example 3: Gateway Methods

**Before** (static duplication):

```markdown
The GitGateway provides these methods:

- `get_current_branch(cwd) -> str | None` - Returns current branch name
- `get_remote_url(repo_root, remote) -> str` - Returns remote URL
- `has_uncommitted_changes(cwd) -> bool` - Checks if working tree has changes
- `list_branches(cwd) -> list[str]` - Lists local branches
```

**After** (dynamic pointer):

```markdown
See git gateway sub-ABCs in `packages/erk-shared/src/erk_shared/gateway/git/` (e.g., `branch_ops/abc.py`, `status_ops/abc.py`) for available methods.
```

**Why it's better**:

- Method signatures can't go stale
- Users see actual implementation
- Less documentation to update when methods change

**Savings**: 4+ lines per gateway → 1 line pointer

## Pattern 2: Duplication Removal

**Problem**: Same information appears in multiple docs, creating synchronization burden.

**Solution**: Choose single canonical location, remove duplicates, add cross-references.

### Example 1: Learn Pipeline Architecture

**Before** (duplicated in 3 docs):

- `docs/learned/planning/learn-workflow.md`: 40 lines describing learn pipeline
- (second doc): 35 lines describing same pipeline
- (third doc): 30 lines describing same pipeline

**After** (single canonical doc):

- `docs/learned/planning/learn-pipeline-workflow.md`: 60 lines (consolidated)
- Other docs: 1-line pointer to canonical doc

**Why it's better**:

- Updates happen in one place
- No risk of contradictory information
- Clear single source of truth

**Savings**: 105 lines across 3 docs → 60 lines in 1 doc + 2 pointers = 43 lines saved

### Example 2: Roadmap Validation Checks

**Before** (duplicated):

- `docs/learned/objectives/roadmap-parser.md`: Lists all 5 validation checks
- `docs/learned/objectives/roadmap-validation.md`: Lists same 5 checks
- `docs/learned/cli/objective-commands.md`: Mentions validation checks

**After** (consolidated):

- `docs/learned/objectives/roadmap-validation.md`: Canonical list of all checks
- Other docs: Pointer to roadmap-validation.md

**Why it's better**:

- Adding new validation check requires updating one doc
- No risk of docs listing different check counts
- Clear ownership of validation documentation

**Savings**: 20+ lines of duplication → 2-3 pointers

## Pattern 3: Scope Reduction

**Problem**: Documentation tries to cover too much, becoming unwieldy.

**Solution**: Narrow scope to essential information, move peripheral details to specialized docs.

### Example 1: Gateway Documentation

**Before** (overly broad):

```markdown
# Gateway Pattern

[30 lines explaining ABC pattern]
[40 lines showing all 8 gateway implementations]
[25 lines describing testing approach]
[20 lines on when to create new gateways]
[15 lines on subprocess wrappers]
```

**After** (focused):

```markdown
# Gateway Pattern

[30 lines explaining ABC pattern]
[10 lines linking to gateway-abc-implementation.md for checklist]
[10 lines linking to subprocess-wrappers.md for wrapper details]

See `src/erk/gateway/*.py` for implementations.
```

**Why it's better**:

- Core concept explained, details delegated
- Readers find what they need faster
- Specialized docs can go deeper

**Savings**: 130 lines → 50 lines focused + specialized docs

### Example 2: Session Documentation

**Before** (overly broad):

```markdown
# Session Discovery

[50 lines on session file format]
[40 lines on parallel session coordination]
[30 lines on session upload workflow]
[20 lines on session analysis]
```

**After** (focused):

```markdown
# Session Discovery

[25 lines on how Claude Code stores sessions]
[10 lines on discovery algorithm]

Related workflows:

- Session analysis: See session-inspector skill
- Parallel sessions: See parallel-session-awareness.md
```

**Why it's better**:

- Discovery doc focuses on discovery only
- Related topics have their own docs
- Users don't wade through unrelated content

**Savings**: 140 lines → 35 lines + cross-references

## Metrics from Audit PRs

These patterns were proven effective across three major cleanup PRs:

| PR    | Files Modified | Pattern Applied     | Lines Removed | Broken Paths Fixed |
| ----- | -------------- | ------------------- | ------------- | ------------------ |
| #6637 | 8 docs         | Duplication removal | 156           | 12                 |
| #6660 | 10 docs        | Static → dynamic    | 200           | 8                  |
| #6666 | 10 docs        | Scope reduction     | 197           | 32                 |
| Total | 20 docs        | All three patterns  | **553 lines** | **52 paths**       |

**Average**: ~28 lines removed per doc, 2.6 broken paths fixed per doc.

## When to Apply Each Pattern

### Use Static → Dynamic when:

- Documentation lists fields, methods, or config options
- Source code is the source of truth
- Information changes when code changes

### Use Duplication Removal when:

- Same content appears in 2+ docs
- Information is conceptual (not code-derived)
- Clear canonical location exists or can be created

### Use Scope Reduction when:

- Documentation covers multiple distinct topics
- Doc length exceeds 100 lines
- Readers struggle to find specific information

## Anti-Patterns

### Anti-Pattern 1: Removing Too Much

**Problem**: Over-applying simplification removes valuable context.

**Example**: Deleting "why" explanations because they're "not code"

**Fix**: Keep conceptual documentation, remove only duplication/derivable content.

### Anti-Pattern 2: Breaking Without Fixing

**Problem**: Deleting content without updating cross-references.

**Example**: Removing a section and leaving broken links to it.

**Fix**: Run `erk docs sync` after deletions to regenerate index and fix links.

### Anti-Pattern 3: Pointing to Unstable Code

**Problem**: Using source pointers to code that changes frequently.

**Example**: Pointing to implementation details instead of stable ABCs.

**Fix**: Point to ABCs, interfaces, and schemas (stable) not implementations (volatile).

## Related Documentation

- [audit-methodology.md](audit-methodology.md) - Complete audit process
- [doc-audit-review.md](../review/doc-audit-review.md) - Automated quality checking
- [documentation tripwires](tripwires.md) - Critical documentation rules
