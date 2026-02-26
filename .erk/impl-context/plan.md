# Documentation Plan: Change Dispatch to Queue keyboard shortcut from 's' to 'd'

## Context

This PR (#8305) makes two distinct changes, only one of which was documented in the original plan. The stated goal was to change the "Dispatch to Queue" TUI command's keyboard shortcut from 's' to 'd' for better mnemonics. However, the implementation also includes a significant architectural change: moving the plan-header metadata block from the top to the bottom of planned PR bodies.

The keyboard shortcut change itself is straightforward and validates that existing TUI documentation is comprehensive. The agent successfully identified all three locations requiring updates (registry, launch screen, tests) and executed without errors. This confirms the three-location coordination pattern documented in `docs/learned/tui/tui-command-registration.md` works well.

The undocumented metadata positioning change has broader architectural implications. It affects PR body formatting, validation rules, and test utilities. This change is part of the broader flat format elimination effort (see commit c5854b1e2) and improves user experience by placing technical metadata after the human-readable plan summary.

## Raw Materials

PR #8305

## Summary

| Metric | Count |
|--------|-------|
| Documentation items | 2 |
| Contradictions to resolve | 0 |
| Tripwire candidates (score>=4) | 0 |
| Potential tripwires (score 2-3) | 0 |

## Documentation Items

### HIGH Priority

#### 1. Update Metadata Block Position in Planned PR Lifecycle Documentation

**Location:** `docs/learned/planning/planned-pr-lifecycle.md`
**Action:** UPDATE
**Source:** [PR #8305]

**Draft Content:**

The body format examples at lines 38-70 show metadata at the top. These need to be updated to show the new format where metadata appears after the `</details>` tag.

```markdown
## Stage Definitions

### Stage 1: Plan Creation

`plan_save` / `PlannedPRBackend.create_plan()` creates a draft PR with `lifecycle_stage: planned` in the plan-header metadata. The body contains the plan content collapsed in a `<details>` tag, followed by the plan-header metadata block at the bottom, with a checkout footer.

Body format:

\`\`\`
<details>
<summary>original-plan</summary>

[plan content]

</details>
\n\n
[metadata block]
\n---\n
[checkout footer]
\`\`\`

### Stage 2: Implementation

After code changes, `erk pr submit` / `erk pr rewrite` rewrites the body. The metadata block is preserved at the bottom. The AI-generated summary is inserted before the collapsed plan.

Body format:

\`\`\`
[AI-generated summary]

<details>
<summary>original-plan</summary>

[plan content]

</details>
\n\n
[metadata block]
\n---\n
[checkout footer]
\`\`\`
```

Also update the function table at line 83:

```markdown
| `build_plan_stage_body(metadata_body, plan_content)` | Build Stage 1 body: details-wrapped plan + metadata at bottom. Footer NOT included (needs PR number). |
```

Add a migration note in the Backward Compatibility section explaining:
- The change from metadata-at-top to metadata-at-bottom happened in PR #8305
- Rationale: Better UX - users see plan summary first, technical metadata last
- This is part of broader flat format elimination (reference commit c5854b1e2)
- Extraction functions maintain backward compatibility with both formats

---

### MEDIUM Priority

#### 1. Update Keyboard Shortcut Table in View-Aware Commands

**Location:** `docs/learned/tui/view-aware-commands.md` (lines 52-59)
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

The shortcut reuse table at lines 52-59 needs updating. Currently shows 's' for "Submit to Queue" in Plan view. Should be updated to reflect that 's' is no longer used for the dispatch command (now 'd'), and the command was renamed from "Submit to Queue" to "Dispatch to Queue".

```markdown
## Shortcut Reuse Across Views

<!-- Source: src/erk/tui/commands/registry.py, shortcut assignments -->

Plan and objective commands safely reuse the same keyboard shortcuts because the view predicates guarantee mutual exclusivity:

| Shortcut | Plan View Command    | Objectives View Command |
| -------- | -------------------- | ----------------------- |
| `d`      | Dispatch to Queue    | —                       |
| `s`      | —                    | Implement (One-Shot)    |
| `5`      | Fix Conflicts Remote | Check Objective         |
| `i`      | Open Issue           | Open Objective          |
| `1`      | Copy Prepare         | Copy Implement          |
| `3`      | Copy Submit          | Copy View               |
```

Note: The table structure changes because 'd' and 's' are no longer shared across views - they now have exclusive commands in Plan view and Objectives view respectively.

## Contradiction Resolutions

No contradictions found. All existing documentation is accurate and consistent with the codebase after these updates are applied.

## Stale Documentation Cleanup

No stale documentation detected. All referenced files exist and are current. The existing docs have accurate file paths and the patterns described remain valid.

## Prevention Insights

No errors or failed approaches occurred during implementation. The session completed successfully on the first attempt, validating that:

1. **Existing TUI documentation is effective**: The agent found all required locations without difficulty
2. **Three-location coordination pattern is well-known**: Registry, launch screen, and tests were all identified and updated correctly
3. **Pre-flight conflict checking is valuable**: Agent verified 'd' wasn't already used before proceeding

No new tripwires are warranted since no unexpected gotchas occurred.

## Tripwire Candidates

No items meeting tripwire-worthiness threshold (score >= 4).

The session demonstrated clean execution of a straightforward task. The patterns for keyboard shortcut changes (three-location updates, view context awareness, pre-flight conflict checking) are already well-documented in existing TUI documentation.

## Potential Tripwires

No items with score 2-3.

The session analyzer identified candidate patterns (shortcut change checklist, view context reuse, pre-flight conflict check) but these are already covered by:
- `docs/learned/tui/tui-command-registration.md` - Three-place coordination
- `docs/learned/tui/view-aware-commands.md` - View context separation

Since the session had no errors and existing docs proved sufficient, no new tripwires are recommended.

## Key Insights

### Discrepancy Between Plan and Implementation

The original plan describes only the keyboard shortcut change. The metadata positioning change was not mentioned in the plan but was included in the implementation. The diff analyzer correctly identified both changes and prioritized the undocumented architectural change (metadata positioning) as HIGH priority while the documented change (keyboard shortcut) is only MEDIUM priority.

This validates that the learn pipeline can detect scope differences between plans and implementations.

### Documentation Coverage Quality

The existing TUI documentation proved comprehensive for the keyboard shortcut change. The agent executed smoothly with no errors, confirming:
- `docs/learned/tui/view-aware-commands.md` documents shortcut reuse correctly
- `docs/learned/tui/tui-command-registration.md` documents three-place coordination
- The documentation provides effective guidance for similar future changes

### No New Documentation Creation Needed

Both items are updates to existing docs rather than new documentation. This is the ideal outcome - the documentation structure is already in place, only specific details need updating.
