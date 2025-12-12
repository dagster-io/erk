---
title: CLI List Formatting Standards
read_when:
  - "formatting list output"
  - "designing list commands"
  - "ensuring consistent list display"
---

# CLI List Formatting Standards

This document defines the visual design principles for all list commands in the erk-kits CLI, ensuring a consistent and user-friendly experience across `artifact list`, `hook list`, `kit list`, `kit search`, and `status`.

## Audience

This guide is for **human developers** working on the erk-kits CLI. It focuses on the "why" behind formatting choices and what users should see, not implementation details.

## Core Principles

### 1. Visual Hierarchy

**Why**: Users need to quickly scan lists and understand relationships between items.

**How**: Use consistent indentation levels and section headers to create clear structure:

- **Section headers**: Bold, white text to mark major divisions
- **Subsection headers**: Bold, white text with 2-space indent to mark groups
- **List items**: 4-space indent under subsections
- **Details**: 6-8 space indent under list items for metadata

### 2. Color as Meaning

**Why**: Color should communicate information, not just decoration.

**Color conventions**:

| Color            | Meaning                    | Usage                            |
| ---------------- | -------------------------- | -------------------------------- |
| **Green** (bold) | Project-level              | `[P]` badges, success indicators |
| **Blue** (bold)  | User-level                 | `[U]` badges                     |
| **Cyan**         | Kit sources and versions   | `[kit-id@version]`, PR numbers   |
| **Yellow**       | Local sources and branches | `[local]`, branch names          |
| **White** (bold) | Primary content            | Section headers, artifact names  |
| **White** (dim)  | Secondary metadata         | Descriptions, paths              |
| **Red**          | Errors or warnings         | Error states                     |

### 3. Consistent Layout Patterns

**Why**: Users should be able to predict how information is organized.

#### Compact View (Default)

Shows essential information in a scannable format:

```
Section Header:
  Subsection Header:
    [level] artifact-name [source]
    [level] another-artifact [source]
```

**Example**:

```
Claude Artifacts:
  Skills:
    [P] erk [erk@0.1.0]
    [U] custom-skill [local]
```

#### Verbose View (`-v` flag)

Adds indented details below each item:

```
Section Header:
  Subsection Header:
    [level] artifact-name [source]
        → Description goes here
        Kit: kit-id@version
        Path: relative/path/to/file
```

**Example**:

```
Claude Artifacts:
  Skills:
    [P] erk [erk@0.1.0]
        → Use erk for git worktree management
        Kit: erk@0.1.0
        Path: skills/erk.md
```

### 4. Badge Indicators

**Why**: Badges provide quick context about item properties.

#### Level Badges

- `[P]` - Project-level (green, bold) - Installed in `./.claude/`
- `[U]` - User-level (blue, bold) - Installed in `~/.claude/`

#### Source Badges

- `[kit-id@version]` - Managed by kit (cyan) - Tracked in `kits.toml`
- `[local]` - Locally created (yellow) - Not tracked by kit system

**When to show**: Always display both level and source badges in list views.

### 5. Section Organization

**Why**: Logical grouping reduces cognitive load.

#### Primary Sections

**Claude Artifacts**: Items that extend Claude's behavior

- Skills
- Commands
- Agents
- Hooks

**Installed Items**: Supporting resources

- Docs
- Kit CLI Commands

**Other Contexts**:

- Hook List: Group by lifecycle event (UserPromptSubmit, etc.)
- Kit List: Group by installation type (bundled vs managed)
- Status: Group by management status (managed vs unmanaged)

### 6. Spacing and Readability

**Why**: Whitespace prevents visual clutter.

**Rules**:

- Blank line between major sections
- Blank line between items in verbose view
- No blank lines between items in compact view
- Section headers have no blank line before their first item

## Before/After Examples

### Before: Plain Text Hook List

```
erk:gt-submit-hook [UserPromptSubmit / command_name:gt:submit-branch]
dignified-python:type-checker [UserPromptSubmit / *]
```

### After: Formatted Hook List

```
Hooks by Lifecycle:
  UserPromptSubmit:
    [P] erk:gt-submit-hook [erk@0.1.0]
        Matcher: command_name:gt:submit-branch
    [U] dignified-python:type-checker [local]
        Matcher: *
```

**What improved**:

- Visual hierarchy with section headers
- Color-coded level and source badges
- Clear grouping by lifecycle event
- Indented matcher details in verbose mode

## Common Mistakes to Avoid

1. **Inconsistent indentation**: Always use 2-space increments (0, 2, 4, 6, 8)
2. **Missing section headers**: Every group should have a bold header
3. **Color overload**: Only use colors with semantic meaning
4. **Cramped layout**: Add blank lines between major sections
5. **Unaligned columns**: Use consistent spacing for badge alignment

## Testing Your Formatting

When implementing or modifying list commands:

1. **Visual test**: Run the command and verify:
   - Section headers are bold and clearly visible
   - Colors match the documented conventions
   - Indentation creates clear hierarchy
   - Badges are consistently formatted

2. **Consistency test**: Compare output with `artifact list`:
   - Do sections use the same header style?
   - Are colors used consistently?
   - Is spacing between sections the same?

3. **Edge cases**: Test with:
   - Empty lists (should show appropriate message)
   - Mixed levels (project and user)
   - Mixed sources (managed and local)
   - Long names (verify no line wrapping issues)

## Implementation Notes

For technical implementation details, see:

- `packages/erk-kits/src/erk_kits/cli/list_formatting.py` - Shared formatting utilities
- `packages/erk-kits/src/erk_kits/commands/artifact/formatting.py` - Artifact-specific formatters

This document focuses on **what** the output should look like and **why**, not **how** to implement it.
