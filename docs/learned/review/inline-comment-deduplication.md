---
title: Inline Comment Deduplication
read_when:
  - "modifying how PR review comments are posted or fetched"
  - "debugging duplicate review comments on a PR"
  - "changing the review prompt template's deduplication instructions"
tripwires:
  - action: "posting inline review comments without deduplication"
    warning: "Always deduplicate before posting. The dedup logic is prompt-embedded, not code-enforced — see Step 4 of REVIEW_PROMPT_TEMPLATE."
---

# Inline Comment Deduplication

## Why This Exists

Automated reviews run repeatedly on the same PR (after each push, on re-review requests). Without deduplication, every review iteration posts the same violations again, flooding the PR with identical comments. The problem is worse than simple repetition — GitHub doesn't collapse duplicate review comments, so reviewers see N copies of each violation where N is the number of review iterations.

## Architecture Decision: Prompt-Embedded, Not Code-Enforced

The deduplication logic lives entirely in the prompt template, not in Python code. The AI agent executing the review is instructed to fetch existing comments, build a dedup index, and skip matches — all within the prompt steps.

<!-- Source: src/erk/review/prompt_assembly.py, REVIEW_PROMPT_TEMPLATE -->

This is intentional: the agent needs flexibility to interpret near-matches and make judgment calls that rigid code dedup cannot. For example, a slightly reworded violation on a line that shifted by 1 is "the same comment" to a human reviewer but would slip past exact-match code.

The trade-off is that dedup quality depends on the AI agent correctly following the instructions. If the prompt template's Step 4 instructions are unclear, dedup fails silently — the agent just posts duplicates.

## Design Trade-offs in the Matching Heuristic

Two parameters control the dedup sensitivity, chosen to balance false positives (suppressing distinct comments) against false negatives (posting duplicates):

| Parameter              | Value    | Why this value                                                                                                                                 |
| ---------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| **Body prefix length** | 80 chars | Short enough to tolerate minor rephrasing between iterations; long enough that distinct comments with the same opening phrase aren't collapsed |
| **Line proximity**     | ±2 lines | Accounts for small diff shifts between pushes without matching unrelated comments on nearby lines                                              |

**Anti-pattern — exact line matching**: Using exact line numbers causes false negatives on every push that shifts code, since the same violation moves by a few lines. The 2-line window handles the common case of small surrounding edits.

**Anti-pattern — full body matching**: Using the entire comment body for matching causes false negatives whenever the agent slightly rephrases its explanation across iterations. The 80-char prefix captures the violation type and location, which are the stable parts.

## Cross-System Interaction

The dedup pipeline spans three distinct components:

1. **Fetch** — `erk exec get-pr-review-comments --include-resolved` returns existing threads with path, line, and body fields
2. **Match** — The agent builds and queries the dedup index (prompt-instructed, not code)
3. **Post** — `erk exec post-pr-inline-comment` posts only non-duplicate comments

<!-- Source: src/erk/cli/commands/exec/scripts/get_pr_review_comments.py, get_pr_review_comments -->
<!-- Source: src/erk/cli/commands/exec/scripts/post_pr_inline_comment.py, post_pr_inline_comment -->

The `--include-resolved` flag is critical for dedup: without it, resolved threads are invisible and the agent re-posts violations that a human already dismissed.

## Review Name Prefix as Scope Boundary

The prompt instructs the agent to match only comments starting with the same review prefix (`**{review_name}**:`). This prevents cross-review dedup — if two different review definitions both flag the same line, both comments are posted. This is correct behavior because different reviews enforce different rules and their comments serve different purposes.

## Related Documentation

- [Review Prompt Assembly](prompt-assembly.md) — The two-mode prompt system where dedup instructions are embedded
