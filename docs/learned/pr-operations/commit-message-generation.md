---
title: Commit Message Generation
read_when:
  - "understanding how PR descriptions are generated"
  - "working with plan context in PR summaries"
  - "customizing commit message generation"
---

# Commit Message Generation

The `CommitMessageGenerator` uses Claude to generate PR titles and descriptions from diffs, with optional plan and objective context.

## Context Priority Ordering

When generating PR descriptions, context sources are prioritized:

| Priority | Source            | Provides                                            |
| -------- | ----------------- | --------------------------------------------------- |
| 1 (High) | Plan Context      | Intent, rationale, "why" behind changes             |
| 2        | Objective Summary | Parent goal context (e.g., "Objective #123: Title") |
| 3 (Low)  | Commit Messages   | Technical details, developer notes                  |

Plan context is marked as "primary source of truth" in the prompt, ensuring Claude uses it over conflicting commit message details.

## How Context Is Built

The `_build_context_section()` method assembles context:

1. **Branch info** - Always included (current branch, parent branch)
2. **Plan context** - If available from `PlanContextProvider`:
   - Full plan markdown
   - Objective summary if linked
   - Instruction to use plan as primary source
3. **Commit messages** - If available, appended as supplementary context

## Plan Context Extraction

Plan context comes from `PlanContextProvider.get_plan_context()`:

1. Extract issue number from branch name (e.g., `P5763-fix-bug` → 5763)
2. Fetch issue body from GitHub
3. Extract `plan_comment_id` from YAML metadata
4. Fetch comment containing full plan markdown
5. Optionally fetch linked objective title

See [Plan Context Integration](../architecture/plan-context-integration.md) for full algorithm.

## Graceful Degradation

When plan context is unavailable:

- Provider returns `None`
- Generator falls back to commit messages only
- PR still gets a reasonable description from diff analysis

This allows the same workflow for plan-linked and non-plan branches.

## Model Selection

Default model is `haiku` for:

- Speed (commits generate quickly)
- Cost (frequent operation during development)
- Sufficient quality for structured task (diff → description)

Override via `CommitMessageGenerator(executor, model="sonnet")` for complex diffs.

## Reference Implementation

See `src/erk/core/commit_message_generator.py` for the canonical implementation.

## Related Topics

- [Plan Context Integration](../architecture/plan-context-integration.md) - How plan context is extracted
- [Plan Lifecycle](../planning/lifecycle.md) - How plans link to branches
