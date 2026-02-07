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

**File**: `erkdesk/src/main/index.ts:44-53`

```typescript
ipcMain.on("webview:update-bounds", (_event, bounds: WebViewBounds) => {
  if (!webView) return;
  webView.setBounds({
    x: Math.max(0, Math.floor(bounds.x)),
    y: Math.max(0, Math.floor(bounds.y)),
    width: Math.max(0, Math.floor(bounds.width)),
    height: Math.max(0, Math.floor(bounds.height)),
  });
});
```

### Pattern Breakdown

```typescript
Math.max(0, Math.floor(bounds.x));
```

**Step 1**: `Math.floor(bounds.x)` — Truncate fractional pixels to integers.

- `400.7` → `400`
- `200.1` → `200`

**Step 2**: `Math.max(0, ...)` — Clamp negative values to zero.

- `-5` → `0`
- `400` → `400`

This two-step pattern ensures:

1. ✅ All values are non-negative integers
2. ✅ Electron receives safe bounds that won't cause crashes

## Why Not Validate in Renderer?

**Q**: Why not clamp bounds in the SplitPane component before sending to IPC?

**A**: Defense-in-depth. The main process is the authoritative layer that directly calls Electron APIs, so it must be robust against all possible inputs:

- **Trust boundary** — Main process should never assume renderer sends perfect data
- **Multiple renderers** — Future versions might have multiple windows/sources of bounds
- **Electron quirks** — Platform-specific Electron behavior may change

### Renderer's Responsibility

The SplitPane component ensures **logical correctness**:

```typescript
const maxLeft = containerRect.width - DIVIDER_WIDTH - minRightWidth;
setLeftWidth(Math.max(minLeftWidth, Math.min(maxLeft, newLeft)));
```

This prevents the user from dragging the divider beyond minimum width constraints.

### Main Process's Responsibility

The main process ensures **API safety**:

```typescript
Math.max(0, Math.floor(bounds.x));
```

This prevents Electron from receiving coordinates that could cause crashes.

## Zero-Bounds Initialization

On startup, the WebContentsView is initialized with zero bounds:

```typescript
// Start invisible until renderer reports bounds.
webView.setBounds({ x: 0, y: 0, width: 0, height: 0 });
webView.webContents.loadURL("about:blank");
```

**Source**: `erkdesk/src/main/index.ts:40-42`

**Rationale**:

- The WebContentsView has no valid position until the renderer measures the split layout
- Zero bounds make it invisible (not displayed)
- Once the renderer reports real bounds via IPC, the view becomes visible

This avoids a flash of incorrectly-positioned content during startup.

## Related Crashes Prevented

This pattern prevents crashes from:

1. **Fractional coordinates** — `setBounds({ x: 400.5, ... })` → Electron crash
2. **Negative coordinates** — `setBounds({ x: -10, ... })` → Electron crash
3. **Negative dimensions** — `setBounds({ width: -200, ... })` → Electron crash

The defensive pattern catches all three cases.

## Related Documentation

- [WebView API](webview-api.md) — IPC channels and bounds update flow
- [SplitPane Implementation](split-pane-implementation.md) — How renderer calculates bounds
