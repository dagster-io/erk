---
title: Review Prompt Assembly
read_when:
  - "modifying review prompt generation or templates"
  - "adding a new review mode to the review system"
  - "understanding why PR mode and local mode are structured differently"
tripwires:
  - action: "adding a new review mode without updating assemble_review_prompt validation"
    warning: "The function validates mutual exclusivity of pr_number and base_branch. New modes must fit within or extend this validation."
---

# Review Prompt Assembly

## Why Two Modes Exist

<!-- Source: src/erk/review/prompt_assembly.py, assemble_review_prompt -->

The review system needs to work at two different points in the development lifecycle: **before** a PR exists (local mode) and **after** (PR mode). These aren't just different output targets — they have fundamentally different interaction models:

| Concern                | PR Mode                                                                              | Local Mode                                              |
| ---------------------- | ------------------------------------------------------------------------------------ | ------------------------------------------------------- |
| **Output destination** | GitHub inline comments + summary comment                                             | Terminal stdout                                         |
| **Deduplication**      | Required — reviews re-run on each push and must not flood with duplicates            | Not needed — each local run is a fresh terminal session |
| **State management**   | Maintains an activity log across review iterations via marker-based summary comments | Stateless — each run is independent                     |
| **Diff source**        | `gh pr diff` (GitHub's view of the PR)                                               | `git diff` against a merge-base (local working tree)    |

The modes are **mutually exclusive by design**, enforced by LBYL validation at the function boundary. This prevents ambiguous states where the prompt would contain instructions for both GitHub posting and terminal output.

## Why Deduplication Lives in the Prompt, Not Code

The most surprising architectural decision is that deduplication logic is embedded in the PR mode prompt template rather than implemented in Python. This was deliberate — see [Inline Comment Deduplication](inline-comment-deduplication.md) for the full rationale. The short version: dedup requires fuzzy judgment (is a slightly reworded comment on a shifted line "the same" violation?) that an AI agent handles better than rigid string matching.

This means the PR mode template is significantly more complex than the local mode template: it includes steps for fetching existing comments, building a dedup index, and conditionally skipping posts. Local mode has none of this machinery because terminal output is ephemeral.

## The Prompt-as-Orchestration Pattern

<!-- Source: src/erk/review/prompt_assembly.py, REVIEW_PROMPT_TEMPLATE -->
<!-- Source: src/erk/review/prompt_assembly.py, LOCAL_REVIEW_PROMPT_TEMPLATE -->

Both templates follow a numbered step structure that orchestrates the reviewing agent's behavior. This is not incidental formatting — the step ordering encodes **causal dependencies**:

- **PR mode**: Fetch existing summary → get diff → fetch existing comments → post new comments → update summary. The dedup fetch (Step 4) must come before posting (Step 5), and the summary (Step 6) needs to know what was posted vs skipped.
- **Local mode**: Get diff → output violations → print summary. No state management steps needed.

The review body (user-defined review instructions from the `.erk/reviews/*.md` file) is injected as Step 1 in both modes, ensuring the agent reads the specific review criteria before examining any code.

## How Review Definitions Flow Through the System

<!-- Source: src/erk/cli/commands/exec/scripts/run_review.py, run_review -->
<!-- Source: src/erk/review/models.py, ParsedReview -->

A review definition file (`.erk/reviews/*.md`) contains YAML frontmatter with metadata (`name`, `paths`, `marker`, `model`) and a markdown body with review-specific instructions. The flow:

1. `run_review` CLI command parses the review file and resolves the mode (PR vs local, with auto-detection of trunk branch for local mode)
2. `assemble_review_prompt` injects the review's name, body, and marker into the appropriate template
3. The assembled prompt is either printed (`--dry-run`) or executed via `PromptExecutor`

The `marker` field deserves special attention: it's an HTML comment string (e.g., `<!-- tripwires-review -->`) used to locate and update the summary comment across review iterations. Each review definition gets its own marker, so multiple review types can coexist on the same PR without overwriting each other's summaries.

## Anti-Patterns

**Adding a mode without extending validation** — The validation at the top of `assemble_review_prompt` enforces mutual exclusivity between `pr_number` and `base_branch`. A third mode (e.g., commit-range review) would need to extend this validation to maintain a clean three-way exclusion, not just add a third parameter that ignores the existing checks.

**Putting dedup logic in Python code** — It's tempting to implement deduplication as a pre-filter before posting. But the matching heuristic requires judgment about near-duplicates (see [Inline Comment Deduplication](inline-comment-deduplication.md) for the specific trade-offs around body prefix length and line proximity). Code-level dedup would either be too strict (missing near-duplicates) or too loose (suppressing distinct comments).

## Related Documentation

- [Inline Comment Deduplication](inline-comment-deduplication.md) — Why dedup is prompt-embedded and the matching heuristic trade-offs
