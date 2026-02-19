# Linkify PR/Issue References in TUI Objective Body

## Context

When viewing an objective body in the TUI (`PlanBodyScreen`), PR and issue references like `#7543` appear as plain text in markdown tables. These are rendered via Textual's `Markdown` widget which supports clickable links - but the source markdown contains plain `#NNNN` text, not `[#NNNN](url)` links. The `render_roadmap_tables()` function in `roadmap.py` outputs bare `#123` strings because `RoadmapNode` only stores the number, not URLs.

Meanwhile, the plan detail screen already uses `ClickableLink` widgets for structured data, and the plan table uses click handlers. The gap is specifically in the **markdown body views** (objective body, plan body).

## Approach

Preprocess the markdown content in `PlanBodyScreen._on_content_loaded()` to convert `#NNNN` patterns into proper markdown links before passing to the `Markdown` widget. Textual's Markdown widget has `open_links=True` by default, so links will automatically open in the browser when clicked.

### Step 1: Add a `linkify_issue_references()` utility

**File:** `src/erk/tui/screens/plan_body_screen.py` (private helper, or a small utility in `src/erk/tui/`)

```python
import re

def linkify_issue_references(content: str, repo_base_url: str) -> str:
    """Convert #NNNN references to markdown links.

    Skips references that are already inside markdown links (preceded by '[').
    Uses /issues/ path - GitHub auto-redirects to /pull/ for PRs.
    """
    return re.sub(
        r'(?<!\[)#(\d+)\b',
        rf'[#\1]({repo_base_url}/issues/\1)',
        content,
    )
```

The `repo_base_url` would be `https://github.com/owner/repo` extracted from `plan_url`.

### Step 2: Extract repo base URL from `plan_url`

The `PlanBodyScreen` doesn't currently have repo context, but the caller (`app.py:712`) passes a `PlanDataProvider` which knows the repo. Two options:

**Option A (simpler):** Pass `plan_url` to `PlanBodyScreen` and extract the base from it:
```python
# plan_url = "https://github.com/owner/repo/issues/123"
# base = "https://github.com/owner/repo"
```

**Option B:** Add a `repo_base_url` property to `PlanDataProvider` ABC.

Option A is simpler since `plan_url` is already on `PlanRowData` and avoids ABC changes.

### Step 3: Apply linkification before rendering

In `PlanBodyScreen._on_content_loaded()`, preprocess `content` before mounting:

```python
elif content:
    if self._plan_url:
        base = self._plan_url.rsplit("/issues/", 1)[0]
        content = linkify_issue_references(content, base)
    container.mount(Markdown(content, id="body-content"))
```

## Files to modify

1. **`src/erk/tui/screens/plan_body_screen.py`** - Add `plan_url` parameter, add `linkify_issue_references()` helper, apply preprocessing in `_on_content_loaded`
2. **`src/erk/tui/app.py`** - Pass `plan_url=row.plan_url` when constructing `PlanBodyScreen`
3. **`tests/tui/test_plan_body_screen.py`** (if exists) - Add test for linkification

## Risk: Markdown links in table cells

Textual's `Markdown` widget uses `markdown-it-py` for parsing which supports links in table cells (`| [#123](url) |`). If this renders correctly (likely), we're done. If table cell links don't render as clickable, a fallback would be to add a custom `on_markdown_link_clicked` handler or preprocess the markdown differently.

## Verification

1. Run `erk dash -i`, navigate to an objective with roadmap tables
2. Press the body-view key to open `PlanBodyScreen`
3. Verify `#NNNN` references in tables are rendered as clickable links
4. Click one - should open the correct GitHub URL in the browser
5. Run existing TUI tests to confirm no regressions