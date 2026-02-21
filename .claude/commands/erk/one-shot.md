---
description: Submit a task for fully autonomous remote planning and implementation
argument-hint: <prompt>
---

# One-Shot Autonomous Execution

Submit a task for fully autonomous remote execution. The prompt will be dispatched to a GitHub Actions workflow where Claude autonomously explores, plans, implements, and creates a PR.

## Steps

1. Validate that `$ARGUMENTS` is non-empty. If empty, tell the user they need to provide a prompt.

2. Write the prompt text to a scratch file to avoid shell quoting issues with long or complex prompts:

```bash
# Write prompt to session-scoped scratch file
mkdir -p .erk/scratch/sessions/${CLAUDE_SESSION_ID}
cat > .erk/scratch/sessions/${CLAUDE_SESSION_ID}/one-shot-prompt.md << 'PROMPT_EOF'
$ARGUMENTS
PROMPT_EOF
```

3. Run the CLI command with --file:

```bash
erk one-shot --file .erk/scratch/sessions/${CLAUDE_SESSION_ID}/one-shot-prompt.md
```

4. Clean up the scratch file:

```bash
rm -f .erk/scratch/sessions/${CLAUDE_SESSION_ID}/one-shot-prompt.md
```

5. Display the output to the user, which includes the PR URL and workflow run URL.

If the command fails, display the error message.
