---
title: Electron Backend Communication Patterns
read_when:
  - "connecting Electron to a Python backend"
  - "choosing between HTTP server and CLI shelling for IPC"
  - "implementing the desktop dashboard backend"
last_audited: "2026-02-04 14:18 PT"
audit_result: clean
---

# Electron Backend Communication Patterns

Analysis of three backend communication patterns for connecting Electron to the Python erk backend, with recommendations based on the current TUI data flow.

## Current TUI Data Flow

Understanding how the TUI works today informs the desktop dashboard architecture.

### Data Fetching (In-Process)

The TUI fetches plan data in-process using the `PlanDataProvider`:

```
Textual TUI → PlanDataProvider → PlanListService → GitHub API
                                                  → Local filesystem
                                                  → Git worktrees
```

**Characteristics:**

- Synchronous Python calls
- Direct access to erk's Python codebase
- No network boundary
- Fetches complete data (~50ms for 20 plans)

### Action Execution (Mixed)

Actions follow two patterns:

**In-Process (Fast Actions):**

- `close_plan` - HTTP calls to GitHub API
- `submit_to_queue` - HTTP calls to GitHub API

**Subprocess (Long-Running Actions):**

- `land_pr` - Spawns `erk land <pr>` subprocess
- `fix_conflicts_remote` - Spawns `erk launch pr-fix-conflicts --pr <pr>`
- `address_remote` - Spawns `erk launch pr-address --pr <pr>`

**Why the split?** Fast actions run in-process to avoid subprocess overhead (~200ms Python startup). Long-running actions run as subprocesses to:

1. Stream output line-by-line
2. Run with 600s timeout
3. Isolate failures

## Evaluated Backend Communication Patterns

### 1. FastAPI Local Server (Considered, Rejected)

**Concept:** Run a local HTTP server (`uvicorn`) that serves JSON data and accepts action requests.

**Architecture:**

```
Electron → HTTP (localhost:5000) → FastAPI → PlanDataProvider
```

**Pros:**

- Standard HTTP/JSON interface
- Easy to develop and debug (curl, Postman)
- Built-in async support
- OpenAPI docs

**Cons:**

- **Lifecycle complexity:** Server must be managed (start, stop, port conflicts)
- **Port conflicts:** Need to discover free port or handle collisions
- **Overhead:** HTTP stack adds latency for every request (~10-50ms)
- **Startup time:** uvicorn + FastAPI initialization (~500ms)
- **Over-engineered:** We don't need HTTP's features (caching, proxying, auth)

**When to consider:** If we need to support multiple clients or web browser access.

**Verdict:** Overkill for a single local desktop app.

---

### 2. CLI Shelling (RECOMMENDED for MVP)

**Concept:** Spawn CLI commands from Electron and parse JSON output.

**Architecture:**

```
Electron Main Process → spawn("erk dash-data --json")
                      → spawn("erk exec land <pr>")  [streaming]
                      → spawn("erk plan close <issue>")
```

**Pros:**

- **Simple:** No server lifecycle management
- **Consistent with TUI:** Same pattern TUI uses for actions
- **Stateless:** Each request is independent
- **Easy debugging:** Commands work from terminal
- **Streaming support:** Natural for long-running commands

**Cons:**

- **Python startup cost:** ~200ms per command (mostly import time)
- **No connection pooling:** Each request pays startup cost
- **JSON parsing:** Need to ensure stable JSON output format

**Startup Cost Analysis:**

```bash
# Time to import and print JSON (simulates dash-data)
time python -c "import json; print(json.dumps({'test': 'data'}))"
# Result: ~180-220ms

# Time for actual dash-data command
time erk dash-data --json
# Result: ~1.5-2s (GitHub API calls dominate)
```

**Key Insight:** Python startup (~200ms) is noise compared to GitHub API latency (~1.5-2s). Not worth optimizing away for MVP.

**Verdict:** Start here. Simple, reliable, and good enough.

---

### 3. stdio JSON-RPC (Future Upgrade)

**Concept:** Long-running Python process communicating via stdin/stdout JSON-RPC.

**Architecture:**

```
Electron Main Process → spawn("erk dash-server")
                      → stdin/stdout JSON-RPC messages
                      ← stream responses
```

**Example Message:**

```json
// Request (stdin)
{"jsonrpc": "2.0", "id": 1, "method": "fetch_plans", "params": {"state": "open"}}

// Response (stdout)
{"jsonrpc": "2.0", "id": 1, "result": [{"issue_number": 123, ...}]}
```

**Pros:**

- **No startup cost:** Process stays alive
- **Stateful:** Can maintain caches, connections
- **Bidirectional streaming:** Natural for long-running actions
- **No port conflicts:** Uses stdio only

**Cons:**

- **More complex:** JSON-RPC protocol implementation
- **Process management:** Must monitor health, restart on crashes
- **Debugging harder:** Can't run individual commands manually
- **Over-engineered for MVP:** Optimization without evidence

**When to consider:** If Python startup cost becomes a bottleneck (unlikely given GitHub API dominates latency).

**Verdict:** Defer until profiling shows it's needed.

## Recommendation: Start with CLI Shelling

### Implementation Plan

#### Phase 1: Data Fetching

Add a new CLI command that serializes `PlanRowData` to JSON:

```bash
erk dash-data --json
```

Output:

```json
{
  "plans": [
    {
      "issue_number": 123,
      "title": "Add dark mode",
      "pr_number": 456,
      "pr_url": "https://github.com/owner/repo/pull/456",
      "last_local_impl_at": "2026-01-30T14:23:00Z",
      ...
    }
  ]
}
```

**Electron Side:**

```typescript
import { exec } from "child_process";
import { promisify } from "util";

const execAsync = promisify(exec);

async function fetchPlans(): Promise<PlanRowData[]> {
  const { stdout } = await execAsync("erk dash-data --json");
  const data = JSON.parse(stdout);
  return data.plans;
}
```

#### Phase 2: Fast Actions

Execute via CLI, parse JSON response:

```bash
erk plan close 123 --json
# Output: {"success": true, "closed_prs": [456]}

erk plan submit 123 --json
# Output: {"success": true, "queued": true}
```

#### Phase 3: Streaming Actions

Execute via CLI, stream stdout line-by-line:

```typescript
import { spawn } from "child_process";

function executeLand(prNumber: number, onOutput: (line: string) => void) {
  const proc = spawn("erk", ["land", prNumber.toString()]);

  proc.stdout.on("data", (data) => {
    const lines = data.toString().split("\n");
    lines.forEach((line) => onOutput(line));
  });

  return proc; // Caller can monitor exit code
}
```

### Upgrade Path to stdio JSON-RPC

If profiling shows Python startup is a bottleneck:

1. Add `erk dash-server` command that runs a long-lived JSON-RPC server on stdin/stdout
2. Update Electron to spawn once and reuse the process
3. Keep CLI commands working for backward compatibility and debugging

This upgrade is transparent to the Electron renderer (same data shape, just faster).

## Command Interface Specification

### Data Command

```bash
erk dash-data --json [--state open|closed|all] [--limit N]
```

Returns:

```json
{
  "plans": [PlanRowData...],
  "fetched_at": "2026-01-30T14:23:00Z"
}
```

### Action Commands

All return JSON with `success` boolean and optional result data:

```bash
erk plan close <issue> --json
erk plan submit <issue> --json
erk land <pr> [--streaming]  # Streams stdout if --streaming
erk launch pr-fix-conflicts --pr <pr> [--streaming]
erk launch pr-address --pr <pr> [--streaming]
```

## Error Handling

CLI commands exit with non-zero codes on failure. Electron must check exit codes:

```typescript
try {
  const { stdout, stderr } = await execAsync("erk dash-data --json");
  return JSON.parse(stdout);
} catch (error) {
  if (error.code !== 0) {
    // Command failed, check stderr for error message
    console.error("erk command failed:", error.stderr);
  }
  throw error;
}
```

## Related Documentation

- [TUI Data Contract Reference](../tui/data-contract.md) - PlanRowData fields returned by `erk dash-data`
- [TUI Action Command Inventory](../tui/action-inventory.md) - Action execution patterns
- [Desktop Dashboard Framework Evaluation](framework-evaluation.md) - Why Electron was chosen
