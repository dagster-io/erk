---
title: Defensive Bounds Handling
read_when:
  - working with WebContentsView bounds, debugging Electron crashes, implementing IPC bounds updates
last_audited: "2026-02-07 18:13 PT"
audit_result: edited
---

# Defensive Bounds Handling

The erkdesk main process applies defensive clamping and rounding to WebContentsView bounds before calling `setBounds()`. This prevents silent Electron crashes caused by fractional or negative coordinates.

## The Problem

Electron's `WebContentsView.setBounds()` expects integer values for `x`, `y`, `width`, and `height`. Passing fractional or negative values can cause:

1. **Silent crashes** — Electron may terminate without error messages
2. **Rendering glitches** — WebContentsView appears in wrong position or doesn't render
3. **Unpredictable behavior** — Varies by platform (macOS vs Windows vs Linux)

### Source of Invalid Bounds

Even though the renderer uses `getBoundingClientRect()` (which should return valid values), edge cases can produce problematic coordinates:

- **Fractional pixels** — CSS transforms or zoom levels can yield `rect.x = 400.5`
- **Negative coordinates** — Rare browser quirks or off-screen elements
- **Race conditions** — Window resize events where measurements are mid-transition

## The Solution

The `webview:update-bounds` IPC handler applies `Math.max(0, Math.floor(value))` to every coordinate before calling `setBounds()`. See `erkdesk/src/main/index.ts:44-53` for the implementation.

### Pattern Breakdown

The two-step clamping — `Math.max(0, Math.floor(bounds.x))` — works as follows:

1. `Math.floor()` truncates fractional pixels to integers (e.g., `400.7` → `400`)
2. `Math.max(0, ...)` clamps negative values to zero (e.g., `-5` → `0`)

This ensures Electron always receives non-negative integer bounds.

## Why Not Validate in Renderer?

**Q**: Why not clamp bounds in the SplitPane component before sending to IPC?

**A**: Defense-in-depth. The main process is the authoritative layer that directly calls Electron APIs, so it must be robust against all possible inputs:

- **Trust boundary** — Main process should never assume renderer sends perfect data
- **Multiple renderers** — Future versions might have multiple windows/sources of bounds
- **Electron quirks** — Platform-specific Electron behavior may change

### Renderer's Responsibility

The SplitPane component ensures **logical correctness** by clamping the divider position between minimum left and right widths. See `SplitPane.tsx` for the constraint logic.

### Main Process's Responsibility

The main process ensures **API safety** by applying `Math.max(0, Math.floor())` to all bounds values before passing to Electron.

## Zero-Bounds Initialization

On startup, the WebContentsView is initialized with zero bounds (`{x: 0, y: 0, width: 0, height: 0}`) and loads `about:blank`. See `erkdesk/src/main/index.ts:40-42`.

**Rationale**: The WebContentsView has no valid position until the renderer measures the split layout. Zero bounds make it invisible, avoiding a flash of incorrectly-positioned content during startup. Once the renderer reports real bounds via IPC, the view becomes visible.

## Related Crashes Prevented

This pattern prevents crashes from:

1. **Fractional coordinates** — `setBounds({ x: 400.5, ... })` → Electron crash
2. **Negative coordinates** — `setBounds({ x: -10, ... })` → Electron crash
3. **Negative dimensions** — `setBounds({ width: -200, ... })` → Electron crash

The defensive pattern catches all three cases.

## Related Documentation

- [WebView API](webview-api.md) — IPC channels and bounds update flow
- [SplitPane Implementation](split-pane-implementation.md) — How renderer calculates bounds
