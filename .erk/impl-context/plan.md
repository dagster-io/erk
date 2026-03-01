# Plan: Restructure review prompt to prevent duplicate bot comments

## Context

Review bots post duplicate inline comments on PRs because deduplication is only prompt-based — the AI agent is *instructed* to check for duplicates but sometimes fails. The current prompt structure encourages the agent to interleave finding violations and posting comments, making it easy to skip the dedup step. This is a prompt-only fix (no code changes).

## Problem analysis

Current Steps 4-5 in `REVIEW_PROMPT_TEMPLATE`:
- **Step 4**: "Fetch existing comments, build a dedup index" (abstract, easy to skip)
- **Step 5**: "Post an inline comment for EACH violation found. Skip if duplicate." (finding + posting interleaved, dedup is a side note)

The agent often posts-as-it-goes and forgets the dedup check.

## Changes

### File: `src/erk/review/prompt_assembly.py`

Rewrite Steps 4-5 into a **collect → dedup → post** flow with 3 sub-steps:

**Step 4: Collect violations** (analysis only, no posting)
- Analyze the diff from Step 3
- Build a numbered list of ALL violations found
- Each entry: `{path, line, body}`
- Explicit instruction: **DO NOT post any comments in this step**

**Step 5: Deduplicate against existing comments**
- Fetch existing review comments: `erk exec get-pr-review-comments --pr {pr_number} --include-resolved`
- For EACH violation in the list, check against existing comments using the matching heuristic (same path, line ±2, same 80-char body prefix, same review prefix)
- Mark each violation as `NEW` or `DUPLICATE`
- **Output the dedup decision for every violation** — e.g.:
  ```
  1. src/foo.py:42 - NEW (no matching existing comment)
  2. src/bar.py:10 - DUPLICATE (matches existing comment on line 11)
  ```
- This forced output makes silent dedup failures impossible

**Step 6: Post only NEW violations**
- For each violation marked `NEW`, post via `erk exec post-pr-inline-comment`
- Log the count of skipped duplicates for the summary

**Step 7: Post Summary Comment** (renumbered from current Step 6, unchanged)

### File: `docs/learned/review/inline-comment-deduplication.md`

Update to document the collect-then-dedup-then-post pattern and why it replaced the previous interleaved approach.

## Key design decisions

1. **Collect-then-post, not post-as-you-go**: Separating analysis from posting forces the agent to have a complete violation list before touching GitHub, making dedup a required gate rather than an optional side-check.

2. **Forced dedup reasoning output**: Requiring the agent to print `NEW`/`DUPLICATE` for each violation makes failures visible. If the agent skips dedup, the missing output is obvious.

3. **No code changes**: The dedup remains prompt-embedded. This preserves the fuzzy matching advantage (AI judgment on near-duplicates) without adding code complexity.

## Verification

1. Review the rewritten prompt template for clarity
2. Run a local review (`erk exec run-review --name test-coverage --local --dry-run`) to verify the assembled prompt looks correct
3. On the next PR push, observe whether bot comments are deduplicated correctly
