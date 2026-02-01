---
title: Research Documentation Integration with Objectives
read_when:
  - "creating research documentation during objective work"
  - "linking learned docs to objective issues"
  - "working with objective research phases"
  - "documenting discoveries from objective investigations"
---

# Research Documentation Integration with Objectives

When working on objectives that involve research phases, create learned documentation to capture discoveries and link it bidirectionally to the objective issue.

## When to Create Research Documentation

Create learned documentation during objectives when:

1. **You discover architectural patterns** worth documenting for future work
2. **You encounter tripwires** that should be codified
3. **You learn integration patterns** between systems
4. **You document mental models** for complex domains

Not every objective needs documentation - only create it when you discover reusable knowledge.

## Documentation Creation Workflow

### 1. Identify the Category

Place the documentation in the appropriate category:

- **Architecture patterns**: `docs/learned/architecture/`
- **Desktop/erkdesk patterns**: `docs/learned/desktop-dash/`
- **CLI patterns**: `docs/learned/cli/`
- **Testing patterns**: `docs/learned/testing/`
- **Gateway patterns**: `docs/learned/gateway/`
- **TUI patterns**: `docs/learned/tui/`

See [Guide](../guide.md) for complete category descriptions.

### 2. Write the Documentation

Include proper frontmatter:

```yaml
---
title: Your Document Title
read_when:
  - "trigger condition 1"
  - "trigger condition 2"
tripwires: # Optional, only if you're documenting tripwires
  - action: "action that should trigger warning"
    warning: "warning message with guidance"
---
```

See [Generated Files Architecture](../architecture/generated-files.md) for frontmatter schema.

### 3. Run erk docs sync

After creating the documentation:

```bash
erk docs sync
```

This regenerates:

- Category index files
- Root index file
- Tripwires aggregation files

### 4. Verify Generated Files

Check that your documentation appears in the appropriate index:

```bash
# Check category index
cat docs/learned/<category>/index.md

# Check root index
cat docs/learned/index.md

# If you added tripwires, check tripwires file
cat docs/learned/<category>/tripwires.md
```

## Objective Linking Workflow

After creating and syncing documentation, link it to the objective:

### 1. Update Objective Issue

Add a "Learned Documentation" section to the objective issue:

```markdown
## Learned Documentation

Research from this objective produced the following documentation:

- [Document Title](https://github.com/yourorg/erk/blob/master/docs/learned/category/document.md)
```

### 2. Reference Objective in Documentation

In the documentation, reference the objective that prompted it:

```markdown
## Context

This pattern was discovered during [Objective #123: Desktop Dashboard Research](https://github.com/yourorg/erk/issues/123).
```

This creates a bidirectional link between the objective and the learned documentation.

## Example: Desktop Dashboard Research

During objective #6431 (Desktop Dashboard Research), the research phase produced:

1. **security.md** - Context bridge security pattern
2. **typescript-multi-config.md** - Multi-config TypeScript checking
3. **dual-handler-pattern.md** - Context-agnostic command handlers
4. **research-documentation-integration.md** - This document

Each was:

- Placed in the appropriate category
- Given proper frontmatter
- Synced with `erk docs sync`
- Referenced in the objective issue

## When NOT to Create Documentation

Don't create documentation for:

- **One-time fixes**: Bugs specific to this objective
- **Temporary workarounds**: Things you plan to change
- **Speculative patterns**: Patterns not yet proven in practice
- **Obvious patterns**: Things well-covered by existing docs or common knowledge

Only document reusable knowledge that will help future work.

## Integration with Learn Workflow

If the objective produces a PR, you can also extract learned documentation via the learn workflow:

```bash
# After PR is merged
erk learn <pr-number>
```

The learn workflow will:

- Analyze the PR and associated session
- Identify documentation gaps
- Create learned documentation
- Update the learn plan issue

This complements manual research documentation creation.

## Related Documentation

- [Generated Files Architecture](../architecture/generated-files.md) - Frontmatter schema and sync process
- [Guide](../guide.md) - Documentation category descriptions
- [Learn Workflow](../planning/learn-workflow.md) - Automated documentation extraction from PRs
