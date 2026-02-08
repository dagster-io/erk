---
title: Frontmatter and Tripwire Format
read_when:
  - creating new documentation in docs/learned/
  - adding tripwires to existing docs
  - understanding frontmatter schema for agent docs
  - running erk docs sync
tripwires:
  - action: "critical: before creating a gateway"
    warning: "CRITICAL: Before creating a gateway without all 5 implementation layers"
  - action: "critical: before modifying pr footer"
    warning: "CRITICAL: Before modifying PR footer format validation"
  - action: "critical: before using eafp (try/except)"
    warning: "CRITICAL: Before using EAFP (try/except) for control flow"
```

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

| Field          | Required | Type                              | Notes                                                                  |
| -------------- | -------- | --------------------------------- | ---------------------------------------------------------------------- |
| `title`        | Yes      | string                            | Used in navigation and indexes                                         |
| `read_when`    | Yes      | list of strings                   | Must be non-empty. Each item is a condition phrase for agent discovery |
| `tripwires`    | No       | list of `{action, warning}` dicts | Both keys required per item                                            |
| `last_audited` | No       | string                            | Free-form date string                                                  |
| `audit_result` | No       | `"clean"` or `"edited"`           | Literal type check                                                     |

## The Two-Field Tripwire Format

Tripwires use a structured `{action, warning}` format, **not** plain strings:

```yaml
# CORRECT — structured format
tripwires:
  - action: "don't forget to implement all"
    warning: "Don't forget to implement all 5 layers"

# WRONG — plain string (fails validation with 'must be an object')
tripwires:
  - action: "performing actions related to this tripwire"
    warning: "CRITICAL: Before working with gateways"

# BAD - Describes consequence, not action
tripwires:
  - action: "performing actions related to this tripwire"
    warning: "CRITICAL: Before breaking tests"
```

### Why Two Fields Instead of One String?

An earlier format used flat strings like `"CRITICAL: Before doing X"`. This had problems:

- **No separation of trigger from guidance** — agents could detect what to avoid but not why or what to do instead
- **Generated output was action-only** — category tripwire files could only say "don't do X" with no actionable alternative
- **Inconsistent prefix** — `"CRITICAL: Before"` was convention, not enforced, leading to format drift

The structured format separates the **trigger** (`action`) from the **guidance** (`warning`).

<!-- Source: src/erk/agent_docs/operations.py, generate_category_tripwires_doc -->

```markdown
---
read_when:
  - "using subprocess wrappers"
  - "handling subprocess errors"
tripwires:
  - action: "performing actions related to this tripwire"
    warning: "CRITICAL: Before using subprocess.run(check=True) directly"
  - action: "performing actions related to this tripwire"
    warning: "--"

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
6. Formats all output through prettier (run twice for idempotency — see `_format_with_prettier()` in `operations.py` for why the double-pass is necessary)

### Required Frontmatter Check

All docs MUST have `read_when` field:

```yaml
# INVALID - Missing read_when
---
title: My Doc
---
# VALID - Has read_when
---
read_when:
  - "working with feature X"
---
```

### Tripwire Format Check

All tripwires MUST start with `CRITICAL: Before`:

```yaml
# INVALID
tripwires:
  - action: "performing actions related to this tripwire"
    warning: "Remember to check X"
  - action: "critical: don't do y\" #"
    warning: "CRITICAL: Don't do Y\"  # Wrong - should be \"Before doing Y"

# VALID
tripwires:
  - action: "critical: before doing x without"
    warning: "CRITICAL: Before doing X without checking Y"
  - action: "performing actions related to this tripwire"
    warning: "CRITICAL: Before modifying Z"
```

### YAML Syntax Check

Frontmatter must be valid YAML:

```yaml
# INVALID - Unquoted colon in string
read_when:
  - working with: gateway patterns

# VALID - Quoted strings
read_when:
  - "working with: gateway patterns"
```

## Category Assignment

<!-- Source: src/erk/agent_docs/operations.py, _get_category_from_path -->

Category is derived purely from directory path: `docs/learned/architecture/foo.md` → category `architecture`. Root-level docs go into "uncategorized" in the tripwires index.

To create a new category: create the directory, add docs with valid frontmatter, run `erk docs sync`. Optionally add entries to `CATEGORY_DESCRIPTIONS` and `CATEGORY_ROUTING_HINTS` in `operations.py` for richer index and tripwire-index display.

## Common Mistakes

### Minimal Doc (read_when only)

```yaml
---
read_when:
  - "understanding project glossary"
  - "looking up erk terminology"
---
```

### Complete Doc (all fields)

```yaml
---
title: Gateway ABC Implementation Checklist
read_when:
  - "implementing gateway abstractions"
  - "creating new gateway"
  - "working with 5-layer pattern"
tripwires:
  - action: "critical: before creating gateway without"
    warning: "CRITICAL: Before creating gateway without fake implementation"
  - action: "critical: before skipping dryrun or"
    warning: "CRITICAL: Before skipping DryRun or Printing layers"
  - action: "performing actions related to this tripwire"
    warning: "--"
```

### Doc with Multiple Tripwires

```yaml
---
read_when:
  - "writing CLI commands"
  - "handling user input validation"
tripwires:
  - action: "critical: before using runtimeerror for"
    warning: "CRITICAL: Before using RuntimeError for expected CLI failures"
  - action: "critical: before adding cli flags"
    warning: "CRITICAL: Before adding CLI flags without validation"
  - action: "critical: before using dict .get()"
    warning: "CRITICAL: Before using dict .get() on exec script JSON without TypedDict"
  - action: "performing actions related to this tripwire"
    warning: "--"
```

## Troubleshooting

### Tripwires Not Appearing in Generated Files

**Cause**: Tripwire doesn't start with `CRITICAL: Before`

**Fix**: Update frontmatter format, re-run `erk docs sync`

### "Invalid YAML" Error

**Cause**: Syntax error in frontmatter (unquoted colons, wrong indentation)

**Fix**: Validate YAML with online parser, fix syntax

### Doc Not in Index

**Cause**: Missing `read_when` field

**Fix**: Add `read_when` field with at least one condition

### Tripwire in Wrong Category File

**Cause**: Doc is in wrong directory for its content

**Fix**: Move doc to correct category directory, re-run `erk docs sync`

## Related Documentation

- [Documentation Hub](guide.md) - Complete documentation navigation guide
- [Claude MD Best Practices](claude-md-best-practices.md) - Frontmatter for CLAUDE.md files
- [Tripwires Index](../tripwires-index.md) - Complete list of all tripwires
