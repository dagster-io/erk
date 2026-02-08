---
title: Step Renumbering in Slash Commands
read_when:
  - "merging, removing, or reordering steps in slash commands"
  - "refactoring command workflows that use numbered steps"
  - "encountering broken step references after editing a command"
tripwire:
  trigger: "Before merging or removing steps in slash commands"
  action: "Read [Step Renumbering in Slash Commands](step-renumbering-checklist.md) first. Search for `Step \\d+[a-z]?` in the file to find ALL references — headers, forward refs, backward refs, conditional jumps — and update them as a unit."
---

# Step Renumbering in Slash Commands

Erk slash commands (`.claude/commands/`) use numbered steps as their primary control flow mechanism. Step numbers appear in four distinct roles — headers, forward references, backward references, and conditional jumps — creating a web of cross-references that must be updated atomically when steps change.

## Why This Is Cross-Cutting

Step references span not just the command file itself but also external documentation. The `token-optimization-patterns.md` doc references specific `/erk:replan` step numbers. Skill files reference command steps. When a step number shifts, the blast radius extends beyond the modified file.

As of writing, 24 command files contain a combined 239 step references. The larger commands (`/erk:replan` at 17, `/erk:plan-implement` at 21, `/erk:pr-address` at 13) have dense cross-reference networks where a single step removal can invalidate dozens of references.

## The Four Reference Types

Step numbers serve four distinct roles, and each role has different failure modes when numbers shift:

| Reference Type       | Example                               | Failure When Stale                            |
| -------------------- | ------------------------------------- | --------------------------------------------- |
| **Header**           | `### Step 4: Validate`                | Duplicate or gap in sequence                  |
| **Forward ref**      | "Skip to Step 7"                      | Agent jumps to wrong step or nonexistent step |
| **Backward ref**     | "Using plans from Step 3"             | Agent looks at wrong context                  |
| **Conditional jump** | "If validation fails, skip to Step 7" | Control flow silently corrupted               |

Forward references and conditional jumps are the most dangerous because they redirect agent execution. A stale backward reference misleads; a stale forward reference causes the agent to execute the wrong step entirely.

## The Atomic Update Rule

**All four reference types must be updated as a single pass.** The common mistake is updating headers first, then searching for cross-references separately — which leads to partial updates when the search is incomplete.

Instead:

1. **Build a mapping first**: old number → new number for every affected step
2. **Search once** for the pattern `Step \d+[a-z]?` across the entire file
3. **Apply the mapping** to every match, regardless of reference type
4. **Check external docs**: grep `docs/learned/` and `.claude/skills/` for references to the command's step numbers

## Sub-Step Renumbering

Steps use a letter suffix system (Step 4a, 4b, 4c) for sub-steps. When the parent step number changes, all sub-steps must follow. When a sub-step is removed, remaining sub-steps do NOT renumber — this prevents a cascade through their own cross-references.

## Historical Example: /erk:replan Step 3 Merge

<!-- Source: .claude/commands/erk/replan.md, Step 3 -->

When `/erk:replan` merged Step 3 (Plan Content Fetching) into Step 4 (Deep Investigation) for token optimization, the step wasn't removed — it was converted into a delegation marker ("Skip to Step 4"). This preserved the numbering of Steps 5-7 and all their sub-steps (4a-4f), limiting the blast radius to only forward/backward references mentioning Step 3 specifically.

**Key insight**: Converting a step to a pass-through ("delegated to Step X") is less disruptive than deleting it, because downstream step numbers don't shift. This is a deliberate trade-off: a vestigial step marker costs a few tokens but avoids a cascade of renumbering across the file and external documentation.

## Anti-Patterns

**Updating headers but not cross-references**: The most common failure. Agent renumbers `### Step N` headers but misses "See Step N" in body text two pages away. Always use regex search, never rely on memory.

**Renumbering sub-steps when parent changes**: If Step 4 becomes Step 3, then 4a→3a, 4b→3b. But if Step 4b is deleted, do NOT renumber 4c→4b — the cross-reference cascade isn't worth it for sub-steps.

**Forgetting external documentation**: `docs/learned/planning/token-optimization-patterns.md` directly references `/erk:replan` step numbers. Any renumbering in the command file must check downstream docs.

## Related Documentation

- [Token Optimization Patterns](../planning/token-optimization-patterns.md) - Documents the rationale behind the `/erk:replan` Step 3 merge and references its step numbers
