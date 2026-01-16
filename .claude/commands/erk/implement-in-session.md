---
description: Implement plan in current session - saves to GitHub, creates worktree, runs implementation
---

# /erk:implement-in-session

Implements a plan within the current Claude Code session by:

1. Saving the plan to GitHub as an issue
2. Creating a new worktree with P-naming pattern
3. Changing directory to the worktree
4. Running post-create hooks (venv activation)
5. Executing implementation steps

## Prerequisites

- Must be in a git repository managed by erk
- Must have a plan in `~/.claude/plans/` (from plan mode)
- GitHub CLI (`gh`) must be authenticated

## When to Use This Command

Use this command when you've finished planning in plan mode and want to implement in a **new worktree** within the same session.

**Key difference from `/erk:system:impl-execute`**: This command creates a new worktree, while `impl-execute` implements in the current worktree.

## When NOT to Use This Command

- **After `/erk:plan-save`**: The plan is already saved. Use `erk implement <issue-number>` instead.
- **When implementing an existing GitHub issue**: Use `erk implement <issue-number>`.
- **When you want to implement in current worktree**: Use `/erk:system:impl-execute`.

---

## Agent Instructions

### Step 1: Extract Session ID

Get the session ID by reading the `session:` line from the `SESSION_CONTEXT` reminder in your conversation context (e.g., `session: a8e2cb1d-...`). This value is already visible - just copy it directly, no tools needed.

### Step 2: Save Plan to GitHub

Save the current plan to GitHub and capture the issue number:

```bash
erk exec plan-save-to-issue --format json --session-id="<session-id>"
```

Parse the JSON output to get:

- `issue_number`: The created issue number
- `title`: The issue title (for branch naming)

If this fails, display the error and stop.

### Step 3: Create Worktree from Plan

Create a new worktree using the saved plan issue:

```bash
erk wt create --from-plan <issue_number> --json --stay
```

This command:

- Creates worktree with P-naming pattern (e.g., `P123-fix-auth-bug-01-15-1430`)
- Creates `.impl/` folder with `plan.md` and `issue.json`
- Runs post-create hooks from `.erk/config.toml` (e.g., `uv sync`)
- Returns JSON with `worktree_path`

The `--stay` flag prevents automatic shell navigation since we'll `cd` manually.

Parse the JSON output to get the `worktree_path`.

If this fails, display the error and stop.

### Step 4: Change Directory to Worktree

Use Bash to change to the new worktree:

```bash
cd <worktree_path>
```

Then verify the change succeeded:

```bash
pwd
```

### Step 5: Run impl-init

Initialize implementation tracking:

```bash
erk exec impl-init --json
```

This validates `.impl/` is set up correctly. Use the returned `phases` for TodoWrite entries.

If this fails, display the error and stop.

### Step 6: Read Plan and Load Context

Read `.impl/plan.md` to understand:

- Overall goal and context
- Context & Understanding sections (API quirks, architectural insights, pitfalls)
- Implementation phases and dependencies
- Success criteria

**Context Consumption**: Plans contain expensive discoveries. Ignoring `[CRITICAL:]` tags, "Related Context:" subsections, or "DO NOT" items causes repeated mistakes.

### Step 7: Load Related Documentation

If plan contains "Related Documentation" section, load listed skills via Skill tool and read listed docs.

### Step 8: Create TodoWrite Entries

Create todo entries for each phase from impl-init output.

### Step 9: Signal GitHub Started

```bash
erk exec impl-signal started --session-id="<session-id>" 2>/dev/null || true
```

This also deletes the Claude plan file (from `~/.claude/plans/`) since:

- The content has been saved to GitHub issue
- The content has been snapshotted to `.erk/scratch/`
- Keeping it could cause confusion if the user tries to re-save

### Step 10: Execute Each Phase Sequentially

For each phase:

1. **Mark phase as in_progress** (in TodoWrite)
2. **Read task requirements** carefully
3. **Implement code AND tests together**:
   - Load `dignified-python` skill for coding standards
   - Load `fake-driven-testing` skill for test patterns
   - Follow project AGENTS.md standards
4. **Mark phase as completed** (in TodoWrite)
5. **Report progress**: changes made, what's next

**Important:** `.impl/plan.md` is immutable - NEVER edit during implementation

### Step 11: Report Progress

After each phase: report changes made and what's next.

### Step 12: Final Verification

Confirm all tasks executed, success criteria met, note deviations, summarize changes.

### Step 13: Signal GitHub Ended

```bash
erk exec impl-signal ended --session-id="<session-id>" 2>/dev/null || true
```

### Step 14: Verify .impl/ Preserved

**CRITICAL GUARDRAIL**: Verify the .impl/ folder was NOT deleted.

```bash
erk exec impl-verify
```

If this fails, you have violated instructions. The .impl/ folder must be preserved for user review.

### Step 15: Run CI Iteratively

1. If `.erk/prompt-hooks/post-plan-implement-ci.md` exists: follow its instructions
2. Otherwise: check CLAUDE.md/AGENTS.md for CI commands

After CI passes, clean up `.worker-impl/` if present:

```bash
if [ -d .worker-impl/ ]; then
  git rm -rf .worker-impl/
  git commit -m "Remove .worker-impl/ after implementation"
  git push
fi
```

**CRITICAL**: Never delete `.impl/` - leave for user review (no auto-commit).

### Step 16: Create/Update PR (if .worker-impl/ present)

**Only if .worker-impl/ was present:**

```bash
gh pr create --fill --label "ai-generated" || gh pr edit --add-label "ai-generated"
```

Then validate PR rules:

```bash
erk pr check
```

If checks fail, display output and warn user.

### Step 17: Output Format

- **Start**: "Saving plan to GitHub..."
- **After save**: "Plan saved as issue #X. Creating worktree..."
- **After worktree**: "Worktree created at <path>. Starting implementation..."
- **Each phase**: "Phase X: [brief description]" with code changes
- **End**: "Plan execution complete. [Summary]"

### Step 18: Submit PR

After all phases complete and CI passes, submit the PR:

```
/erk:pr-submit
```

This delegates to `erk pr submit` which handles commit message generation, Graphite submission, and PR metadata.

---

## Command Flow Diagram

```
Session with plan in ~/.claude/plans/<slug>.md
    │
    ▼
erk exec plan-save-to-issue --session-id="..." --format json
    │ Returns: {"issue_number": 123, "title": "Fix auth bug", ...}
    ▼
erk wt create --from-plan 123 --json --stay
    │ Creates: P123-fix-auth-bug-01-15-1430/
    │ Sets up: .impl/plan.md, .impl/issue.json
    │ Runs: post-create hooks (uv sync, etc.)
    │ Returns: {"worktree_path": "/path/to/worktree", ...}
    ▼
cd /path/to/worktree
    │
    ▼
erk exec impl-init --json
    │ Validates .impl/, returns phases
    ▼
erk exec impl-signal started --session-id="..."
    │ Deletes Claude plan file (now saved to GitHub)
    ▼
Load skills (dignified-python, fake-driven-testing)
    │
    ▼
Execute plan phases with TodoWrite tracking
    │
    ▼
erk exec impl-signal ended --session-id="..."
    │
    ▼
/erk:pr-submit
```

---

## Related Commands

- `/erk:system:impl-execute` - Implement in current worktree (no new worktree)
- `/erk:plan-save` - Save plan only, don't implement (for defer-to-later workflow)
- `/erk:plan-implement-here` - Implement from existing GitHub issue (skips save step)
