<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->

# Tui Documentation

- **[action-inventory.md](action-inventory.md)** — adding a new command to the TUI or desktop dashboard, understanding how command availability is determined, choosing which execution pattern a new command should use
- **[adding-commands.md](adding-commands.md)** — adding a new command to the TUI command palette, implementing TUI actions with streaming output, understanding the dual-handler pattern for TUI commands
- **[architecture.md](architecture.md)** — understanding TUI structure, implementing TUI components, working with TUI data providers
- **[async-state-snapshot.md](async-state-snapshot.md)** — adding async data fetching to the TUI, reading self.\_view_mode during async operations, debugging stale data appearing in the wrong tab
- **[column-addition-pattern.md](column-addition-pattern.md)** — adding a column to the plan table, adding a field to PlanRowData, modifying plan_table.py column layout
- **[command-execution.md](command-execution.md)** — executing commands in TUI, choosing between sync and streaming execution, implementing command runners
- **[command-palette.md](command-palette.md)** — implementing command palette in Textual TUI, hiding system commands from command palette, get_system_commands method, removing Keys Quit Screenshot Theme from palette, adding emoji prefixes to command palette entries, using CommandCategory for command categorization
- **[data-contract.md](data-contract.md)** — building an alternate frontend consuming plan data, adding fields to PlanRowData or PlanDataProvider, understanding the display-vs-raw field duality, serializing plan data to JSON for external consumers
- **[dual-handler-pattern.md](dual-handler-pattern.md)** — implementing a TUI command that works from both list and detail views, understanding how MainListCommandProvider and PlanCommandProvider share commands, adding command palette support to a new screen
- **[modal-screen-pattern.md](modal-screen-pattern.md)** — adding a new modal screen to the TUI, implementing a ModalScreen subclass, displaying detail views or confirmation dialogs
- **[modal-streaming-pattern.md](modal-streaming-pattern.md)** — adding a new long-running CLI operation to the TUI, working with PlanDetailScreen or CommandOutputPanel, implementing real-time subprocess output in TUI modals, debugging thread safety issues in Textual widgets
- **[plan-row-data.md](plan-row-data.md)** — writing command availability predicates, understanding what data is available for TUI commands, checking which PlanRowData fields are nullable
- **[plan-title-rendering-pipeline.md](plan-title-rendering-pipeline.md)** — debugging why plan titles display incorrectly, troubleshooting missing prefixes in TUI, understanding plan data flow in TUI
- **[streaming-output.md](streaming-output.md)** — displaying streaming command output in TUI, executing long-running commands with progress, cross-thread UI updates in Textual
- **[textual-async.md](textual-async.md)** — overriding Screen actions, working with async/await in Textual, testing async TUI code
- **[title-truncation-edge-cases.md](title-truncation-edge-cases.md)** — implementing title truncation in TUI, troubleshooting truncated titles showing only prefix, working with title display lengths
- **[view-aware-commands.md](view-aware-commands.md)** — registering a new TUI command with view-mode filtering, understanding how commands are filtered by view mode (plans, learn, objectives), adding objective-specific commands to the command palette, implementing streaming commands in the TUI
- **[view-switching.md](view-switching.md)** — adding a new view mode to the TUI, understanding how view switching and caching work, debugging data not appearing in a specific view, working with PlanBodyScreen content type parameterization
