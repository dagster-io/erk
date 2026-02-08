# Plan: Allow Third-Party Reference Caches in Learned Docs

## Context

The batch regeneration + audit pipeline deleted 650 lines of stable GitHub Actions API reference material from `docs/learned/reference/github-actions-api.md` because the current quality standards treat all reproduced external content as DUPLICATIVE. But these reference tables are "token caches" — the exact purpose of learned docs. Fetching, parsing, and distilling GitHub's API docs costs significant agent time/tokens, and the material is stable. The standards need a carve-out for this type of content.

## Approach

Introduce **`content_type: reference-cache`** as a frontmatter marker. This gives audit and regeneration a mechanical signal (no heuristic guessing). When present, third-party reference tables are classified as valuable rather than duplicative.

## Files to Modify

### 1. `.claude/skills/learned-docs/learned-docs-core.md`

The single source of truth — all other files inherit from here.

- **Add 5th exception** to the One Code Rule (after line 57):
  ```
  5. **Third-party reference caches** — API endpoint tables, DSL syntax references,
     expression catalogs from stable external sources (requires `content_type: reference-cache`
     in frontmatter and a `## Sources` section with URLs)
  ```
  Update heading from "Four Exceptions" to "Five Exceptions"

- **Update Decision Test** (line 61) — add cost awareness:
  ```
  For third-party reference material: "Is re-acquiring this expensive?" If fetching,
  parsing, and distilling external docs costs significant tokens, that's a reference
  cache — mark with `content_type: reference-cache` in frontmatter.
  ```

- **Add bullet to "Belongs in Learned Docs"** (after line 74):
  ```
  - Third-party reference caches (stable API tables, DSL syntax) with `content_type: reference-cache`
  ```

- **Clarify "Doesn't Belong"** (line 81): Change "File listings with counts" to "Erk file listings with counts" to distinguish from third-party API tables

- **Add new section** before "## See Also": "Reference Cache Requirements"
  - Required frontmatter: `content_type: reference-cache`, `source_date: YYYY-MM-DD`
  - Must have `## Sources` section with URLs to original documentation
  - A doc can contain both erk-specific analysis AND reference cache content

### 2. `.claude/commands/local/audit-doc.md`

- **Phase 1** (after line 44): Extract `content_type` from frontmatter; note if `reference-cache` for downstream phases

- **Phase 5** — Add **REFERENCE CACHE** to the value categories table:
  | REFERENCE CACHE | Distilled third-party reference material in a `content_type: reference-cache` doc | Keep — expensive to re-fetch |

  Add note: sections in reference-cache docs are not DUPLICATIVE just because the info exists in external docs

- **Phase 6** — Add **REFERENCE TABLE** to the code block classifications:
  | REFERENCE TABLE | Yes (if `content_type: reference-cache`) | Third-party API tables/syntax in a reference-cache doc |

- **Phase 7** — Update verdict thresholds: count REFERENCE CACHE alongside HIGH VALUE and CONTEXTUAL in the positive bucket

- **Design Principles**: Add principle about token cache value of reference material

### 3. `.github/reviews/audit-pr-docs.md`

- **Step 1** (line 1): Update "four exceptions" to "five exceptions" in the description
- **Step 3** (line 35): Add REFERENCE CACHE to the adversarial analysis classification list
- **Step 4** (line 47): Add REFERENCE CACHE to the "do not produce inline comments" list

### 4. `scripts/batch_regenerate_docs.py`

Update `REGEN_PROMPT_TEMPLATE` (lines 68-91):

- Add to the "Keep:" list: `third-party reference cache sections in docs with content_type: reference-cache frontmatter`
- Change "file listings" to "erk file listings" in the "Remove:" list
- Add instruction: `Check frontmatter for content_type: reference-cache. If present, preserve all third-party reference tables and content intact.`

### 5. `docs/learned/documentation/source-pointers.md`

- Add row to "When to Use Source Pointers vs Code Blocks" table (after line 59):
  | Third-party reference tables (API endpoints, syntax refs) | Keep as code block | Token cache of expensive-to-fetch external docs (requires `content_type: reference-cache`) |

## Verification

1. **Standards coherence**: Read all 5 modified files and confirm the new exception is consistently described
2. **Dry-run audit**: Run `/local:audit-doc docs/learned/reference/github-actions-api.md` after restoring the reference material and adding `content_type: reference-cache` — verify it gets KEEP verdict, not REPLACE
3. **Dry-run regen**: Run batch_regenerate_docs.py with `--dry-run` to confirm discovery still works
4. **PR review check**: Confirm `.github/reviews/audit-pr-docs.md` references are consistent with the updated audit-doc.md