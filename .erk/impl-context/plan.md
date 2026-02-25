# Documentation Plan: Remove plan ID encoding from branch names, migrate to plan-ref.json

## Context

This PR (8071) represents a significant architectural shift in how erk discovers and tracks plan relationships. Previously, plan IDs were encoded directly into branch names using a `P{issue}-{slug}` pattern, which created tight coupling between branch naming and plan discovery. The new approach decouples these concerns: branch names are now purely descriptive (`plnd/{slug}-{timestamp}`), while plan discovery happens exclusively through `.impl/plan-ref.json`.

This is a breaking change that affects multiple layers of the system. Functions like `get_branch_issue()` and `resolve_plan_id_for_branch()` now return `None` instead of parsing branch names, and commands like `erk implement` require `.impl/plan-ref.json` to auto-detect plans. Four implementation sessions successfully landed this change, demonstrating effective workflows for PR comment resolution, batch thread operations, and skill-based discovery.

Documentation matters here because: (1) the breaking changes silently fail rather than raising errors, requiring tripwires to warn agents; (2) the shift from branch parsing to plan-ref.json affects how agents discover plans; and (3) several workflow patterns emerged from implementation sessions that should be captured before they're forgotten.

## Raw Materials

PR #8071

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 30    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 10    |
| Potential tripwires (score 2-3)| 4     |

## Documentation Items

### HIGH Priority

#### 1. `get_branch_issue()` deprecation tripwire

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE
**Source:** [PR #8071]

**Draft Content:**

```markdown
## get_branch_issue() Always Returns None

**Trigger:** Before calling `get_branch_issue()` or code relying on extracting plan IDs from branch names

**Warning:** As of #8071, `get_branch_issue()` always returns None. Use `read_plan_ref()` from `.impl/plan-ref.json` instead.

**Details:**
The gateway method `get_branch_issue()` was deprecated because plan IDs are no longer encoded in branch names. Code that expects this method to return issue numbers will silently receive None, potentially causing downstream failures.

**Migration:** See `packages/erk-shared/src/erk_shared/impl_folder.py` for `read_plan_ref()` usage.
```

---

#### 2. Gateway 5-place docstring sync tripwire

**Location:** `docs/learned/architecture/gateway-abc-implementation.md`
**Action:** UPDATE
**Source:** [PR #8071]

**Draft Content:**

```markdown
## Gateway Modification Checklist

**Trigger:** Before committing changes to gateway ABC methods

**Warning:** Verify all 5 files updated with consistent docstrings. PR #8071 missed 2 of 5 files initially.

When modifying a gateway method, verify these files are updated:
- [ ] `abc.py` - Abstract method definition
- [ ] `real.py` - Production implementation
- [ ] `fake.py` - Test fake implementation
- [ ] `dry_run.py` - Dry-run implementation
- [ ] `printing.py` - Printing/logging implementation

The PR review caught stale docstrings in `dry_run.py` and `printing.py` after `get_branch_issue()` behavior changed. All 5 implementations must have synchronized documentation.
```

---

#### 3. `validate_plan_linkage()` behavior change tripwire

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Source:** [PR #8071]

**Draft Content:**

```markdown
## validate_plan_linkage() Only Reads plan-ref.json

**Trigger:** Before relying on `validate_plan_linkage()` for branch name validation

**Warning:** As of #8071, this function only reads plan-ref.json and doesn't validate branch name prefixes. It no longer checks that branch names match `P{issue}-` patterns.

**Details:**
Previously, `validate_plan_linkage()` verified that the current branch name contained the plan issue number. Now it only confirms that `.impl/plan-ref.json` exists and is valid. Code that depended on branch name format validation must implement that separately if still needed.

**See:** `packages/erk-shared/src/erk_shared/impl_folder.py` for current implementation.
```

---

#### 4. `extract_objective_number()` pattern restriction tripwire

**Location:** `docs/learned/erk/tripwires.md`
**Action:** UPDATE
**Source:** [PR #8071]

**Draft Content:**

```markdown
## extract_objective_number() Pattern Restriction

**Trigger:** Before using `extract_objective_number()` with legacy branch formats

**Warning:** As of #8071, only matches `plnd/O{N}-` patterns. Legacy `P{N}-O{N}-` format no longer supported and will silently return None.

**Details:**
The function was updated to only recognize the current objective branch pattern. Branches using the old format where objectives were embedded in issue-prefixed branch names will not extract correctly.

**See:** `packages/erk-shared/src/erk_shared/naming.py` for the pattern regex.
```

---

#### 5. Documentation-code sync on deletion tripwire

**Location:** `docs/learned/documentation/tripwires.md`
**Action:** UPDATE
**Source:** [PR #8071]

**Draft Content:**

```markdown
## Grep docs/learned/ Before Deleting Functions

**Trigger:** Before committing removal of public functions

**Warning:** Grep `docs/learned/` for references and update/remove them. Use `rg 'function_name' docs/learned/`

**Details:**
PR #8071 review caught multiple instances where deleted or deprecated functions were still referenced in documentation. The audit-pr-docs bot detected:
- `extract_leading_issue_number()` references in branch-naming.md
- `generate_issue_branch_name()` references in branch-naming.md
- Private method `_build_worktree_mapping()` documented (should never be in learned docs)

Run grep before pushing to catch these issues before review.
```

---

#### 6. `resolve_plan_id_for_branch()` deprecation tripwire

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE
**Source:** [PR #8071]

**Draft Content:**

```markdown
## resolve_plan_id_for_branch() Returns None

**Trigger:** Before calling `resolve_plan_id_for_branch()` or code expecting issue numbers from it

**Warning:** This function returns None as of #8071. Use PR lookup or `read_plan_ref()` instead.

**Details:**
The function in `GitHubPlanStore` no longer parses branch names to extract plan IDs. It always returns None, directing callers to use either PR lookup (via GitHub API) or the local `.impl/plan-ref.json` file.

**See:** `packages/erk-shared/src/erk_shared/plan_store/github.py` for implementation.
```

---

#### 7. pr-feedback-classifier Task isolation tripwire

**Location:** `docs/learned/commands/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Fork Context Doesn't Isolate in --print Mode

**Trigger:** Before invoking skills with `context: fork` for structured output

**Warning:** Fork context doesn't isolate in `--print` mode. Use Task tool with explicit prompt for true subagent isolation.

**Details:**
The `pr-feedback-classifier` skill has `context: fork` metadata, but this doesn't create true subagent isolation when invoked in `--print` mode. Sessions impl-06f336be and impl-dda1efb2 both noted this issue.

For skills that must return structured data (JSON), use Task tool invocation:
```
Use Task tool with prompt: "Invoke pr-feedback-classifier skill on these comments and return JSON..."
```

Direct skill invocation may pollute the parent agent's context.
```

---

#### 8. Stale branch-naming.md cleanup

**Location:** `docs/learned/erk/branch-naming.md`
**Action:** UPDATE_REFERENCES
**Source:** [PR #8071]

**Draft Content:**

Remove or update these references caught by audit-pr-docs bot:

1. **Remove private method reference:** `_build_worktree_mapping()` - private methods must never appear in learned docs
2. **Mark deprecated:** `extract_leading_issue_number()` - function kept for backward compatibility but deprecated; redirect to plan-ref.json approach
3. **Mark deprecated:** `generate_issue_branch_name()` - function kept for backward compatibility; redirect to `generate_planned_pr_branch_name()`
4. **Verify Usage Sites:** All "Usage Sites" or "Callers" sections must be verified with grep before documenting

---

### MEDIUM Priority

#### 9. Skill invocation namespacing tripwire

**Location:** `docs/learned/commands/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Custom Skills Require local: Prefix

**Trigger:** Before invoking custom slash commands or skills

**Warning:** Custom skills require `local:` prefix (e.g., `/local:py-fast-ci` not `/py-fast-ci`). Core managed skills don't need prefix.

**Details:**
Session impl-9fdecc22 encountered `Unknown skill: py-fast-ci` error because the `local:` prefix was omitted. The agent self-corrected to `local:py-fast-ci`.

Core managed skills (those bundled with erk or Claude Code) don't require a prefix. Custom project-specific skills in `.claude/skills/local/` require the `local:` prefix.
```

---

#### 10. Path awareness in worktree slots tripwire

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Worktree Slots Have Different cwd Than Root

**Trigger:** Before using relative paths to src/ in implementation sessions

**Warning:** Implementation worktree slots have different cwd than root repo. Use absolute paths or skill-based references.

**Details:**
Session impl-b9efc4be encountered path errors when trying to grep `src/erk/exec/` - the working directory was `/Users/.../.erk/repos/erk/worktrees/erk-slot-39`, not the root repository.

When implementing in a worktree slot:
- Relative paths like `src/` won't resolve
- Load relevant skills instead of exploring implementation files
- Use absolute paths when necessary
```

---

#### 11. Usage Sites verification tripwire

**Location:** `docs/learned/documentation/tripwires.md`
**Action:** UPDATE
**Source:** [PR #8071]

**Draft Content:**

```markdown
## Verify Usage Sites With Grep

**Trigger:** Before documenting "Usage Sites" or "Callers" in learned docs

**Warning:** Verify claims with grep: `rg 'function_name' src/`. Never list files speculatively.

**Details:**
PR #8071 review caught documentation listing usage sites that didn't exist in the current codebase. Session impl-9fdecc22 demonstrated the correct pattern: use grep to verify actual usage sites before updating documentation tables.

Bad: "This function is used in file_a.py, file_b.py" (from memory or plan text)
Good: Run `rg 'function_name' src/` and document only confirmed callers
```

---

#### 12. Plan-ref.json architecture migration section

**Location:** `docs/learned/architecture/plan-ref-architecture.md`
**Action:** UPDATE
**Source:** [PR #8071]

**Draft Content:**

```markdown
## Migration from Branch-Based Discovery

As of PR #8071, plan discovery shifted from branch name parsing to plan-ref.json as the sole source of truth.

### What Changed

**Before:** Plan IDs encoded in branch names as `P{issue}-{slug}-{timestamp}`
**After:** Branch names are purely descriptive as `plnd/{slug}-{timestamp}`

### Breaking Changes

Functions that now return None instead of parsing branches:
- `get_branch_issue()` - gateway method, all 5 implementations
- `resolve_plan_id_for_branch()` - GitHubPlanStore method
- `extract_leading_issue_number()` - kept for backward compat but deprecated

### Migration Path

Replace branch parsing with plan-ref.json reads:
- Before: `issue = extract_leading_issue_number(branch)`
- After: `plan_ref = read_plan_ref(impl_dir); plan_id = plan_ref.plan_id if plan_ref else None`

See `packages/erk-shared/src/erk_shared/impl_folder.py` for `read_plan_ref()` implementation.
```

---

#### 13. Branch name inference evolution note

**Location:** `docs/learned/planning/branch-name-inference.md`
**Action:** UPDATE
**Source:** [PR #8071]

**Draft Content:**

```markdown
## Historical Note: Plan ID Encoding Removed

As of PR #8071, plan IDs are no longer encoded in branch names. This affects the two-layer resolution pattern documented in this file.

### Previous Behavior (removed)

Branch names like `P123-fix-auth-bug-02-24-1430` encoded the plan issue number (123) as a prefix. The two-layer resolution could extract plan IDs from both plan-ref.json AND branch names.

### Current Behavior

Branch names like `plnd/fix-auth-bug-02-24-1430` are purely descriptive. Plan discovery ONLY reads from `.impl/plan-ref.json`. The two-layer resolution now means: (1) plan-ref.json lookup, (2) PR API lookup. Branch parsing is no longer a layer.

This decoupling allows branch names to be renamed without breaking plan linkage.
```

---

#### 14. Branch-plan resolution implementation change

**Location:** `docs/learned/planning/branch-plan-resolution.md`
**Action:** UPDATE
**Source:** [PR #8071]

**Draft Content:**

```markdown
## Implementation Change: Regex Parsing Removed

The `resolve_plan_id_for_branch()` function no longer parses branch names using regex. As of PR #8071, it always returns None and directs callers to use alternative discovery mechanisms.

### Why This Changed

Plan ID encoding in branch names created tight coupling that:
- Made branch renames break plan tracking
- Required regex patterns to stay synchronized
- Added complexity to the naming module

### Current Resolution Strategy

When you need to find the plan for a branch:
1. Read `.impl/plan-ref.json` if in a worktree with impl folder
2. Use GitHub PR API to look up PR by branch name, extract plan from PR body
3. No fallback to branch name parsing (returns None)

See `packages/erk-shared/src/erk_shared/plan_store/github.py` for implementation.
```

---

#### 15. LBYL vs. error-handling functions

**Location:** `docs/learned/architecture/erk-architecture.md`
**Action:** UPDATE
**Source:** [PR #8071]

**Draft Content:**

```markdown
## When LBYL Is Required vs Functions That Handle Their Own Errors

PR #8071 review noted unnecessary existence checks before `read_plan_ref()`. This section clarifies when to use LBYL.

### Functions That Return None (LBYL not required)

Some functions handle missing resources gracefully by returning None:
- `read_plan_ref(impl_dir)` - returns None if plan-ref.json doesn't exist
- `get_worktree_root(path)` - returns None if not in a worktree

For these, you can call directly and check the result:
```python
# Good
plan_ref = read_plan_ref(impl_dir)
if plan_ref is None:
    handle_missing()
```

### Operations That Raise (LBYL required)

Operations that raise exceptions require existence checks:
- `path.read_text()` - raises FileNotFoundError
- `json.loads()` - raises JSONDecodeError

For these, check before calling:
```python
# Good (LBYL)
if path.exists():
    content = path.read_text()
```

The distinction: check function signatures and docstrings to determine if they return Optional or raise.
```

---

#### 16. Discovery-before-edit pattern

**Location:** `docs/learned/architecture/discovery-patterns.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when: verifying code state before making changes, updating documentation about callers or usage
---

# Discovery-Before-Edit Pattern

Use grep to verify current state before making changes. This prevents documenting outdated information or editing based on stale assumptions.

## The Pattern

Before updating documentation or code based on a plan's description:
1. Use grep to verify the current state
2. Check if the change is still needed
3. Update only based on verified findings

## Example from Session impl-9fdecc22

The plan said to update documentation showing `generate_planned_pr_branch_name` usage sites. Instead of copying the plan's list:

```bash
# Verify actual current usage
rg 'generate_planned_pr_branch_name' src/
```

This revealed different callers than the plan listed, avoiding inaccurate documentation.

## When to Apply

- Updating "Usage Sites" or "Callers" tables in documentation
- Removing code that "should be unused"
- Fixing issues described in review comments (code may have changed)
- Any time a plan describes current state rather than desired state
```

---

#### 17. Verification-first for outdated review threads

**Location:** `docs/learned/pr-operations/verification-patterns.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when: addressing PR review comments, working with outdated threads
---

# Verification-First for Outdated Review Threads

When PR review threads are marked `is_outdated: true`, read the current code before planning fixes.

## The Pattern

Session 06f336be demonstrated this pattern effectively:

1. **Recognize the signal:** All 8 review threads had `is_outdated: true`
2. **Read current code:** Agent read all 4 flagged files before planning
3. **Discover: issues already fixed:** All 8 comments were on already-resolved code
4. **Minimal plan:** Created plan to resolve threads, not fix non-existent issues

## Why This Matters

Outdated threads indicate the code has changed since the comment was made. The issue may be:
- Already fixed in a later commit
- Addressed differently than the reviewer suggested
- No longer applicable due to refactoring

Planning fixes without verification wastes time and may introduce regressions.

## Implementation

When `get-pr-review-comments` shows all `is_outdated: true`:
1. Group threads by file
2. Read each file
3. Check if each issue still exists
4. Only plan fixes for issues that remain
```

---

#### 18. Documentation audit workflow

**Location:** `docs/learned/documentation/audit-pr-docs.md`
**Action:** CREATE
**Source:** [PR #8071]

**Draft Content:**

```markdown
---
read-when: understanding PR documentation bot, addressing audit-pr-docs violations
---

# Documentation Audit Workflow

The audit-pr-docs bot automatically reviews PRs for documentation-code drift.

## What It Checks

Based on PR #8071 review, the bot detects:

1. **Deleted function references:** Functions removed from code but still in docs
2. **Private method exposure:** `_underscore` methods documented (forbidden)
3. **Phantom usage sites:** Documentation claiming callers that don't exist
4. **Stale code paths:** Documentation of non-existent features or workflows

## How to Address Violations

When the bot comments on your PR:

1. **Read the violation:** Bot identifies specific file and line
2. **Verify with grep:** `rg 'term' src/` to confirm the reference is stale
3. **Choose action:**
   - DELETE: Remove the documentation entirely if obsolete
   - UPDATE: Fix incorrect references with current values
   - MARK DEPRECATED: For backward-compat functions, add deprecation note

## Prevention

Before pushing documentation changes:
```bash
# Check for phantom references
rg 'function_name_you_documented' src/
```

If grep returns nothing, don't document the function as being used.
```

---

#### 19. Plan checkout discovery mechanism

**Location:** `docs/learned/cli/plan-checkout.md`
**Action:** CREATE
**Source:** [PR #8071]

**Draft Content:**

```markdown
---
read-when: using erk plan checkout, understanding plan discovery
---

# Plan Checkout Discovery Mechanism

`erk plan checkout` finds branches by iterating worktrees and reading `.impl/plan-ref.json`, not by parsing branch names.

## How It Works

1. Command iterates all worktrees in the repository
2. For each worktree, checks for `.impl/plan-ref.json`
3. Reads plan reference to get plan ID
4. If plan ID matches requested issue number, returns that branch

## Breaking Change from PR #8071

Previously, checkout could discover plan branches by pattern matching `P{issue}-*` branch names. This no longer works.

Branches without `.impl/plan-ref.json`:
- Won't be discovered by `erk plan checkout`
- Must be manually checked out with `git checkout`
- Should be recreated with `erk implement` to get proper tracking

## Source

See `src/erk/cli/commands/plan/checkout_cmd.py` for `_find_branches_for_issue()` implementation.
```

---

#### 20. Implement auto-detect behavior

**Location:** `docs/learned/cli/implement.md`
**Action:** CREATE
**Source:** [PR #8071]

**Draft Content:**

```markdown
---
read-when: using erk implement without specifying target, debugging auto-detect failures
---

# Implement Auto-Detect Behavior

`erk implement` auto-detect requires `.impl/plan-ref.json`. Branch name parsing is no longer supported.

## Auto-Detect Flow

When no TARGET is specified:
1. Check for `.impl/` directory in current worktree
2. Read `.impl/plan-ref.json`
3. Extract plan ID from the reference
4. If no plan-ref.json exists, fail with guidance

## Error Message

```
Could not auto-detect plan number
Either provide TARGET or switch to a branch with .impl/plan-ref.json
```

## Breaking Change from PR #8071

Previously, `erk implement` could auto-detect from branch names matching `P{issue}-*`. This fallback was removed.

Existing worktrees created before this change:
- Won't auto-detect (missing plan-ref.json)
- Use `erk implement <issue>` with explicit target
- Or recreate the worktree to get plan-ref.json

## Source

See `src/erk/cli/commands/implement.py` for auto-detect implementation.
```

---

#### 21. Batch PR thread resolution

**Location:** `docs/learned/pr-operations/batch-resolution.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when: resolving multiple PR review threads, using resolve-review-threads
---

# Batch PR Thread Resolution

Use `erk exec resolve-review-threads` with JSON stdin to resolve multiple threads in a single operation.

## The Pattern

Session impl-b9efc4be demonstrated batch resolution for 8 threads:

```bash
echo '[{"thread_id": "PRRT_xxx", "body": "Fixed in commit abc123"}, ...]' | erk exec resolve-review-threads --pr 8071 --stdin
```

## JSON Input Format

```json
[
  {
    "thread_id": "PRRT_kwDOPxC3hc5...",
    "body": "Resolution message explaining what was done"
  }
]
```

## Post-Resolution Verification

Always verify after batch resolution:

```bash
erk exec get-pr-review-comments --pr 8071 --unresolved
```

Session impl-b9efc4be ran this and confirmed only a new CI bot thread remained (not part of original 8).

## When to Use

- Multiple review threads need similar resolutions
- "Already fixed" threads that just need acknowledgment
- Batch cleanup of outdated comments
```

---

#### 22. Plan mode exit workflow

**Location:** `docs/learned/planning/plan-mode-exit.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when: exiting plan mode, understanding exit-plan-mode-hook behavior
---

# Plan Mode Exit Workflow

The exit-plan-mode hook intercepts ExitPlanMode and presents a structured choice.

## Flow

1. Agent calls ExitPlanMode tool
2. Hook intercepts and blocks
3. Hook requires agent to:
   - Display the plan contents
   - Use AskUserQuestion with three options
4. User selects an option
5. If "implement now", agent creates marker
6. Agent retries ExitPlanMode (now allowed)

## Three Options

1. **Create plan PR (recommended)** - Saves plan to GitHub issue before implementation
2. **Skip PR and implement here** - Implements directly without tracking
3. **View/Edit plan** - Returns to plan editing

## Implement-Now Marker

When user chooses option 2:
```bash
erk exec marker create --session-id "${CLAUDE_SESSION_ID}" --name "exit-plan-mode-hook.implement-now"
```

This marker signals the hook to allow ExitPlanMode without plan PR creation.

## Source

Sessions 06f336be and dda1efb2 both demonstrated this workflow.
```

---

#### 23. Private method exclusion prominence

**Location:** `docs/learned/documentation/learned-docs-core.md`
**Action:** UPDATE
**Source:** [PR #8071]

**Draft Content:**

Move this rule to the TOP of the "What Not to Document" section with stronger emphasis:

```markdown
## What Not to Document

### Private Methods (CRITICAL)

**NEVER document private methods (`_underscore`) in learned docs.**

PR #8071 caught `_build_worktree_mapping()` documented in branch-naming.md. This violates the rule that private methods:
- Belong in docstrings, not external documentation
- Have unstable names that change without notice
- Create maintenance burden when implementation details shift

If you find yourself wanting to document a private method, either:
1. Make it public if it's genuinely part of the interface
2. Document the public API that uses it instead
3. Add information to the private method's docstring

The audit-pr-docs bot will flag private method references in PRs.
```

---

#### 24. Historical vs. current behavior guidance

**Location:** `docs/learned/documentation/historical-notes.md`
**Action:** CREATE
**Source:** [PR #8071]

**Draft Content:**

```markdown
---
read-when: documenting removed features, marking deprecated behavior
---

# Historical vs Current Behavior Documentation

When documenting removed code paths, clearly distinguish historical behavior from current behavior.

## The Problem

PR #8071 review caught documentation of "GitHubPlanStore legacy path" that never existed in the codebase. When features are removed or changed, documentation must be updated to avoid describing phantom functionality.

## Format for Historical Notes

```markdown
## Historical Note: [Feature Name]

**Removed in:** PR #XXXX / version X.Y
**Reason:** Brief explanation

Previously, [description of old behavior].

This was replaced by [current approach] because [rationale].
```

## When to Use

- Documenting deprecated functions kept for backward compatibility
- Explaining why certain patterns no longer work
- Providing context for users migrating from old workflows

## When NOT to Use

Don't create historical notes for:
- Features that never existed (speculatively documented)
- Internal implementation details users never saw
- Refactoring that didn't change user-facing behavior
```

---

### LOW Priority

#### 25. Two-step preview pattern

**Location:** `docs/learned/pr-operations/preview-then-address.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when: using pr-preview-address, understanding PR comment workflow
---

# Two-Step Preview Pattern

Use `/erk:pr-preview-address` (read-only preview) followed by `/erk:pr-address` (action command).

## The Pattern

Sessions 06f336be and dda1efb2 demonstrated this workflow:

1. **Preview:** `/erk:pr-preview-address` - See what would be addressed without making changes
2. **Review:** User reviews the plan (N actionable items in M batches)
3. **Address:** `/erk:pr-address` - Execute the plan

## Benefits

- See scope before committing to changes
- Catch misclassifications or missed comments
- Abort if the batch is too complex for current context
- Review batch groupings (local vs cross-cutting)

## When to Skip Preview

For simple PRs with few comments, you can go directly to `/erk:pr-address`. The preview step is most valuable when:
- PR has many comments
- Uncertain about comment complexity
- Want to estimate time before committing
```

---

#### 26. Hook-driven plan save flow

**Location:** `docs/learned/hooks/exit-plan-mode-hook.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when: understanding plan save workflow, customizing exit-plan-mode behavior
---

# Exit-Plan-Mode Hook Flow

The exit-plan-mode-hook implements a three-option prompt for plan disposition.

## Hook Behavior

When agent calls ExitPlanMode:

1. Hook blocks the tool use
2. Hook instructs agent to display plan and ask user
3. Agent shows plan contents
4. Agent uses AskUserQuestion with options:
   - 1) Create plan PR (recommended)
   - 2) Skip PR and implement here
   - 3) View/Edit plan
5. Based on selection, agent proceeds

## Marker Protocol

For "implement now" path, agent must create marker:
```bash
erk exec marker create --session-id "${CLAUDE_SESSION_ID}" --name "exit-plan-mode-hook.implement-now"
```

Hook checks for this marker before allowing ExitPlanMode without PR creation.

## Customization

The hook is in `.claude/hooks/exit-plan-mode-hook.py`. Modify to:
- Change default recommendation
- Add additional options
- Require plan PR for certain conditions
```

---

#### 27. Batch complexity classification

**Location:** `docs/learned/pr-operations/complexity-classification.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when: understanding pr-address batch grouping, tuning auto-proceed behavior
---

# Batch Complexity Classification

PR comments are classified by complexity level which determines batch grouping and auto-proceed behavior.

## Complexity Levels

| Level | Description | Auto-Proceed |
|-------|-------------|--------------|
| `local` | Change within a single function | Yes |
| `single_file` | Change within one file | Yes |
| `cross_cutting` | Change spans multiple files | Confirm |
| `complex` | Architectural or major change | Confirm |

## Batch Formation

Comments with same complexity level and related files are grouped:
- Simple batches (local + single_file) auto-proceed
- Complex batches require user confirmation

## Source

Session dda1efb2 showed 8 items grouped into 2 batches based on complexity. See `pr-feedback-classifier` skill for classification logic.
```

---

#### 28. detect-plan-from-branch fallback

**Location:** `.claude/skills/erk-exec/reference.md`
**Action:** UPDATE (verify completeness)
**Source:** [PR #8071]

**Draft Content:**

Verify this section exists and is complete:

```markdown
## detect-plan-from-branch

Detects the plan associated with the current branch.

### Behavior Change (PR #8071)

Branch name parsing removed. Now uses:
1. Read `.impl/plan-ref.json` if exists
2. Fall back to PR API lookup (find PR for branch, extract plan from body)

### JSON Output

```json
{
  "plan_id": 123,
  "detection_method": "plan_ref" | "pr_lookup"
}
```

The `detection_method` field indicates how the plan was discovered.
```

---

#### 29. Deprecated function markers in branch-naming.md

**Location:** `docs/learned/erk/branch-naming.md`
**Action:** UPDATE
**Source:** [PR #8071]

**Draft Content:**

Add deprecation notices:

```markdown
## Deprecated Functions

### extract_leading_issue_number() (DEPRECATED)

**Status:** Kept for backward compatibility, but deprecated as of PR #8071.
**Migration:** Use `read_plan_ref(impl_dir)` to get plan ID from `.impl/plan-ref.json`.
**Note:** This function still works but plan IDs are no longer encoded in branch names, so it will return None for new branches.

### generate_issue_branch_name() (DEPRECATED)

**Status:** Kept for backward compatibility, but deprecated as of PR #8071.
**Migration:** Use `generate_planned_pr_branch_name()` which creates `plnd/{slug}-{timestamp}` format.
**Note:** New code should not create `P{issue}-*` branches.
```

---

#### 30. Plan-ref.json migration guide (CONDITIONAL)

**Location:** `docs/learned/planning/plan-ref-migration.md`
**Action:** CREATE (only if breaking change affects users)
**Source:** [PR #8071]

**Draft Content:**

```markdown
---
read-when: migrating from P{issue}- branches, fixing broken plan discovery
---

# Plan-ref.json Migration Guide

For users with existing worktrees using `P{issue}-` branch naming.

## Symptoms

- `erk implement` fails with "Could not auto-detect plan"
- `erk plan checkout <issue>` doesn't find your branch
- Plan linkage appears broken

## Diagnosis

Check if your worktree has plan-ref.json:
```bash
ls .impl/plan-ref.json
```

If missing, your worktree uses the old branch-based plan discovery.

## Migration Options

### Option 1: Recreate Worktree

```bash
# Save any uncommitted changes
git stash

# Delete old worktree
erk wt delete <slot-or-path>

# Recreate with current tooling
erk implement <issue-number>
```

This creates a new worktree with proper `.impl/plan-ref.json`.

### Option 2: Manual Creation

If you can't recreate the worktree:
```bash
mkdir -p .impl
echo '{"plan_id": <issue-number>}' > .impl/plan-ref.json
```

Replace `<issue-number>` with your plan's GitHub issue number.

## Why This Changed

PR #8071 decoupled branch naming from plan discovery. This allows:
- Branch renames without breaking plan tracking
- Simpler branch naming conventions
- Consistent discovery via plan-ref.json
```

---

## Stale Documentation Cleanup

Existing docs with phantom references requiring action:

### 1. branch-naming.md private method reference

**Location:** `docs/learned/erk/branch-naming.md`
**Action:** DELETE_STALE
**Phantom References:** `_build_worktree_mapping()`
**Cleanup Instructions:** Remove any mention of this private method. Private methods must never appear in learned docs per learned-docs-core.md.

### 2. one-shot-workflow.md GitHubPlanStore legacy path

**Location:** `docs/learned/planning/one-shot-workflow.md`
**Action:** DELETE_STALE
**Phantom References:** "GitHubPlanStore legacy path"
**Cleanup Instructions:** Remove documentation of this non-existent code path caught by audit-pr-docs bot.

### 3. Speculative Usage Sites

**Location:** Multiple docs
**Action:** UPDATE_REFERENCES
**Phantom References:** Usage Sites sections not verified with grep
**Cleanup Instructions:** For any documentation with "Usage Sites" or "Callers" sections, verify each entry with `rg 'function_name' src/`. Remove entries that don't match.

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Skill Prefix Error

**What happened:** Session impl-9fdecc22 invoked `py-fast-ci` without the `local:` prefix, resulting in "Unknown skill" error.
**Root cause:** Custom skills in `.claude/skills/local/` require namespace prefix, but this isn't obvious from skill names.
**Prevention:** Document that custom skills need `local:` prefix; core managed skills don't.
**Recommendation:** TRIPWIRE

### 2. Path Resolution in Worktree Slots

**What happened:** Session impl-b9efc4be tried to grep `src/erk/exec/` but got "path does not exist" because working directory was a worktree slot, not root repo.
**Root cause:** Worktree slots have different directory structure; relative paths to `src/` fail.
**Prevention:** Load relevant skills for command reference instead of exploring files, or use absolute paths.
**Recommendation:** TRIPWIRE

### 3. Outdated Review Thread Assumption

**What happened:** Session 06f336be initially planned to fix 8 review comments before discovering all were already resolved.
**Root cause:** Agent planned based on review thread existence without reading current code.
**Prevention:** When all threads are `is_outdated: true`, read files first to verify issues still exist.
**Recommendation:** ADD_TO_DOC (verification-patterns.md)

### 4. Fork Context Isolation Misconception

**What happened:** Sessions 06f336be and dda1efb2 noted that `context: fork` in skills doesn't provide true subagent isolation in `--print` mode.
**Root cause:** Fork context metadata doesn't affect all invocation modes equally.
**Prevention:** Use Task tool with explicit prompt for skills that must return structured data.
**Recommendation:** TRIPWIRE

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. get_branch_issue() Always Returns None

**Score:** 8/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2, External tool quirk +2)
**Trigger:** Before calling `get_branch_issue()` or code relying on extracting plan IDs from branch names
**Warning:** This method always returns None as of #8071. Use `read_plan_ref()` from .impl/plan-ref.json instead.
**Target doc:** `docs/learned/architecture/tripwires.md`

This is the highest-priority tripwire because it affects all 5 gateway implementations and any code that expected branch-based plan discovery. The silent failure (returning None instead of raising) makes debugging difficult.

### 2. Gateway 5-Place Docstring Sync

**Score:** 6/10 (Cross-cutting +2, Repeated pattern +2, Destructive potential +2)
**Trigger:** Before committing changes to gateway ABC methods
**Warning:** Verify all 5 files updated: abc.py, real.py, fake.py, dry_run.py, printing.py. Use checklist in gateway-abc-implementation.md.
**Target doc:** `docs/learned/architecture/gateway-abc-implementation.md`

PR #8071 initially missed updating docstrings in 2 of 5 files. This is a repeated pattern across PRs modifying gateway methods.

### 3. validate_plan_linkage() Behavior Change

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before relying on `validate_plan_linkage()` for branch name validation
**Warning:** As of #8071, this function only reads plan-ref.json and doesn't validate branch name prefixes.
**Target doc:** `docs/learned/planning/tripwires.md`

Code that expected branch name format validation will silently pass validation even for malformed branches.

### 4. extract_objective_number() Pattern Restriction

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before using `extract_objective_number()` with legacy branch formats
**Warning:** As of #8071, only matches `plnd/O{N}-` patterns. Legacy `P{N}-O{N}-` format no longer supported.
**Target doc:** `docs/learned/erk/tripwires.md`

Existing objective branches using old format will silently fail to extract.

### 5. Documentation-Code Sync on Deletion

**Score:** 5/10 (Cross-cutting +2, Repeated pattern +1, Destructive potential +2)
**Trigger:** Before committing removal of public functions
**Warning:** Grep `docs/learned/` for references: `rg 'function_name' docs/learned/`. Update or remove documentation.
**Target doc:** `docs/learned/documentation/tripwires.md`

PR #8071 review caught multiple stale references. This pattern recurs across PRs that delete or rename functions.

### 6. resolve_plan_id_for_branch() Returns None

**Score:** 5/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +1)
**Trigger:** Before calling `resolve_plan_id_for_branch()` or code expecting issue numbers from it
**Warning:** This function returns None as of #8071. Use PR lookup or read_plan_ref() instead.
**Target doc:** `docs/learned/architecture/tripwires.md`

Similar to get_branch_issue() but specific to GitHubPlanStore.

### 7. pr-feedback-classifier Task Isolation

**Score:** 5/10 (Non-obvious +2, Silent failure +2, Repeated pattern +1)
**Trigger:** Before invoking skills with `context: fork` for structured output
**Warning:** Fork context doesn't isolate in `--print` mode. Use Task tool with explicit prompt for true subagent isolation.
**Target doc:** `docs/learned/commands/tripwires.md`

Multiple sessions encountered this issue when expecting skill invocation to provide isolation.

### 8. Skill Invocation Namespacing

**Score:** 4/10 (Non-obvious +2, Repeated pattern +2)
**Trigger:** Before invoking custom slash commands or skills
**Warning:** Custom skills require `local:` prefix (e.g., `/local:py-fast-ci`). Core managed skills don't need prefix.
**Target doc:** `docs/learned/commands/tripwires.md`

Session impl-9fdecc22 self-corrected after encountering this error.

### 9. Path Awareness in Worktree Slots

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)
**Trigger:** Before using relative paths to src/ in implementation sessions
**Warning:** Implementation worktree slots have different cwd than root. Use absolute paths or skill references.
**Target doc:** `docs/learned/planning/tripwires.md`

Session impl-b9efc4be encountered path errors due to worktree directory structure.

### 10. Usage Sites Verification

**Score:** 4/10 (Cross-cutting +2, Repeated pattern +2)
**Trigger:** Before documenting "Usage Sites" or "Callers" in learned docs
**Warning:** Verify claims with grep: `rg 'function_name' src/`. Never list files speculatively.
**Target doc:** `docs/learned/documentation/tripwires.md`

PR #8071 review caught speculative usage sites. Session impl-9fdecc22 demonstrated the correct verification pattern.

---

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. LBYL vs. Error-Handling Functions

**Score:** 3/10 (Non-obvious +2, Repeated pattern +1)
**Notes:** Pattern appeared once in PR review (unnecessary `if impl_dir.exists()` before `read_plan_ref()`). May warrant tripwire if pattern recurs.

### 2. Private Method Documentation

**Score:** 3/10 (Cross-cutting +2, Repeated pattern +1)
**Notes:** Already a rule in learned-docs-core.md but needs more prominence. PR #8071 caught violation despite existing rule.

### 3. Historical vs. Current Behavior Marking

**Score:** 2/10 (Non-obvious +2)
**Notes:** Single instance from PR review (non-existent GitHubPlanStore legacy path). Warrants guidance but not full tripwire until pattern recurs.

### 4. Plan Mode Exit Marker Creation

**Score:** 2/10 (Non-obvious +2)
**Notes:** Specific to exit-plan-mode hook. Narrow scope limits tripwire value, better as procedural documentation.
