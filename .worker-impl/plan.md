# Documentation Plan: Restore third-party reference content stripped by batch regeneration

## Context

This PR (#6882) is a maintenance-focused change with a minimal documentation footprint. The core work involved restoring 20 documentation files that were over-aggressively stripped during batch regeneration—these ARE documentation files containing third-party API reference content, not code requiring documentation. The PR also removed disabled objective reconciliation infrastructure (two GitHub Actions workflows, the CLI trigger function, and related tests) that were never operational for autonomous batch processing.

A future agent reviewing this PR would benefit from understanding: (1) the distinction between documentation work that generates docs vs. documentation work that IS docs, and (2) the critical pattern discovered where incomplete feature removal left a dead reference in the command dispatch map. The session analysis revealed an excellent recovery pattern where the agent immediately pivoted after user clarification that `content_type` should be removed rather than added, but this was situation-specific and not broadly applicable.

The key non-obvious learning is the tripwire-worthy pattern: when removing CLI command infrastructure, all dispatch map entries must also be removed. The `_trigger_objective_reconcile()` function was deleted but the `WORKFLOW_COMMAND_MAP` entry remains at `constants.py:28`, creating a runtime failure waiting to happen.

## Raw Materials

https://gist.github.com/schrockn/013f87a214d401a3fc8a5b0839f2aa37

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 2     |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 1     |
| Potential tripwires (score2-3) | 0     |

## Stale Documentation Cleanup

Existing docs with phantom references requiring action (processed BEFORE new content):

### 1. Objective Reconciler Workflow Documentation

**Location:** `docs/learned/ci/objective-reconciler-workflow.md`
**Action:** DELETE_STALE
**Phantom References:** `.github/workflows/objective-reconciler.yml` (DELETED), `.github/workflows/objective-reconcile.yml` (DELETED)
**Source:** [PR #6882]

**Cleanup Instructions:**

Delete this file entirely. Both workflow files referenced in the documentation were removed in PR #6882, along with the trigger function `_trigger_objective_reconcile()` in `launch_cmd.py`. The documentation now describes features that no longer exist. After deletion, run `erk docs sync` to update the category index files.

## Documentation Items

### HIGH Priority

#### 1. Incomplete Command/Workflow Removal Tripwire

**Location:** `docs/learned/cli/tripwires.md`
**Action:** UPDATE
**Source:** [PR #6882]

**Draft Content:**

```markdown
## Incomplete Command/Workflow Removal

**Trigger**: Before removing CLI command functions, workflow triggers, or command infrastructure

**Warning**: When removing command infrastructure:
1. Search for command name in `WORKFLOW_COMMAND_MAP` and similar dispatch maps in `src/erk/cli/constants.py`
2. Remove or update map entries that reference the deleted function
3. Verify no dead references remain using `grep -r "command_name" src/erk/cli/`
4. Check for related test files that should be removed

**Why This Matters**: Dead map entries look valid in code review but cause runtime failures. Static analysis won't catch function references via string dispatch maps.

**Example**: PR #6882 removed `_trigger_objective_reconcile()` but left the `objective-reconcile` entry in `WORKFLOW_COMMAND_MAP`, creating a dead reference that would fail at runtime with AttributeError.
```

---

### MEDIUM Priority

None.

### LOW Priority

None.

## Contradiction Resolutions

**None detected.** All existing documentation is internally consistent. The batch regeneration prompt in `scripts/batch_regenerate_docs.py` correctly instructs preservation of third-party content, and the learned-docs-core.md skill properly defines the exceptions.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Plan-Implementation Requirements Mismatch

**What happened:** Agent completed full implementation following the plan exactly (adding `content_type` field infrastructure, validation tests, and restoring 20 docs with the marker). After completion, user clarified the actual intent was to *remove* the `content_type` field entirely, not add it.

**Root cause:** The plan explicitly called for adding `content_type` infrastructure (Step 1: "Add `content_type` to AgentDocFrontmatter model"), but this was not the user's actual requirement. User's question "i thought we could rid of the content_type header in frontmatter?" revealed the discrepancy.

**Prevention:** When a plan includes optional infrastructure (like marker fields that could be omitted), consider confirming at implementation start: "Should we add the `content_type` marker, or just restore the docs without it?"

**Recommendation:** CONTEXT_ONLY — The recovery pattern was exemplary (acknowledge, verify, offer options, execute) but the situation was specific to this one PR. Not broadly applicable enough for a tripwire.

### 2. Incomplete Feature Removal

**What happened:** The trigger function `_trigger_objective_reconcile()` was deleted from `launch_cmd.py`, but the `objective-reconcile` entry in `WORKFLOW_COMMAND_MAP` at `constants.py:28` was left in place.

**Root cause:** When removing feature code, the dispatch map wasn't checked for dependent entries. String-based command routing makes these dead references invisible to static analysis.

**Prevention:** Before completing any feature removal, grep for the feature name across all constant files, dispatch maps, and configuration dictionaries.

**Recommendation:** TRIPWIRE — This pattern scores 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2) and is documented in HIGH priority item #1 above.

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Incomplete Command/Workflow Removal Pattern

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before removing CLI command infrastructure or workflow triggers
**Warning:** Verify all dispatch map entries are cleaned up; search for command name in constants and maps
**Target doc:** `docs/learned/cli/tripwires.md`

This pattern is tripwire-worthy because:

1. **Non-obvious**: The `WORKFLOW_COMMAND_MAP` entry looks completely valid in isolation. Only runtime execution would reveal the missing function.

2. **Cross-cutting**: The command dispatch system is used by multiple commands (`erk launch <workflow-name>`), so this pattern applies whenever any workflow trigger is removed.

3. **Silent failure**: No static analysis or type checking catches this. The error only manifests when a user tries to run `erk launch objective-reconcile`, which could be weeks or months after the PR lands.

The specific case: `src/erk/cli/constants.py:28` still contains `objective-reconcile` entry, but `_trigger_objective_reconcile()` was deleted from `launch_cmd.py`. This creates a dead reference that would fail at runtime.

## Potential Tripwires

None with score 2-3. All other patterns discovered in this implementation were either already documented or were too situation-specific to warrant tripwires.

## Skipped Items

Items not requiring documentation:

| Item | Reason |
|------|--------|
| 20 restored documentation files | These ARE documentation (third-party reference content), not code requiring documentation |
| `generate_category_index()` subdirectory fix | Self-documenting bug fix using `Path(doc.rel_path).name` for relative links |
| `docs/learned/cli/commands/pr-summarize.md` | Is documentation itself |
| Auto-generated file conflict resolution pattern | Already documented in `.claude/commands/erk/fix-conflicts.md` |
| Post-implementation user correction pattern | LOW severity, specific incident, not broadly applicable |
| Test file deletion (`test_launch_cmd.py`) | Tests removed with feature, no doc needed |
| Batch frontmatter editing with sed | Session technique but not worthy of standalone doc |

## Verification Checklist

Before closing this learn plan, verify:

- [ ] `docs/learned/ci/objective-reconciler-workflow.md` is deleted
- [ ] New tripwire entry added to `docs/learned/cli/tripwires.md` for incomplete command removal pattern
- [ ] Verify whether `WORKFLOW_COMMAND_MAP` entry at `constants.py:28` should be removed (confirm it's actually dead)
- [ ] Run `erk docs sync` to update index files after deleting objective-reconciler-workflow.md

## Final Assessment

**Documentation burden**: MINIMAL

This PR has a very light documentation footprint:
- 7 of 10 inventory items are SKIP (already documented or are documentation themselves)
- 1 item is DELETE_STALE (removing stale docs, not creating new ones)
- 1 item is a single tripwire entry (~15 lines)
- 1 item requires investigation (may result in no action if map entry is still valid)

**Net documentation delta**: -1 file (delete objective-reconciler-workflow.md) + 1 tripwire entry (~15 lines)

The primary work was content restoration, not creating new code or patterns requiring documentation.