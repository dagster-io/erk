---
title: Preview Command Pattern
read_when:
  - "pairing destructive commands with preview commands"
  - "implementing dry-run for slash commands"
  - "adding preview functionality to existing commands"
tripwires:
  - action: "creating a destructive slash command without a preview variant"
    warning: "Consider pairing with a preview command (e.g., pr-address + pr-preview-address). Preview commands show planned actions without executing, reducing costly mistakes."
    score: 3
---

# Preview Command Pattern

Pair destructive slash commands with preview commands that show planned actions without executing them.

## Pattern

For commands that perform destructive or hard-to-reverse operations, create a companion preview command:

| Command           | Preview                   |
| ----------------- | ------------------------- |
| `/erk:pr-address` | `/erk:pr-preview-address` |

The preview command runs the same analysis pipeline (fetch data, classify, plan actions) but outputs a summary instead of executing.

## Implementation

1. **Same analysis pipeline**: Preview reuses the same data fetching and classification logic
2. **Different output mode**: Preview summarizes planned actions instead of executing them
3. **Cost-efficient model**: Preview commands can use cheaper models (e.g., haiku) since they don't need to produce high-quality code changes
4. **User verification**: Users review the preview output, then run the real command with confidence

## Benefits

- **Reduced risk**: Users see exactly what will happen before committing
- **Cost savings**: Preview with haiku model is much cheaper than a full execution that needs to be reverted
- **Debugging aid**: When the real command produces unexpected results, compare against preview output

## When to Use

Use preview commands when:

- The command modifies code or resolves review threads
- Mistakes are costly to undo (pushed commits, resolved threads)
- The command involves classification or judgment calls users want to verify

Skip preview when:

- The command is inherently idempotent (read-only operations)
- The operation is trivially reversible (e.g., creating a branch)

## Related Documentation

- [PR Address Workflows](../erk/pr-address-workflows.md) — The primary use case for preview commands
