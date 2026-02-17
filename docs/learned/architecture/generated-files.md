---
last_audited: "2026-02-17 00:00 PT"
audit_result: clean
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

| File                                   | Source                            | Purpose                                          |
| -------------------------------------- | --------------------------------- | ------------------------------------------------ |
| `docs/learned/index.md`                | All doc frontmatter               | Root navigation with categories and documents    |
| `docs/learned/<category>/index.md`     | Category doc frontmatter          | Category-specific navigation (only for 2+ docs)  |
| `docs/learned/<category>/tripwires.md` | `tripwires:` field in frontmatter | Per-category action-triggered rules              |
| `docs/learned/tripwires-index.md`      | All category tripwire files       | Routing table linking to category tripwire files |

All generated files include a banner warning against direct edits. See `GENERATED_FILE_BANNER` in `src/erk/agent_docs/operations.py`.

## Generation Pipeline

The full pipeline is implemented in `sync_agent_docs()` in `src/erk/agent_docs/operations.py`. The stages are:

1. **Discovery**: `discover_agent_docs()` finds all `.md` files in `docs/learned/`, excluding `index.md`, `tripwires-index.md`, and auto-generated `tripwires.md` files.
2. **Validation**: `validate_agent_doc_frontmatter()` checks frontmatter against the schema. Invalid files are counted but skipped.
3. **Collection**: `collect_valid_docs()` groups docs by category; `collect_tripwires()` extracts tripwire definitions.
4. **Generation**: `generate_root_index()`, `generate_category_index()`, `generate_category_tripwires_doc()`, and `generate_tripwires_index()` produce markdown content.
5. **Sync**: Files are written only if content changed (created/updated/unchanged tracking via `SyncResult`).

## Frontmatter Schema

See `validate_agent_doc_frontmatter()` in `src/erk/agent_docs/operations.py` for the authoritative schema.

- **Required**: `title` (string), `read_when` (list of strings)
- **Optional**: `tripwires` (list of `{action, warning}` objects), `last_audited` (string), `audit_result` (`clean` or `edited`)

## Banner Placement

Banner location varies by file type:

- **Index files**: Banner at file start (no frontmatter needed)
- **tripwires.md**: Banner after frontmatter (YAML must parse correctly)

This distinction matters because tripwires.md has its own frontmatter for the index system, while index files are pure navigation.

## Adding a Tripwire: Full Workflow

When asked to "add a tripwire", follow this complete workflow:

### Step 1: Add Documentation

First, document the issue in the appropriate source file (usually in `docs/learned/`):

1. **Find or create the right doc file** - Match the topic to an existing doc or create a new one
2. **Add a section explaining the pattern** - Include:
   - What the problem is
   - Wrong pattern (with code example)
   - Correct pattern (with code example)
   - Why the correct pattern works

### Step 2: Add Tripwire to Frontmatter

Add the tripwire to the document's YAML frontmatter:

```yaml
---
title: Document Title
read_when:
  - "relevant condition"
tripwires:
  - action: "doing the problematic thing" # Action pattern agents recognize
    warning: "Do this instead." # Concise guidance
---
```

The `action` should describe what triggers the warning (in present participle form), and `warning` should give the corrective action.

### Step 3: Regenerate

Run the sync command to propagate the tripwire:

```bash
erk docs sync
```

This updates category tripwire files (e.g., `docs/learned/architecture/tripwires.md`) with tripwires from source files in each category.

### Complete Example

To add a tripwire about path-based worktree detection:

1. **Document in `erk-architecture.md`**:
   - Add "Current Worktree Detection" section
   - Show wrong pattern (path comparisons)
   - Show correct pattern (git-based detection)

2. **Add frontmatter tripwire**:

   ```yaml
   tripwires:
     - action: "detecting current worktree using path comparisons on cwd"
       warning: "Use git.get_repository_root(cwd) instead..."
   ```

3. **Regenerate**: `erk docs sync`

## Progress Reporting

The `sync_agent_docs()` function supports progress reporting through a callback parameter. When provided, the callback is invoked at 6 milestone points:

1. **Scanning docs** - Before document discovery
2. **Generating root index** - Before root index generation
3. **Generating category indexes** - Before category index loop
4. **Collecting tripwires** - Before tripwire collection
5. **Generating tripwire files** - Before tripwire file loop
6. **Generating tripwires index** - Before final index generation

This coarse-grained approach (6 messages for ~55 files) provides adequate user feedback without overwhelming output. The CLI binds this to styled progress output; validation commands like `erk docs check` pass a no-op lambda to suppress output.

See [Callback Progress Pattern](callback-progress-pattern.md) for the implementation pattern.

## Adding New Generated File Types

To add a new generated file type, follow the existing pattern in `sync_agent_docs()`:

1. **Define collection function**: Similar to `collect_tripwires()`, extract data from frontmatter
2. **Define generation function**: Similar to `generate_category_tripwires_doc()`, produce markdown content
3. **Update sync function**: Add collection and generation calls in `sync_agent_docs()`
4. **Update SyncResult**: Track new file type in sync results

## Related Topics

- [Learned Documentation Guide](../../../.claude/skills/learned-docs/SKILL.md) - Operational guidance for doc maintenance
- [Erk Architecture Patterns](erk-architecture.md) - Core architecture patterns and tripwire definitions
