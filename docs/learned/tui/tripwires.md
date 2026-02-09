---
title: Tui Tripwires
read_when:
  - "working on tui code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from tui/*.md frontmatter -->

# Tui Tripwires

Rules triggered by matching actions in code.

**adding a command without an availability predicate** → Read [TUI Command Architecture](action-inventory.md) first. Every command needs an is_available predicate based on PlanRowData field presence. Commands without predicates appear when they can't execute.

**adding a field to PlanRowData without updating make_plan_row** → Read [TUI Data Contract](data-contract.md) first. The fake's make_plan_row() helper must stay in sync. Add the new field with a sensible default there too, or all TUI tests will break.

**adding an ACTION command that executes instantly** → Read [TUI Command Architecture](action-inventory.md) first. ACTION category implies mutative operations. Instant operations belong in OPEN or COPY categories.

**duplicating command definitions for list and detail contexts** → Read [Dual Provider Pattern for Context-Agnostic Commands](dual-handler-pattern.md) first. Commands are defined once in the registry. Use a second Provider subclass with its own \_get_context() to serve the same commands from a new context.

**duplicating execute_palette_command logic between ErkDashApp and PlanDetailScreen** → Read [Dual Provider Pattern for Context-Agnostic Commands](dual-handler-pattern.md) first. This duplication is a known trade-off. Both ErkDashApp.execute_palette_command() and PlanDetailScreen.execute_command() implement the same command_id switch because they dispatch to different APIs (provider methods vs executor methods). See the asymmetries section below.

**formatting display strings during table render** → Read [TUI Data Contract](data-contract.md) first. Display strings are pre-formatted at fetch time. Add new \*\_display fields to PlanRowData and format in RealPlanDataProvider.\_build_row_data(), not in the widget layer.

**generating TUI commands that depend on optional PlanRowData fields** → Read [Adding Commands to TUI](adding-commands.md) first. Implement three-layer validation: registry predicate, handler guard, app-level helper. Never rely on registry predicate alone.

**modifying how plan titles are displayed in TUI** → Read [TUI Plan Title Rendering Pipeline](plan-title-rendering-pipeline.md) first. Ensure `[erk-learn]` prefix is added BEFORE any filtering/sorting stages.

**putting PlanDataProvider ABC in src/erk/tui/** → Read [TUI Data Contract](data-contract.md) first. The ABC lives in erk-shared so desktop-dash and other external consumers can depend on it without importing the full TUI package.

**using subprocess.Popen in TUI code without stdin=subprocess.DEVNULL** → Read [Command Execution Strategies](command-execution.md) first. Child processes inherit stdin from parent; in TUI context this creates deadlocks when child prompts for user input. Always set `stdin=subprocess.DEVNULL` for TUI subprocess calls.

**using title-stripping functions** → Read [TUI Plan Title Rendering Pipeline](plan-title-rendering-pipeline.md) first. Distinguish `_strip_plan_prefixes` (PR creation) vs `_strip_plan_markers` (plan creation) vs `strip_plan_from_filename` (filename handling).
