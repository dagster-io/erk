---
title: PR Feedback Classification
read_when:
  - "working with PR review comment classification"
  - "understanding how pr-address categorizes feedback"
  - "implementing feedback handling workflows"
tripwires:
  - action: "treating all PR comments as actionable without classification"
    warning: "PR comments fall into distinct categories (actionable, informational, praise, question). Only actionable comments need code changes. Classify first to avoid unnecessary work."
    score: 3
---

# PR Feedback Classification

PR review feedback is classified into categories to determine the appropriate response for each comment.

## Categories

| Category          | Description                                        | Response                                              |
| ----------------- | -------------------------------------------------- | ----------------------------------------------------- |
| **Actionable**    | Comments requesting specific code changes          | Modify code, then resolve thread                      |
| **Informational** | FYI comments, observations, suggestions for future | Acknowledge, no code change needed                    |
| **Praise**        | Positive feedback                                  | Acknowledge, no action needed                         |
| **Question**      | Clarification requests                             | Answer the question, may or may not need code changes |

## Classification Flow

1. **Fetch comments**: Get all unresolved review threads from the PR
2. **Classify**: Determine category for each comment based on content analysis
3. **Present**: Show classification to agent with recommended actions
4. **Execute**: Agent acts on each comment according to its category

## Thread Resolution

- **Actionable**: Make code changes, then resolve the thread
- **Informational/Praise**: Reply acknowledging the comment, resolve the thread
- **Question**: Answer the question; if it reveals a code issue, treat as actionable

## Integration with pr-address

The `/erk:pr-address` command uses this classification system:

1. Phase 1 fetches and classifies all feedback
2. Phase 2 generates code fixes for actionable items
3. Phase 3 applies changes
4. Phase 4 resolves threads

The `/erk:pr-preview-address` command runs Phase 1 only to show classification results without executing.

## Related Documentation

- [Preview Command Pattern](../commands/preview-command-pattern.md) — Preview before executing
- [PR Address Workflows](../erk/pr-address-workflows.md) — Complete pr-address workflow
