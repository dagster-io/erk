---
title: Review Spec Format
read_when:
  - creating a new code review
  - understanding review spec structure
  - debugging review behavior
last_audited: "2026-02-05 17:40 PT"
audit_result: edited
---

# Review Spec Format

Review specification files in `.github/reviews/` follow a consistent structure beyond the YAML frontmatter. This document captures the body patterns that have emerged across erk's review suite.

## Overview

A review spec consists of:

1. **YAML frontmatter** - Configuration (documented in [convention-based-reviews.md](convention-based-reviews.md))
2. **Algorithm steps** - Step-by-step instructions for the review agent
3. **Classification taxonomy** - What to flag vs skip
4. **Comment templates** - Formats for inline and summary comments
5. **Activity log** - Historical tracking of review runs

## Algorithm Structure

Reviews typically follow a **5-6 step algorithm pattern**:

### Pattern

```markdown
## Step 1: [Gather Context]

Run commands to get PR diff, changed files, etc.

## Step 2: [Extract/Classify]

Process the gathered data into categories or buckets

## Step 3: [Detection/Analysis]

Apply heuristics or rules to detect violations

## Step 4: [Classification]

Decide what to flag vs what to skip

## Step 5: [Post Comments]

Post inline comments on flagged items

## Step 6: [Summary]

Post summary comment with aggregate results
```

### Examples Across Reviews

**Learned Docs Review** (6 steps):

1. Get PR diff and identify changed doc files
2. Extract code blocks from changed/added lines
3. Check each code block for verbatim source matches
4. Classify each code block
5. Post inline comments
6. Summary comment format

**Test Coverage Review** (6 steps):

1. Categorize PR files
2. Early exit (if no source changes)
3. Check test coverage for each source file
4. Analyze test balance
5. Post inline comments
6. Summary comment with table

**Tripwires Review** (5 steps):

1. Load tripwire index (category-specific tripwire files)
2. Match tripwires to diff
3. Load docs for matched tripwires (lazy loading)
4. Post inline comments
5. Summary comment

## Classification Taxonomy

Reviews define clear classification rules for what to flag vs skip.

### Pattern

```markdown
## Step N: Classify Each [Item]

- **Category A**: Description → **FLAG IT**
- **Category B**: Description → Skip
- **Category C**: Description → Skip
```

### Examples

**Learned Docs** (4 categories):

- Verbatim copy → FLAG
- Pattern/template → Skip
- CLI/command example → Skip
- Short snippet (≤5 lines) → Skip

**Test Coverage** (6 buckets + untestable detection):

- source_added → Check for tests
- source_modified (significant) → Check for tests
- Legitimately untestable → Skip

## Comment Templates

### Inline Comment Format

Reviews use a consistent inline comment structure: `**[Review Name]**: [Brief violation description]`, followed by details, context, and a suggested fix. See the Step 5 sections of each review spec in `.github/reviews/` for the exact templates (e.g., `.github/reviews/learned-docs.md` Step 5, `.github/reviews/test-coverage.md` Step 5).

### Summary Comment Format

Most reviews include three parts: (1) a review name header, (2) a table with aggregate results per file/category, and (3) an activity log with the last 10 entries. See the Step 6 sections of each review spec in `.github/reviews/` for the exact formats.

## Activity Log Pattern

Multiple reviews use an activity log to track behavior over time.

### Pattern Rules

1. **Prepend new entries** at the top
2. **Keep last 10 entries** maximum
3. **Include timestamp** and brief description
4. **Provide context** for debugging review behavior across PR iterations

### Example Entry Formats

**Learned Docs**:

- "Found 2 verbatim blocks (src/erk/gateway/git/git.py in docs/learned/testing/testing.md)"
- "All docs clean, no verbatim copies detected"
- "1 verbatim block detected in docs/learned/architecture/subprocess-wrappers.md"

**Test Coverage**:

- "2 source files added, 1 untested (src/erk/foo.py)"
- "All source additions have tests"
- "Net test reduction: 3 deleted, 1 added"

### Retention Limit

**Why 10 entries?** Balances history (debugging recurring issues) with comment size (GitHub comment length limits).

## Step Descriptions

Each step should have:

1. **Clear heading**: `## Step N: [Action Verb + Object]`
2. **Commands to run**: Specific bash/tool commands
3. **Expected output**: What the step should produce
4. **Decision logic**: How to process the results

### Good Examples

✅ `## Step 1: Get PR Diff and Identify Changed Doc Files`
✅ `## Step 3: Check Each Code Block for Verbatim Source Matches`
✅ `## Step 2: Categorize PR Files`

### Avoid

❌ `## Step 1: Setup` (too vague)
❌ `## Do the analysis` (no step number)
❌ `## Check files` (which files? for what?)

## Heuristics Over Precision

Review agents use **heuristic-based detection** rather than precise parsing for speed and robustness.

### Example: Learned Docs Review

Instead of AST parsing:

- Import checks: Look for `from erk` patterns
- Name extraction: Regex for `class Foo`, `def bar`
- Line matching: Simple line-by-line comparison

**Why heuristics?**

- Fast execution (no import overhead)
- Handles incomplete code blocks
- Tolerates formatting differences
- Good enough for review purposes

## Review Examples

| Review                  | File                           | Steps | Categories | Activity Log |
| ----------------------- | ------------------------------ | ----- | ---------- | ------------ |
| Learned Docs Review     | `learned-docs.md`              | 6     | 4          | Yes          |
| Test Coverage Review    | `test-coverage.md`             | 6     | 6          | Yes          |
| Tripwires Review        | `tripwires.md`                 | 5     | Varies     | Yes          |
| Dignified Python        | `dignified-python.md`          | 5     | Varies     | Yes          |
| Dignified Code Simplify | `dignified-code-simplifier.md` | 3     | N/A        | Yes          |
| Doc Audit               | `doc-audit.md`                 | 5     | 6          | Yes          |

## Related Documentation

- [Convention-Based Reviews](convention-based-reviews.md) - Frontmatter schema and workflow
- [Inline Comment Deduplication](../review/inline-comment-deduplication.md) - Marker-based deduplication
- [Learned Docs Review](../review/learned-docs-review.md) - Example review with 6-step algorithm
