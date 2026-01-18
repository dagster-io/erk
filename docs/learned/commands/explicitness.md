---
title: Command Explicitness
read_when:
  - "writing slash commands"
  - "designing command prompts for Claude"
  - "debugging unreliable command execution"
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

```markdown
After CI passes, clean up .worker-impl/ if present:

\`\`\`bash
if [ -d .worker-impl/ ]; then
git rm -rf .worker-impl/
git commit -m "Remove .worker-impl/ after implementation"
git push
fi
\`\`\`
```

Explicit code blocks are executed more reliably and prevent implementation errors.

## Related

- [Implementation Folder Lifecycle](../architecture/impl-folder-lifecycle.md) - Cleanup mechanism details
- [CI Prompt Patterns](../ci/prompt-patterns.md) - Heredoc patterns for GitHub Actions
