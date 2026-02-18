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

**adding a DataTable column with add_column(key=...)** → Read [TUI Architecture Overview](architecture.md) first. Column key is a data binding contract — must match data field name. Silent failure when mismatched.

**adding a column to PlanDataTable without updating make_plan_row** → Read [Column Addition Pattern](column-addition-pattern.md) first. Column additions require 5 coordinated changes. See column-addition-pattern.md for the complete checklist.

**adding a command without an availability predicate** → Read [TUI Command Architecture](action-inventory.md) first. Every command needs an is_available predicate based on PlanRowData field presence. Commands without predicates appear when they can't execute.

**adding a field to PlanRowData without updating make_plan_row** → Read [TUI Data Contract](data-contract.md) first. The fake's make_plan_row() helper must stay in sync. Add the new field with a sensible default there too, or all TUI tests will break.

**adding a new ViewMode without updating VIEW_CONFIGS** → Read [TUI View Switching](view-switching.md) first. Every ViewMode must have a corresponding ViewConfig in VIEW_CONFIGS. Missing configs cause KeyError at runtime.

**adding an ACTION command that executes instantly** → Read [TUI Command Architecture](action-inventory.md) first. ACTION category implies mutative operations. Instant operations belong in OPEN or COPY categories.

**adding streaming commands without using \_push_streaming_detail helper** → Read [View-Aware Command Filtering](view-aware-commands.md) first. Streaming ACTION commands need \_push_streaming_detail() to handle the push-then-stream sequence correctly. Direct streaming without it skips the detail screen push.

**caching fetched data under self.\_view_mode after an async operation** → Read [TUI Async State Snapshot Pattern](async-state-snapshot.md) first. Cache under fetched_mode (snapshot at start), not self.\_view_mode (may have changed during fetch).

**calling widget methods directly from @work(thread=True) background threads** → Read [TUI Architecture Overview](architecture.md) first. Direct widget calls from background threads cause silent UI corruption. Must use self.app.call_from_thread(callback, ...).

**calling widget methods from @work(thread=True) without call_from_thread()** → Read [TUI Modal Screen Pattern](modal-screen-pattern.md) first. Background thread widget mutations cause silent UI corruption. Use self.app.call_from_thread(callback, ...).

**constructing PlanFilters without copying all fields from existing filters** → Read [TUI Data Contract](data-contract.md) first. All fields must be explicitly copied in \_load_data() PlanFilters construction. Missing fields (like creator) cause silent filtering failures.

**creating a ModalScreen without CSS for dismiss behavior** → Read [TUI Modal Screen Pattern](modal-screen-pattern.md) first. ModalScreen requires explicit CSS for the overlay. Without it, clicking outside the modal does nothing.

**duplicating command definitions for list and detail contexts** → Read [Dual Provider Pattern for Context-Agnostic Commands](dual-handler-pattern.md) first. Commands are defined once in the registry. Use a second Provider subclass with its own \_get_context() to serve the same commands from a new context.

**duplicating execute_palette_command logic between ErkDashApp and PlanDetailScreen** → Read [Dual Provider Pattern for Context-Agnostic Commands](dual-handler-pattern.md) first. This duplication is a known trade-off. Both ErkDashApp.execute_palette_command() and PlanDetailScreen.execute_command() implement the same command_id switch because they dispatch to different APIs (provider methods vs executor methods). See the asymmetries section below.

**extending PlanDataProvider ABC** → Read [TUI Architecture Overview](architecture.md) first. Requires 3-file update: abc.py + real.py + fake.py. Fake must initialize new dict in **init**. Missing init causes AttributeError at test time.

**formatting display strings during table render** → Read [TUI Data Contract](data-contract.md) first. Display strings are pre-formatted at fetch time. Add new \*\_display fields to PlanRowData and format in RealPlanDataProvider.\_build_row_data(), not in the widget layer.

**generating TUI commands that depend on optional PlanRowData fields** → Read [Adding Commands to TUI](adding-commands.md) first. Implement three-layer validation: registry predicate, handler guard, app-level helper. Never rely on registry predicate alone.

**modifying how plan titles are displayed in TUI** → Read [TUI Plan Title Rendering Pipeline](plan-title-rendering-pipeline.md) first. Ensure `[erk-learn]` prefix is added BEFORE any filtering/sorting stages.

**pushing IssueBodyScreen without explicit content_type** → Read [TUI View Switching](view-switching.md) first. Content type must come from view_mode at push time, not derived inside the screen.

**putting PlanDataProvider ABC in src/erk/tui/** → Read [TUI Data Contract](data-contract.md) first. The ABC lives in erk-shared so provider implementations are co-located in the shared package. External consumers import from erk-shared alongside other shared gateways.

**reading self.\_view_mode during async data fetch without snapshotting** → Read [TUI Async State Snapshot Pattern](async-state-snapshot.md) first. Snapshot at fetch start with fetched_mode = self.\_view_mode. Read this doc.

**registering a new TUI command without a view-mode predicate** → Read [View-Aware Command Filtering](view-aware-commands.md) first. Every command must use \_is_plan_view() or \_is_objectives_view() to prevent it from appearing in the wrong view. Commands without view predicates appear in all views.

**reusing same DOM element id across loading/empty/content states** → Read [TUI Architecture Overview](architecture.md) first. query_one() returns wrong element silently when id is reused across lifecycle phases. Use unique IDs per phase.

**using \_render() as a method name in Textual widgets** → Read [TUI View Switching](view-switching.md) first. Textual's LSP reserves \_render(). Use \_refresh_display() instead (see ViewBar).

**using subprocess.Popen in TUI code without stdin=subprocess.DEVNULL** → Read [Command Execution Strategies](command-execution.md) first. Child processes inherit stdin from parent; in TUI context this creates deadlocks when child prompts for user input. Always set `stdin=subprocess.DEVNULL` for TUI subprocess calls.

**using title-stripping functions** → Read [TUI Plan Title Rendering Pipeline](plan-title-rendering-pipeline.md) first. Distinguish `_strip_plan_prefixes` (PR creation) vs `_strip_plan_markers` (plan creation) vs `strip_plan_from_filename` (filename handling).
