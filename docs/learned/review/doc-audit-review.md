---
title: Doc Audit Review
last_audited: "2026-02-04 05:48 PT"
audit_result: clean
read_when:
  - working with documentation audit system
  - understanding documentation quality classification
  - debugging code duplication violations
tripwires:
  - action: "duplicating implementation details into docs/learned/ files"
    warning: "Documentation that duplicates what code already expresses will drift. Use source pointers instead. See doc-audit review for classification guidance."
---

# Doc Audit Review

The Doc Audit Review is a GitHub review automation that analyzes documentation files under `docs/learned/**/*.md` for code duplication and drift risk. When a PR adds or modifies documentation, the review classifies content into five categories and provides a percentage-based verdict on whether the documentation adds value or creates maintenance burden.

## What It Does

The review runs automatically on PRs that modify `docs/learned/**/*.md` files and:

1. **Analyzes content** in changed documentation files
2. **Classifies by category** using five-category system (DUPLICATIVE, DRIFT RISK, HIGH VALUE, CONTEXTUAL, EXAMPLES)
3. **Calculates percentages** for each category
4. **Posts verdict** on whether the documentation should be kept, revised, or removed
5. **Provides specific recommendations** for improving documentation quality

## Why It Exists

**Problem**: Documentation duplication and drift.

Documentation that re-expresses what the code already says creates two problems:

1. **Maintenance burden**: Every code change requires updating docs in multiple places
2. **Drift risk**: When code changes but docs don't, users get incorrect information

**Solution**: The doc-audit review catches problematic documentation patterns at PR time and guides authors toward high-value documentation that complements rather than duplicates code.

## Five-Category Classification

### DUPLICATIVE (Bad)

Content that re-expresses what the code already says clearly.

**Examples**:

- Listing all fields from a dataclass that has descriptive field names
- Documenting function parameters when the signature is self-explanatory
- Describing simple class hierarchies that are obvious from reading the code

**Why it's problematic**: Pure duplication provides no value and creates maintenance burden.

### DRIFT RISK (Bad)

Content that will become incorrect when implementation changes.

**Examples**:

- File paths or line numbers that reference current code locations
- Implementation details that are likely to change (algorithm specifics, internal data structures)
- Workflow steps that are tightly coupled to current UI or CLI design

**Why it's problematic**: These docs rot silently when code evolves, misleading users.

### HIGH VALUE (Good)

Content that provides insights not easily extracted from code.

**Examples**:

- "Why" explanations for non-obvious design decisions
- Tradeoffs and alternatives that were considered
- Cross-cutting patterns that span multiple files
- Mental models and conceptual frameworks

**Why it's valuable**: This is what documentation should do - provide context and insight that code cannot express.

### CONTEXTUAL (Good)

Content that connects scattered pieces of the codebase.

**Examples**:

- How multiple components interact to achieve a goal
- Workflow diagrams showing the sequence of operations
- Integration points between subsystems
- Mapping of concepts to code locations (pointers, not copies)

**Why it's valuable**: Helps readers navigate and understand system-level behavior.

### EXAMPLES (Neutral to Good)

Concrete usage examples showing how to use an API or feature.

**Examples**:

- CLI command invocations with realistic arguments
- Code snippets showing typical usage patterns
- Before/after examples demonstrating transformations

**Why it's neutral**: Examples are valuable for users but can drift if APIs change. Keep them short and focused on the pattern, not the details.

## Percentage-Based Verdict System

The review calculates percentage breakdowns across the five categories and provides a verdict:

### Verdict: REMOVE (Red Flag)

**Criteria**: DUPLICATIVE + DRIFT RISK ≥ 60%

**Recommendation**: This documentation creates more problems than it solves. Either remove it or substantially revise to focus on HIGH VALUE content.

### Verdict: REVISE (Yellow Flag)

**Criteria**: 30% ≤ DUPLICATIVE + DRIFT RISK < 60%

**Recommendation**: This documentation has value but needs cleanup. Remove duplicative sections, replace drift-prone details with source pointers, and strengthen HIGH VALUE content.

### Verdict: KEEP (Green Flag)

**Criteria**: DUPLICATIVE + DRIFT RISK < 30%

**Recommendation**: This documentation adds value. Minor improvements may still be suggested (e.g., converting some EXAMPLES to pointers if they're getting long).

## Review Spec Details

**File**: `.github/reviews/doc-audit.md`

**Frontmatter**: See `.github/reviews/doc-audit.md:1-9` for the complete review specification.

**Key configuration**:

- **Model**: `claude-sonnet-4-5` for nuanced classification and percentage estimation
- **Scope**: `docs/learned/**/*.md`
- **Tool constraints**: Read-only with GitHub CLI and erk exec access

## Integration Points

The doc-audit review integrates with existing erk systems:

1. **Convention-based review system** ([convention-based-reviews.md](../ci/convention-based-reviews.md)) - Uses standard frontmatter and discovery
2. **learned-docs review** - Complementary focus (learned-docs catches verbatim code, doc-audit catches duplication)
3. **Audit methodology** ([audit-methodology.md](../documentation/audit-methodology.md)) - Provides the underlying audit patterns

## Example Classification

Given documentation about the `RoadmapStep` dataclass:

**DUPLICATIVE** (40%):

```
The RoadmapStep has these fields:
- id: The step identifier
- title: The step title
- description: What the step does
```

**HIGH VALUE** (30%):

```
The roadmap parser supports dual-format backward compatibility: it tries
parsing the new 7-column format first, then falls back to the legacy
4-column format. This allows existing roadmaps to continue working while
new roadmaps get additional metadata.
```

**CONTEXTUAL** (20%):

```
Roadmap parsing happens in two phases:
1. Table extraction (src/erk/cli/commands/exec/scripts/objective_roadmap_shared.py:45)
2. Validation (src/erk/cli/commands/objective/check_cmd.py:166-197)
```

**EXAMPLES** (10%):

```bash
# Check roadmap for errors
erk objective check 123
```

**Verdict**: REVISE (40% duplicative) - Remove field list, keep backward compatibility explanation and pointers.

## Constants and Defaults Exception

**CRITICAL**: Constants and defaults in prose are classified as **HIGH VALUE**, not DUPLICATIVE.

### Why This Exception Exists

When documentation explains "what value is used by default" or "what constant controls this behavior," it provides **scannable context** that is hard to extract from code:

**In code**:

```python
DEFAULT_MACHINE_TYPE = "premiumLinux"
```

**In docs (HIGH VALUE)**:

```markdown
The default machine type for codespace creation is `premiumLinux`.
```

### The Key Distinction

- **DUPLICATIVE**: Re-expressing what the code already says clearly (field names, parameter types, class hierarchies)
- **HIGH VALUE**: Providing scannable defaults and constants that require grep/search to find in code

### Examples of HIGH VALUE Constants

1. **Default values**:

   ```markdown
   By default, erk uses `premiumLinux` as the machine type for codespaces.
   ```

2. **Configuration constants**:

   ```markdown
   Session markers are stored in `.erk/scratch/<session-id>/markers/`.
   ```

3. **Timeout values**:
   ```markdown
   The retry mechanism waits 2 seconds between attempts.
   ```

### Why Scannability Matters

Readers need to quickly answer "what's the default?" without:

- Searching through implementation files
- Reading constructor logic
- Tracing constant definitions across modules

Documentation that surfaces these values serves as an **index** to the codebase, not a duplicate of it.

**Related**: [Documentation Audit Methodology](../documentation/audit-methodology.md) - Tripwire on broad exclusion rules

## Related Documentation

- `.github/reviews/doc-audit.md` - The review specification
- `docs/learned/documentation/audit-methodology.md` - Audit process and patterns
- `docs/learned/ci/convention-based-reviews.md` - How reviews fit in the broader system
- `docs/learned/review/learned-docs-review.md` - Complementary verbatim code detection
