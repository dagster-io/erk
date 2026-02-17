---
description: Submit a task for fully autonomous remote planning and implementation
argument-hint: <instruction>
---

# One-Shot Autonomous Execution

Submit a task for fully autonomous remote execution. The instruction will be dispatched to a GitHub Actions workflow where Claude autonomously explores, plans, implements, and creates a PR.

## Steps

1. Validate that `$ARGUMENTS` is non-empty. If empty, tell the user they need to provide an instruction.

2. Write the instruction text to a temp file to avoid shell quoting issues with long or complex instructions:

```bash
# Write instruction to temp file
cat > /tmp/erk-one-shot-instruction.md << 'INSTRUCTION_EOF'
$ARGUMENTS
INSTRUCTION_EOF
```

3. Run the CLI command with --file:

```bash
erk one-shot --file /tmp/erk-one-shot-instruction.md
```

4. Clean up the temp file:

```bash
rm -f /tmp/erk-one-shot-instruction.md
```

5. Display the output to the user, which includes the PR URL and workflow run URL.

If the command fails, display the error message.
