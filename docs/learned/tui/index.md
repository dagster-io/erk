<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->

# Tui Documentation

- **[action-inventory.md](action-inventory.md)** — adding a new command to the TUI or desktop dashboard, understanding how command availability is determined, choosing which execution pattern a new command should use
- **[adding-commands.md](adding-commands.md)** — adding a new command to the TUI command palette, implementing TUI actions with streaming output, understanding the dual-handler pattern for TUI commands
- **[architecture.md](architecture.md)** — understanding TUI structure, implementing TUI components, working with TUI data providers
- **[async-action-refresh-pattern.md](async-action-refresh-pattern.md)** — adding background operations to the TUI, implementing worker thread actions in the dashboard, refreshing TUI data after a background subprocess
- **[async-state-snapshot.md](async-state-snapshot.md)** — adding async data fetching to the TUI, reading self.\_view_mode during async operations, debugging stale data appearing in the wrong tab
- **[clipboard-text-generation.md](clipboard-text-generation.md)** — implementing copy-to-clipboard in the TUI, adding a new command that supports clipboard copy, debugging why a copy command returns wrong text
- **[column-addition-pattern.md](column-addition-pattern.md)** — adding a column to the plan table, adding a field to PlanRowData, modifying plan_table.py column layout
- **[command-execution.md](command-execution.md)** — executing commands in TUI, choosing between sync and streaming execution, implementing command runners
- **[command-palette.md](command-palette.md)** — implementing command palette in Textual TUI, hiding system commands from command palette, get_system_commands method, removing Keys Quit Screenshot Theme from palette, adding emoji prefixes to command palette entries, using CommandCategory for command categorization
- **[dashboard-columns.md](dashboard-columns.md)** — adding a new column to the erk dash TUI, understanding which columns are always present vs conditional, debugging why a column is missing in a particular view mode
- **[data-contract.md](data-contract.md)** — building an alternate frontend consuming plan data, adding fields to PlanRowData or PlanDataProvider, understanding the display-vs-raw field duality, serializing plan data to JSON for external consumers
- **[derived-display-columns.md](derived-display-columns.md)** — adding a TUI column that uses an existing PlanRowData field, deciding whether a new column needs gateway/query changes
- **[dual-handler-pattern.md](dual-handler-pattern.md)** — implementing a TUI command that works from both list and detail views, understanding how MainListCommandProvider and PlanCommandProvider share commands, adding command palette support to a new screen
- **[filter-pipeline.md](filter-pipeline.md)** — adding a new filter to the TUI dashboard, understanding how objective/stack/text filters interact, modifying the escape key behavior in the TUI
- **[filter-toggle-pattern.md](filter-toggle-pattern.md)** — adding a filter toggle to the TUI dashboard, implementing server-side filtering in the TUI, adding keybindings that toggle dashboard state
- **[frozen-dataclass-field-management.md](frozen-dataclass-field-management.md)** — removing a field from a frozen dataclass, renaming a field in PlanRowData or similar frozen dataclass, getting unexpected constructor errors after field changes
- **[keyboard-shortcuts.md](keyboard-shortcuts.md)** — adding a new keyboard shortcut to the TUI, checking for shortcut conflicts before binding a new key, understanding what keys are available in the TUI
- **[lifecycle-display.md](lifecycle-display.md)** — adding a new lifecycle stage to the TUI, changing lifecycle abbreviations or colors, modifying PR status emoji indicators, understanding the stage column in erk dash
- **[modal-screen-pattern.md](modal-screen-pattern.md)** — adding a new modal screen to the TUI, implementing a ModalScreen subclass, displaying detail views or confirmation dialogs
- **[modal-widget-embedding.md](modal-widget-embedding.md)** — reusing PlanDataTable in a modal screen, embedding complex widgets in Textual modal screens, handling null safety for optional gateway fields in TUI
- **[multi-operation-tracking.md](multi-operation-tracking.md)** — adding a new background operation to the TUI, implementing status bar progress for a workflow command, debugging operation lifecycle or stuck operations
- **[one-shot-prompt-modal.md](one-shot-prompt-modal.md)** — adding a new modal or input screen to the TUI, working with the one-shot dispatch workflow in erk dash, adding global keybindings that trigger modals
- **[plan-row-data.md](plan-row-data.md)** — writing command availability predicates, understanding what data is available for TUI commands, checking which PlanRowData fields are nullable
- **[plan-title-rendering-pipeline.md](plan-title-rendering-pipeline.md)** — debugging why plan titles display incorrectly, troubleshooting missing prefixes in TUI, understanding plan data flow in TUI
- **[stacked-pr-indicator.md](stacked-pr-indicator.md)** — adding or modifying PR indicators in the TUI dashboard, understanding blocking vs. informational indicators, working with stacked PR detection
- **[status-indicators.md](status-indicators.md)** — working with status indicators in TUI dashboard, adding new emoji indicators to plan display, modifying the sts column
- **[streaming-output.md](streaming-output.md)** — displaying streaming command output in TUI, executing long-running commands with progress, cross-thread UI updates in Textual
- **[subprocess-feedback.md](subprocess-feedback.md)** — adding subprocess calls to the TUI, implementing background worker feedback in the TUI, parsing subprocess stderr for status markers
- **[textual-async.md](textual-async.md)** — overriding Screen actions, working with async/await in Textual, testing async TUI code
- **[title-truncation-edge-cases.md](title-truncation-edge-cases.md)** — implementing title truncation in TUI, troubleshooting truncated titles showing only prefix, working with title display lengths
- **[tui-command-registration.md](tui-command-registration.md)** — adding a new TUI command to the registry, understanding the 3-place coordination pattern for TUI commands, working with TUI command categories or display formatters
- **[view-aware-commands.md](view-aware-commands.md)** — registering a new TUI command with view-mode filtering, understanding how commands are filtered by view mode (plans, learn, objectives), adding objective-specific commands to the command palette, implementing streaming commands in the TUI
- **[view-switching.md](view-switching.md)** — adding a new view mode to the TUI, understanding how view switching and caching work, debugging data not appearing in a specific view, working with PlanBodyScreen content type parameterization
