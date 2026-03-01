---
title: Inline Comment Deduplication
read_when:
  - "modifying how PR review comments are posted or fetched"
  - "debugging duplicate review comments on a PR"
  - "changing the review prompt template's deduplication instructions"
tripwires:
  - action: "posting inline review comments without deduplication"
    warning: "Always deduplicate before posting. The dedup logic is prompt-embedded using a collect→dedup→post flow — see Steps 4-6 of REVIEW_PROMPT_TEMPLATE."
last_audited: "2026-02-16 14:20 PT"
audit_result: edited
---

# Inline Comment Deduplication

## Why This Exists

Automated reviews run repeatedly on the same PR (after each push, on re-review requests). Without deduplication, every review iteration posts the same violations again, flooding the PR with identical comments. The problem is worse than simple repetition — GitHub doesn't collapse duplicate review comments, so reviewers see N copies of each violation where N is the number of review iterations.

## Architecture Decision: Prompt-Embedded, Not Code-Enforced

The deduplication logic lives entirely in the prompt template, not in Python code. The prompt uses a **collect → dedup → post** flow across three separate steps (Steps 4-6 of `REVIEW_PROMPT_TEMPLATE`):

1. **Step 4 — Collect**: The agent analyzes the diff and builds a numbered list of all violations. No comments are posted in this step.
2. **Step 5 — Dedup**: The agent fetches existing review comments and checks each collected violation against them, outputting an explicit `NEW` or `DUPLICATE` label for every violation.
3. **Step 6 — Post**: Only violations marked `NEW` are posted. Duplicates are skipped and counted.

<!-- Source: src/erk/review/prompt_assembly.py, REVIEW_PROMPT_TEMPLATE -->

This replaced an earlier interleaved approach where the agent would find violations and post comments in a single step with a side instruction to "skip if duplicate." That interleaved pattern made it easy for the agent to skip the dedup check — it would post-as-it-goes and forget to consult the dedup index.

The collect-then-post structure forces the agent to have a complete violation list before touching GitHub, making dedup a required gate rather than an optional side-check. The forced dedup output (every violation must have a `NEW`/`DUPLICATE` label) makes silent dedup failures impossible — if the agent skips dedup, the missing output is obvious.

The trade-off is that dedup quality still depends on the AI agent following the instructions. However, the structured flow and required output make failures visible rather than silent.

## Design Trade-offs in the Matching Heuristic

Two parameters control the dedup sensitivity, chosen to balance false positives (suppressing distinct comments) against false negatives (posting duplicates):

| Parameter              | Value    | Why this value                                                                                                                                 |
| ---------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| **Body prefix length** | 80 chars | Short enough to tolerate minor rephrasing between iterations; long enough that distinct comments with the same opening phrase aren't collapsed |
| **Line proximity**     | ±2 lines | Accounts for small diff shifts between pushes without matching unrelated comments on nearby lines                                              |

**Anti-pattern — exact line matching**: Using exact line numbers causes false negatives on every push that shifts code, since the same violation moves by a few lines. The 2-line window handles the common case of small surrounding edits.

**Anti-pattern — full body matching**: Using the entire comment body for matching causes false negatives whenever the agent slightly rephrases its explanation across iterations. The 80-char prefix captures the violation type and location, which are the stable parts.

## Cross-System Interaction

The dedup pipeline spans three prompt steps and two CLI commands:

1. **Collect** (Step 4) — The agent analyzes the diff and builds a violation list (no external calls)
2. **Dedup** (Step 5) — `erk exec get-pr-review-comments --include-resolved` fetches existing threads; the agent matches each collected violation against them
3. **Post** (Step 6) — `erk exec post-pr-inline-comment` posts only violations labeled `NEW`

<!-- Source: src/erk/cli/commands/exec/scripts/get_pr_review_comments.py, get_pr_review_comments -->
<!-- Source: src/erk/cli/commands/exec/scripts/post_pr_inline_comment.py, post_pr_inline_comment -->

The `--include-resolved` flag is critical for dedup: without it, resolved threads are invisible and the agent re-posts violations that a human already dismissed.

## Review Name Prefix as Scope Boundary

The prompt instructs the agent to match only comments starting with the same review prefix (`**{review_name}**:`). This prevents cross-review dedup — if two different review definitions both flag the same line, both comments are posted. This is correct behavior because different reviews enforce different rules and their comments serve different purposes.

## Related Documentation

Related review documentation covers the prompt assembly system where deduplication instructions are embedded.
