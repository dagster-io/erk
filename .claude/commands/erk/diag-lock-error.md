---
description: Create diagnostic report for git index.lock errors from current context
---

# Diagnostic Report: Git Lock Error

When a git operation fails with `fatal: Unable to create '.../.git/index.lock': File exists`, this command collects diagnostic information and uploads it as a GitHub gist for analysis.

## Usage

Run this command when you encounter a git index.lock error:

```bash
/erk:diag-lock-error
```

## Implementation

### Step 1: Identify the Lock Error in Context

Search the current conversation context for the git index.lock error. Look for:

- Tool results containing `fatal: Unable to create` and `index.lock`
- The specific repository path where the error occurred
- The command that triggered the error

If no lock error is found in the recent context, report "No git index.lock error found in current context" and stop.

### Step 2: Collect Diagnostic Data

Create a temporary directory and collect all diagnostic files:

```bash
DIAG_DIR=$(mktemp -d)
echo "Collecting diagnostics in $DIAG_DIR"
```

#### 2a. Error Context

Write the error message and context from the conversation to a file:

```bash
cat > "$DIAG_DIR/01-error-context.txt" << 'EOF'
# Error Context
<paste the error message and surrounding context here>
EOF
```

#### 2b. Git Status

```bash
git status > "$DIAG_DIR/02-git-status.txt" 2>&1
```

#### 2c. Lock File State

Check if the lock file exists and get details:

```bash
LOCK_FILE=".git/index.lock"
if [ -f "$LOCK_FILE" ]; then
    echo "Lock file EXISTS" > "$DIAG_DIR/03-lock-state.txt"
    ls -la "$LOCK_FILE" >> "$DIAG_DIR/03-lock-state.txt"
    # Try to get file creation time (macOS)
    stat "$LOCK_FILE" >> "$DIAG_DIR/03-lock-state.txt" 2>&1
else
    echo "Lock file does NOT exist" > "$DIAG_DIR/03-lock-state.txt"
fi
```

#### 2d. Git Processes

```bash
ps aux | grep -E '[g]it|[c]laude' | head -20 > "$DIAG_DIR/04-processes.txt" 2>&1
```

#### 2e. Recent Erk Commands

```bash
if [ -f ~/.erk/command_history.jsonl ]; then
    tail -50 ~/.erk/command_history.jsonl > "$DIAG_DIR/05-erk-history.jsonl"
else
    echo "No erk command history found" > "$DIAG_DIR/05-erk-history.jsonl"
fi
```

#### 2f. Git Config

```bash
git config --list --show-origin > "$DIAG_DIR/06-git-config.txt" 2>&1
```

#### 2g. Worktree Info

```bash
git worktree list > "$DIAG_DIR/07-worktree-list.txt" 2>&1
pwd >> "$DIAG_DIR/07-worktree-list.txt"
```

#### 2h. Session ID

```bash
echo "${CLAUDE_SESSION_ID:-unknown}" > "$DIAG_DIR/08-session-id.txt"
```

### Step 3: Create Gist

Upload all files as a gist:

```bash
gh gist create --desc "Git index.lock diagnostic report - $(date +%Y-%m-%d-%H%M%S)" "$DIAG_DIR"/*
```

Capture the gist URL from the output.

### Step 4: Cleanup

```bash
rm -rf "$DIAG_DIR"
```

### Step 5: Report

Display the result:

```markdown
## Diagnostic Report Created

**Gist URL**: <gist_url>

The diagnostic report has been uploaded. Share this URL when reporting the issue.

### Files Included

1. `01-error-context.txt` - The error message and context
2. `02-git-status.txt` - Current git status
3. `03-lock-state.txt` - Lock file existence and details
4. `04-processes.txt` - Running git/claude processes
5. `05-erk-history.jsonl` - Recent erk command history
6. `06-git-config.txt` - Git configuration
7. `07-worktree-list.txt` - Git worktree information
8. `08-session-id.txt` - Claude Code session ID
```

## Notes

- This command requires `gh` CLI to be authenticated
- The gist is created as a secret (not public) by default
- Run this command immediately after encountering the error for best results
- The error context must be visible in the current conversation
