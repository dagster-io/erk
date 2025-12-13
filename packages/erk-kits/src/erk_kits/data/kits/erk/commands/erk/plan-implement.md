---
description: Execute the implementation plan from .impl/ folder in current directory
erk:
  kit: erk
---

# /erk:plan-implement

## Prerequisites

- Must be in a worktree directory with `.impl/` folder
- `.impl/plan.md` should contain a valid implementation plan

---

## Agent Instructions

### Step 0: Initialize

```bash
erk kit exec erk impl-init --json
```

If validation fails, display error and stop. Use returned `phases` for TodoWrite entries.

### Step 1: Read Plan and Load Context

Read `.impl/plan.md` to understand:

- Overall goal and context
- Context & Understanding sections (API quirks, architectural insights, pitfalls)
- Implementation phases and dependencies
- Success criteria

**Context Consumption**: Plans contain expensive discoveries. Ignoring `[CRITICAL:]` tags, "Related Context:" subsections, or "DO NOT" items causes repeated mistakes.

### Step 2: Load Related Documentation

If plan contains "Related Documentation" section, load listed skills via Skill tool and read listed docs.

### Step 3: Create TodoWrite Entries

Create todo entries for each phase from impl-init output.

### Step 4: Signal GitHub Started

```bash
erk kit exec erk impl-signal started 2>/dev/null || true
```

### Step 5: Execute Each Phase Sequentially

For each phase:

1. **Mark phase as in_progress**
2. **Read task requirements** carefully
3. **Implement code AND tests together**:
   - Load `dignified-python-313` skill for coding standards
   - Load `fake-driven-testing` skill for test patterns
   - Follow project AGENTS.md standards
4. **Mark phase as completed**:
   ```bash
   erk kit exec erk mark-step <step_number>
   ```
   **NEVER** run multiple `mark-step` commands in parallel - use batching: `mark-step 1 2 3`
5. **Report progress**: changes made, what's next

**Progress Tracking:**

- `.impl/plan.md` is immutable - NEVER edit during implementation
- `.impl/progress.md` is mutable - use `mark-step` command to update

### Step 6: Report Progress

After each phase: report changes made and what's next.

### Step 7: Final Verification

Confirm all tasks executed, success criteria met, note deviations, summarize changes.

### Step 8: Signal GitHub Ended

```bash
erk kit exec erk impl-signal ended 2>/dev/null || true
```

### Step 8.5: Verify .impl/ Preserved

**CRITICAL GUARDRAIL**: Verify the .impl/ folder was NOT deleted.

```bash
erk kit exec erk impl-verify
```

If this fails, you have violated instructions. The .impl/ folder must be preserved for user review.

### Step 9: Run CI Iteratively

1. If `.erk/post-implement.md` exists: follow its instructions
2. Otherwise: check CLAUDE.md/AGENTS.md for CI commands

After CI passes:

- `.worker-impl/`: delete folder, commit cleanup, push
- `.impl/`: **NEVER DELETE** - leave for user review (no auto-commit)

### Step 10: Create/Update PR (if .worker-impl/ present)

**Only if .worker-impl/ was present:**

```bash
gh pr create --fill --label "ai-generated" || gh pr edit --add-label "ai-generated"
```

Then validate PR rules:

```bash
erk pr check
```

If checks fail, display output and warn user.

### Step 11: Output Format

- **Start**: "Executing implementation plan from .impl/plan.md"
- **Each phase**: "Phase X: [brief description]" with code changes
- **End**: "Plan execution complete. [Summary]"
