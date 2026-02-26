# Plan mismatch recovery, stale doc cleanup, and evolving-systems patterns

## Context

This learn plan captures insights from a documentation-only PR (#8346) that updated agent documentation to reflect the codebase migration from `.impl/issue.json` to `.impl/plan-ref.json`. While the PR itself contained no code changes, the implementation session revealed several undocumented agent workflows and error recovery patterns that warrant new documentation.

The implementation agent encountered a plan reference mismatch (wrong PR content loaded into `.impl/impl-context/`), silent failures from `erk pr submit`, and discovered that existing documentation contains phantom file references to files that no longer exist. These discoveries, combined with PR review feedback that identified documentation anti-patterns (hardcoded step counts drifting), provide valuable lessons for future agents.

Documentation matters here because agents frequently work with the `.impl/` folder structure during plan implementation, and the current documentation doesn't adequately cover validation workflows, error recovery, or the fallback chain behavior. Additionally, several existing docs have become stale with phantom references that actively mislead agents.

## Raw Materials

PR #8346: https://github.com/dagster-io/erk/pull/8346

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 6     |
| Contradictions to resolve      | 2     |
| Tripwire candidates (score>=4) | 2     |
| Potential tripwires (score2-3) | 1     |

## Stale Documentation Cleanup

Existing docs with phantom references requiring action. Resolve these BEFORE creating new documentation:

### 1. issue-pr-linkage-storage.md (phantom file references)

**Location:** `docs/learned/erk/issue-pr-linkage-storage.md`
**Action:** UPDATE_REFERENCES or DELETE_STALE
**Phantom References:** `src/erk/cli/commands/exec/scripts/get_closing_text.py`, `setup_impl_from_issue.py`

**Cleanup Instructions:**

The "Key Files" table references files that no longer exist in the codebase. The document also presents `.impl/issue.json` as the primary storage location, but current architecture uses `plan-ref.json` as primary with `issue.json` as legacy fallback.

Options:
1. **UPDATE_EXISTING**: Reposition `issue.json` as legacy format, add `plan-ref.json` as primary, and replace phantom file references with current file paths. Verify current file structure with `ls src/erk/cli/commands/exec/scripts/`.
2. **DELETE_STALE**: If content is fully superseded by `docs/learned/architecture/ref-json-migration.md` and `docs/learned/architecture/plan-ref-architecture.md`, delete this document to avoid confusion.

### 2. impl-context.md (phantom line number references)

**Location:** `docs/learned/planning/impl-context.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** `setup_impl_from_issue.py:202` (file does not exist)

**Cleanup Instructions:**

Replace phantom `setup_impl_from_issue.py:202` reference with the correct file path `setup_impl_from_pr.py`. Verify the specific line numbers against current source before updating. Do not include line numbers if the referenced code may move — use file-level pointers instead.

### 3. issue-reference-flow.md (command/exec naming verification)

**Location:** `docs/learned/architecture/issue-reference-flow.md`
**Action:** INVESTIGATE_PATTERN
**Phantom References:** `setup-impl-from-pr` (command), `get-closing-text` (exec script)

**Cleanup Instructions:**

Verify whether these command/exec names exist in the current codebase:
- Run `erk --help | grep -i setup` to check command names
- Run `ls src/erk/cli/commands/exec/scripts/` to check exec script names

If names have changed, update the document. If the entire document describes an obsolete architecture, consider DELETE_STALE.

## Contradiction Resolutions

### 1. issue-pr-linkage-storage.md: issue.json presented as primary

**Existing doc:** `docs/learned/erk/issue-pr-linkage-storage.md`
**Conflict:** Document presents `.impl/issue.json` as the primary storage location, but current architecture uses `plan-ref.json` as primary with `issue.json` as legacy fallback.
**Resolution:** This is a staleness issue, not an architectural conflict. Handle as part of the stale documentation cleanup above (UPDATE_EXISTING or DELETE_STALE).

### 2. impl-context.md: phantom file references

**Existing doc:** `docs/learned/planning/impl-context.md`
**Conflict:** Document references `setup_impl_from_issue.py:202` with specific line numbers and inline comments, but the file does not exist (actual file is `setup_impl_from_pr.py`).
**Resolution:** This is a staleness issue, not an architectural conflict. Handle as UPDATE_REFERENCES in the stale documentation cleanup above.

## Documentation Items

### HIGH Priority

#### 1. Plan reference mismatch recovery

**Location:** `docs/learned/planning/plan-mismatch-recovery.md`
**Action:** CREATE
**Source:** [Impl] - session-175fe42a-part1

**Draft Content:**

```markdown
---
category: planning
description: How to detect and recover when setup-impl fetches wrong plan content
read_when: detecting plan/branch mismatch in .impl folder, recovering from wrong plan content in impl-context
tripwires:
  - action: After running erk exec setup-impl
    warning: Verify .impl/impl-context/ref.json plan_id matches expected issue/PR number from branch name
---

# Plan Reference Mismatch Recovery

## The Problem

After running `erk exec setup-impl`, the `.impl/impl-context/` folder may contain content from a different PR or issue than the current branch expects. This happens when:
- The worktree was previously used for a different plan
- The setup-impl command resolved to the wrong issue/PR
- Stale cached content wasn't cleared

## Detection Pattern

Check that the plan reference matches the branch name:

1. Read `.impl/impl-context/ref.json` and note the `plan_id` field
2. Extract the expected issue/PR number from the branch name (e.g., `plnd/some-feature-02-26-2053` implies PR number from associated issue)
3. If they don't match, you have stale content

## Recovery Pattern

When mismatch is detected, fetch the correct plan content directly:

1. Run `gh pr view <correct-number> --json body` to get the plan markdown
2. Parse the body to extract the implementation plan
3. Continue implementation using the fetched content rather than stale `.impl/impl-context/plan.md`

## Why This Matters

Implementing the wrong plan wastes time and creates incorrect PRs. Always validate plan content matches your branch before starting implementation work.

## See Also

- See `src/erk/cli/commands/exec/scripts/setup_impl_from_pr.py` for setup-impl internals
```

---

#### 2. erk pr submit silent failure fallback (TRIPWIRE)

**Location:** `docs/learned/planning/tripwires.md` (add entry) OR `docs/learned/cli/pr-submission-patterns.md` (add section)
**Action:** UPDATE
**Source:** [Impl] - session-175fe42a-part2

**Draft Content:**

```markdown
## erk pr submit Silent Failure Fallback

**Tripwire:** Before running `erk pr submit -f` when branch has diverged from remote

**Warning:** If `erk pr submit -f` produces empty output or appears to hang, use `gt submit --no-interactive --force` directly via devrun agent. The erk wrapper may have edge cases with diverged branches.

**Context:** In session-175fe42a-part2, the agent attempted `erk pr submit -f` twice with no output before falling back to direct `gt submit` invocation, which succeeded immediately. This suggests the wrapper command has unhandled edge cases when local and remote branches have diverged.

**Prevention:**
1. Check `git status` for divergence warnings before submitting
2. If diverged, consider using `gt submit --no-interactive --force` directly
3. If `erk pr submit` produces no output after several seconds, cancel and use the direct command
```

---

### MEDIUM Priority

#### 3. Setup-impl validation workflow

**Location:** `docs/learned/planning/setup-impl-validation.md`
**Action:** CREATE
**Source:** [Impl] - session-175fe42a-part1

**Draft Content:**

```markdown
---
category: planning
description: How to verify plan content matches branch after setup-impl
read_when: verifying plan content after setup-impl, checking impl folder structure
---

# Setup-Impl Validation Workflow

## After Running setup-impl

After `erk exec setup-impl` completes, validate the setup before proceeding:

### 1. Locate the Plan File

The plan may be in one of two locations:
- `.impl/plan.md` (standard location)
- `.impl/impl-context/plan.md` (when impl-context subdirectory is used)

Check both paths. Use `ls -la .impl/` to understand the directory structure.

### 2. Verify Plan Reference

Read `.impl/impl-context/ref.json` (or `.impl/plan-ref.json`) and confirm the `plan_id` matches the expected issue/PR number for your branch.

### 3. Handle impl-signal Failures

The `impl-signal started` command may fail with `error_type: "no-issue-reference"` if the plan reference isn't in the expected location. This is **non-fatal** — continue with implementation if you've manually verified the plan content is correct.

## Why Validation Matters

Skipping validation can lead to implementing the wrong plan, which wastes time and creates incorrect PRs. The few seconds spent validating prevent hours of rework.

## See Also

- `docs/learned/planning/plan-mismatch-recovery.md` for recovery when validation fails
```

---

#### 4. Documenting evolving systems (anti-pattern)

**Location:** `docs/learned/documentation/documenting-evolving-systems.md`
**Action:** CREATE
**Source:** [PR #8346] - all 4 audit violations were hardcoded step-count drift

**Draft Content:**

```markdown
---
category: documentation
description: Anti-patterns and patterns for documenting systems that evolve
read_when: documenting pipeline steps, field counts, or other enumerated implementation details
tripwires:
  - action: When documenting pipeline step counts or state field counts
    warning: Avoid hardcoded counts that will drift. Use source pointers or ranges.
---

# Documenting Evolving Systems

## The Problem

Documentation that references specific counts, field names, or implementation details becomes stale as code evolves. In PR #8346, all 4 audit violations were caused by hardcoded step counts that drifted from 8 to 10 steps.

## Anti-Patterns

**Hardcoded counts:**
- "The pipeline has 8 steps" — Will drift silently as steps are added/removed
- "The dataclass has 12 fields" — Becomes stale when fields change
- "Lines 45-67 contain the validation logic" — Line numbers shift constantly

**Verbatim code blocks:**
- Copying implementation code into docs creates two sources of truth
- Code changes but docs don't, creating confusion

## Patterns

**Use source pointers instead of counts:**
- "See `_submit_pipeline()` for pipeline steps" — Points to canonical location
- "See the `PlanRef` dataclass in `impl_folder.py`" — Agents can grep to find current state

**Use ranges for approximate counts:**
- "~20 fields" or "approximately 10 steps" — Communicates scale without false precision
- Acceptable when the exact count isn't critical to understanding

**Separate user-facing from internal docs:**
- User-facing docs can include counts if they're part of the user contract
- Internal/agent docs should use source pointers

## Why This Matters

Stale documentation is worse than no documentation — it actively misleads agents and wastes time on confusion and rework. Source pointers ensure agents always see current reality.

## See Also

- `docs/learned/documentation/source-pointers.md` for pointer format guidance
```

---

### LOW Priority

None identified.

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. erk pr submit silent failure fallback

**Score:** 5/10 (Non-obvious +2, Silent failure +2, External tool quirk +1)
**Trigger:** Before running `erk pr submit -f` when branch is diverged
**Warning:** Use `gt submit --no-interactive --force` directly if erk pr submit hangs or produces empty output. The erk wrapper may have edge cases with diverged branches.
**Target doc:** `docs/learned/planning/tripwires.md` or `docs/learned/cli/pr-submission-patterns.md`

This is highly tripwire-worthy because the failure is completely silent — no error message, no timeout, just empty output. Agents may retry multiple times before discovering the workaround. The session shows two failed attempts before the agent switched to direct `gt submit` invocation.

### 2. Plan reference mismatch detection

**Score:** 5/10 (Non-obvious +2, Cross-cutting +2, Repeated pattern +1)
**Trigger:** After running `erk exec setup-impl`
**Warning:** Verify `.impl/impl-context/ref.json` plan_id matches expected issue/PR number from branch name. If mismatched, fetch correct plan with `gh pr view <number> --json body`. Check both `.impl/plan.md` and `.impl/impl-context/plan.md` for plan content.
**Target doc:** `docs/learned/planning/tripwires.md`

This is tripwire-worthy because agents naturally trust that setup-impl provides the correct content. The mismatch is subtle and can lead to implementing an entirely wrong plan. The session shows the agent had to detect this independently and recover by fetching from GitHub API.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Documenting evolving systems with hardcoded counts

**Score:** 3/10 (Non-obvious +2, Repeated pattern +1)
**Notes:** This isn't a runtime error, but a documentation quality anti-pattern. All 4 PR audit violations were this exact pattern — hardcoded step counts drifted from 8 to 10. Not promoted to full tripwire because it doesn't cause agent failures, only documentation staleness that's caught by automated audit.

**Promotion criteria:** If documentation staleness becomes a significant time sink (agents frequently confused by stale counts), promote this to a full tripwire.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Plan content mismatch in .impl/impl-context/

**What happened:** Agent started implementation work but discovered `.impl/impl-context/ref.json` pointed to PR #8336 while the branch was for PR #8346.
**Root cause:** `setup-impl` sometimes fetches content from a different PR/issue than expected, possibly due to stale worktree state or resolution logic edge cases.
**Prevention:** Add validation after `setup-impl`: check that `.impl/impl-context/ref.json` plan_id matches expected issue/PR number from branch name before proceeding.
**Recommendation:** TRIPWIRE — this error is non-obvious and leads to wasted work implementing the wrong plan.

### 2. erk pr submit silent failures

**What happened:** Agent ran `erk pr submit -f` twice, getting empty output both times, before switching to direct `gt submit --no-interactive --force` which succeeded immediately.
**Root cause:** The erk wrapper command has unhandled edge cases with diverged branches. The failure is completely silent — no error message, no indication of what went wrong.
**Prevention:** Check `git status` for divergence warnings before submitting. If `erk pr submit` produces no output, switch to direct `gt submit` invocation.
**Recommendation:** TRIPWIRE — silent failures are the most dangerous because agents may retry indefinitely without realizing the issue.

### 3. Hardcoded step counts drifting

**What happened:** Documentation stated "8 steps" in the pipeline, but actual code had 10 steps. Bot audit caught this discrepancy.
**Root cause:** Documentation used hardcoded counts instead of source pointers. As code evolved, counts drifted.
**Prevention:** Use source pointers ("see `_submit_pipeline()`") instead of hardcoded counts. Or use ranges ("~10 steps") when precision isn't critical.
**Recommendation:** ADD_TO_DOC — create `documenting-evolving-systems.md` with anti-patterns and patterns.

## Validation Checklist

Before marking this plan complete:

- [ ] All 3 stale reference issues resolved (issue-pr-linkage-storage.md, impl-context.md, issue-reference-flow.md)
- [ ] All 2 contradictions resolved (both are staleness-based, handled in stale cleanup)
- [ ] 2 new documentation files created (plan-mismatch-recovery.md, setup-impl-validation.md)
- [ ] 1 new documentation file created (documenting-evolving-systems.md)
- [ ] 2 tripwires added to planning/tripwires.md
- [ ] Grep verification: no more phantom file references in updated docs
- [ ] Grep verification: `issue.json` references include "(legacy)" qualifier where appropriate
