# Collect Agent Results

Collect outputs from background analysis agents and save to scratch storage.

## Collect via TaskOutput

Use TaskOutput to retrieve findings from each launched agent:

```
TaskOutput(task_id: <agent-task-id>, block: true)
```

Collect all results before proceeding to synthesis.

Tell the user:

```
Parallel analysis complete. Running sequential synthesis:
  - Identifying documentation gaps
  - Synthesizing learn plan
  - Extracting tripwire candidates
```

## Write Results to Scratch Storage

**CRITICAL:** Use the Write tool to save each agent's output. Do NOT use bash heredoc syntax — it fails with large outputs.

First, create the directory:

```bash
mkdir -p .erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/
```

Then use the Write tool for each agent output:

1. **Session analysis results** — Write to `.erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/session-<session-id>.md`
2. **Diff analysis results** — Write to `.erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/diff-analysis.md`
3. **Existing docs check results** — Write to `.erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/existing-docs-check.md`
4. **PR comment analysis results** — Write to `.erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/pr-comments-analysis.md`

Only write files for agents that were actually launched. Skip files for agents that were not applicable (e.g., no diff-analysis.md if no PR).

**Why Write tool instead of heredoc?**

- Agent outputs can be 10KB+ of markdown
- Bash heredoc fails silently with special characters
- Write tool guarantees the file is created with exact content

## Verify Files Exist

**Verify files exist before launching gap-identifier:**

```bash
ls -la .erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/
```

Confirm you see the expected files before proceeding. If any files are missing, the Write tool call failed and must be retried.
