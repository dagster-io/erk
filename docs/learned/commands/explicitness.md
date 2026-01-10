---
title: Command Explicitness
read_when:
  - "writing slash commands with multi-step instructions"
  - "debugging why an agent skipped or misexecuted command steps"
  - "creating commands that involve filesystem or git operations"
---

# Command Explicitness

When writing Claude slash commands, prefer explicit bash code blocks over prose instructions.

## Why

Prose instructions like "delete folder, commit cleanup, push" may be:

- Misinterpreted by Claude
- Skipped if Claude loses track of steps
- Executed incorrectly (e.g., using `rm` instead of `git rm`)

## Pattern

**Avoid:**

```markdown
After CI passes:

- Delete .worker-impl/ folder
- Commit the cleanup
- Push to remote
```

**Prefer:**

````markdown
After CI passes, clean up .worker-impl/ if present:

```bash
if [ -d .worker-impl/ ]; then
  git rm -rf .worker-impl/
  git commit -m "Remove .worker-impl/ after implementation"
  git push
fi
```
````

Explicit code blocks are executed more reliably and prevent implementation errors.

## When to Use Prose vs Code

| Situation                          | Recommendation      |
| ---------------------------------- | ------------------- |
| Single, obvious operation          | Prose is fine       |
| Multi-step filesystem/git workflow | Explicit code block |
| Operations with common pitfalls    | Explicit code block |
| Conditional logic                  | Explicit code block |
| Operations where order matters     | Explicit code block |

## Related Topics

- [Implementation Folder Lifecycle](../architecture/impl-folder-lifecycle.md) - The context where this pattern was discovered
- [Optimization Patterns](optimization-patterns.md) - Other slash command patterns
