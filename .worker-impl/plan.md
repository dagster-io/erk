# Extraction Plan: Markdown Widget Selection Guide

## Objective

Document when to use Textual's `Markdown` vs `MarkdownViewer` widgets, specifically around scrolling behavior.

## Source Information

- **Session ID**: 03b39fac-f80b-4946-8208-772556bf45ed
- **Context**: Planning markdown viewing feature for erk dash TUI

## Documentation Items

### Item 1: Markdown vs MarkdownViewer Widget Selection

**Type**: Category A (Learning Gap)
**Location**: `docs/agent/tui/textual-quirks.md` (add new section)
**Action**: Add
**Priority**: Medium

**Content**:

```markdown
## Markdown Widget Selection

### Markdown vs MarkdownViewer

Textual provides two markdown widgets with different scrolling behaviors:

| Widget | Scrolling | Use Case |
|--------|-----------|----------|
| `Markdown` | `overflow-y: hidden` - no built-in scroll | Embed in scrollable container, streaming updates |
| `MarkdownViewer` | Extends `VerticalScroll` - built-in scroll | Full document viewing with navigation |

**When to use `Markdown`:**
- Content embedded in a larger scrollable area
- Streaming markdown updates (has `MarkdownStream` helper)
- Custom scroll handling needed

**When to use `MarkdownViewer`:**
- Full-screen or modal document display
- Built-in vim-style scrolling (j/k/g/G via subclass)
- Optional table of contents sidebar

**Example: Scrollable Markdown Modal**

\`\`\`python
from textual.widgets import MarkdownViewer

class DocViewerScreen(ModalScreen):
    BINDINGS = [
        Binding("j", "scroll_down", show=False),
        Binding("k", "scroll_up", show=False),
    ]

    def compose(self) -> ComposeResult:
        yield MarkdownViewer(self._content, show_table_of_contents=False)

    def action_scroll_down(self) -> None:
        self.query_one(MarkdownViewer).scroll_down()
\`\`\`

**Key insight**: `Markdown` has `height: auto` and `overflow-y: hidden` in its DEFAULT_CSS, meaning it sizes to content but won't scroll. `MarkdownViewer` wraps `Markdown` in a `VerticalScroll` container with `height: 1fr`.
```