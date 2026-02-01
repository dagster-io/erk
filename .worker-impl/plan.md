# Plan: Add Progress Logging to Learn Workflow

## Goal

Make the learn workflow transparent so users understand what local data is accessed, what gets uploaded, and what happens remotely.

## Changes

### 1. `src/erk/cli/commands/land_cmd.py`

**In `_prompt_async_learn_and_continue()`** — add a sub-description under menu option 1 (after line 379):

```python
user_output("  1. Trigger async learn and continue (recommended)")
user_output("     Reads session logs, uploads to gist, runs analysis in GitHub Actions")
```

**In `_trigger_async_learn()`** — add explanation after "Triggering..." message (line 435):

```python
user_output(f"Triggering async learn for plan #{plan_issue_number}...")
user_output(
    "  Reads local session logs, preprocesses them, and uploads to a secret gist."
)
user_output(
    "  A GitHub Actions workflow then analyzes sessions and creates a documentation plan."
)
```

**In `_trigger_async_learn()`** — add result summary after success message (inside `if output.get("success"):` block, after the if/else for workflow_url):

```python
user_output(
    f"  Results will appear as a new GitHub issue linked to plan #{plan_issue_number}."
)
```

### 2. `.claude/commands/erk/learn.md`

Add **"Tell the user:"** instructions at 6 key pipeline steps:

**A. Before Step 1 (~line 29)** — Pipeline overview:

```
Learn pipeline for plan #<issue-number>:
  1. Read local session logs from ~/.claude/projects/
  2. Preprocess sessions (compress JSONL → XML, deduplicate, truncate)
  3. Upload preprocessed XML + PR comments to a secret GitHub gist
  4. Launch analysis agents (session, diff, docs check)
  5. Synthesize findings into a documentation plan
  6. Save plan as a new GitHub issue
```

**B. After Step 2 session parsing (~line 71)** — Session discovery results:

```
Found N session(s) for plan #<issue-number>:
  - N local session(s) from ~/.claude/projects/
  - N remote session(s) from GitHub Actions
```

**C. After Step 4 preprocessing (~line 211)** — Preprocessing status:

```
Preprocessing N session(s): compressing JSONL → XML, deduplicating, truncating to 20k tokens each...
```

**D. After Step 4 gist upload (~line 243)** — Upload confirmation:

```
Uploaded preprocessed sessions to secret gist: <gist_url>
  Contents: N session XML file(s), PR review comments, PR discussion comments
```

**E. Before Step 4 parallel agents (~line 249)** — Agent launch:

```
Launching analysis agents in parallel:
  - Session analyzer (1 per session file)
  - Code diff analyzer (PR #<number>)
  - Existing documentation checker
```

**F. After Step 4 agent results collected (~line 326)** — Synthesis phase:

```
Parallel analysis complete. Running sequential synthesis:
  - Identifying documentation gaps
  - Synthesizing learn plan
  - Extracting tripwire candidates
```

## Files to modify

- `src/erk/cli/commands/land_cmd.py` — 3 insertions in `_trigger_async_learn` and `_prompt_async_learn_and_continue`
- `.claude/commands/erk/learn.md` — 6 "Tell the user:" instruction blocks

## Verification

1. Run `erk land` on a branch with an unlearned plan — confirm new messages appear in the menu and trigger flow
2. Run `/erk:learn <issue>` locally — confirm the agent outputs progress messages at each step
3. Run fast-ci to ensure no regressions