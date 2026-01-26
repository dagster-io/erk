---
title: Tui Tripwires
read_when:
  - "working on tui code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from tui/*.md frontmatter -->

# Tui Tripwires

Action-triggered rules for this category. Consult BEFORE taking any matching action.

**CRITICAL: Before generating TUI commands that depend on optional PlanRowData fields** → Read [Adding Commands to TUI](adding-commands.md) first. Implement three-layer validation: registry predicate → handler guard → app-level helper. Never rely on registry predicate alone.

**CRITICAL: Before modifying how plan titles are displayed in TUI** → Read [TUI Plan Title Rendering Pipeline](plan-title-rendering-pipeline.md) first. Ensure `[erk-learn]` prefix is added BEFORE any filtering/sorting stages.

**CRITICAL: Before using subprocess.Popen in TUI code without stdin=subprocess.DEVNULL** → Read [Command Execution Strategies](command-execution.md) first. Child processes inherit stdin from parent; in TUI context this creates deadlocks when child prompts for user input. Always set `stdin=subprocess.DEVNULL` for TUI subprocess calls.

**CRITICAL: Before using title-stripping functions** → Read [TUI Plan Title Rendering Pipeline](plan-title-rendering-pipeline.md) first. Distinguish `_strip_plan_prefixes` (PR creation) vs `_strip_plan_markers` (plan creation) vs `strip_plan_from_filename` (filename handling).
