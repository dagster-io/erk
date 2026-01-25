# Documentation Plan: Analysis: PR #6023 .worker-impl/ Not Cleaned Up

## Context

This plan documents learnings from investigating and fixing PR #6023, where `.worker-impl/` transient artifacts were not properly cleaned up during remote implementation workflows. The investigation revealed a critical architectural flaw: the erk-impl workflow had two broken cleanup mechanisms - (1) agent-dependent cleanup that was non-deterministic, and (2) workflow-native staging that was silently discarded by a subsequent `git reset --hard` command.

The fix moved `.worker-impl/` cleanup from unreliable agent behavior and broken staging to a dedicated deterministic workflow step that commits and pushes cleanup BEFORE any destructive git operations. This pattern of "deterministic vs non-deterministic cleanup" and "commit-before-reset" ordering represents a significant architectural learning for CI reliability.

Future agents implementing similar workflow modifications will benefit from understanding: (1) why critical cleanup operations must be workflow-native rather than agent-dependent, (2) the destructive interaction between `git add` staging and `git reset --hard`, and (3) patterns for designing multi-layer failure mode resilience in CI workflows.

## Raw Materials

https://gist.github.com/schrockn/ea8c49ec5958b6955d32f41391e54cf1

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 10    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 3     |
| Potential tripwires (score 2-3)| 5     |

## Documentation Items

### HIGH Priority

#### 1. Workflow Step Ordering: Cleanup Before Reset [NEW]

**Location:** `docs/learned/ci/erk-impl-workflow-patterns.md`

**Rationale:** Critical ordering dependency discovered - staged changes are discarded by `git reset --hard` if not committed first. This pattern affects all workflow-native cleanup operations.

**Key Points:**
- Document critical ordering: commit/push cleanup BEFORE any `git reset --hard`
- Explain why staging without commit fails silently
- Provide before/after examples
- Cross-reference tripwire

**Source:** [Impl] session-impl-2.md

---

#### 2. Compound Condition Validation in Workflows [NEW]

**Location:** `docs/learned/ci/github-actions-workflow-patterns.md`

**Rationale:** Complex step output conditions discovered in erk-impl cleanup step. Silent failures occur when step IDs or output keys don't match.

**Key Points:**
- Validate each `steps.step_id.outputs.key` reference
- Document correct `steps.step_id.outcome` syntax
- Provide validation checklist
- Cross-reference tripwire

**Source:** [Impl] session-impl-2.md

---

#### 3. Closing Text Implicit Dependency [UPDATE]

**Location:** `docs/learned/planning/lifecycle.md`

**Rationale:** `erk exec get-closing-text` silently returns empty string if `.impl/issue.json` missing. This creates PRs without "Closes #N" reference.

**Key Points:**
- Add tripwire to lifecycle.md
- Document `.impl/issue.json` as worktree setup contract
- Explain silent failure pattern
- Reference from pr-submission-patterns

**Source:** [Impl] session-impl-1.md, session-impl-3.md

---

### MEDIUM Priority

#### 4. Deterministic vs Non-Deterministic Cleanup [NEW]

**Location:** `docs/learned/planning/reliability-patterns.md`

**Rationale:** Pattern for choosing between agent vs workflow-native cleanup. Critical operations should be deterministic (workflow-native), not agent-dependent.

**Key Points:**
- Explain non-determinism in agent behavior
- Document multi-layer failure mode design
- Provide decision framework: when to use which approach
- Example: .worker-impl/ cleanup progression

**Source:** [Impl] session-impl-2.md

---

#### 5. Idempotent PR Submission Pattern [NEW]

**Location:** `docs/learned/planning/pr-submission-patterns.md`

**Rationale:** Sessions demonstrate existing PR detection pattern that prevents duplicate PRs and handles retries gracefully.

**Key Points:**
- Show pattern for checking existing PRs before creation
- Explain benefits for concurrent/retried submissions
- Document `gh pr list --head` usage
- Implementation notes about branch-based discovery

**Source:** [Impl] session-impl-1.md, session-impl-3.md

---

#### 6. erk exec Command Interface Reference [UPDATE]

**Location:** `docs/learned/cli/erk-exec-commands.md`

**Rationale:** Agent encountered inconsistency with `--format` flag. Unclear which exec commands support it.

**Key Points:**
- Create reference table: which commands support `--format json`
- Document which always return JSON without flag
- Best practice: always check `--help`
- Reduce confusion for future agents

**Source:** [Plan] session-planning.md

---

#### 7. Plan Metadata Field Population Lifecycle [UPDATE]

**Location:** `docs/learned/planning/lifecycle.md`

**Rationale:** Planning-stage plans lack `branch_name` field. Document when each field is populated across stages.

**Key Points:**
- Add field population table by plan stage
- Clarify planning vs submitted vs implementing vs landed
- Explain why `branch_name` is null at planning stage
- Reference from plan analysis workflows

**Source:** [Plan] session-planning.md

---

### LOW Priority

#### 8. Two-Layer Skill Composition Pattern [NEW]

**Location:** `docs/learned/claude-code/skill-composition-patterns.md`

**Rationale:** Sessions demonstrate skill loading skill loading (erk-diff-analysis loads commit-message-prompt). Useful pattern for domain-specific skills.

**Key Points:**
- Document skill composition hierarchy
- Show example: /erk:git-pr-push → erk-diff-analysis → commit-message-prompt
- Explain composition benefits
- Reference from skill authoring guidelines

**Source:** [Impl] session-impl-1.md, session-impl-3.md

---

#### 9. Commit Message Generation Constraints [UPDATE]

**Location:** `docs/learned/conventions.md`

**Rationale:** AI-generated commit messages have specific constraints discovered in sessions.

**Key Points:**
- NO Claude attribution footer
- NO metadata headers
- Component-level descriptions only
- Max 5 key changes

**Source:** [Impl] session-impl-1.md, session-impl-3.md

---

#### 10. Prettier Failure Patterns with Transient Artifacts [UPDATE]

**Location:** `docs/learned/ci/formatter-tools.md`

**Rationale:** Prettier fails on `.worker-impl/` markdown files. This is intentional - it serves as cleanup detection.

**Key Points:**
- Explain prettier behavior on transient artifacts
- Provide detection pattern: prettier failures on `.worker-impl/*.md`
- Suggest recovery: manual cleanup command
- Cross-reference tripwire and lifecycle docs

**Source:** [Plan] session-planning.md

---

## Prevention Insights

### Silent Failures

1. **Staged changes discarded by reset**: `git add` followed by `git reset --hard` silently undoes work
2. **Missing .impl/issue.json**: `get-closing-text` returns empty string, PR lacks Closes reference
3. **Typos in workflow conditions**: Step IDs mismatch causes silent condition failure

### Non-Determinism

1. **Agent cleanup skipping**: Agent behavior varies across runs - context limits, interpretation, early termination
2. **Skill output constraints**: If not documented, agents generate invalid commit messages with Claude footers

### Subtle Interactions

1. **Workflow step ordering**: Cleanup must happen before reset, before CI triggers, after PR submission
2. **Metadata dependencies**: Worktree setup and PR submission have implicit contract via `.impl/issue.json`

---

## Tripwires Identified

### Score >= 4 (Recommended for addition)

**1. Git Reset After Staging Cleanup (Score: 6)**
- **Trigger:** Before running `git reset --hard` in workflows after staging cleanup
- **Warning:** Verify all cleanup changes are committed BEFORE reset; staged changes without commit will be silently discarded
- **Target:** `docs/learned/ci/erk-impl-workflow-patterns.md`
- **Rationale:** Silent failure + cross-cutting pattern + destructive potential

**2. Compound Workflow Conditions (Score: 4)**
- **Trigger:** Before composing conditions across multiple GitHub Actions workflow steps
- **Warning:** Verify each `steps.step_id.outputs.key` reference exists and matches actual step IDs
- **Target:** `docs/learned/ci/github-actions-workflow-patterns.md`
- **Rationale:** Silent step skipping + non-obvious syntax

**3. Missing .impl/issue.json Metadata (Score: 4)**
- **Trigger:** Before calling commands that depend on `.impl/issue.json` metadata
- **Warning:** Verify metadata file exists in worktree; if missing, operations silently return empty values
- **Target:** `docs/learned/planning/lifecycle.md`
- **Rationale:** Silent failure + cross-cutting + subtle dependency

---

## Contradictions

**NONE DETECTED** - All existing documentation is internally consistent on `.worker-impl/` cleanup requirements and workflow patterns.

---

## Summary Statistics

- **New documentation:** 5 new files (skill composition, reliability patterns, workflow patterns, PR patterns, prettier failures)
- **Updated documentation:** 5 existing files (lifecycle, conventions, erk-exec-commands, formatter-tools, tripwires)
- **Tripwires to add:** 3 high-priority tripwires
- **Potential tripwires:** 5 additional candidates (lower priority)
- **Case studies:** None (focus on patterns and prevention, not incident documentation)