# Documentation Plan: Fix alignment in erk objective view roadmap by using Rich tables

## Context

This plan addresses documentation needs arising from PR #7090, which fixed alignment issues in the `erk objective view` command's roadmap display. The core problem was that Python format strings with fixed widths (`:N` specifiers) assume each character occupies exactly one terminal cell, but emoji characters like checkmarks, arrows, and hourglasses typically consume two cells. This caused misalignment in the status column whenever emoji were present.

The solution migrated from fixed-width format strings to Rich tables, which use `cell_len()` to calculate actual terminal width. The implementation also introduced several reusable patterns: pre-computed column widths for global alignment across multiple tables, clickable reference links using Rich markup, and a clean migration path from `click.style()` to Rich markup strings.

Future agents working on CLI commands with emoji or unicode content will benefit significantly from this documentation. The patterns established here apply to any tabular CLI output requiring proper alignment, and the tripwire for fixed-width format strings will prevent this subtle bug from recurring in other commands.

## Raw Materials

https://gist.github.com/schrockn/626d6e626d3d11ec10a8a376b5cdf63c

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 7     |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 1     |
| Potential tripwires (score2-3) | 2     |

## Documentation Items

### HIGH Priority

#### 1. Fixed-width format strings with emoji anti-pattern (Tripwire)

**Location:** `docs/learned/cli/tripwires.md`
**Action:** UPDATE
**Source:** [Impl], [PR #7090]

**Draft Content:**

```markdown
## Fixed-Width Format Strings with Emoji

**Trigger:** Before using Python format strings with `:N` width specifiers for CLI output containing emoji or unicode characters

**Warning:** Use Rich tables instead - emoji have variable terminal widths (typically 2 cells) which break fixed-width alignment.

**Why this matters:** Python's `str.ljust()` and format strings like `f"{text:30}"` assume each character is one terminal cell. But emoji characters consume 2 cells:
- `checkmark` (check emoji) = 2 cells
- `arrows` (cycle emoji) = 2 cells
- `hourglass` (waiting emoji) = 2 cells
- ASCII = 1 cell

This causes columns to appear misaligned whenever emoji are present.

**Solution:** Use Rich tables with `cell_len()` for automatic width handling. See the pre-computed column widths pattern in output-styling.md and the implementation in `view_cmd.py` function `view_objective()` (grep for `cell_len` or `Table(show_header`).
```

---

#### 2. Rich Table Pre-Computed Column Widths Pattern

**Location:** `docs/learned/cli/output-styling.md` (new section)
**Action:** UPDATE
**Source:** [Impl], [PR #7090]

**Draft Content:**

```markdown
## Rich Tables for Variable-Width Characters

### Problem Statement

Python format strings assume fixed character width, but emoji have variable terminal widths. A format string like `f"{text:30}"` doesn't account for terminal cell width, causing misalignment when emoji are present.

### Solution: Rich Tables with cell_len()

Rich tables use `cell_len()` from `rich.cells` to calculate actual terminal width. Import the necessary components and let Rich handle alignment automatically.

### Pre-Computed Column Widths Pattern

When rendering multiple Rich tables in sequence (e.g., one per phase), each table calculates its own column widths, resulting in misalignment between tables. Pre-compute maximum column widths across ALL tables before rendering.

**Pattern overview:** Calculate max widths by iterating all data before creating tables, then pass `min_width` to each column. See `view_cmd.py` function `view_objective()` for the complete implementation (grep for `max_id_width`, `max_status_width`, or `min_width`).

### When to Use

- Any CLI output with emoji or unicode characters requiring column alignment
- Multiple tables that should visually align as a single logical table
- Status indicators, progress displays, or any output with variable-width symbols
```

---

### MEDIUM Priority

#### 3. Clickable Reference Link Pattern with Rich Markup

**Location:** `docs/learned/cli/output-styling.md` (extend existing OSC 8 section)
**Action:** UPDATE
**Source:** [Impl], [PR #7090]

**Draft Content:**

```markdown
### Rich Markup Approach for Clickable Links

When using Rich tables, use Rich's link markup instead of raw OSC 8 escape sequences.

**Pattern:** `[link=URL]display text[/link]`

**Advantages over raw OSC 8:**
- Rich handles terminal compatibility automatically
- More readable than escape codes
- Consistent with Rich's styling approach elsewhere

**Helper function pattern:** Create functions like `_format_ref_link()` that convert GitHub refs (e.g., `#6871`) to clickable Rich markup. See `view_cmd.py` functions `_format_ref_link()` and `_extract_repo_base_url()` for the implementation pattern (lines 45-96).

**When to use:** Any CLI table displaying issue/PR references that should be clickable.
```

---

#### 4. click.style() to Rich Markup Migration Pattern

**Location:** `docs/learned/cli/output-styling.md` (new section)
**Action:** UPDATE
**Source:** [Impl], [PR #7090]

**Draft Content:**

```markdown
## Migrating from click.style() to Rich Markup

When migrating CLI output to Rich tables, status indicators need Rich markup format instead of click-styled strings.

### Mapping Table

| click.style() call | Rich Markup equivalent |
|--------------------|------------------------|
| `click.style(text, fg="green")` | `[green]{text}[/green]` |
| `click.style(text, fg="yellow")` | `[yellow]{text}[/yellow]` |
| `click.style(text, dim=True)` | `[dim]{text}[/dim]` |

### Function Signature Changes

Functions that previously returned click-styled strings now return Rich markup strings. The return type stays `str`, but the content format changes. See `view_cmd.py` function `_format_step_status()` for an example migration.

### Escaping User Content

Use `escape()` from `rich.markup` for user-provided content that may contain brackets. Unescaped brackets like `[foo]` would be interpreted as Rich style tags and disappear from output.

**Pattern:** Import `escape` from `rich.markup`, then wrap user content: `f"[yellow]status {escape(user_text)}[/yellow]"`
```

---

#### 5. Emoji Terminal Width Handling with cell_len()

**Location:** `docs/learned/cli/output-styling.md` (integrate with Rich table section)
**Action:** UPDATE
**Source:** [Impl], [PR #7090]

**Draft Content:**

```markdown
### Understanding Terminal Cell Width

Terminal characters have different widths:
- ASCII characters: 1 terminal cell
- Most emoji: 2 terminal cells
- Some unicode: varies

Rich's `cell_len()` function from `rich.cells` calculates actual terminal width. Rich tables use this internally for proper alignment.

**Import:** `from rich.cells import cell_len`

**Why this matters:** When manually calculating column widths, use `cell_len(Text(string))` instead of `len(string)`. This ensures emoji-containing strings are measured correctly.
```

---

#### 6. view_objective() Rich Table Implementation

**Location:** `docs/learned/cli/objective-commands.md`
**Action:** UPDATE
**Source:** [Impl], [PR #7090]

**Draft Content:**

```markdown
## view_objective() Command

The `view_objective()` command renders a roadmap using Rich tables for proper emoji alignment.

**Key implementation details:**
- Uses pre-computed column widths for global alignment across phases
- Clickable links for issue/PR references via `_format_ref_link()` pattern
- Status indicators use Rich markup (see output-styling.md for migration pattern)
- Console outputs to stderr with `Console(stderr=True, force_terminal=True)`

**Reference:** See [CLI Output Styling Guide](output-styling.md) for the full Rich table pattern details, particularly the sections on variable-width characters and pre-computed column widths.
```

---

### LOW Priority

#### 7. OSC 8 via Rich Markup (Extend Existing)

**Location:** `docs/learned/cli/output-styling.md` (extend existing OSC 8 section)
**Action:** UPDATE
**Source:** [Impl], [PR #7090]

**Draft Content:**

```markdown
### Alternative: Rich Link Markup

In addition to raw OSC 8 escape sequences, Rich provides `[link=URL]text[/link]` markup that renders the same clickable links with better terminal compatibility handling.

**When to choose Rich markup over raw OSC 8:**
- Output is rendered via Rich Console or Table
- Need consistent styling with other Rich components
- Want automatic terminal capability detection
```

---

## Contradiction Resolutions

No contradictions found. The existing documentation is consistent with the implemented changes.

## Stale Documentation Cleanup

No stale documentation detected. All referenced documentation files exist and are current.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Prettier Formatting Failures in Unrelated Files

**What happened:** During CI iteration, prettier reported formatting failures in files not directly modified by the implementation (`.claude/commands/erk/objective-create.md` and `.worker-impl/plan.md`).

**Root cause:** Files modified by other processes or previous edits were not auto-formatted before the PR submission workflow.

**Prevention:** Always run `make prettier` before PR submission. Consider including it in the CI iteration workflow or pre-commit hooks.

**Recommendation:** CONTEXT_ONLY (severity LOW, standard CI hygiene, not worth a tripwire)

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Fixed-Width Format Strings with Emoji

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before using Python format strings with `:N` width specifiers for CLI output containing emoji
**Warning:** Use Rich tables instead - emoji have variable terminal widths (typically 2 cells) which break fixed-width alignment. See output-styling.md for the Rich table pattern.
**Target doc:** `docs/learned/cli/tripwires.md`

This tripwire is particularly valuable because the failure mode is silent. Code using fixed-width format strings with emoji will run without errors but produce visually misaligned output. The fix is non-obvious to agents who haven't encountered this terminal width behavior before. The pattern is cross-cutting because any CLI command displaying status indicators with emoji could fall into this trap.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Console Instantiation in Loops

**Score:** 3/10 (criteria: Cross-cutting +2, Repeated pattern +1)
**Notes:** The automated PR review caught Console being instantiated inside a loop. This was already documented, and the review system successfully enforced it. The existing documentation is sufficient; the automated review provides the enforcement layer.

### 2. Rich Markup Injection Vulnerability

**Score:** 3/10 (criteria: Non-obvious +2, Silent failure +1)
**Notes:** User content containing brackets `[foo]` would be interpreted as Rich style tags if not escaped. This was caught by automated review and is already documented in output-styling.md. Consider elevating to tripwire if this pattern continues to appear in PR reviews, but current documentation coverage appears adequate.

## Session Efficiency Observations

**What worked well in the planning session (4d998d92):**
- Task/Explore agent used effectively for code discovery
- Pattern recognition from existing implementations (`list_cmd.py` as reference)
- Complete workflow: Plan -> Save -> Submit executed smoothly

**What worked well in the implementation session (07c25466):**
- First-try success: All 11 tests passed immediately
- Plan quality impact: Exact line numbers and reference files enabled zero rework
- Automated reviews caught violations (Console in loop, markup injection, imports)
- All violations had existing documentation references

**Key success factors:**
1. Detailed plan with specific locations and line numbers
2. Reference to existing patterns in codebase
3. Comprehensive existing documentation
4. Automated review system with doc links

This PR demonstrates high documentation coverage with only 7 new documentation items needed out of 14 total candidates. The automated review system successfully enforced existing standards, validating documentation completeness.