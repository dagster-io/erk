---
title: Review Spec Format
read_when:
  - creating a new code review
  - understanding why review specs follow certain patterns
  - debugging review behavior or structure
last_audited: "2026-02-08 13:45 PT"
audit_result: clean
---

# Review Spec Format

Review specifications in `.github/reviews/` follow conventions that evolved to balance agent comprehension, maintenance burden, and historical debugging needs.

## Why Structured Algorithm Steps

Review specs use numbered steps (`## Step 1: [Action]`, `## Step 2: [Next Action]`) instead of prose instructions because:

1. **Sequential execution clarity** — Agents process steps in order without confusion about dependency order
2. **Clear checkpoints** — Each step produces discrete output that the next step consumes
3. **Debugging specificity** — When a review misbehaves, activity logs can reference "Step 3 failed" instead of ambiguous prose
4. **Failure isolation** — If Step 2 fails, the agent doesn't attempt Steps 3-6 with partial data

The alternative (prose instructions like "gather context, then analyze, then comment") fails because agents struggle with implicit ordering and error recovery.

<!-- Source: .github/reviews/audit-pr-docs.md, Step 1-6 pattern -->
<!-- Source: .github/reviews/test-coverage.md, Step 1-6 pattern -->
<!-- Source: .github/reviews/tripwires.md, Step 1-5 pattern -->

See the actual review files in `.github/reviews/` for implemented step structures.

## Why Classification Taxonomies

Reviews define explicit classification rules ("Category A: FLAG IT", "Category B: Skip") rather than general guidance because:

1. **Deterministic behavior** — Same code produces same classification across runs
2. **False positive control** — Explicit skip rules prevent flagging known-acceptable patterns
3. **Activity log consistency** — Classifications map directly to log entries ("2 verbatim blocks detected")

### Example: The 5-Line Threshold

The learned docs review skips code blocks ≤5 lines because:

- Short snippets (≤5 lines) are teaching aids, not implementation copies
- Verbatim detection heuristics have high false positive rates below 6 lines
- Activity logs would be dominated by noise ("flagged 40 short snippets")

This threshold isn't about staleness risk (even 3-line snippets go stale). It's about signal-to-noise ratio in review output.

<!-- Source: docs/learned/documentation/source-pointers.md, 5-line threshold -->

See `docs/learned/documentation/source-pointers.md` for the decision checklist behind this threshold.

## Why Activity Logs Exist

Activity logs track review behavior across PR iterations for debugging recurring issues:

**Problem being solved**: Review agent behavior changes between runs due to:

- Code changes in the PR (new commits)
- Changes to the review spec itself
- Model behavior drift

**Why 10 entries?** Balance between:

- Sufficient history to identify patterns ("flagged this 3 times, then stopped")
- GitHub comment size limits (100KB hard limit)
- Visual scan burden (humans debugging reviews need to read these)

**What logs capture**:

- Aggregate counts ("2 verbatim blocks detected")
- Specific violations ("src/erk/foo.py in docs/learned/bar.md")
- Clean runs ("All docs clean, no verbatim copies detected")

<!-- Source: .github/reviews/audit-pr-docs.md, activity log section -->
<!-- Source: .github/reviews/test-coverage.md, activity log section -->

See existing review specs for implemented log formats.

## Why Heuristics Over Precision

Reviews use pattern matching and line-by-line comparison instead of AST parsing because:

1. **Execution speed** — No import overhead, runs in <30s on large PRs
2. **Incomplete code robustness** — Handles partial code blocks and pseudo-code
3. **Formatting tolerance** — Matches despite whitespace/comment differences
4. **Good enough threshold** — False negatives are acceptable (human reviews catch them), false positives are not

<!-- Source: .github/reviews/audit-pr-docs.md, verbatim detection heuristic -->

The learned docs review demonstrates this: it looks for `from erk` patterns and `class Foo`/`def bar` names rather than importing modules and inspecting ASTs.

## Why Comment Templates Are Rigid

Inline comment format is highly structured:

```markdown
**[Review Name]**: [Brief violation description]

[Context/details]

Suggested fix: [Specific action]
```

**Not for human politeness** — for agent parsing. Other erk tools may:

- Parse review comments to generate reports
- Detect duplicate violations across reviews
- Track resolution status

Future tooling depends on consistent structure. See `docs/learned/review/inline-comment-deduplication.md` for marker-based deduplication patterns.

## Common Pitfalls When Creating Reviews

### Anti-Pattern: Vague Step Descriptions

**WRONG**: `## Step 1: Setup`

**RIGHT**: `## Step 1: Get PR Diff and Identify Changed Doc Files`

Agents need action verbs and objects, not abstract phases.

### Anti-Pattern: Embedding Classification Logic in Steps

**WRONG**:

```markdown
## Step 3: Analyze Files

Read each file and decide if it needs tests...
```

**RIGHT**: Separate classification into its own step with explicit taxonomy:

```markdown
## Step 3: Classify Each File

- **Thin CLI wrapper**: Only Click decorators → Skip
- **Type-only file**: Only TypeVar/Protocol → Skip
- **New source file with logic**: → FLAG IT
```

This makes activity logs meaningful ("3 thin CLI wrappers skipped, 1 source file flagged").

### Anti-Pattern: Assuming Tool Availability

Review specs must declare tool constraints in frontmatter (`allowed_tools`). Don't assume `Write` or `Bash(*)` access. Most reviews only need `Read(*)` and `Bash(gh:*)`.

<!-- Source: docs/learned/ci/convention-based-reviews.md, tool constraints section -->

See `docs/learned/ci/convention-based-reviews.md` for the tool permission model.

## Related Documentation

- [Convention-Based Reviews](convention-based-reviews.md) — Frontmatter schema and discovery workflow
- [Source Pointers](../documentation/source-pointers.md) — Why the learned docs review exists
- [Inline Comment Deduplication](../review/inline-comment-deduplication.md) — Marker-based comment tracking
