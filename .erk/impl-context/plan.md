# Fix Objective Auto-Close When Auto-Match Fails But All Nodes Are Complete

## Context

When landing a PR, `erk land` invokes the `objective-update-with-landed-pr` skill. The skill's closing logic (Step 3) depends entirely on `roadmap.all_complete` from the Step 1 CLI output. But `all_complete` is only `true` if the CLI command actually updated the YAML frontmatter by matching nodes to the PR.

In this case, `node_updates` was empty (auto-match found no nodes because the YAML `pr` field wasn't pre-populated), so `all_complete = false`. Step 2 (prose reconciliation) then manually confirmed all nodes complete and updated the prose comment — but Step 3 never re-evaluated. The objective was left open even though all nodes were complete.

**Root cause:** Step 3's closing trigger is coupled to Step 1's stale `all_complete` value and doesn't account for what Step 2 learns during prose reconciliation.

## Fix

Edit the skill's Step 3 to add a fallback: if Step 1 returned `all_complete: false` BUT during Step 2 prose reconciliation the agent confirmed that all roadmap nodes are now done (including any not auto-matched), treat the objective as complete and apply the same closing logic.

### Critical file

`.claude/commands/erk/system/objective-update-with-landed-pr.md` — Lines 86–104 (Step 3: Closing Triggers)

### Change

Replace the current Step 3 preamble:

```
Use `roadmap.all_complete` from Step 1 output to determine next action.
```

With logic that also covers the prose-reconciliation case:

```
Use `roadmap.all_complete` from Step 1 output as the primary signal.
Additionally, if `node_updates` from Step 1 was empty (auto-match found no nodes)
AND during Step 2 prose reconciliation you confirmed that all roadmap nodes
(including the one addressed by this PR) are now complete, treat `all_complete`
as true for the purposes of this step.
```

The `--auto-close` and user-prompt branches below remain unchanged.

## Implementation

Edit `.claude/commands/erk/system/objective-update-with-landed-pr.md`, Step 3 section only.

**Old text (line 88):**
```
Use `roadmap.all_complete` from Step 1 output to determine next action.
```

**New text:**
```
Use `roadmap.all_complete` from Step 1 output as the primary signal. Additionally, if `node_updates` from Step 1 was empty (auto-match found no nodes) AND Step 2 prose reconciliation confirmed all roadmap nodes are now done, treat `all_complete` as `true` for the purposes of this step.
```

## Verification

1. Read the file after edit to confirm the change is correct.
2. The fix is behavior-only (skill prompt), no tests needed for the skill layer.
3. Manually verify next time an objective lands with empty `node_updates` — it should auto-close.
