# Plan: Make `/erk:one-shot` handle long instructions reliably

## Context

The `/erk:one-shot` Claude Code command currently passes the instruction as a raw CLI argument:
```bash
erk one-shot "$ARGUMENTS"
```

For long instructions containing help text, stack traces, or multi-line content, this is fragile:
- Shell quoting issues with special characters in `$ARGUMENTS`
- The CLI then passes the instruction to `gh workflow run -f instruction=<text>`, which has its own limits

## Changes

### 1. Add `--file` option to `erk one-shot` CLI
**File:** `src/erk/cli/commands/one_shot.py`

Add a `--file` / `-f` option that reads the instruction from a file instead of a CLI argument. Make the `INSTRUCTION` argument optional when `--file` is provided.

### 2. Commit instruction to branch in dispatch
**File:** `src/erk/cli/commands/one_shot_dispatch.py`

After branch checkout (before the currently-empty commit):
- Write instruction to `.impl/task.md`
- Stage via `ctx.git.commit.stage_files()`
- Commit includes the instruction file (no longer empty)
- Truncate the `instruction` value in workflow inputs to 500 chars (it's now just for display; the real instruction is in the committed file)

### 3. Update workflow to prefer committed file
**File:** `.github/workflows/one-shot.yml`

Change "Write instruction to .impl/task.md" step to check if the file already exists from the commit. Only write from env var as fallback:
```yaml
if [ -f .impl/task.md ]; then
  echo "Instruction already committed to .impl/task.md"
else
  mkdir -p .impl
  printf '%s\n' "$INSTRUCTION" > .impl/task.md
fi
```

### 4. Update the Claude Code command
**File:** `.claude/commands/erk/one-shot.md`

Instead of passing `$ARGUMENTS` as a shell argument, instruct Claude to:
1. Write the instruction text to a temp file
2. Call `erk one-shot --file <temp-file>`

### 5. Update tests
**File:** `tests/commands/one_shot/test_one_shot_dispatch.py`

- Update happy path to verify `.impl/task.md` staging and truncated workflow input
- Add test for `--file` option
- Add test with long instruction verifying truncation

## Verification

1. `pytest tests/commands/one_shot/`
2. `ty` and `ruff` on modified files
3. Manual: `erk one-shot --file /tmp/test.txt --dry-run`