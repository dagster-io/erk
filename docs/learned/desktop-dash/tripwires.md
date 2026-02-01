---
title: Desktop Dash Tripwires
read_when:
  - "working on desktop-dash code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from desktop-dash/*.md frontmatter -->

# Desktop Dash Tripwires

Action-triggered rules for this category. Consult BEFORE taking any matching action.

**CRITICAL: Before creating WebContentsView or setting bounds** → Read [WebContentsView Lifecycle](webcontentsview-lifecycle.md) first. Initialize with zero bounds {x: 0, y: 0, width: 0, height: 0}, wait for renderer to report measurements. Always apply defensive clamping: Math.max(0, Math.floor(value)) to prevent fractional/negative coordinates that cause Electron crashes. Clean up IPC listeners on window close.

**CRITICAL: Before handling GitHub tokens in frontend code** → Read [erkdesk Security Architecture](security.md) first. GitHub tokens must NEVER reach the renderer process. Keep all GitHub API calls in the Python backend layer.

**CRITICAL: Before implementing Electron IPC without context bridge** → Read [erkdesk Security Architecture](security.md) first. NEVER expose Node.js APIs directly to renderer. Use context bridge with preload script. Set contextIsolation: true, nodeIntegration: false.
