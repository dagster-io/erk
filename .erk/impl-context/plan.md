# Documentation Plan: Add `erk wt create-from` command for allocating slots to existing branches

## Context

PR #7712 implemented the `erk wt create-from <branch>` command, which enables users to allocate worktree pool slots for existing branches (local or remote). This complements the existing `erk wt create` command that creates new branches and allocates slots simultaneously. The implementation followed erk's established patterns: dignified Python standards, fake-driven testing, gateway ABC usage, and CLI conventions with styled messages and remediation steps.

The implementation session revealed several documentation opportunities. First, the new command itself requires user-facing documentation explaining when to use it versus related commands (`wt create`, `wt checkout`). Second, the session uncovered a critical workflow gap: agents editing Python files should run `make format` before CI checks, not after failures. Third, the PR review process demonstrated an efficient batch thread resolution pattern using the JSON API that should be documented for future agents.

Beyond the command itself, the session exposed a subtle haiku agent behavior issue: vague delegation prompts like "verify threads resolved" cause the agent to describe skills rather than execute commands. This non-obvious behavior warrants a tripwire to prevent future agent confusion.

## Raw Materials

https://gist.github.com/schrockn/18cfd7e3b1214040ad4338dfbb92c510

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 11    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 2     |
| Potential tripwires (score2-3) | 5     |

## Documentation Items

### HIGH Priority

#### 1. `erk wt create-from` command documentation

**Location:** `docs/learned/cli/wt-create-from.md`
**Action:** CREATE
**Source:** [PR #7712]

**Draft Content:**

```markdown
---
read-when:
  - using erk wt create-from command
  - allocating worktree slots for existing branches
  - opening existing branches in worktree slots
category: cli
tripwires: 0
---

# erk wt create-from

Allocates a worktree pool slot for an existing branch (local or remote).

## Purpose

Use `create-from` when you want to open an existing branch in a worktree slot without modifying your current worktree. This is the "open in slot" operation.

## Usage

See `src/erk/cli/commands/wt/create_from_cmd.py` for implementation.

Key behaviors:

- Validates target branch is not trunk (errors with remediation: use `erk wt co root`)
- Automatically fetches and creates tracking branches for remote-only branches
- Supports `--force` flag to auto-unassign oldest branch when pool is full
- Reuses inactive slots with artifact cleanup (`.impl/`, `.erk/scratch/`)
- Generates activation scripts for worktree environment setup
- Displays sync status after allocation (ahead/behind remote)

## When to Use

Decision tree for worktree commands:

- **New branch needed?** Use `erk wt create`
- **Existing branch, want to open in slot?** Use `erk wt create-from`
- **Already in a slot, just navigate?** Use `erk wt checkout`

## Related

- Slot allocation algorithm: See `src/erk/cli/commands/slot/common.py` (grep for `allocate_slot_for_branch`)
- Navigation helpers: See `src/erk/cli/commands/checkout_helpers.py`
- Test coverage: See `tests/unit/cli/commands/wt/test_create_from_cmd.py` (8 test cases)
```

---

#### 2. Format-then-commit workflow tripwire

**Location:** `docs/learned/ci/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

Add the following tripwire entry:

```markdown
**Before running CI checks on edited Python files:**

- FORBIDDEN: Running `make fast-ci` or `make all-ci` immediately after editing Python files
- REQUIRED: Run `make format` first to fix formatting issues
- Workflow: Edit files -> `make format` -> `make fast-ci` -> commit if passing
- WHY: Format check validates but doesn't fix. Running formatter before CI prevents format check failures.
```

This tripwire has a score of 6/10:

- Non-obvious: +2 (format-check validates but doesn't auto-fix)
- Cross-cutting: +2 (applies to all Python file edits)
- Repeated pattern: +1 (session ended at this failure)
- Destructive potential: +1 (causes CI failure, requires rerun)

---

#### 3. PR comment batch addressing workflow

**Location:** `docs/learned/pr-operations/batch-addressing.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

````markdown
---
read-when:
  - addressing multiple PR review comments
  - resolving review threads in batch
  - using erk exec resolve-review-threads
category: pr-operations
tripwires: 0
---

# PR Comment Batch Addressing

Efficiently address multiple PR review comments using batching strategy.

## Batching Strategy

Group review comments by complexity:

1. **Local fixes** - Changes within single function (auto-proceed)
2. **Single-file changes** - Modifications to one file
3. **Multi-file changes** - Coordinated changes across files

Display execution plan before proceeding to confirm groupings.

## Batch Thread Resolution

Resolve multiple threads in a single API call using JSON input:

```bash
echo '[
  {"thread_id": "PRRT_...", "comment": "Fixed in <commit>"},
  {"thread_id": "PRRT_...", "comment": "Fixed in <commit>"}
]' | erk exec resolve-review-threads
```
````

This is more efficient than individual resolutions.

## Verification Workflow

After resolving threads:

1. Run classifier to parse unresolved threads
2. Direct count check: `erk exec get-pr-review-comments | python3 -c "import json, sys; data=json.load(sys.stdin); print(len(data['threads']))"`
3. Update PR description: `erk exec update-pr-description --session-id <id>`
4. Push with `gt submit --no-interactive`

## Related

- PR operations skill: Load `pr-operations` skill for complete workflow
- Thread resolution command: See `erk exec resolve-review-threads --help`

````

---

### MEDIUM Priority

#### 4. wt command comparison reference

**Location:** `docs/learned/cli/wt-command-comparison.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - choosing between erk wt commands
  - confused about wt create variants
  - understanding worktree command differences
category: cli
tripwires: 0
---

# Worktree Command Comparison

Clarifies the semantic differences between worktree command variants.

## erk wt create --from-current-branch

A **"move"** operation:
- Operates on the branch you're currently on
- Moves the branch out of current worktree into a new one
- Switches current worktree to trunk or Graphite parent
- Creates new worktree directory (not pool-based)
- Runs post-create commands (.env setup, post_create_commands)

Use case: "I'm done working here in root worktree, give this branch its own slot"

## erk wt create-from <branch>

An **"open in slot"** operation:
- Takes explicit branch name as argument
- Allocates pool slot for that branch
- Does NOT touch current worktree at all
- Uses pool system with inactive slot reuse
- Does NOT run post-create commands

Use case: "Open this existing branch in a slot without affecting where I am"

## Core Distinction

`--from-current-branch` modifies current worktree state (switches it away from the branch).
`create-from` leaves current worktree completely untouched.

## Decision Tree

1. **Want to move current branch elsewhere?** Use `erk wt create --from-current-branch`
2. **Want to open different branch in slot?** Use `erk wt create-from <branch>`
3. **Want to navigate to existing slot?** Use `erk wt checkout <slot>`
````

---

#### 5. Haiku agent task specificity tripwire

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

Add the following tripwire entry:

```markdown
**When delegating tasks to haiku agents:**

- FORBIDDEN: Vague prompts like "verify all threads resolved" or "analyze this"
- REQUIRED: Explicit "run this command" instruction with expected output format
- Example (WRONG): "Verify all threads resolved"
- Example (RIGHT): "Run `erk exec get-pr-review-comments` and parse the JSON output to count unresolved threads"
- WHY: Haiku agents with vague prompts often describe skills instead of executing commands
```

This tripwire has a score of 4/10:

- Non-obvious: +2 (haiku behavior is not intuitive)
- Cross-cutting: +2 (applies to all haiku agent delegation)

---

#### 6. Variable locality in CLI commands

**Location:** `docs/learned/cli/cli-variable-locality.md`
**Action:** CREATE
**Source:** [PR #7712]

**Draft Content:**

````markdown
---
read-when:
  - receiving variable locality feedback in code review
  - refactoring CLI command functions
  - applying dignified-python variable rules
category: cli
tripwires: 1
---

# Variable Locality in CLI Commands

CLI-specific guidance for the dignified-python variable locality rule.

## Rule

Variables should be declared as close as possible to their first use, not at the beginning of function scope.

## Pattern

When a function has early returns, variables used only after those returns should be declared after them.

**Before (problematic):**

```python
def create_from_wt(...):
    styled_branch = click.style(branch, bold=True)  # Declared early
    styled_slot = click.style(slot.name, bold=True)  # Declared early

    if already_assigned:
        return  # Early return

    # Variables used here, but declared above early return
    user_output(f"Assigned {styled_branch} to {styled_slot}")
```
````

**After (correct):**

```python
def create_from_wt(...):
    if already_assigned:
        return  # Early return

    # Variables declared after early return, close to use
    styled_branch = click.style(branch, bold=True)
    styled_slot = click.style(slot.name, bold=True)
    user_output(f"Assigned {styled_branch} to {styled_slot}")
```

## Rationale

- Reduces cognitive load (don't need to track unused variables)
- Makes code more linear and easier to follow
- Prevents wasted computation if early returns trigger

## Tripwire

When receiving automated review feedback about variable locality, move declarations to immediately before first use.

## Related

- dignified-python skill: Core variable locality rule
- See PR #7712 review threads for real-world examples

````

---

#### 7. Automated review bot reference

**Location:** `docs/learned/ci/automated-reviews.md`
**Action:** CREATE
**Source:** [PR #7712]

**Draft Content:**

```markdown
---
read-when:
  - understanding automated PR review feedback
  - preparing PR for review
  - reviewing what bots check vs manual review
category: ci
tripwires: 0
---

# Automated PR Reviews

Reference for what each automated reviewer checks in PRs.

## Review Bots

### test-coverage-review
Checks for new source files without corresponding tests.

### dignified-python-review
Validates Python code against dignified-python standards:
- LBYL patterns (no try/except for control flow)
- Exception handling practices
- Import conventions (absolute imports only)
- Click patterns (help text formatting, command structure)
- Path operations (pathlib usage)
- Type annotations

### dignified-code-simplifier-review
Identifies code simplification opportunities:
- Variable locality (declare close to first use)
- Indentation depth (max 4 levels)
- Unnecessary intermediate variables
- Early return opportunities

### tripwires-review
Loads relevant documentation based on code patterns and warns about known pitfalls.

## Manual Review Focus

Since bots handle:
- Style and formatting issues
- Known pattern violations
- Test coverage gaps

Manual reviewers should focus on:
- Logic correctness
- Architecture decisions
- API design
- Performance considerations
- Edge cases not covered by tests

## Related

- Tripwires documentation: See `docs/learned/*/tripwires.md` files
- dignified-python skill: Load for complete coding standards
````

---

#### 8. Artifact cleanup details

**Location:** `docs/learned/erk/slot-pool-architecture.md`
**Action:** UPDATE
**Source:** [PR #7712]

**Draft Content:**

Add the following section to the existing slot-pool-architecture.md:

```markdown
## Artifact Cleanup on Slot Reuse

When reusing inactive slots, erk optionally cleans up session-specific artifacts.

### What Gets Cleaned

- `.impl/` - Implementation plan files from previous sessions
- `.erk/scratch/` - Session artifacts and temporary files

### When Cleanup Happens

Cleanup occurs only when both conditions are met:

1. `cleanup_artifacts=True` is passed to slot allocation
2. An inactive slot is being reused (not fresh allocation)

### Why These Directories

These directories are session-specific and should not persist across slot reuse:

- `.impl/` contains plan context from the previous implementation session
- `.erk/scratch/` contains temporary artifacts from agent operations

### Configuration

See `src/erk/cli/commands/slot/common.py` (grep for `cleanup_artifacts`) for the implementation.
```

---

### LOW Priority

#### 9. Click \b placement ambient knowledge

**Location:** `docs/learned/cli/tripwires.md`
**Action:** UPDATE (consider elevation)
**Source:** [Impl]

**Draft Content:**

Consider adding to tripwires for ambient awareness (currently in help-text-formatting.md):

```markdown
**When editing Click command help text with Examples sections:**

- Place `\b` AFTER section headings, not before
- Correct format: "Examples:\n\n\\b\n command example"
- WHY: Click interprets `\b` as "stop line wrapping here" - it must follow the heading
- Reference: docs/learned/cli/help-text-formatting.md
```

Note: This scores 4/10 on tripwire criteria but is already documented and caught by automated reviewer. LOW priority for elevation decision.

---

#### 10. Intermediate variable guidelines enhancement

**Location:** `dignified-python` skill
**Action:** UPDATE
**Source:** [PR #7712]

**Draft Content:**

Add nuance to intermediate variable guidelines in the dignified-python skill:

```markdown
## Intermediate Variable Inlining

**General rule:** Inline simple ternaries and single-use expressions directly into function calls.

**Exception:** Very long or complex expressions may warrant intermediate variables for readability.

**Heuristic:** If the expression fits on one line and is self-explanatory, inline it.

**When NOT to inline:**

- Multi-condition expressions with multiple operators
- Expressions that would exceed reasonable line length
- Cases where the variable name adds significant clarity
```

---

#### 11. Early return transformation examples

**Location:** `dignified-python` skill or `docs/learned/refactoring/`
**Action:** UPDATE
**Source:** [PR #7712]

**Draft Content:**

Add explicit examples of nested if to early return refactoring:

````markdown
## Early Return Flattening

Transform nested conditionals into early returns to reduce indentation.

**Before:**

```python
def process(...):
    if should_output:
        styled = click.style(value, bold=True)
        user_output(f"Result: {styled}")
        navigate_to_result(result)
```
````

**After:**

```python
def process(...):
    if not should_output:
        return

    styled = click.style(value, bold=True)
    user_output(f"Result: {styled}")
    navigate_to_result(result)
```

**Connection:** This supports the max 4 indentation levels rule by removing one level of nesting.

```

---

## Contradiction Resolutions

**No contradictions detected.**

All existing documentation aligns with the new implementation. The `create-from` command follows established patterns from slot-pool-architecture.md, checkout-helpers.md, and branch-manager-decision-tree.md.

---

## Stale Documentation Cleanup

**No stale documentation detected.**

All referenced artifacts in existing documentation were verified as present:
- erk/slot-pool-architecture.md: All file paths confirmed
- erk/placeholder-branches.md: All file paths confirmed
- cli/checkout-helpers.md: All file paths confirmed
- architecture/branch-manager-decision-tree.md: All file paths confirmed

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Format Check Failure After Edits

**What happened:** Agent edited Python files, then ran `make fast-ci` which includes format validation. The format check failed because edits introduced formatting issues.

**Root cause:** The `format-check` target validates formatting but does not auto-fix. Agent assumed running CI would handle formatting.

**Prevention:** Always run `make format` after editing Python files, before running CI checks. The workflow should be: edit -> format -> fast-ci -> commit.

**Recommendation:** TRIPWIRE (score 6/10, documented above)

### 2. Haiku Agent Describes Instead of Executes

**What happened:** When delegating "verify all threads resolved" to a haiku agent, the agent read and described the pr-feedback-classifier skill file instead of executing the classifier command.

**Root cause:** Vague prompt language ("verify", "analyze") led the agent to interpret the task as description rather than execution.

**Prevention:** When delegating to haiku agents, always include explicit "run this command" instructions with expected output format. Never use vague verbs like "verify" or "analyze" without specifying the exact command.

**Recommendation:** TRIPWIRE (score 4/10, documented above)

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Format-then-commit workflow

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Destructive potential +1, Repeated pattern +1)
**Trigger:** Before running CI checks on edited Python files
**Warning:** Run `make format` first, then `make fast-ci`. Format check validates but doesn't fix.
**Target doc:** `docs/learned/ci/tripwires.md`

This is tripwire-worthy because the session actually ended at this failure. The agent made correct edits but got stuck on CI validation because it didn't know to run the formatter first. Format-check's validate-only behavior is non-obvious since many developers expect CI to auto-fix simple issues.

### 2. Haiku agent task specificity

**Score:** 4/10 (criteria: Non-obvious +2, Cross-cutting +2)
**Trigger:** When delegating tasks to haiku agents
**Warning:** Use explicit "run this command" instructions, not vague prompts like "verify" or "analyze". Haiku agents describe skills instead of executing them when prompts are vague.
**Target doc:** `docs/learned/planning/tripwires.md`

This is tripwire-worthy because the haiku agent's behavior when given vague prompts is counter-intuitive. Developers expect "verify X" to mean "execute verification," but haiku interprets it as "describe how to verify." The cross-cutting nature (applies to all haiku delegation) makes this valuable to capture.

---

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Variable locality in CLI commands

**Score:** 3/10 (criteria: Non-obvious +2, Repeated pattern +1)
**Notes:** This is specific to dignified-python enforcement, not erk-specific. The automated reviewer catches it and cites correct documentation, reducing the need for ambient tripwire. Would promote if reviewers miss it frequently.

### 2. Batch thread resolution efficiency

**Score:** 3/10 (criteria: Non-obvious +2, External tool quirk +1)
**Notes:** Using JSON batch API is more efficient than individual calls, but individual calls still work. Not dangerous if done wrong, just slower. Document in workflow docs rather than tripwires.

### 3. Remote branch fetch behavior

**Score:** 2/10 (criteria: Non-obvious +2)
**Notes:** Automatic fetch when branch only exists on remote is helpful, not dangerous. The behavior is automatic and correct, so no tripwire needed.

### 4. Pool exhaustion handling

**Score:** 2/10 (criteria: Non-obvious +2)
**Notes:** Interactive prompt prevents destructive action when pool is full. The `--force` flag documentation explains behavior. No tripwire needed since UX is self-documenting.

### 5. Artifact cleanup on slot reuse

**Score:** 2/10 (criteria: Non-obvious +2)
**Notes:** Cleanup of `.impl/` and `.erk/scratch/` when reusing slots is documented behavior. Not a gotcha since these are session-specific directories expected to be transient.

---

## Additional Context

### Patterns Successfully Applied

The implementation correctly followed erk's established patterns:

1. **Dignified Python:** LBYL pattern, frozen dataclasses, no default parameters, pathlib usage
2. **Fake-driven testing:** 8 comprehensive test cases using FakeGit, no real git operations
3. **CLI patterns:** Hidden `--script` flag, styled messages, error remediation, `user_output()` usage
4. **Gateway ABC:** All git operations via `ctx.git.*`, no direct subprocess calls
5. **Shared infrastructure:** Leveraged `allocate_slot_for_branch()`, `navigate_to_worktree()`, `display_sync_status()`

### Documentation System Effectiveness

The automated review system worked well for this PR:
- All 4 review threads were accurate and cited correct documentation
- All threads resolved in single commit with batch API call
- Tripwire system successfully loaded relevant documentation

The primary gap was the format-then-commit workflow, which was not documented anywhere and caused the first session to end at CI failure.
```
