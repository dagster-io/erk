# Plan: Consolidated erk-learn Documentation Gaps

> **Consolidates:** #5889, #5888, #5883, #5880, #5879, #5874

## Source Plans

| #    | Title                                                           | Items Merged |
| ---- | --------------------------------------------------------------- | ------------ |
| 5889 | Phase 3 - Unify Entry Points in erk land                       | 5 items      |
| 5888 | Prevent Graphite Divergence from git pull --rebase              | 1 item       |
| 5883 | Phase 3B: Decision Menu Post-Documentation                     | 2 items      |
| 5880 | Command Palette Description Prefixes with Dimmed Command Text   | 2 items      |
| 5879 | Improve TUI command palette UX with label:command display format | 2 items      |
| 5874 | Consolidated erk-learn documentation plans                      | 4 items      |

## What Changed Since Original Plans

- All code implementations are merged (PRs #5887, #5878, #5870, and land_cmd.py refactoring)
- Some planned docs already exist or are partially covered by other docs
- Plans #5880 and #5879 overlap 90%+ (same source issue #5877) - merged below
- Plan #5888 is effectively complete (only missing low-priority tripwire-system.md overview)

## Investigation Findings

### Corrections to Original Plans

- **#5889**: All code exists (LandTarget, CleanupContext, resolvers). Plan is documentation-only.
- **#5888**: ALL items implemented via PR #5887. Only missing: tripwire-system.md (low priority overview doc).
- **#5883**: Decision menu Step 6b implemented (commit 03224c45). Only missing docs.
- **#5880/#5879**: Code implemented via PR #5878. Existing docs need section updates, not new files.
- **#5874**: Partially implemented via PR #5870. Several planned docs not created.

### Overlap Analysis

- **#5880 + #5879**: 90%+ overlap. Both document command palette label:command format from source issue #5877. Merged into single set of doc updates.
- **#5889 config-override-chains**: Partially covered by existing `docs/learned/configuration/config-layers.md`.
- **#5889 frozen-dataclass-patterns**: Partially covered by existing `docs/learned/architecture/protocol-vs-abc.md`.

## Remaining Gaps

All gaps are **documentation-only** - no code changes needed.

### New Documentation Files (10 files)

1. `docs/learned/cli/multi-entry-point-commands.md` _(from #5889)_
2. `docs/learned/cli/resolver-pattern.md` _(from #5889)_
3. `docs/learned/architecture/config-override-chains.md` _(from #5889)_
4. `docs/learned/architecture/frozen-dataclass-patterns.md` _(from #5889)_
5. `docs/learned/architecture/tripwire-system.md` _(from #5888)_
6. `docs/learned/architecture/skill-based-cli.md` _(from #5883)_
7. `docs/learned/tui/menu-patterns.md` _(from #5883)_
8. `docs/learned/erk/metadata-helpers.md` _(from #5874)_
9. `docs/learned/planning/pr-optional-learn-flow.md` _(from #5874)_
10. `docs/learned/planning/agent-coordination-via-files.md` _(from #5874)_

### Documentation Updates (2 files)

11. `docs/learned/tui/command-palette.md` — Add sections: "Label:Command Search Pattern", "Three-Tier Display Architecture", "Provider Stability" _(from #5880, #5879)_
12. `docs/learned/tui/adding-commands.md` — Add section: "Description Field as Display Label", update Step 1 example to show new single-word label format _(from #5880, #5879)_

### Dropped Items

- `docs/learned/cli/land-command-refactoring-phase-3.md` _(from #5889)_ — Covered by multi-entry-point-commands.md and resolver-pattern.md combined
- `docs/learned/sessions/session-preprocessing.md` _(from #5874)_ — preprocessing.md already exists with different scope; not worth a separate doc

## Implementation Steps

1. Create `docs/learned/cli/multi-entry-point-commands.md` documenting frozen dataclass unification pattern (LandTarget/CleanupContext) for commands with multiple entry points _(from #5889)_
2. Create `docs/learned/cli/resolver-pattern.md` documenting thin resolver functions that return common types _(from #5889)_
3. Create `docs/learned/architecture/config-override-chains.md` documenting how CLI flags override config values with precedence rules _(from #5889)_
4. Create `docs/learned/architecture/frozen-dataclass-patterns.md` documenting frozen dataclass usage as "common currency" in command pipelines _(from #5889)_
5. Create `docs/learned/architecture/tripwire-system.md` overview of how tripwires work: frontmatter triggers, auto-generation, behavioral routing _(from #5888)_
6. Create `docs/learned/architecture/skill-based-cli.md` documenting skill-driven CLI pattern (learn command Step 6b decision menu) _(from #5883)_
7. Create `docs/learned/tui/menu-patterns.md` documenting decision menu patterns for agent-driven workflows _(from #5883)_
8. Update `docs/learned/tui/command-palette.md` with three-tier display architecture, label:command format, provider stability sections _(from #5880, #5879)_
9. Update `docs/learned/tui/adding-commands.md` with description-as-label section and updated examples _(from #5880, #5879)_
10. Create `docs/learned/erk/metadata-helpers.md` documenting metadata_helpers.py module _(from #5874)_
11. Create `docs/learned/planning/pr-optional-learn-flow.md` documenting when learn step is optional vs required _(from #5874)_
12. Create `docs/learned/planning/agent-coordination-via-files.md` documenting file-based agent coordination patterns _(from #5874)_
13. Run `erk docs sync` to regenerate index files
14. Run CI checks to verify no formatting or link issues

## Attribution

Items by source:
- **#5889**: Steps 1, 2, 3, 4
- **#5888**: Step 5
- **#5883**: Steps 6, 7
- **#5880/#5879** (merged): Steps 8, 9
- **#5874**: Steps 10, 11, 12

## Related Documentation

- Load `learned-docs` skill for document creation standards
- Load `dignified-python` skill if any code examples are included
- Reference `docs/learned/guide.md` for category placement rules

## Verification

- All new docs have proper frontmatter (title, read_when, category)
- `erk docs sync` succeeds and index files are updated
- `make format` passes (prettier for markdown)
- No broken links in generated index files