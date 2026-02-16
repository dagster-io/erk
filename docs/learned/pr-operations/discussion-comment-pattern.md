---
title: Discussion Comment Reply Pattern
read_when:
  - "completing PR review address workflow"
  - "after resolving inline review threads"
---

# Discussion Comment Reply Pattern

After resolving inline PR review threads, reply to the bot's summary discussion comment to close the feedback loop.

## Why This Matters

Automated reviewers (like Dignified Code Simplifier) post:

1. Inline comments on specific lines
2. A summary discussion comment listing all issues

Resolving inline threads doesn't automatically indicate completion. Reply to the summary to signal the review is addressed.

## Command

```bash
erk exec reply-to-discussion-comment --pr <number> --comment-id <id> --body "Addressed all feedback"
```

## Source

See the `pr-address` slash command for the complete workflow that includes this step.

## Related Documentation

- [Batch Review Workflow](batch-review-workflow.md) — Complete PR review addressing workflow
- [Automated Review Handling](automated-review-handling.md) — Bot-generated review patterns
