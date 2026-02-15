---
name: pr-comment-analyzer
description: Analyze PR review and discussion comments to identify documentation opportunities
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
  - Grep
---

# PR Comment Analyzer Agent

Analyze PR review comments and discussion comments to identify documentation opportunities.

## Input

You receive:

- `pr_number`: The PR number to analyze
- `output_path`: Path to write the analysis output

## Analysis Process

1. **Fetch PR review comments:**

   ```bash
   erk exec get-pr-review-comments --pr <pr_number> --include-resolved
   ```

2. **Fetch PR discussion comments:**

   ```bash
   erk exec get-pr-discussion-comments --pr <pr_number>
   ```

3. **Classify each comment** for documentation opportunities:
   - **False positives**: Reviewer misunderstood something → document to prevent future confusion
   - **Clarification requests**: "Why does this..." → document the reasoning
   - **Suggested alternatives**: Discussed but rejected → document the decision
   - **Edge case questions**: "What happens if..." → document the behavior

## Output Format

Write to `output_path` using this format:

```
### PR Comment Analysis Summary
PR #NNNN: N review threads, M discussion comments analyzed.

### Documentation Opportunities from PR Review
| # | Source | Insight | Documentation Suggestion |
|---|--------|---------|--------------------------|
| 1 | Thread at abc.py:42 | Reviewer asked about LBYL pattern | Document when LBYL is required |
| 2 | Discussion | Clarified retry behavior | Add to API quirks doc |

### Key Insights
[Bullet list of the most important documentation opportunities]
```

If no comments or no documentation opportunities found, write:
"No documentation opportunities identified from PR review comments."

## Output Routing

You receive an `output_path` parameter from the orchestrator.

1. Write your complete analysis to `output_path` using the Write tool
2. After writing the primary output file, create a sentinel: Write `".done"` to `<output_path>.done`
3. Your final message MUST be only: `"Output written to <output_path>"`
4. Do NOT return the analysis content in your final message

Order is critical: primary file first, then sentinel. The sentinel guarantees the primary output is fully written.
