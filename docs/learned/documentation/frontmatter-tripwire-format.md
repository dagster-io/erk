---
title: Frontmatter and Tripwire Format
last_audited: "2026-02-17 00:00 PT"
audit_result: clean
read_when:
  - creating new documentation in docs/learned/
  - adding tripwires to existing docs
  - understanding frontmatter schema for agent docs
  - running erk docs sync
tripwires:
  - action: "writing a tripwire as a plain string instead of {action, warning} dict"
    warning: "The validator requires structured dicts with action and warning keys. Plain strings fail validation with 'must be an object'."
  - action: "creating a doc in docs/learned/ without read_when field"
    warning: "read_when is required. Without it, the doc won't appear in any index and agents will never discover it."
---

# Frontmatter and Tripwire Format

## Why Frontmatter Exists

Every doc in `docs/learned/` needs YAML frontmatter because the sync pipeline (`erk docs sync`) uses it to build three things agents rely on:

1. **Index files** — root and per-category `index.md` files that agents grep to discover relevant docs
2. **Tripwire files** — per-category `tripwires.md` files aggregating "before you do X, read Y" warnings
3. **Tripwires index** — master routing table mapping categories to their tripwire files

Without frontmatter, a doc is invisible to automated discovery. Agents would only find it through manual grep of individual files.

## Schema

<!-- Source: src/erk/agent_docs/models.py, AgentDocFrontmatter -->
<!-- Source: src/erk/agent_docs/operations.py, validate_agent_doc_frontmatter -->

The canonical schema is defined in `AgentDocFrontmatter` in `src/erk/agent_docs/models.py` and enforced by `validate_agent_doc_frontmatter()` in `src/erk/agent_docs/operations.py`.

| Field          | Required | Type                              | Notes                                                                   |
| -------------- | -------- | --------------------------------- | ----------------------------------------------------------------------- |
| `title`        | Yes      | string                            | Used in navigation and indexes                                          |
| `read_when`    | Yes      | list of strings                   | Must be non-empty. Each item is a condition phrase for agent discovery  |
| `tripwires`    | No       | list of `{action, warning}` dicts | Both keys required per item                                             |
| `last_audited` | No       | string                            | `YYYY-MM-DD HH:MM PT` format (validated by regex in `operations.py:30`) |
| `audit_result` | No       | `"clean"` or `"edited"`           | Literal type check                                                      |

## The Two-Field Tripwire Format

Tripwires use a structured `{action, warning}` format, **not** plain strings:

```yaml
# CORRECT — structured format
tripwires:
  - action: "calling subprocess.run(check=True) directly"
    warning: "Use erk's subprocess wrappers instead for consistent error handling."

# WRONG — plain string (fails validation with 'must be an object')
tripwires:
  - "CRITICAL: Before calling subprocess.run(check=True) directly"
```

### Why Two Fields Instead of One String?

An earlier format used flat strings like `"CRITICAL: Before doing X"`. This had problems:

- **No separation of trigger from guidance** — agents could detect what to avoid but not why or what to do instead
- **Generated output was action-only** — category tripwire files could only say "don't do X" with no actionable alternative
- **Inconsistent prefix** — `"CRITICAL: Before"` was convention, not enforced, leading to format drift

The structured format separates the **trigger** (`action`) from the **guidance** (`warning`).

<!-- Source: src/erk/agent_docs/operations.py, generate_category_tripwires_doc -->

During sync, these render into category tripwire files as: **CRITICAL: Before {action}** → Read [{doc title}]({doc path}) first. {warning}

The "CRITICAL: Before" prefix is added automatically — don't include it in the `action` field.

### Writing Good Tripwires

**action field** — use a gerund phrase describing the specific action an agent might take:

| Pattern                                    | Quality           | Why                                                 |
| ------------------------------------------ | ----------------- | --------------------------------------------------- |
| `"adding a new method to Git ABC"`         | Good              | Specific, matches agent intent at decision point    |
| `"working with gateways"`                  | Bad — too vague   | Matches too broadly, causes alert fatigue           |
| `"breaking tests"`                         | Bad — consequence | Agents can't self-check "am I about to break tests" |
| `"Don't forget to implement all 5 layers"` | Bad — imperative  | Not an action pattern agents can match against      |

**warning field** — explain what to do instead, not just what's wrong. Agents need actionable guidance, not just prohibitions.

## Writing Effective read_when Conditions

`read_when` conditions are how agents discover docs — they grep index files for keywords matching their current task.

Design conditions for **keyword overlap with agent task descriptions**:

- Start with present participles: "implementing", "debugging", "working with"
- Include synonym coverage: both "gateway" and "ABC" if both terms apply
- Be specific enough to avoid false matches: "resolving git merge conflicts" not "using git"

Overly broad conditions waste agent context window by loading irrelevant docs. Overly narrow conditions prevent future discovery.

## The Sync Pipeline

<!-- Source: src/erk/agent_docs/operations.py, sync_agent_docs -->

`erk docs sync` performs a multi-step pipeline:

1. Discovers all non-generated `.md` files in `docs/learned/` (skips `index.md`, `tripwires-index.md`, and auto-generated `tripwires.md`)
2. Validates frontmatter — invalid docs are skipped with a warning
3. Generates root `index.md` and per-category `index.md` (categories need 2+ docs for their own index)
4. Collects tripwires from valid docs, groups by category directory
5. Generates per-category `tripwires.md` and the master `tripwires-index.md`
6. Formats all output through prettier via `agent_docs.format_markdown()`

**Always commit both source docs AND generated files.** Generated files are checked in because agents load them directly — they're not rebuilt at runtime.

## Category Assignment

<!-- Source: src/erk/agent_docs/operations.py, _get_category_from_path -->

Category is derived purely from directory path: `docs/learned/architecture/foo.md` → category `architecture`. Root-level docs go into "uncategorized" in the tripwires index.

To create a new category: create the directory, add docs with valid frontmatter, run `erk docs sync`. Optionally add entries to `CATEGORY_DESCRIPTIONS` and `CATEGORY_ROUTING_HINTS` in `operations.py` for richer index and tripwire-index display.

## Common Mistakes

| Symptom                                            | Cause                                            | Fix                                                            |
| -------------------------------------------------- | ------------------------------------------------ | -------------------------------------------------------------- |
| Tripwire missing from generated files              | Plain string instead of `{action, warning}` dict | Restructure as `{action: "...", warning: "..."}`               |
| Doc missing from index                             | No `read_when` field or empty list               | Add at least one condition                                     |
| Validation error: `tripwires[N] must be an object` | Tripwire item is a string                        | Convert to structured dict format                              |
| "Invalid YAML" parse error                         | Unquoted colons or special characters            | Quote strings: `"working with: patterns"`                      |
| Prettier cycling between sync and CI               | Single-pass formatting                           | Already fixed — `agent_docs.format_markdown()` runs two passes |
| Doc shows in wrong category tripwires              | Doc is in wrong directory for its content        | Move to correct category directory, re-sync                    |
