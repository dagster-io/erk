# Review Plan

Validate the synthesized learn plan before saving.

## Read Synthesized Plan

Read the PlanSynthesizer output:

```
Read(.erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/learn-plan.md)
```

The PlanSynthesizer has already:

- Collected all candidates from the parallel agents via DocumentationGapIdentifier
- Created a narrative context explaining what was built
- Generated documentation items with draft content starters
- Described tripwire insights naturally in prose

The TripwireExtractor has:

- Extracted structured tripwire candidate data into `tripwire-candidates.json`

## Validation Checkpoint

**Before proceeding to save:**

Verify the PlanSynthesizer output:

- [ ] Context section accurately describes what was built
- [ ] Documentation items have actionable draft content (not just "document this")
- [ ] Every SKIP has an explicit, valid reason (not "self-documenting")
- [ ] HIGH priority contradictions have resolution plans
- [ ] All PR comment insights are captured (if PR exists)

## "No Documentation Needed" Justification

If the synthesized plan shows NO documentation items:

1. Re-read the agent's skip reasons
2. Ask: "Would a future agent benefit from this?"
3. If still no documentation needed, state: "After explicit review of N inventory items, no documentation is needed because [specific reasons for top 3 items]"

Only skip saving after this explicit justification.

## Outdated Documentation Check (MANDATORY)

**Removals and behavior changes require doc audits.** When the work removes features or changes behavior, existing documentation may become incorrect.

**Search for documentation that references changed features:**

```bash
# Search docs for terms related to removed/changed features
grep -r "<removed-feature>" docs/learned/ .claude/commands/ .claude/skills/
```

**Categorize findings:**

| Finding                           | File | Status        | Action Needed          |
| --------------------------------- | ---- | ------------- | ---------------------- |
| Reference to removed feature      | ...  | Outdated      | Remove/update section  |
| Describes old behavior            | ...  | Incorrect     | Update to new behavior |
| Conflicts with new implementation | ...  | Contradictory | Reconcile              |

**Common patterns to check:**

- **Removed CLI flags**: Search for `--flag-name` in docs
- **Removed files/modules**: Search for import paths, file references
- **Changed behavior**: Search for behavioral descriptions that no longer apply
- **Removed modes**: Search for "three modes", "fallback", etc.

**Include outdated doc updates in the documentation plan** alongside new documentation needs.

## Reference: Common Documentation Locations

| What was built            | Documentation needed                                       |
| ------------------------- | ---------------------------------------------------------- |
| New CLI command           | Document in `docs/learned/cli/` - usage, flags, examples   |
| New gateway method        | Add tripwire about ABC implementation (5 places to update) |
| New capability            | Update capability system docs, add to glossary             |
| New config option         | Add to `docs/learned/glossary.md`                          |
| New exec script           | Document purpose, inputs, outputs                          |
| New architectural pattern | Create architecture doc or add tripwire                    |
| External API integration  | Document quirks, rate limits, auth patterns discovered     |

## PR Comment Analysis Integration

PR comment insights are already integrated via the PRCommentAnalyzer agent → DocumentationGapIdentifier pipeline. Review the gap analysis output to verify PR comment documentation opportunities were captured correctly. If you spot additional insights not covered by the agent, add them manually to the plan.
