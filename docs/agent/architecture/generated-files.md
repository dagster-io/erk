---
title: Generated Files Architecture
read_when:
  - "understanding how agent docs sync works"
  - "debugging generated file issues"
  - "adding new generated file types"
---

# Generated Files Architecture

This document explains the frontmatter-to-generated-file pattern used for agent documentation.

## The Source-of-Truth Principle

**Frontmatter is authoritative; generated files are derived.**

Documentation metadata lives in YAML frontmatter at the top of each source file. Index files and aggregated views are automatically generated from this metadata. This ensures:

- **Single source of truth**: Metadata is defined once, not duplicated
- **Consistency**: Generated files always reflect current frontmatter
- **Discoverability**: Agents can find relevant docs through standardized indexes

## Generated Files

The sync command (`erk docs sync`) produces these files:

| File                             | Source                            | Purpose                                         |
| -------------------------------- | --------------------------------- | ----------------------------------------------- |
| `docs/agent/index.md`            | All doc frontmatter               | Root navigation with categories and documents   |
| `docs/agent/<category>/index.md` | Category doc frontmatter          | Category-specific navigation (only for 2+ docs) |
| `docs/agent/tripwires.md`        | `tripwires:` field in frontmatter | Aggregated action-triggered rules               |

All generated files include a banner warning against direct edits:

```markdown
<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
```

## Generation Pipeline

The sync process follows these stages:

### 1. Discovery

`discover_agent_docs()` finds all `.md` files in `docs/agent/`, excluding `index.md` files (which are generated).

### 2. Validation

`validate_agent_doc_frontmatter()` checks each file's frontmatter against the schema:

- Required fields present (`title`, `read_when`)
- Correct types (strings, lists)
- Valid tripwire structure (if present)

Invalid files are counted but skipped—they don't break the sync.

### 3. Collection

Two parallel collection paths:

- `collect_valid_docs()`: Groups docs by category (subdirectory) and root level
- `collect_tripwires()`: Extracts all tripwire definitions with source attribution

### 4. Generation

Functions produce markdown content:

- `generate_root_index()`: Categories list + uncategorized docs
- `generate_category_index()`: Docs within a single category
- `generate_tripwires_doc()`: Formatted tripwire rules with doc links

### 5. Sync

Files are written only if content changed:

- **Created**: File didn't exist
- **Updated**: Content differs from existing
- **Unchanged**: Content matches (no write)

## Frontmatter Schema

### Required Fields

```yaml
---
title: Document Title # Human-readable title for indexes
read_when: # List of trigger conditions
  - "first condition"
  - "second condition"
---
```

### Optional Fields

```yaml
---
title: Document Title
read_when:
  - "trigger condition"
tripwires: # Action-triggered warnings
  - action: "doing something" # Action pattern that triggers
    warning: "Do this instead." # What to do instead
---
```

## Banner Placement

Banner location varies by file type:

- **Index files**: Banner at file start (no frontmatter needed)
- **tripwires.md**: Banner after frontmatter (YAML must parse correctly)

This distinction matters because tripwires.md has its own frontmatter for the index system, while index files are pure navigation.

## The Meta-Tripwire Pattern

The system protects itself through a self-documenting mechanism:

1. `erk-architecture.md` defines a tripwire about editing generated files:

   ```yaml
   tripwires:
     - action: "editing docs/agent/index.md or docs/agent/tripwires.md directly"
       warning: "These are generated files. Edit the source frontmatter instead..."
   ```

2. During sync, this tripwire is collected from `erk-architecture.md`

3. It appears in the generated `tripwires.md` file

4. Agents see the warning before they would violate it

This creates a protection loop: the tripwire that protects generated files is itself propagated through the generation system.

## Adding New Generated File Types

To add a new generated file type:

1. **Define collection function**: Similar to `collect_tripwires()`, extract data from frontmatter
2. **Define generation function**: Similar to `generate_tripwires_doc()`, produce markdown content
3. **Update sync function**: Add collection and generation calls in `sync_agent_docs()`
4. **Update SyncResult**: Track new file type in sync results

Follow the existing pattern of:

- Collecting metadata from source files
- Generating content with the standard banner
- Writing only when content changes

## Related Topics

- [Agent Documentation Guide](../../../.claude/skills/agent-docs/SKILL.md) - Operational guidance for doc maintenance
- [Erk Architecture Patterns](erk-architecture.md) - Contains the meta-tripwire definition
