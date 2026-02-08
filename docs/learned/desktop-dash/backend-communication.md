---
title: Backend Communication Pattern Decision
read_when:
  - "choosing how erkdesk communicates with the Python backend"
  - "evaluating whether to add a persistent backend server"
  - "understanding why erkdesk shells out to CLI commands"
tripwires:
  - action: "adding a persistent server process for erkdesk"
    warning: "CLI shelling was chosen deliberately. Python startup (~200ms) is noise compared to GitHub API latency (~1.5-2s). Don't optimize the wrong bottleneck."
    score: 5
  - action: "duplicating PlanDataProvider logic in TypeScript"
    warning: "erkdesk delegates all data fetching to `erk exec dash-data`. The Python side owns data assembly — erkdesk is a thin rendering shell over CLI output."
    score: 6
---

# Backend Communication Pattern Decision

erkdesk communicates with the Python backend exclusively through CLI subprocess calls. This was a deliberate architectural choice over two alternatives.

## Three Patterns Evaluated

| Pattern                   | Mechanism                          | Startup Cost               | Lifecycle Complexity                                        |
| ------------------------- | ---------------------------------- | -------------------------- | ----------------------------------------------------------- |
| FastAPI local server      | HTTP on localhost                  | ~500ms (uvicorn + FastAPI) | High — port conflicts, health monitoring, daemon management |
| **CLI shelling (chosen)** | `execFile`/`spawn` per command     | ~200ms (Python import)     | None — stateless, each call independent                     |
| stdio JSON-RPC            | Long-lived process on stdin/stdout | Zero (process stays alive) | Medium — crash recovery, health checks, protocol framing    |

## Why CLI Shelling Won

**The latency analysis sealed the decision.** Python startup (~200ms) is dominated by GitHub API latency (~1.5-2s) on every data fetch. Eliminating startup cost saves ~10% of total request time — not worth the lifecycle complexity of a persistent server.

Additional factors:

- **Consistency with TUI**: The Textual TUI already uses `PlanDataProvider` in-process and delegates long-running actions to `erk` subprocesses. erkdesk shells out for _everything_ (including data fetches), which is simpler but slightly different.
- **Debuggability**: Every erkdesk action maps to a terminal command. Running `erk exec dash-data` manually reproduces exactly what the UI does.
- **No server lifecycle**: No port conflicts, no daemon management, no "is the server running?" failure mode.

## The Two Execution Modes

erkdesk uses two Node.js subprocess APIs, chosen by action duration:

| Duration  | Node.js API  | IPC Pattern                             | Use Case                                             |
| --------- | ------------ | --------------------------------------- | ---------------------------------------------------- |
| <1 second | `execFile()` | Request-response (`ipcMain.handle`)     | Data fetching (`erk exec dash-data`)                 |
| >1 second | `spawn()`    | Fire-and-forget + events (`ipcMain.on`) | Actions (`erk plan submit`, `erk launch pr-address`) |

The split exists because `execFile` buffers all output and returns it at once (simple but blocks the UI), while `spawn` streams chunks as they arrive (complex but keeps the UI responsive).

<!-- Source: erkdesk/src/main/index.ts, plans:fetch handler and actions:start-streaming handler -->

See the `plans:fetch` handler (blocking) and `actions:start-streaming` handler (streaming) in `erkdesk/src/main/index.ts` for the two patterns side by side.

## Cross-Boundary Data Contract

The Python and TypeScript sides share a data contract through JSON serialization:

1. **Python side**: `dash_data.py` serializes `PlanRowData` (36-field frozen dataclass) to JSON, handling datetime→ISO 8601 and tuple→list conversions.
2. **TypeScript side**: `erkdesk.d.ts` defines `PlanRow` as a subset (~20 fields) of the Python type, keeping only what the UI renders.

<!-- Source: src/erk/cli/commands/exec/scripts/dash_data.py, _serialize_plan_row -->
<!-- Source: erkdesk/src/types/erkdesk.d.ts, PlanRow interface -->

The TypeScript `PlanRow` is intentionally a subset — it omits fields like `issue_body`, `log_entries`, and `learn_status` that only the TUI uses. This keeps the renderer lightweight.

## TUI vs erkdesk: Action Execution Divergence

Both UIs display the same plan data, but execute actions differently:

| Aspect                       | TUI (Textual)                                   | erkdesk (Electron)                                   |
| ---------------------------- | ----------------------------------------------- | ---------------------------------------------------- |
| Data fetching                | In-process via `PlanDataProvider.fetch_plans()` | Subprocess: `erk exec dash-data`                     |
| Fast actions (close, submit) | In-process via `PlanDataProvider` methods       | Subprocess: `erk exec close-plan`, `erk plan submit` |
| Long-running actions         | Subprocess with streaming                       | Subprocess with streaming                            |
| Action dispatch              | Command palette + keybindings                   | ActionToolbar button bar                             |

The key difference: the TUI calls Python methods directly for fast actions (avoiding ~200ms subprocess overhead), while erkdesk _always_ shells out since it has no in-process Python. This means erkdesk actions feel slightly slower for quick operations but the architecture is simpler.

## When to Reconsider This Decision

The stdio JSON-RPC upgrade path remains viable if:

- **Data fetching frequency increases** beyond the current 15-second auto-refresh cycle, making cumulative startup cost noticeable
- **In-process state** becomes necessary (e.g., caching GitHub responses, connection pooling)
- **Bidirectional streaming** is needed (e.g., the backend pushing real-time updates to the UI)

The upgrade would be transparent to the renderer — same `PlanRow` data shape, just delivered through a persistent process instead of per-command subprocesses.

## Related Documentation

- [erkdesk App Architecture](app-architecture.md) — State management and streaming action lifecycle
- [IPC Actions](ipc-actions.md) — Four-location checklist and handler patterns
- [Action Toolbar](action-toolbar.md) — Action definitions and availability predicates
