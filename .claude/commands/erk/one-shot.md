---
description: Submit a task for fully autonomous remote planning and implementation
argument-hint: <instruction>
---

# One-Shot Autonomous Execution

Submit a task for fully autonomous remote execution. The instruction will be dispatched to a GitHub Actions workflow where Claude autonomously explores, plans, implements, and creates a PR.

## Steps

1. Validate that `$ARGUMENTS` is non-empty. If empty, tell the user they need to provide an instruction.

2. Run the CLI command:

```bash
erk one-shot "$ARGUMENTS"
```

3. Display the output to the user, which includes the PR URL and workflow run URL.

If the command fails, display the error message.
