---
title: Graphite PR Rendering Quirks
read_when:
  - "writing PR body content that will render on Graphite"
  - "using <details>/<summary> in PR descriptions"
  - "debugging PR body formatting differences between GitHub and Graphite"
tripwires:
  - action: "adding <code> inside <summary> elements in PR bodies"
    warning: "Graphite does not render <code> inside <summary> elements — it displays the raw HTML. Use plain text instead. GitHub renders it correctly, so test on graphite.dev specifically."
    score: 8
  - action: "closing a <details> block without a blank line after </details>"
    warning: "Graphite requires a blank line after </details> for proper spacing. Without it, the following content runs up against the collapsed section."
    score: 5
---

# Graphite PR Rendering Quirks

Graphite renders PR bodies differently from GitHub in a few important ways. Content that looks correct on github.com may display incorrectly on graphite.dev.

## `<code>` Inside `<summary>` Does Not Render

Graphite does not render `<code>` tags inside `<summary>` elements. The raw HTML tag appears as literal text.

**Broken (renders badly on Graphite):**

```html
<details>
  <summary><code>original-plan</code></summary>
  ...
</details>
```

**Correct (renders correctly on both):**

```html
<details>
  <summary>original-plan</summary>
  ...
</details>
```

The `DETAILS_OPEN` constant in `packages/erk-shared/src/erk_shared/plan_store/draft_pr_lifecycle.py:89` uses the correct plain-text format. A `_LEGACY_DETAILS_OPEN` constant (line 90) retains the old `<code>` format for backward-compatible parsing only — it is never written.

## Blank Line Required After `</details>`

Graphite requires a blank line after `</details>` for the content block to render with proper spacing. Without it, the following paragraph or section header runs directly against the collapsed element.

**Incorrect:**

```markdown
</details>
## Next Section
```

**Correct:**

```markdown
</details>

## Next Section
```

## Testing Guidance

When modifying PR body templates, verify rendering on **both** platforms:

1. **github.com** — Usually more lenient; renders `<code>` inside `<summary>` correctly
2. **graphite.dev** — Stricter HTML rendering; `<code>` inside `<summary>` appears as raw text

Test by creating a draft PR on a test branch and viewing it on both sites before merging.

## Related Implementation

- `draft_pr_lifecycle.py:89-90` — `DETAILS_OPEN` (current) and `_LEGACY_DETAILS_OPEN` (compat parsing)
- `metadata_blocks.py:226` — PR body assembly
- `draft_pr_lifecycle.py:89-90` — Constants for details wrapping
