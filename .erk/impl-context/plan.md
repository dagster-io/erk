# Documentation Plan: Move `erk plan create` command to `erk pr create`

## Context

PR #8097 reorganized the CLI mental model by moving the plan creation command from `erk plan create` to `erk pr create`. This unifies plan creation with other PR-related viewing/closing operations, creating a more cohesive mental model where `erk pr` handles all plan creation/viewing/closing operations, while `erk plan` focuses exclusively on plan submission and management.

The implementation was executed cleanly with comprehensive documentation updates across 11 files spanning 7 documentation categories (user-facing, workflow, agent instructions, skills, error messages). This PR demonstrates best practices for CLI command refactoring - updating all reference locations atomically with the code change, leaving no stale documentation.

The session that addressed PR review feedback (session 1ed01ff2) provides a successful example of the `/erk:pr-address` workflow, demonstrating proper classifier isolation via Task tool, source pointer replacement, and batch thread resolution. No errors or retries were needed - a clean execution that can serve as a reference implementation.

## Summary

| Metric | Count |
|--------|-------|
| Documentation items | 6 |
| Contradictions to resolve | 0 |
| Tripwire candidates (score>=4) | 1 |
| Potential tripwires (score 2-3) | 1 |

## Documentation Items

### HIGH Priority

#### 1. CLI Command Function Naming Convention Tripwire

**Location:** `docs/learned/cli/tripwires.md`
**Action:** UPDATE (add tripwire via source frontmatter)
**Source:** [PR #8097]

This item is HIGH priority because it's a cross-cutting pattern that affects all CLI command functions across all command groups, yet isn't enforced by code or explicitly documented as a requirement. The PR demonstrated the pattern (`create_plan` -> `pr_create`) but didn't document it as a convention.

**Draft Content:**

```markdown
Add to the source document's frontmatter tripwires section:

- action: "creating a new CLI command function"
  warning: "Command functions MUST be prefixed with their group name (e.g., `pr_create`, `plan_submit`, `wt_list`). Never use generic names like `create()` that could collide across groups. See pr/__init__.py for registration pattern."
```

**Rationale:** Prevents import collisions when multiple command groups have similar verbs (create, list, view). The prefix maintains namespace clarity and makes grep searches unambiguous.

---

### MEDIUM Priority

#### 2. Command Rename Checklist Verification

**Location:** `docs/learned/cli/command-rename-checklist.md`
**Action:** UPDATE (verify completeness)
**Source:** [PR #8097]

PR #8097 updated 11 files across 7 categories when moving the command. The existing checklist documents 9 places. Verify the checklist covers all update locations demonstrated by this PR:

1. Source file location and function name
2. Command group registration (`__init__.py`)
3. Test file location and invocations
4. User-facing documentation (`docs/learned/cli/`)
5. Workflow documentation (`docs/learned/planning/`)
6. Agent instructions (`AGENTS.md`)
7. Skill examples (`.claude/skills/`)
8. Error messages referencing the command
9. CHANGELOG entry

**Draft Content:**

```markdown
Verify the existing checklist covers:

- Skill references: `.claude/skills/objective/SKILL.md` and `.claude/skills/objective/references/workflow.md` need updating when commands move
- Multiple workflow docs: Both `lifecycle.md` and `plan-creation-pathways.md` may reference the same command

If not present, add these as sub-items under existing checklist categories.
```

#### 3. Bot Summary Discussion Comment Handling

**Location:** `docs/learned/pr-operations/automated-review-handling.md`
**Action:** UPDATE (add guidance section)
**Source:** [Impl]

The session demonstrated that bot summary discussion comments (from `github-actions[bot]` with titles like "Audit PR Docs", "Tripwires Review") reference inline threads but don't require separate action when the underlying threads are resolved. The classifier flagged these as actionable, but the agent correctly dismissed them.

**Draft Content:**

```markdown
## Bot Summary Discussion Comments

Bot summary comments (posted as PR discussion comments, not inline threads) aggregate inline review thread findings. When addressing review feedback:

1. **Identify**: Comment is from `github-actions[bot]` and references "violations" or "review summary"
2. **Check**: Are the underlying inline threads already resolved?
3. **Dismiss**: If underlying threads are resolved, the summary doesn't need separate action

These comments show `classification: "actionable"` from the classifier but are effectively resolved once their underlying threads are addressed.
```

---

### LOW Priority

#### 4. Verify Plan Lifecycle Examples Use New Command

**Location:** `docs/learned/planning/lifecycle.md`
**Action:** VERIFY (already updated in PR)
**Source:** [PR #8097]

**Status:** ALREADY DONE in PR #8097. Verification only - confirm all examples use `erk pr create` not `erk plan create`.

No draft content needed - this is a verification check.

#### 5. Verify Command Organization Mental Model

**Location:** `docs/learned/cli/command-organization.md`
**Action:** VERIFY (already updated in PR)
**Source:** [PR #8097]

**Status:** ALREADY DONE in PR #8097. Verification only - confirm the mental model section correctly documents:
- `erk plan` group handles plan submission operations (`submit`, `list`, `co`, `check`)
- `erk pr` group handles plan creation, viewing, closing, and PR operations

No draft content needed - this is a verification check.

#### 6. Verify Plan Creation Pathways Entry Point Table

**Location:** `docs/learned/planning/plan-creation-pathways.md`
**Action:** VERIFY (already updated in PR)
**Source:** [PR #8097]

**Status:** ALREADY DONE in PR #8097. Verification only - confirm the entry point table shows `erk pr create` as the CLI path.

No draft content needed - this is a verification check.

## Contradiction Resolutions

The gap analysis identified one contradiction regarding `erk plan create` placement in `command-organization.md`, but this was **RESOLVED** as part of PR #8097:

- docs/learned/cli/command-organization.md updated to reflect `erk pr create` placement
- Mental model section reorganized
- Decision framework updated
- All examples updated from `erk plan create` -> `erk pr create`

No further action needed on contradiction.

## Stale Documentation Cleanup

**None detected**. All referenced files in existing documentation are valid and current. The PR's comprehensive update approach prevented any stale references.

## Prevention Insights

No errors or failed approaches occurred during implementation. Session 1ed01ff2 completed with zero errors or retries, demonstrating a mature workflow with proper guardrails in place.

**What went well:**
- Agent correctly loaded `pr-operations` skill as prerequisite
- Used Task tool for classifier isolation as instructed
- Followed batched execution plan (auto-proceeded for simple Batch 1)
- Applied source pointer format correctly
- Ran CI check (prettier) before committing
- Successfully used batch resolution command with JSON stdin
- Verification step correctly handled bot summary comments

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. CLI Command Function Naming Convention

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)
**Trigger:** Before creating a new CLI command function
**Warning:** "Command functions MUST be prefixed with their group name (e.g., `pr_create`, `plan_submit`, `wt_list`). Never use generic names like `create()` that could collide across groups."
**Target doc:** `docs/learned/cli/tripwires.md` (via source document frontmatter)

This pattern was demonstrated in PR #8097 when `create_plan` was renamed to `pr_create`, but it's not explicitly documented as a requirement. Without this tripwire, future contributors might create functions like `def create(...)` or `def view(...)` that collide when imported from multiple command groups.

The pattern prevents:
- Import collisions between groups with similar commands
- Ambiguous grep results when searching for command implementations
- Confusion about which group a function belongs to

## Potential Tripwires

Items with score 2-3 (may warrant tripwire status with additional context):

### 1. Command Group Selection Flowchart Consultation

**Score:** 3/10 (Cross-cutting +2, External tool quirk +1)
**Notes:** This didn't meet threshold because a flowchart already exists in `command-organization.md` - the pattern is documented, just not enforced as a tripwire. However, PR #8097 required reorganizing the mental model, suggesting the flowchart wasn't being consulted before command placement decisions.

If future PRs show ad-hoc command placement decisions, consider promoting this to a tripwire: "Consult the decision framework flowchart in docs/learned/cli/command-organization.md before creating new commands or moving existing commands."

## Skipped Items

| Item | Reason |
|------|--------|
| `create_plan` -> `pr_create` function rename | Internal implementation detail, no cross-cutting pattern |
| CLI registration pattern | Already documented in command-organization.md |
| Test relocation | Test moved with command, no new test patterns |
| Test invocation pattern (`["pr", "create"]`) | Standard test pattern already used throughout |
| Error message update in implement.py | Minor user-facing text change |
| Source pointer replacement pattern | Already documented in docs/learned/documentation/source-pointers.md |
| Batch resolution command | Internal exec script, used correctly per existing docs |
| pr-address workflow example | Already well-documented in docs/learned/erk/pr-address-workflows.md |
| Task tool for subagent isolation | Already documented in docs/learned/architecture/task-context-isolation.md |
| Automated review bot suite | Already documented in docs/learned/ci/automated-review-system.md |
| PR comment metadata format | SHOULD_BE_CODE - belongs as typed structure in source, not documentation |

## Attribution Summary

| Source | Candidates Contributed |
|--------|----------------------|
| Session-analyzer (1ed01ff2) | 5 items (pr-address workflow, bot summary distinction, Task tool pattern) |
| Code-diff-analyzer | 10 items (command rename, function naming, refactoring checklist) |
| Existing-docs-checker | 3 items (contradiction resolution, verification checks) |
| PR-comment-analyzer | 1 item (automated review bot suite - already documented) |

**Total unique candidates after deduplication and SKIP filtering:** 6 documentation items
