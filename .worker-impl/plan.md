# Plan: Create Learned Docs for Desktop Dashboard Research

## Overview

Create learned documentation capturing all research and reasoning from the Electron desktop dashboard exploration (objective #6423). Five documents across three categories: `tui/` for existing TUI internals, and a new `desktop-dash/` category for desktop-specific research.

## Documents to Create

### 1. `docs/learned/tui/data-contract.md` — TUI Data Contract Reference

**Content:** PlanRowData field inventory (40 fields organized by category), PlanDataProvider ABC interface, PlanFilters dataclass, RealPlanDataProvider data fetch flow, display string pattern (pre-formatted `*_display` fields), JSON serialization considerations (datetime fields).

**read_when:**
- "building on top of the TUI data layer"
- "serializing PlanRowData to JSON"
- "understanding what data the dashboard displays"

### 2. `docs/learned/tui/action-inventory.md` — TUI Action Command Inventory

**Content:** All 14 commands across 3 categories (ACTION/OPEN/COPY), availability predicates per command, execution patterns (in-process HTTP vs subprocess streaming vs long-running 600s), keyboard shortcuts, command context fields, the dual-handler pattern (main list + detail modal).

**read_when:**
- "adding actions to the dashboard"
- "understanding TUI command execution patterns"
- "replicating TUI functionality in another frontend"

### 3. `docs/learned/desktop-dash/framework-evaluation.md` — Desktop App Framework Evaluation

**Content:** Five approaches evaluated (Textual-web, Electron, Tauri, Full Web App, Hybrid terminal+browser) with pros/cons. GitHub X-Frame-Options constraint as the deciding factor. WebContentsView vs `<webview>` tag vs iframe analysis.

**read_when:**
- "choosing a framework for the desktop dashboard"
- "embedding GitHub pages in an application"
- "understanding why Electron was chosen for the desktop dashboard"

### 4. `docs/learned/desktop-dash/backend-communication.md` — Electron Backend Communication Patterns

**Content:** Three patterns evaluated (FastAPI local server, CLI shelling, stdio JSON-RPC). Analysis of current TUI data flow (in-process Python for data, subprocess for actions). Why CLI shelling is the right starting point. Upgrade path to stdio JSON-RPC. Python startup cost analysis.

**read_when:**
- "connecting Electron to a Python backend"
- "choosing between HTTP server and CLI shelling for IPC"
- "implementing the desktop dashboard backend"

### 5. `docs/learned/desktop-dash/interaction-model.md` — Desktop Dashboard Interaction Model

**Content:** Why not to port TUI features 1:1. Right pane as primary workspace (inverted hierarchy). GUI-native actions (toolbar, context menu) over memorized keyboard shortcuts. No detail modal (right pane replaces it). Notification-driven workflow vs visual polling. Comparison of TUI constraints vs desktop affordances.

**read_when:**
- "designing the desktop dashboard UX"
- "deciding which TUI features to carry forward to Electron"
- "understanding the interaction model differences between TUI and desktop"

## Steps

1. Create `docs/learned/desktop-dash/` directory
2. Create all 5 docs with proper frontmatter, content, and cross-references
3. Run `erk docs sync` to regenerate indexes (creates `desktop-dash/index.md` and `desktop-dash/tripwires.md`)
4. Update objective #6423 to reference the new docs in its Related Documentation section

## Files to Create

- `docs/learned/tui/data-contract.md`
- `docs/learned/tui/action-inventory.md`
- `docs/learned/desktop-dash/framework-evaluation.md`
- `docs/learned/desktop-dash/backend-communication.md`
- `docs/learned/desktop-dash/interaction-model.md`

## Verification

- `erk docs sync` completes without errors
- Each doc appears in its category index
- New `desktop-dash/` category appears in `docs/learned/index.md`
- Cross-references between docs are valid