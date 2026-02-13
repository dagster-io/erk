# Use Geist and Geist Mono fonts in erkweb

## Context

The erkweb UI currently uses a system font stack (`-apple-system, BlinkMacSystemFont, ...`) for body text and `SF Mono, Fira Code` for monospace. We want to switch to Vercel's Geist and Geist Mono fonts for a more intentional, consistent look.

## Plan

### 1. Add Geist font CSS imports to `erkweb/index.html`

Import both fonts from the CDN in the `<head>`:

```html
<link rel="preconnect" href="https://cdn.jsdelivr.net" />
<link href="https://cdn.jsdelivr.net/npm/geist@1/dist/fonts/geist-sans/style.css" rel="stylesheet" />
<link href="https://cdn.jsdelivr.net/npm/geist@1/dist/fonts/geist-mono/style.css" rel="stylesheet" />
```

### 2. Update body font in `erkweb/src/client/App.css`

Line 13 — change:
```css
font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, sans-serif;
```
to:
```css
font-family: 'Geist', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
```

### 3. Update all monospace font declarations

Replace every occurrence of `'SF Mono', 'Fira Code', monospace` with `'Geist Mono', monospace` across 11 declarations in 7 files:

- `erkweb/src/client/components/ChatPanel.css` (lines 34, 83, 104)
- `erkweb/src/client/components/ChatMessage.css` (line 52)
- `erkweb/src/client/components/ToolBlock.css` (lines 35, 44)
- `erkweb/src/client/components/CommandTypeahead.css` (lines 32, 38)
- `erkweb/src/client/components/PlanSidebar.css` (line 81)
- `erkweb/src/client/components/PlanDetail.css` (line 81)
- `erkweb/src/client/components/PermissionPrompt.css` (line 48)

## Verification

1. Run `yarn dev` in `erkweb/` and confirm both fonts load (check Network tab for CDN requests)
2. Visually verify body text uses Geist and code/mono elements use Geist Mono