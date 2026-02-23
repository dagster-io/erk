---
description: Implement a plan from GitHub issue, file path, current branch, or current .impl folder
argument-hint: "[<issue-number-or-url-or-path>]"
---

# /erk:plan-implement

Implement a plan - either from a GitHub issue, a markdown file, an existing `.impl/` folder, or by saving the current plan first.

This is the primary implementation workflow - it orchestrates:

1. Setting up the `.impl/` folder (from issue, file, existing folder, or fresh plan)
2. Executing the implementation
3. Running CI and submitting the PR

## Prerequisites

- Must be in a git repository managed by erk
- GitHub CLI (`gh`) must be authenticated
- One of:
  - An issue number, URL, or file path argument
  - An existing `.impl/` folder
  - A plan branch checked out (e.g., `plnd/...` or `P{number}-...`)
  - A plan in `~/.claude/plans/` (from plan mode)

## Usage

```bash
/erk:plan-implement                    # Use .impl/, detect from branch, or save current plan
/erk:plan-implement 2521               # Fetch and implement issue #2521
/erk:plan-implement https://github.com/owner/repo/issues/2521  # URL form
/erk:plan-implement ./my-plan.md       # Implement from local markdown file
```

---

## Agent Instructions

### Step 1: Set Up Implementation

Parse `$ARGUMENTS` and run the consolidated setup command:

- **If numeric** (e.g., `2521`): `erk exec setup-impl --issue 2521`
- **If GitHub URL** (e.g., `https://github.com/.../issues/2521`): Extract number, `erk exec setup-impl --issue 2521`
- **If path to file** (anything else non-empty): `erk exec setup-impl --file <path>`
- **If empty**: `erk exec setup-impl` (auto-detects from `.impl/`, branch, or fails)

```bash
erk exec setup-impl [--issue <N> | --file <path>]
```

This single command handles:

- Fetching plan from GitHub issue/PR (draft-PR or issue-based)
- Setting up from a local markdown file
- Auto-detecting from existing `.impl/` folder
- Auto-detecting plan number from branch name (P{number}-... or PR lookup)
- Creating/checking out the feature branch
- Creating `.impl/` folder with plan content
- Running impl-init validation
- Cleaning up `.erk/impl-context/` staging directory (git rm + commit + push)

Otherwise, generate a branch slug and set up from the specified issue:

1. Fetch the title: `gh pr view <ISSUE_ARG> --json title -q .title` (for draft-PR plans) or `gh issue view <ISSUE_ARG> --json title -q .title` (for issue plans). Try PR first, fall back to issue.
2. Generate a branch slug from the title:
   - 2-4 hyphenated lowercase words, max 30 characters
   - Capture distinctive essence, drop filler words (the, a, for, implementation, plan)
   - Prefer action verbs: add, fix, refactor, update, consolidate, extract, migrate
   - Examples: "fix-auth-session", "add-plan-validation", "refactor-gateway-abc"
3. Store as `BRANCH_SLUG`.

```bash
erk exec setup-impl --issue <ISSUE_ARG> --branch-slug="${BRANCH_SLUG}"
```

If `setup-impl` exits with code 1 and `error: "no_plan_found"`, fall back to saving the current plan:

Generate a branch slug from the plan title (the first `# ` heading in the plan file):

- 2-4 hyphenated lowercase words, max 30 characters
- Capture distinctive essence, drop filler words (the, a, for, implementation, plan)
- Prefer action verbs: add, fix, refactor, update, consolidate, extract, migrate
- Store as `BRANCH_SLUG`

Save the current plan to GitHub and capture the issue number:

```bash
erk exec plan-save --format json --session-id="${CLAUDE_SESSION_ID}" --branch-slug="${BRANCH_SLUG}"
```

Parse the JSON output to get `issue_number`, then:

```bash
erk exec setup-impl --issue <issue_number>
```

The `setup-impl` output includes `related_docs` (skills and docs to load) and `has_plan_tracking` (whether GitHub issue tracking is active).

If this fails, display the error and stop.

### Step 2: Read Plan and Load Context

Read `.impl/plan.md` to understand:

- Overall goal and context
- Context & Understanding sections (API quirks, architectural insights, pitfalls)
- Implementation phases and dependencies
- Success criteria

**Context Consumption**: Plans contain expensive discoveries. Ignoring `[CRITICAL:]` tags, "Related Context:" subsections, or "DO NOT" items causes repeated mistakes.

### Step 3: Load Related Documentation

If plan contains "Related Documentation" section, load listed skills via Skill tool and read listed docs.

### Step 4: Create TodoWrite Entries

Create todo entries for each phase from the plan.

### Step 5: Signal GitHub Started

```bash
erk exec impl-signal started --session-id="${CLAUDE_SESSION_ID}" 2>/dev/null || true
```

This also deletes the Claude plan file (from `~/.claude/plans/`) since:

- The content has been saved to GitHub issue
- The content has been snapshotted to `.erk/scratch/`
- Keeping it could cause confusion if the user tries to re-save

### Step 6: Execute Each Phase Sequentially

For each phase:

1. **Mark phase as in_progress** (in TodoWrite)
2. **Read task requirements** carefully
3. **Implement code AND tests together**:
   - Load `dignified-python-313` skill for coding standards
   - Load `fake-driven-testing` skill for test patterns
   - Follow project AGENTS.md standards
4. **Mark phase as completed** (in TodoWrite)
5. **Report progress**: changes made, what's next

**Important:** `.impl/plan.md` is immutable - NEVER edit during implementation

### Step 7: Report Progress

After each phase: report changes made and what's next.

### Step 8: Final Verification

Confirm all tasks executed, success criteria met, note deviations, summarize changes.

### Step 9: Signal GitHub Ended

```bash
erk exec impl-signal ended --session-id="${CLAUDE_SESSION_ID}" 2>/dev/null || true
```

### Step 10: Upload Session for Async Learn

```bash
erk exec upload-impl-session --session-id="${CLAUDE_SESSION_ID}" 2>/dev/null || true
```

This reads plan reference from `.impl/`, captures session info, and uploads for async learn processing.

### Step 11: Verify .impl/ Preserved

**CRITICAL GUARDRAIL**: Verify the .impl/ folder was NOT deleted.

```bash
erk exec impl-verify
```

If this fails, you have violated instructions. The .impl/ folder must be preserved for user review.

### Step 12: Run CI Iteratively

1. If `.erk/prompt-hooks/post-plan-implement-ci.md` exists: follow its instructions
2. Otherwise: check CLAUDE.md/AGENTS.md for CI commands

**CRITICAL**: Never delete `.impl/` - leave for user review (no auto-commit).

### Step 13: Submit PR

Push the branch and create or update the PR using the Graphite-aware submit pipeline:

```bash
erk pr submit
```

This handles pushing commits, creating/updating the PR, generating the PR description, and enhancing with Graphite stack metadata when available.

After successful submission, signal lifecycle transition:

```bash
erk exec impl-signal submitted 2>/dev/null || true
```

Then validate PR completion invariants:

```bash
erk pr check --stage=impl
```

This validates PR submission readiness including implementation-specific checks
(e.g., `.erk/impl-context/` must be cleaned up). If checks fail, display output and warn user.

### Step 14: Output Format

- **Start**: "Setting up implementation..." or "Fetching plan from issue #X..."
- **After setup**: "Implementation environment ready, reading plan..."
- **Each phase**: "Phase X: [brief description]" with code changes
- **End**: "Plan execution complete. [Summary]"

---

## Related Commands

- `/erk:plan-save` - Save plan only, don't implement (for defer-to-later workflow)
- `/erk:replan` - Re-plan an existing issue with current codebase state
