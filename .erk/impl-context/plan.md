# Plan: Consolidate learned documentation from 23 erk-learn plans

> **Consolidates:** #8991, #8989, #8988, #8987, #8986, #8979, #8978, #8977, #8972, #8971, #8970, #8969, #8968, #8967, #8964, #8963, #8962, #8956, #8952, #8951, #8946, #8942, #8940

## Context

23 erk-learn plans were generated from recently merged PRs. All code changes are fully implemented. The remaining work is purely documentation: updating stale terminology in docs/learned/, fixing references to deleted architecture layers, and documenting new patterns discovered during implementation.

## Source Plans

| # | Title | Items |
|---|-------|-------|
| #8987 | Rename `plan_issues` module to `objective_issues` | Implemented, doc verified |
| #8971 | Standardize plan terminology | 62 doc instances remaining |
| #8969 | Rename issue_workflow to plan_workflow | Implemented, verified |
| #8963 | Fix cli/ and erk/ docs terminology | 7 files still need updates |
| #8991 | Fix objective auto-close: robust code + prompt | Implemented |
| #8968 | Fix objective auto-close edge case | Implemented |
| #8977 | Enable objective operations without repo | Implemented |
| #8952 | Remove --plan flag from objective-apply-landed-update | Implemented |
| #8962 | Fix objective roadmap sync normalization | Implemented |
| #8967 | Remove printing layer from gateway pattern | 8 docs still reference printing |
| #8986 | Expand mock-to-fake skill with decision framework | Implemented |
| #8956 | Refactor cmux_checkout_workspace mock to fake | Implemented |
| #8946 | Unify local/remote codepaths in PR read commands | Implemented |
| #8979 | Refactor --dangerous to live_dangerously config | Implemented |
| #8978 | Centralize repository resolution logic | Implemented |
| #8970 | Simplify current-worktree commands | Implemented |
| #8972 | Add "l" key to launch launchpad | Implemented |
| #8989 | Add remote dispatch support to pr dispatch | Implemented |
| #8988 | Show per-file metadata in manifest output | Implemented |
| #8964 | Update CHANGELOG.md unreleased section | Implemented, 1 stale ref |
| #8942 | Consolidate session/manifest handling code | Implemented |
| #8940 | Canonicalize session storage branch naming | Implemented |
| #8951 | Fix MCP package workspace source configuration | Implemented |

## Investigation Findings

### What Changed Since Original Plans

All 23 source PRs have been merged. No code gaps remain.

### Remaining Documentation Gaps

**Gap 1: "plan issue" terminology (62 instances in 34 files)**

The largest gap. These docs still say "plan issue" where they should say "plan":

- **architecture/** (8 files, 14 instances): fail-open-patterns.md, github-issue-autoclose.md, github-cli-limits.md, plan-backend-migration.md, plan-context-integration.md, session-discovery.md, index.md, tripwires.md
- **planning/** (14 files, 20 instances): learn-pipeline-workflow.md, learn-plan-metadata-fields.md, complete-inventory-protocol.md, consolidation-labels.md, cross-artifact-analysis.md, token-optimization-patterns.md, planned-pr-context-local-preprocessing.md, session-preprocessing.md, no-changes-handling.md, plan-header-privatization.md, branch-name-inference.md, tripwires.md, learn-plan-validation.md
- **cli/** (6 files, 8 instances): learn-plan-land-flow.md, workflow-commands.md, pr-rewrite.md, slash-command-llm-turn-optimization.md, tripwires.md, commands/pr-summarize.md
- **objectives/** (4 files, 4 instances): research-documentation-integration.md, roadmap-mutation-patterns.md, objective-lifecycle.md, objective-roadmap-check.md
- **erk/** (3 files, 3 instances): pr-commands.md, tripwires.md, index.md
- **Other** (6+ files across pr-operations, tui, ci, documentation, workflows, reference)

**Gap 2: Stale "printing"/"5-file" gateway references (8+ files)**

These docs reference the deleted printing layer:
- `docs/learned/architecture/discriminated-union-error-handling.md` (line 13: "Update ALL 5 implementations")
- `docs/learned/architecture/lbyl-gateway-pattern.md` (mentions DryRunGitHubIssues, printing gateways)
- `docs/learned/architecture/gateway-vs-backend.md`
- `docs/learned/architecture/abc-convenience-methods.md`
- `docs/learned/architecture/erk-shared-package.md`
- `docs/learned/architecture/tripwires.md`

**Gap 3: CHANGELOG async-learn reference**

- `CHANGELOG.md` line 38: says "async-learn branches" should say "planned-pr-context branches"

## Implementation Steps

### Step 1: Fix CHANGELOG stale reference

**File:** `CHANGELOG.md`
- Change "async-learn branches" to "planned-pr-context branches" on line 38
- **Verification:** `grep -n "async-learn" CHANGELOG.md` returns 0 results

### Step 2: Sweep "plan issue" → "plan" in docs/learned/

**Scope:** 34 files, 62 instances across docs/learned/

**Method:** For each file, replace "plan issue" with "plan" (case-sensitive). Key replacements:
- "plan issue" → "plan"
- "plan issues" → "plans"
- "Plan Issue" → "Plan" (in titles)
- "Plan Issues" → "Plans" (in titles)

Preserve "GitHub Issue" and "objective issue" — those are correct terminology.

**Files by directory** (grep `plan issue` in each, fix all hits):
- `docs/learned/architecture/` — 8 files
- `docs/learned/planning/` — 14 files
- `docs/learned/cli/` — 6 files
- `docs/learned/objectives/` — 4 files
- `docs/learned/erk/` — 3 files
- Remaining scattered files

**Verification:** `grep -r "plan issue" docs/learned/ | grep -v "objective issue"` returns 0

### Step 3: Update stale gateway/printing references

**File:** `docs/learned/architecture/discriminated-union-error-handling.md`
- Line 13: Change "Update ALL 5 implementations (ABC, real, fake, dry_run, printing)" to "Update all implementations (ABC, real, fake; add dry_run only for dry-run-participating gateways)"

**File:** `docs/learned/architecture/lbyl-gateway-pattern.md`
- Remove/update references to printing gateways and DryRunGitHubIssues
- Update to reflect 3-file default, 4-file opt-in pattern

**Other files:** gateway-vs-backend.md, abc-convenience-methods.md, erk-shared-package.md, tripwires.md
- Update any "5-file" references to "3-file default / 4-file opt-in"
- Remove references to Printing* classes

**Verification:** `grep -r "printing" docs/learned/architecture/ | grep -iv "print("` shows no stale gateway references

### Step 4: Run docs sync

```bash
erk docs sync
```

Regenerate any auto-generated index files affected by the changes.

**Verification:** `git diff` shows only expected changes in auto-generated files

## Attribution

| Source Plans | Steps |
|---|---|
| #8971, #8963, #8987, #8969 | Step 2 (terminology sweep) |
| #8967, #8986 | Step 3 (gateway docs) |
| #8964, #8940 | Step 1 (CHANGELOG fix) |
| #8991, #8968, #8977, #8952, #8962, #8979, #8978, #8970, #8972, #8989, #8988, #8956, #8946, #8942, #8951 | No remaining gaps — code fully implemented, patterns already documented |

## Verification

1. `grep -r "plan issue" docs/learned/ | grep -v "objective issue"` → 0 results
2. `grep -r "printing" docs/learned/architecture/ | grep -iv "print("` → no stale gateway refs
3. `grep "async-learn" CHANGELOG.md` → 0 results
4. `erk docs sync` runs cleanly
