---
title: PR Review Batch Workflow
read_when:
  - "addressing PR review comments"
  - "using pr-address or pr-preview-address commands"
  - "resolving multiple review threads"
---

# PR Review Batch Workflow

Complete workflow for addressing PR review feedback in batches.

## Workflow Steps

1. **Preview**: Run `/erk:pr-preview-address` to see actionable items without making changes
2. **Check for plan review**: If PR has `erk-plan-review` label, use plan-review-specific workflow
3. **Classify feedback**: Task tool with `pr-feedback-classifier` skill distinguishes inline threads from discussion comments
4. **Display batched plan**: Group related fixes together for efficient execution
5. **Execute by batch**: For each batch: Fix -> Test -> Commit -> Resolve threads
6. **Reply to summary**: After resolving inline threads, reply to bot's summary discussion comment

## Batch Thread Resolution

Use JSON stdin for bulk resolution:

```bash
echo '[{"thread_id": "PRRT_abc", "comment": "Fixed"}, {"thread_id": "PRRT_def", "comment": "Applied"}]' | erk exec resolve-review-threads
```

This resolves multiple threads in a single operation, reducing API calls compared to resolving one at a time.

## Source

See the `pr-address` slash command in `.claude/commands/` for the complete workflow implementation.

## Related Documentation

- [Automated Review Handling](automated-review-handling.md) — Handling bot-generated review comments
- [Discussion Comment Reply Pattern](discussion-comment-pattern.md) — Completing the feedback loop
