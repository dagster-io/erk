---
description: Execute the implementation plan from .impl/ folder in current directory
---

# /erk:plan-implement

This command reads and executes the `.impl/plan.md` file from the current directory. It is designed to be run after switching to a worktree created by `/erk:save-context-enriched-plan` and `/erk:create-wt-from-plan-file`.

## Usage

```bash
/erk:plan-implement
```

## Prerequisites

- Must be in a worktree directory that contains `.impl/` folder
- Typically run after `erk checkout <branch>`
- `.impl/plan.md` should contain a valid implementation plan

## What Happens

When you run this command:

1. Verifies `.impl/plan.md` exists in the current directory
2. Reads and parses the implementation plan
3. Creates todo list for tracking progress
4. Executes each phase of the plan sequentially
5. Updates `.impl/progress.md` with step completions
6. Provides progress updates and summary

## Expected Outcome

- Implementation plan executed according to specifications
- Code changes follow project coding standards (if defined)
- Clear progress tracking and completion summary

---

## Agent Instructions

You are executing the `/erk:plan-implement` command. Follow these steps carefully:

### Step 0: Validate Environment

Run the kit command to validate prerequisites:

```bash
dot-agent run erk check-impl --dry-run
```

This validates:

- .impl/ folder exists
- plan.md exists
- progress.md exists
- issue.json format (if present)

If validation fails, the kit command outputs a clear error message. Display it to the user and stop.

### Step 1: Verify .impl/plan.md Exists

Check that `.impl/plan.md` exists in the current directory.

If not found:

```
❌ Error: No plan folder found in current directory

This command must be run from a worktree directory that contains a .impl/ folder with plan.md.

To create a worktree with a plan:
1. Run /erk:save-context-enriched-plan to save your enhanced plan to disk
2. Run /erk:create-wt-from-plan-file to create a worktree from the plan
3. Run: erk checkout <branch>
4. Then run: claude --permission-mode acceptEdits "/erk:plan-implement"
```

### Step 2: Read the Plan File

Read `.impl/plan.md` from the current directory to get the full implementation plan.

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

### Step 3: Load Related Documentation

If the plan contains a "Related Documentation" section:

1. **Load skills**: For each skill listed, use the Skill tool to load it
2. **Read docs**: For each doc listed, use the Read tool to load it
3. **Keep context**: This documentation informs your implementation approach

Example section to look for:

```markdown
## Related Documentation

**Skills:**

- `dignified-python-313`

**Docs:**

- [Kit CLI Testing](docs/agent/testing/kit-cli-testing.md)
```

### Step 4: Check for GitHub Issue Reference

Progress tracking via GitHub comments is available if `.impl/issue.json` exists.
The kit CLI commands handle all logic automatically - no manual setup required.

### Step 5: Create TodoWrite Entries

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

### Step 6: Post Start Comment to GitHub Issue

Post a single comprehensive start comment with implementation context:

```bash
dot-agent run erk post-start-comment 2>/dev/null || true
```

This posts a comment containing:

- Worktree name and branch name
- Complete list of all implementation steps
- Structured YAML metadata

If issue tracking is not enabled (no valid issue.json), this will output an info message and exit gracefully.

### Step 7: Update Local Implementation Timestamp

Update the GitHub issue's plan-header metadata with the local implementation start time:

```bash
dot-agent run erk mark-impl-started 2>/dev/null || true
```

This updates:

- `last_local_impl_at` field in the plan-header metadata block
- Used by `erk dash` to show relative time since last local implementation

If issue tracking is not enabled, this will exit gracefully.

### Step 8: Execute Each Phase Sequentially

**🔴 MANDATORY: Tests Required With All Changes**

Every implementation phase that modifies code MUST include corresponding tests. This is non-negotiable:

- **No code change is complete without tests** - If you modify behavior, you must test it
- **Write tests alongside code** - Not as a separate "testing phase" at the end
- **Load `fake-driven-testing` skill FIRST** before writing any test code
- **Follow the 5-layer strategy** - Most tests should be Layer 4 (business logic over fakes)

If a plan phase does not explicitly mention tests, you MUST still write them. The absence of test requirements in a plan step does not excuse omitting tests.

For each phase in the plan:

1. **Mark phase as in_progress** before starting
2. **Read task requirements** carefully
3. **Check relevant coding standards** from project documentation (if available)
4. **Implement the code AND tests together** following these standards:
   - NEVER use try/except for control flow - use LBYL (Look Before You Leap)
   - Use Python 3.13+ type syntax (list[str], str | None, NOT List[str] or Optional[str])
   - NEVER use `from __future__ import annotations`
   - Use ABC for interfaces, never Protocol
   - Check path.exists() before path.resolve() or path.is_relative_to()
   - Use absolute imports only
   - Use click.echo() in CLI code, not print()
   - Add check=True to subprocess.run()
   - Keep indentation to max 4 levels - extract helpers if deeper
   - **When writing tests**: Load the `fake-driven-testing` skill FIRST, then follow these principles:
     - Use the 5-layer defense-in-depth strategy (70% of tests should be Layer 4: business logic over fakes)
     - Write tests over in-memory fakes, not real implementations
     - Use `tmp_path` fixture - NEVER hardcode paths
     - Use `CliRunner` for CLI tests, not subprocess
     - Update all layers (ABC/Real/Fake/DryRun) when changing interfaces
     - No speculative tests - only test actively implemented code
     - Consult `fake-driven-testing` skill references for patterns, workflows, and anti-patterns
5. **Verify implementation** against standards
6. **Mark phase as completed** when done:

   ```bash
   dot-agent run erk mark-step <step_number>
   ```

   **IMPORTANT - Sequential Execution Required:**
   - **NEVER** run multiple `mark-step` commands in parallel
   - This command modifies `.impl/progress.md` and parallel execution causes lost updates
   - If marking multiple steps, use a single command: `dot-agent run erk mark-step 1 2 3`

7. **Verify progress** (optional):
   ```bash
   dot-agent run erk get-progress
   ```
8. **Report progress**: what was done and what's next
9. **Move to next phase**

**IMPORTANT - Progress Tracking:**

The new `.impl/` folder structure separates concerns:

1. **`.impl/plan.md` (immutable reference)**: Contains Objective, Context & Understanding, Implementation Steps/Phases, Testing. This file should NEVER be edited during implementation.

2. **`.impl/progress.md` (mutable tracking)**: Contains checkboxes for all steps extracted from plan.md. This is the ONLY file that should be updated during implementation.

When updating progress:

- Only edit `.impl/progress.md` - never touch `.impl/plan.md`
- Use the `mark-step` kit CLI command to update progress
- The command automatically updates YAML frontmatter and regenerates checkboxes

### Step 9: Follow Erk Coding Standards

Project coding standards (if defined) OVERRIDE any conflicting guidance in the plan.

Key standards:

- Exception handling: LBYL, not EAFP
- Type annotations: Modern Python 3.13+ syntax
- Path operations: Check .exists() first
- Dependency injection: ABC, not Protocol
- Imports: Absolute only
- CLI: Use click.echo()
- Code style: Max 4 indentation levels

Testing standards (load `fake-driven-testing` skill for complete guidance):

- Layer distribution: 5% fake tests / 10% integration sanity / 10% pure unit / 70% business logic over fakes / 5% e2e
- Always use fakes: Write business logic tests over in-memory fakes (FakeGit, FakeGh, etc.)
- Never hardcode paths: Use `tmp_path` fixture exclusively
- CLI testing: Use `CliRunner`, never subprocess
- Integration layer changes: Update ABC → Real → Fake → DryRun (all four)
- No speculative tests: Only test code that is actively being implemented

### Step 10: Report Progress

After completing each major phase, provide an update:

```
✅ Phase X complete: [Brief description]

Changes made:
- [Change 1]
- [Change 2]

Tests added:
- [Test 1]
- [Test 2]

Next: [What's coming next]
```

**🔴 IMPORTANT**: If you cannot list tests in your progress report, the phase is NOT complete. Go back and add tests before marking complete.

### Step 11: Final Verification

After all phases are complete:

1. Confirm all tasks were executed
2. Verify all success criteria are met
3. Note any deviations from the plan (with justification)
4. Provide summary of changes

### Step 12: Run Project CI

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

### Step 13: Mark Implementation Ended

After completing all implementation work (but before CI/PR steps), mark the implementation as ended:

```bash
dot-agent run erk mark-impl-ended 2>/dev/null || true
```

This updates:

- `.impl/local-run-state.json` with event="ended" timestamp
- GitHub issue plan-header metadata with the ended event and metadata

This step should be run after all code changes are complete but before any optional CI or PR submission steps.

### Step 14: Run CI and Fix Issues Iteratively

Run iterative CI to validate all changes before completion.

**Check for repo-specific CI configuration:**

1. Check if `.erk/post-implement.md` exists in the repository root
2. If it exists: Read that file and follow its instructions (it contains the complete CI workflow for this repo)
3. If it does not exist: Use the default erk CI process below

**Default CI Process (no `.erk/post-implement.md` found):**

If no repo-specific CI configuration exists, skip automated CI and inform the user:

```
⚠️ No .erk/post-implement.md found. Skipping automated CI validation.
   Run your project's CI manually before submitting.
```

**After CI passes (or if .impl/ folder):**

If in .worker-impl/ folder:

1. Delete .worker-impl/ folder: `rm -rf .worker-impl/`
2. Stage deletion: `git add .worker-impl/`
3. Commit: `git commit -m "Clean up worker implementation artifacts after implementation"`
4. Push: `git push`

If in .impl/ folder:

1. DO NOT delete .impl/
2. DO NOT auto-commit
3. Leave changes for user review

### Step 15: Create/Update PR (if .worker-impl/ present)

**Only if .worker-impl/ was present:**

Use gh CLI to create or update PR:

```bash
gh pr create --fill --label "ai-generated" || gh pr edit --add-label "ai-generated"
```

### Step 16: Validate PR Rules

After creating/updating the PR, run the PR check command to validate:

```bash
erk pr check
```

This validates:

- Issue closing reference (Closes #N) is present when `.impl/issue.json` exists
- PR body contains the standard checkout footer

If any checks fail, display the output and warn the user.

### Step 17: Output Format

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
