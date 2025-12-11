---
description: Execute the implementation plan from .plan/ folder in current directory
---

# /erk:implement-plan

This command reads and executes the `.plan/plan.md` file from the current directory. It is designed to be run after switching to a worktree created by `/erk:persist-plan` and `/erk:create-planned-wt`.

## Usage

```bash
/erk:implement-plan
```

## Prerequisites

- Must be in a worktree directory that contains `.plan/` folder
- Typically run after `erk checkout <branch>`
- `.plan/plan.md` should contain a valid implementation plan

## What Happens

When you run this command:

1. Verifies `.plan/plan.md` exists in the current directory
2. Reads and parses the implementation plan
3. Creates todo list for tracking progress
4. Executes each phase of the plan sequentially
5. Updates `.plan/progress.md` with step completions
6. Provides progress updates and summary

## Expected Outcome

- Implementation plan executed according to specifications
- Code changes follow project coding standards (if defined)
- Clear progress tracking and completion summary

---

## Agent Instructions

You are executing the `/erk:implement-plan` command. Follow these steps carefully:

### Step 1: Verify .plan/plan.md Exists

Check that `.plan/plan.md` exists in the current directory.

If not found:

```
❌ Error: No plan folder found in current directory

This command must be run from a worktree directory that contains a .plan/ folder with plan.md.

To create a worktree with a plan:
1. Run /erk:persist-plan to save your enhanced plan to disk
2. Run /erk:create-planned-wt to create a worktree from the plan
3. Run: erk checkout <branch>
4. Then run: claude --permission-mode acceptEdits "/erk:implement-plan"
```

### Step 2: Read the Plan File

Read `.plan/plan.md` from the current directory to get the full implementation plan.

Parse the plan to understand:

- Overall goal and context
- **Context & Understanding sections** - Extract valuable discoveries and insights:
  - **API/Tool Quirks**: Undocumented behaviors, timing issues, edge cases
  - **Architectural Insights**: WHY decisions were made, not just what
  - **Domain Logic & Business Rules**: Non-obvious requirements and constraints
  - **Complex Reasoning**: Approaches considered, rejected alternatives and why
  - **Known Pitfalls**: What looks right but causes problems
- Individual phases or tasks
- **Critical warnings** marked with `[CRITICAL:]` tags in implementation steps
- **Related Context subsections** that link steps to Context & Understanding
- Dependencies between tasks
- Success criteria
- Any special requirements or constraints

**IMPORTANT - Context Consumption:**

The Context & Understanding section contains expensive discoveries made during planning. Ignoring this context may cause:

- Implementing solutions that were already proven not to work
- Missing security vulnerabilities or race conditions
- Violating discovered constraints (API limitations, timing requirements)
- Making mistakes that were explicitly documented as pitfalls

Pay special attention to:

- `[CRITICAL:]` tags in steps - these are must-not-miss warnings
- "Related Context:" subsections - these explain WHY and link to detailed context
- "DO NOT" items in Known Pitfalls - these prevent specific bugs
- Rejected approaches in Complex Reasoning - these explain what doesn't work

### Step 2.5: Understanding Progress.md Structure

The `.plan/progress.md` file tracks implementation progress using checkboxes AND YAML front matter (for files created after 2025-01-17).

**Front Matter Format:**

```yaml
---
completed_steps: N
total_steps: M
---

# Progress Tracking

- [ ] 1. First step
- [x] 2. Second step (completed)
- [ ] 3. Third step
```

**Key Points:**

- **Checkboxes are source of truth**: `- [ ]` (incomplete) and `- [x]` (complete)
- **Front matter must stay synchronized**: The `completed_steps` field must match the count of checked boxes
- **Progress emoji indicators**: Used by `erk status` to show: ⚪ (0%), 🟡 (1-99%), 🟢 (100%)
- **Backward compatibility**: Older progress.md files may lack front matter - this is OK, just skip front matter updates for those files

**When to Update Front Matter:**

When marking a step complete, you MUST:

1. Change the checkbox from `- [ ]` to `- [x]`
2. IF the file starts with `---` (has front matter):
   - Count the total number of checked boxes in the entire file
   - Update the `completed_steps:` line with the new count
   - DO NOT change the `total_steps:` line
3. IF the file doesn't start with `---` (no front matter):
   - Skip the front matter update entirely
   - Just update the checkbox

This keeps progress indicators accurate in real-time during plan execution.

### Step 3: Create TodoWrite Entries

Create todo list entries for each major phase in the plan to track progress.

- Use clear, descriptive task names
- Set all tasks to "pending" status initially
- Include both `content` and `activeForm` for each task

Example:

```json
[
  {
    "content": "Create noun-based command structure",
    "status": "pending",
    "activeForm": "Creating noun-based command structure"
  },
  {
    "content": "Merge init and install commands",
    "status": "pending",
    "activeForm": "Merging init and install commands"
  }
]
```

### Step 4: Execute Each Phase Sequentially

For each phase in the plan:

1. **Mark phase as in_progress** before starting
2. **Read task requirements** carefully
3. **Check relevant coding standards** from project documentation (if available)
4. **Implement the code** following these standards:
   - NEVER use try/except for control flow - use LBYL (Look Before You Leap)
   - Use Python 3.13+ type syntax (list[str], str | None, NOT List[str] or Optional[str])
   - NEVER use `from __future__ import annotations`
   - Use ABC for interfaces, never Protocol
   - Check path.exists() before path.resolve() or path.is_relative_to()
   - Use absolute imports only
   - Use click.echo() in CLI code, not print()
   - Add check=True to subprocess.run()
   - Keep indentation to max 4 levels - extract helpers if deeper
   - If plan mentions tests, follow patterns in project test documentation (if available)
5. **Verify implementation** against standards
6. **Mark phase as completed** when done:
   - Edit `.plan/progress.md` to change checkbox from `- [ ]` to `- [x]`
   - If front matter exists (file starts with `---`):
     - Count total checked boxes in the entire file
     - Edit the `completed_steps:` line in front matter with new count
     - Do NOT change the `total_steps:` line
   - If no front matter exists, skip the front matter update
7. **Report progress**: what was done and what's next
8. **Move to next phase**

**IMPORTANT - Progress Tracking:**

The new `.plan/` folder structure separates concerns:

1. **`.plan/plan.md` (immutable reference)**: Contains Objective, Context & Understanding, Implementation Steps/Phases, Testing. This file should NEVER be edited during implementation.

2. **`.plan/progress.md` (mutable tracking)**: Contains checkboxes for all steps extracted from plan.md. This is the ONLY file that should be updated during implementation.

When updating progress:

- Only edit `.plan/progress.md` - never touch `.plan/plan.md`
- Mark checkboxes as completed: `- [x]` instead of `- [ ]`
- Simple find-replace operation: no risk of corrupting the plan
- Progress format example:

  ```markdown
  # Progress Tracking

  - [ ] 1. Create module
  - [x] 2. Add tests
  - [ ] 3. Update documentation
  ```

**Example progress.md update:**

Before:

```yaml
---
completed_steps: 2
total_steps: 5
---

# Progress Tracking

- [x] 1. Create module
- [x] 2. Add tests
- [ ] 3. Update documentation  ← marking this complete
- [ ] 4. Add integration tests
- [ ] 5. Update changelog
```

After:

```yaml
---
completed_steps: 3  ← incremented from 2 to 3
total_steps: 5      ← unchanged
---

# Progress Tracking

- [x] 1. Create module
- [x] 2. Add tests
- [x] 3. Update documentation  ← marked complete
- [ ] 4. Add integration tests
- [ ] 5. Update changelog
```

### Step 5: Follow Erk Coding Standards

Project coding standards (if defined) OVERRIDE any conflicting guidance in the plan.

Key standards:

- Exception handling: LBYL, not EAFP
- Type annotations: Modern Python 3.13+ syntax
- Path operations: Check .exists() first
- Dependency injection: ABC, not Protocol
- Imports: Absolute only
- CLI: Use click.echo()
- Code style: Max 4 indentation levels

### Step 6: Report Progress

After completing each major phase, provide an update:

```
✅ Phase X complete: [Brief description]

Changes made:
- [Change 1]
- [Change 2]

Next: [What's coming next]
```

### Step 7: Final Verification

After all phases are complete:

1. Confirm all tasks were executed
2. Verify all success criteria are met
3. Note any deviations from the plan (with justification)
4. Provide summary of changes

### Step 8: Final Verification

After completing all implementation steps:

1. **Check for project documentation** at repository root:
   - Look for `CLAUDE.md` or `AGENTS.md` files
   - If found, read these files for CI/testing instructions
   - Follow any specific commands or workflows documented there

2. **Run project-specific CI checks**:
   - If documentation specifies CI commands, use those
   - Otherwise, run common checks if tools are available:
     - Linting: `ruff check .` or equivalent
     - Type checking: `pyright` or equivalent
     - Tests: `pytest` or equivalent
     - Formatting: `ruff format .` or equivalent

3. **Verify all tests pass** before considering implementation complete

4. **Address any failures** by returning to relevant implementation steps

### Step 9: Output Format

Structure your output clearly:

- **Start**: "Executing implementation plan from .PLAN.md"
- **Each phase**: "Phase X: [brief description]" with code changes
- **Progress updates**: Regular status reports
- **End**: "Plan execution complete. [Summary of what was implemented]"

## Requesting Clarification

If clarification is needed during execution:

1. Explain what has been completed so far
2. Clearly state what needs clarification
3. Suggest what information would help proceed
4. Wait for user response before continuing

## Important Notes

- **No time estimates**: Never provide time-based estimates or completion predictions
- **Standards first**: Project coding standards (if defined) override plan instructions
- **Sequential execution**: Complete phases in order unless plan specifies otherwise
- **Progress tracking**: Keep todo list updated throughout
- **User communication**: Provide clear, concise progress updates
