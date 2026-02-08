---
title: SplitPane Renderer-Native Coordination
read_when:
  - working on split-pane layout or resizable panels in erkdesk
  - debugging WebContentsView positioning or bounds mismatches
  - adding new triggers that affect the right pane's size or position
tripwires:
  - action: "modifying right pane size or layout in erkdesk"
    warning: "every code path that changes the right pane's rendered size must trigger a bounds report to the main process"
  - action: "working with the right pane div in SplitPane"
    warning: "the right pane div is a positioning placeholder only — it renders no content, the WebContentsView overlays it"
  - action: "implementing cleanup for SplitPane component"
    warning: "cleanup lives in the main process window-close handler, not in the SplitPane component"
last_audited: "2026-02-08"
audit_result: clean
---

# SplitPane Renderer-Native Coordination

## Why This Pattern Exists

Electron's `WebContentsView` is a native OS-level surface — it cannot participate in CSS layout. The erkdesk split-pane solves this by using a **placeholder div** in the React layout whose sole purpose is being measured. The renderer continuously reports that div's bounding rect to the main process, which positions the native view on top of it. This creates the illusion of a single integrated layout while the two surfaces (React DOM and native webview) are actually independent.

## Bounds Reporting Triggers

The right pane's position must stay synchronized with any layout change. Four independent triggers ensure this — missing any one creates a desync where the native overlay drifts from its placeholder.

| Trigger                             | Why it exists                                                          | What would break without it                            |
| ----------------------------------- | ---------------------------------------------------------------------- | ------------------------------------------------------ |
| **Initial mount**                   | WebView starts at zero bounds                                          | WebView invisible until first drag or resize           |
| **Divider drag** (leftWidth change) | Repositions the boundary between panes                                 | WebView stays at old position after drag               |
| **Window resize**                   | Viewport changes don't trigger React re-render                         | WebView stays at old position when user resizes window |
| **ResizeObserver on right pane**    | Catches size changes from sibling elements (e.g., log panel appearing) | WebView covers the log panel or leaves a gap           |

<!-- Source: erkdesk/src/renderer/components/SplitPane.tsx, reportBounds and useEffect hooks -->

The first three triggers are straightforward. The **ResizeObserver** is the subtle one — it catches cases where the right pane's size changes due to layout shifts that don't involve the divider or the window (e.g., a collapsible panel appearing below). Without it, the WebContentsView would remain at its previous size until the next drag or resize event.

## Why `getBoundingClientRect()` Is the Right Measurement

The placeholder div uses `flex: 1` to fill remaining space. `getBoundingClientRect()` returns the div's actual rendered position and size in viewport coordinates, which is exactly what `WebContentsView.setBounds()` needs. Alternative approaches like computing the position from `leftWidth + DIVIDER_WIDTH` would miss scroll offsets, browser chrome, and any CSS transforms.

## Layout Mental Model

```
┌─────────────────────────────────────────────┐
│  Container (flex)                           │
│  ┌──────────┬──┬──────────────────────────┐│
│  │  Left    │  │  Right Pane (placeholder)││
│  │  Pane    │DI│  (WebContentsView        ││
│  │  (React) │VI│   overlays this)         ││
│  │          │DE│                           ││
│  │          │R │                           ││
│  └──────────┴──┴──────────────────────────┘│
│  ← fixed  →←4→← flex: 1 (measured)       →│
└─────────────────────────────────────────────┘
```

The left pane and divider have fixed widths; the right pane absorbs remaining space. Minimum width constraints on both sides prevent the divider from being dragged to an unusable position.

## Cross-Process Responsibility Split

| Concern                                         | Where                               | Why there                                                                  |
| ----------------------------------------------- | ----------------------------------- | -------------------------------------------------------------------------- |
| Logical constraints (min widths, drag clamping) | Renderer (`SplitPane`)              | Only the renderer knows the layout geometry                                |
| API safety (non-negative integers)              | Main process (IPC handler)          | Trust boundary — main process must never assume renderer data is safe      |
| IPC cleanup                                     | Main process (window close handler) | Component unmount is unreliable in Electron; main process is authoritative |

This split is intentional. See [Defensive Bounds Handling](defensive-bounds-handling.md) for why clamping must happen at the main process trust boundary even though the renderer already enforces constraints.

## Anti-Patterns

**WRONG**: Adding a new UI element that changes the right pane's size without verifying it triggers a bounds report. The ResizeObserver handles most cases, but if you restructure the DOM hierarchy (e.g., move the right pane div outside the flex container), the observer may not fire.

**WRONG**: Computing WebContentsView bounds from component state (`leftWidth + DIVIDER_WIDTH`) instead of measuring the actual DOM. This breaks under scroll offsets, zoom levels, and CSS transforms.

## Related Documentation

- [Defensive Bounds Handling](defensive-bounds-handling.md) — Why main process clamps bounds at the trust boundary
- [WebView API](webview-api.md) — IPC channels and preload bridge
