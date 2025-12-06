# Extraction Plan: Session Content & Metadata Block Patterns

## Objective

Document patterns discovered during extraction plan enhancement work, covering both learning gaps (what would have helped) and teaching gaps (new patterns built).

## Source Sessions

- `3cadd2ec-8622-467e-84b6-f0c5455c44f3` - Current planning session (GitHub issue #2329, session content metadata blocks)
- `9da22b1c-c7fd-4a5b-8372-14b21566f74d` - Implementation session (erk:plan-implement)
- `a373c86b-2fc9-4587-82fe-df46e1fe6f11` - Merge conflicts and raw extraction session

---

## Documentation Items

### 1. GitHub XML Rendering in Issues

**Type:** Category A (Learning Gap)
**Location:** `docs/agent/architecture/` or glossary addition
**Priority:** Medium
**Action:** Add new doc or glossary entry

**Draft Content:**

```markdown
## GitHub Markdown XML Rendering

**Problem:** When embedding XML content in GitHub issue comments or PR bodies, tags like `<session>`, `<user>`, `<assistant>` are interpreted as HTML and disappear from the rendered output.

**Solution:** Always wrap XML content in code fences:

\`\`\`xml
<session>
  <user>Content here</user>
</session>
\`\`\`

**When this applies:**
- Embedding preprocessed session XML in extraction plan issues
- Any metadata block containing XML-like content
- Debug output that includes angle-bracket syntax

**Key insight:** Some content is double-escaped (e.g., `&lt;command-message&gt;`) while structural tags are not. The code fence approach handles both correctly.
```

---

### 2. Session Content Metadata Block Type

**Type:** Category B (Teaching Gap)
**Location:** `docs/agent/architecture/metadata-blocks.md` (new section)
**Priority:** High
**Action:** Add new metadata block documentation

**Draft Content:**

```markdown
## session-content Metadata Block

A specialized metadata block for embedding preprocessed session XML in GitHub issues.

**Key features:**
- Wraps content in XML code fence for proper GitHub rendering
- Supports numbered chunks for large sessions
- Includes optional session label and extraction hints

**Format:**

<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:session-content -->
<details>
<summary><strong>Session Data (1/3): fix-auth-bug</strong></summary>

**Extraction Hints:**
- Error handling patterns
- Test fixture setup

\`\`\`xml
<session>
...
</session>
\`\`\`