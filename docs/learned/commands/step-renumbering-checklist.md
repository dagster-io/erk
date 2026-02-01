---
title: Step Renumbering Checklist
read_when:
  - "merging or removing steps in slash commands"
  - "refactoring command workflows"
  - "encountering broken step references in commands"
  - "reviewing command documentation for consistency"
tripwire:
  trigger: "Before merging or removing steps in slash commands"
  action: "Read [Step Renumbering Checklist](step-renumbering-checklist.md) first. Update ALL step numbers (headers, forward refs, backward refs) and verify conditional jumps still target correct destinations. Search for `Step \\d+[a-z]?` pattern to find all references."
---

# Step Renumbering Checklist

When merging, removing, or reordering steps in slash commands, all step numbers and cross-references must be updated. Missing updates cause broken workflows and confusing documentation.

## The Problem

Slash commands use numbered steps (Step 1, Step 2, Step 3a, etc.) extensively. These steps are referenced:

1. **In step headers**: `### Step 4: Validate Input`
2. **In cross-references**: "See Step 4b for validation logic"
3. **In conditional jumps**: "If validation fails, skip to Step 7"
4. **In explanatory text**: "Step 3 ensures that..."

When a step is removed or merged, all subsequent step numbers shift, but cross-references don't update automatically.

## Checklist

When modifying command steps, follow this checklist:

### 1. Identify All Affected Steps

- [ ] List all steps being removed, merged, or reordered
- [ ] Identify the new numbering for all subsequent steps
- [ ] Create a mapping: old step number → new step number

### 2. Update Step Headers

- [ ] Renumber all step headers after the modification point
- [ ] Update sub-step letters if needed (4a, 4b, 4c → 3a, 3b, 3c)
- [ ] Verify no duplicate step numbers exist

### 3. Update Forward References

Search for references to steps that come **later** in the command:

- [ ] "See Step X" references pointing to renamed steps
- [ ] "Skip to Step X" conditional jumps
- [ ] "Return to Step X" loop instructions
- [ ] Examples mentioning specific step numbers

### 4. Update Backward References

Search for references to steps that come **earlier** in the command:

- [ ] "As done in Step X" references
- [ ] "After Step X completes" sequencing notes
- [ ] "Step X ensures that..." explanatory text
- [ ] "Building on Step X" continuation notes

### 5. Update Related Documentation

- [ ] Command README if it lists step summaries
- [ ] Related documentation linking to specific steps
- [ ] Skill files that reference command steps

### 6. Verify Consistency

- [ ] Read through entire command start to finish
- [ ] Verify all step references point to existing steps
- [ ] Check that conditional jumps make logical sense
- [ ] Ensure no orphaned references to deleted steps

## Example: /erk:replan Step 3 Removal

When Step 3 (Plan Content Fetching) was merged into Step 4 (Deep Investigation) in `/erk:replan`:

### Changes Required

**Step headers updated:**

- Old Step 4 → New Step 4 (absorbed Step 3 content)
- Old Step 4a → Still Step 4a (sub-step under new Step 4)
- Old Step 5 → New Step 5
- Old Step 6 → New Step 6
- Old Step 7 → New Step 7

**Forward references updated:**

- Step 2 previously said "Skip to Step 3" → Updated to "Skip to Step 4"
- Step 3 said "Delegates to Step 4" → Content merged, reference removed

**Backward references updated:**

- Step 5 said "Using plans from Step 3" → Updated to "Using plans from Step 4"

**No updates needed:**

- Steps 5, 6, 7 kept their numbers (only Step 3 was removed, not Step 4)
- Sub-steps 4a-4f references remained valid

## Common Mistakes

### 1. Updating Headers but Not Cross-References

**Symptom**: Step headers are correct, but text says "See Step 5" when Step 5 no longer exists.

**Fix**: Search entire file for step number patterns: `Step \d+[a-z]?`

### 2. Forgetting Sub-Step References

**Symptom**: Main step numbers updated, but "See Step 4b" now points to wrong sub-step.

**Fix**: Search for both `Step X` and `Step Xa` patterns.

### 3. Partial Updates

**Symptom**: Some references updated, others missed.

**Fix**: Use systematic search for all occurrences, don't rely on memory.

### 4. Broken Conditional Logic

**Symptom**: "If X, skip to Step 7" now skips to wrong step due to renumbering.

**Fix**: Trace each conditional path to ensure destination is still correct.

## Tools

### Search Pattern

Use regex to find all step references:

```bash
grep -n "Step [0-9][a-z]*" command.md
```

This finds both "Step 4" and "Step 4b" style references.

### Diff Review

Before committing, review the diff to ensure:

1. All step header changes are intentional
2. All cross-reference changes match header changes
3. No step numbers appear in unexpected places

## Related Documentation

- [Command Development](command-development.md) - General command authoring guidelines
- [Token Optimization Patterns](../planning/token-optimization-patterns.md) - Example of step merge rationale
