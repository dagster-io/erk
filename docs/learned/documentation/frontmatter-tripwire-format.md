---
title: Frontmatter Tripwire Format
read_when:
  - "Creating new documentation in docs/learned/"
  - "Adding tripwires to existing docs"
  - "Understanding frontmatter schema"
  - "Running erk docs sync"
---

# Frontmatter Tripwire Format

## Overview

All documentation files in `docs/learned/` use YAML frontmatter to specify metadata. This metadata enables automated indexing, tripwire generation, and context-aware doc loading.

## YAML Schema

### Complete Structure

```yaml
---
title: Document Title # Optional: Used in navigation (defaults to filename)
read_when: # Required: List of conditions triggering doc load
  - "condition 1"
  - "condition 2"
tripwires: # Optional: List of critical action-triggered warnings
  - "CRITICAL: Before doing X"
  - "CRITICAL: Before doing Y"
---
```

### Field Definitions

#### `title` (Optional)

**Type**: String

**Purpose**: Human-readable title for navigation and indexes

**Default**: If omitted, derived from filename (`my-file.md` → "My File")

**When to use**: When filename doesn't make a good title

**Example**:

```yaml
title: LibCST Systematic Import Refactoring
```

#### `read_when` (Required)

**Type**: List of strings

**Purpose**: Defines conditions when this document should be loaded into agent context

**Format**: Each item is a condition phrase describing when to read this doc

**Best practices**:

- Use lowercase for consistency
- Start with present participle verbs ("working with", "implementing", "debugging")
- Be specific (not "using git" but "resolving git merge conflicts")
- Include synonyms (e.g., both "gateway" and "ABC" if relevant)

**Examples**:

```yaml
read_when:
  - "implementing gateway abstractions"
  - "working with 5-layer gateway pattern"
  - "creating ABC interfaces"
  - "debugging gateway tests"
```

**How it's used**:

- `erk docs sync` generates index with these conditions
- Agents grep for keywords to find relevant docs
- Documentation-first discovery matches task keywords against conditions

#### `tripwires` (Optional)

**Type**: List of strings

**Purpose**: Critical action-triggered warnings that prevent common mistakes

**Format**: Each item MUST start with `CRITICAL: Before` followed by the action

**Schema**:

```
CRITICAL: Before <action-that-triggers-tripwire>
```

**Best practices**:

- Always start with `CRITICAL: Before`
- Describe the **action**, not the consequence
- Be specific about what triggers the warning
- Link to detailed doc in the tripwire file (auto-generated)

**Examples**:

```yaml
tripwires:
  - "CRITICAL: Before creating a gateway without all 5 implementation layers"
  - "CRITICAL: Before modifying PR footer format validation"
  - "CRITICAL: Before using EAFP (try/except) for control flow"
```

**What NOT to do**:

```yaml
# BAD - Missing "CRITICAL: Before"
tripwires:
  - "Don't forget to implement all 5 layers"

# BAD - Too vague
tripwires:
  - "CRITICAL: Before working with gateways"

# BAD - Describes consequence, not action
tripwires:
  - "CRITICAL: Before breaking tests"
```

**How it's used**:

- `erk docs sync` extracts tripwires into category tripwire files
- Tripwires appear in `docs/learned/<category>/tripwires.md` (auto-generated)
- Agents check tripwires before taking matching actions

## Generation Process

### Step 1: Write Frontmatter

Create new doc with proper frontmatter:

```markdown
---
read_when:
  - "using subprocess wrappers"
  - "handling subprocess errors"
tripwires:
  - "CRITICAL: Before using subprocess.run(check=True) directly"
---

# Subprocess Wrappers

Content goes here...
```

### Step 2: Run `erk docs sync`

```bash
erk docs sync
```

This command:

1. **Scans all docs/learned/ markdown files**
2. **Extracts frontmatter** from each file
3. **Generates index files**:
   - `docs/learned/index.md` - Master index with all docs
   - `docs/learned/<category>/index.md` - Category-specific indexes
4. **Generates tripwire files**:
   - `docs/learned/<category>/tripwires.md` - Aggregated tripwires per category
   - `docs/learned/tripwires-index.md` - Master tripwire index

### Step 3: Verify Generated Files

Check that tripwires appear correctly:

```bash
# View category tripwires
cat docs/learned/architecture/tripwires.md

# View master tripwire index
cat docs/learned/tripwires-index.md
```

### Step 4: Commit All Changes

```bash
git add docs/learned/
git commit -m "Add new doc with tripwires"
```

**Important**: Always commit both source docs AND generated files.

## Validation

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
  - "Remember to check X"
  - "CRITICAL: Don't do Y"  # Wrong - should be "Before doing Y"

# VALID
tripwires:
  - "CRITICAL: Before doing X without checking Y"
  - "CRITICAL: Before modifying Z"
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

Docs are automatically categorized based on directory:

| Directory                    | Category        | Tripwire File               |
| ---------------------------- | --------------- | --------------------------- |
| `docs/learned/architecture/` | architecture    | `architecture/tripwires.md` |
| `docs/learned/cli/`          | cli             | `cli/tripwires.md`          |
| `docs/learned/testing/`      | testing         | `testing/tripwires.md`      |
| `docs/learned/planning/`     | planning        | `planning/tripwires.md`     |
| (any other category)         | (category name) | `<category>/tripwires.md`   |

**New categories**: Create directory, add docs with frontmatter, run `erk docs sync`.

## Examples

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
  - "CRITICAL: Before creating gateway without fake implementation"
  - "CRITICAL: Before skipping DryRun or Printing layers"
---
```

### Doc with Multiple Tripwires

```yaml
---
read_when:
  - "writing CLI commands"
  - "handling user input validation"
tripwires:
  - "CRITICAL: Before using RuntimeError for expected CLI failures"
  - "CRITICAL: Before adding CLI flags without validation"
  - "CRITICAL: Before using dict .get() on exec script JSON without TypedDict"
---
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
