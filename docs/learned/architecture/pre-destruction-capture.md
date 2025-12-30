---
title: Pre-Destruction Data Capture Pattern
read_when:
  - "implementing operations that destroy or transform data"
  - "designing pipelines with data capture requirements"
  - "working with git squash, rebase, or other destructive operations"
---

# Pre-Destruction Data Capture Pattern

When an operation will destroy or transform data, capture any needed information **BEFORE** the destructive operation.

## Core Principle

**Capture first, transform later.** Once data is destroyed or transformed, it cannot be recovered. If you need information from the original state, capture it before any mutations occur.

## Example: Commit Messages Before Squash

### The Problem

When submitting a PR, we squash commits into a single commit for a clean history. However, AI needs the individual commit messages to generate better PR descriptions. Once commits are squashed, the individual messages are lost.

### The Solution

In the preflight phase, capture commit messages BEFORE squashing:

1. Call `git.get_commit_messages_since(cwd, parent_branch)` to capture messages
2. Store the result in the preflight result dataclass
3. THEN perform the squash operation
4. Pass captured messages through to downstream phases

See `packages/erk/src/erk/operations/` for concrete implementations.

### Why This Matters

1. **Squashing combines multiple commits into one**, losing individual messages
2. **AI needs the original commit context** for better PR descriptions
3. **Once squashed, the information is unrecoverable**

## Pattern Application

Apply this pattern whenever you need to preserve information before a destructive operation:

### File Operations

Before deleting a file, read its content if you need to preserve or log it.

### Branch Operations

Before rebasing, capture the commit history if you need it for reporting or AI context.

### Configuration Migration

Before overwriting config, load the old version if you need to report changes or support rollback.

### User Input Before Transformation

Before normalizing user input, store the original if you need it for error messages or logging.

## Pipeline Integration

This pattern works well with multi-phase pipelines (see [Event Progress Pattern](event-progress-pattern.md)):

```
┌─────────────────┐     ┌──────────────────┐     ┌────────────────┐
│   Preflight     │────▶│   Generation     │────▶│   Finalize     │
│                 │     │                  │     │                │
└─────────────────┘     └──────────────────┘     └────────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
 Capture data            Consume data           Use captured data
 BEFORE mutation         for transformation     in final result
```

**Phase 1 (Preflight)**: Capture all data needed by subsequent phases

- Commit messages before squashing
- File content before deletion
- Branch state before rebase

**Phase 2 (Generation)**: Consume captured data

- Use commit messages for AI context
- Use file content for diff generation
- Use branch state for comparison

**Phase 3 (Finalize)**: Preserve captured data in result

- Include original commit messages in result
- Include file history in result
- Include pre-rebase state in result

## Testing This Pattern

When testing code that uses pre-destruction capture:

1. **Test that data is captured**: Verify the result contains the expected captured data
2. **Test that destructive operation occurs**: Verify the mutation was performed
3. **Test ordering**: Verify capture happens before destruction (use a tracking fake that records call order)

## Common Mistakes

### Capturing After Destruction

```python
# WRONG: Data is already lost
def process_file(file_path: Path) -> str:
    file_path.unlink()  # Destructive operation
    content = file_path.read_text()  # ERROR: File already deleted!
    return content
```

### Assuming Data Can Be Recovered

```python
# WRONG: Assuming commit messages can be retrieved after squash
def squash_and_get_messages(repo_root: Path) -> list[str]:
    git.squash_commits(repo_root, "main")  # Destructive operation
    messages = git.get_commit_messages_since(repo_root, "main")  # Only sees squashed commit!
    return messages
```

### Not Passing Captured Data Forward

Don't capture data only to discard it. Ensure captured data is included in result types so downstream phases can use it.

## Related Documentation

- [Erk Architecture Patterns](erk-architecture.md) - Dependency injection and data flow patterns
- [Event Progress Pattern](event-progress-pattern.md) - Multi-phase pipelines and data flow
- [Planning Workflow](../planning/workflow.md) - How plans capture and preserve context
