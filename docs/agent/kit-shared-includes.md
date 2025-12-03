# Kit Shared Includes

This guide documents how to share markdown content between kit commands using the `@` include directive.

## When to Use Shared Includes

Extract shared content when:

- Multiple commands need identical logic or instructions
- Updates should propagate automatically to all consumers
- The shared content is substantial (more than a few lines)

Keep content inline when:

- It's command-specific or context-dependent
- The content is short and unlikely to change
- Sharing would create confusing indirection

## File Location

**Place shared includes in `docs/erk/includes/`** within your kit directory:

```
packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/
├── commands/erk/
│   ├── suggest-agent-docs.md           # Command 1
│   └── suggest-agent-docs-from-log.md  # Command 2
└── docs/erk/includes/
    └── suggest-docs-analysis-shared.md # Shared content
```

**Why `docs/erk/includes/` instead of `commands/`?**

- Keeps command directory clean (only executable commands)
- Clear separation between "runnable" and "reusable" content
- Follows documentation convention (content goes in `docs/`)

## Reference Syntax

Use relative paths from the command file to the include:

```markdown
### Step 1-4: Analyze Session

@../../docs/erk/includes/suggest-docs-analysis-shared.md
```

The `@` directive inserts the entire file contents at that location during command expansion.

**Path breakdown:**

- `../../` - up two levels from `commands/erk/`
- `docs/erk/includes/` - into the includes directory
- `suggest-docs-analysis-shared.md` - the shared file

## Naming Conventions

- **Use kebab-case**: `suggest-docs-analysis-shared.md`
- **Avoid underscore prefix**: `_shared.md` causes Prettier escaping issues
- **Include descriptive suffix**: `-shared.md` or `-common.md` indicates reusability
- **Match the feature**: Name should reflect what the content does

## Symlink Requirements (Kit Installation)

When a kit is installed, both the command AND its includes must be symlinked:

```
.claude/commands/erk/suggest-agent-docs.md  -> kit source
docs/erk/includes/suggest-docs-analysis-shared.md -> kit source
```

The kit installation process handles this automatically via `kit.yaml`:

```yaml
commands:
  - name: suggest-agent-docs
    path: commands/erk/suggest-agent-docs.md

docs:
  - name: suggest-docs-analysis-shared
    path: docs/erk/includes/suggest-docs-analysis-shared.md
```

## Example: Shared Analysis Logic

Two commands share analysis logic:

**suggest-agent-docs.md:**

```markdown
### Step 1-4: Analyze Session

@../../docs/erk/includes/suggest-docs-analysis-shared.md

### Step 5: Confirm with User

[Command-specific confirmation step]
```

**suggest-agent-docs-from-log.md:**

```markdown
### Step 1-4: Analyze Session

@../../docs/erk/includes/suggest-docs-analysis-shared.md

### Step 5: Output Suggestions Directly

[Different step - no confirmation needed]
```

**suggest-docs-analysis-shared.md:**

```markdown
## Signals to Detect

Scan for these signals of missing documentation:

1. **Repeated explanations** - Same concept explained multiple times
2. **Trial-and-error patterns** - Multiple failed attempts
   ...
```

## Common Pitfalls

### Incorrect relative path depth

```markdown
# WRONG - missing one level

@../docs/erk/includes/shared.md

# CORRECT - from commands/erk/ to docs/erk/includes/

@../../docs/erk/includes/shared.md
```

### Using underscore prefix

```markdown
# WRONG - causes Prettier escaping: \_shared.md in output

\_suggest-docs-shared.md

# CORRECT - clean kebab-case

suggest-docs-shared.md
```

### Forgetting symlink registration

If includes aren't registered in `kit.yaml`, they won't be available after installation:

```yaml
# WRONG - only command registered
commands:
  - name: my-command
    path: commands/erk/my-command.md

# CORRECT - include also registered
commands:
  - name: my-command
    path: commands/erk/my-command.md
docs:
  - name: shared-logic
    path: docs/erk/includes/shared-logic.md
```

### Circular includes

The `@` directive does not detect cycles. Avoid include files that reference each other:

```markdown
# shared-a.md

@./shared-b.md # DANGER: if shared-b includes shared-a

# shared-b.md

@./shared-a.md # Creates infinite loop
```

## Decision Criteria

Use this checklist to decide whether to extract shared content:

| Criteria                            | Extract?    |
| ----------------------------------- | ----------- |
| Used by 2+ commands                 | Yes         |
| Logic should stay synchronized      | Yes         |
| Content is command-specific context | No          |
| Less than 10 lines                  | Probably no |
| Likely to diverge per command       | No          |

## Related

- [Kit CLI Commands](kit-cli-commands.md) - Python/LLM boundary standards
- [Kit Code Architecture](kit-code-architecture.md) - Kit structure patterns
