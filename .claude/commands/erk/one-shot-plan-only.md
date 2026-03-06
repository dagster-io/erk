---
description: Submit a task for remote planning only (no implementation)
argument-hint: <prompt>
---

# One-Shot Plan Only

Submit a task for remote planning only. The prompt will be dispatched to a GitHub Actions workflow where Claude autonomously explores the codebase and creates a plan as a draft PR, but does NOT implement it.

## Steps

1. Validate that `$ARGUMENTS` is non-empty. If empty, tell the user they need to provide a prompt.

2. Generate a branch slug inline from the prompt. The slug should be:
   - 2-4 hyphenated lowercase words, max 30 characters
   - Capture the distinctive essence, drop filler words (the, a, for, implementation, plan)
   - Prefer action verbs: add, fix, refactor, update, consolidate, extract, migrate
   - Examples: "fix-auth-session", "add-plan-validation", "refactor-gateway-abc"
     Store the result as `BRANCH_SLUG`.

3. Write the prompt text to a scratch file to avoid shell quoting issues with long or complex prompts:

```bash
# Write prompt to session-scoped scratch file
mkdir -p .erk/scratch/sessions/${CLAUDE_SESSION_ID}
cat > .erk/scratch/sessions/${CLAUDE_SESSION_ID}/one-shot-prompt.md << 'PROMPT_EOF'
$ARGUMENTS
PROMPT_EOF
```

4. Run the CLI command with --plan-only, --file, and --slug:

```bash
erk one-shot --plan-only --file .erk/scratch/sessions/${CLAUDE_SESSION_ID}/one-shot-prompt.md --slug "${BRANCH_SLUG}"
```

5. Clean up the scratch file:

```bash
rm -f .erk/scratch/sessions/${CLAUDE_SESSION_ID}/one-shot-prompt.md
```

6. Display the output to the user, which includes the PR URL and workflow run URL.

If the command fails, display the error message.
