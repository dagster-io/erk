---
title: Pre-Destruction Data Capture Pattern
read_when:
  - "implementing operations that destroy or transform data"
  - "designing multi-phase pipelines"
  - "capturing data before mutations"
---

# Pre-Destruction Data Capture Pattern

When an operation will destroy or transform data, capture any information that might be needed later **before** the destructive operation occurs.

## The Problem

Destructive operations permanently lose information:

- Squashing commits loses individual commit messages
- Deleting files loses their content
- Rebasing loses original commit history
- Migrations lose old configuration format

Once the operation completes, the original data is **unrecoverable**.

## The Solution

**Capture before destruction**: Collect needed data before the operation, then pass it through to consumers who need it.

## Pattern Structure

```python
def operation_that_destroys_data(context, target):
    # Step 1: Capture data BEFORE destruction
    preserved_data = extract_data_we_need(context, target)

    # Step 2: Perform destructive operation
    perform_destructive_operation(target)

    # Step 3: Include preserved data in result
    return OperationResult(
        ...,
        preserved_data=preserved_data,
    )
```

## Real-World Example: Commit Messages Before Squash

### Context

When creating a PR with `erk pr submit`:

1. The command squashes multiple commits into one (destructive)
2. AI needs original commit messages for context
3. After squashing, individual messages are lost

### Implementation

```python
# In pre_analysis.py - preflight phase before PR creation

def run_preflight_phase(ops, options):
    """Run preflight checks and capture data before mutations."""

    # ... other preflight steps ...

    # Step 5a: Get parent branch
    parent_branch = ops.graphite.get_parent_branch(ops.cwd)

    # Step 5b: Capture commit messages BEFORE squashing
    commit_messages = ops.git.get_commit_messages_since(ops.cwd, parent_branch)

    # Step 6: Squash commits (destructive - loses individual messages)
    squash_commits(ops.git, ops.cwd, parent_branch)

    # Step 7: Return result with preserved data
    return PreflightResult(
        parent_branch=parent_branch,
        diff_file=diff_file,
        commit_messages=commit_messages if commit_messages else None,  # ← Preserved!
        ...
    )
```

### Why This Matters

**If we captured commit messages after squashing:**

```python
# ❌ WRONG: Data already destroyed
def run_preflight_phase(ops, options):
    parent_branch = ops.graphite.get_parent_branch(ops.cwd)

    # Squash first (destroys commit messages)
    squash_commits(ops.git, ops.cwd, parent_branch)

    # Too late! Only one squashed message remains
    commit_messages = ops.git.get_commit_messages_since(ops.cwd, parent_branch)
    # Result: ["Squashed commit"] instead of ["feat: add X", "fix: bug Y"]
```

**Result**: AI would only see "Squashed commit" instead of the detailed original messages, producing worse PR descriptions.

## Additional Examples

### Example: File Content Before Migration

```python
def migrate_config_format(config_path: Path):
    """Migrate config from JSON to YAML."""

    # Step 1: Capture old format BEFORE migration
    old_content = config_path.read_text(encoding="utf-8")
    old_config = json.loads(old_content)

    # Step 2: Transform to new format
    new_config = transform_to_yaml(old_config)

    # Step 3: Write new format (destructive)
    config_path.write_text(new_config, encoding="utf-8")

    # Step 4: Return with backup
    return MigrationResult(
        new_path=config_path,
        backup_content=old_content,  # ← Preserved for rollback
    )
```

### Example: Branch State Before Rebase

```python
def rebase_with_fallback(git, cwd: Path, target_branch: str):
    """Rebase onto target with ability to restore original state."""

    # Step 1: Capture current state BEFORE rebase
    original_head = git.get_current_commit(cwd)
    original_branch = git.get_current_branch(cwd)

    # Step 2: Attempt rebase (destructive)
    try:
        git.rebase(cwd, target_branch)
        return RebaseResult(success=True)
    except RebaseConflict as e:
        # Step 3: Use preserved state for recovery
        git.abort_rebase(cwd)
        return RebaseResult(
            success=False,
            error=str(e),
            original_head=original_head,  # ← Can restore to this
            original_branch=original_branch,
        )
```

### Example: User Input Before Transformation

```python
def normalize_and_process_input(raw_input: str):
    """Normalize input for processing while preserving original."""

    # Step 1: Capture original BEFORE normalization
    original_input = raw_input

    # Step 2: Transform (destructive - loses formatting, case, etc.)
    normalized = raw_input.strip().lower().replace("_", "-")

    # Step 3: Process normalized version
    result = process_normalized_input(normalized)

    # Step 4: Return with original for error messages
    return ProcessingResult(
        result=result,
        normalized=normalized,
        original=original_input,  # ← For user-facing error messages
    )
```

## When to Apply This Pattern

Ask yourself these questions:

1. **Does this operation permanently modify or delete data?**
   - Deleting files, squashing commits, rebasing, migrations

2. **Will any downstream code need the original data?**
   - AI context generation, error messages, rollback, audit logs

3. **Is the data unrecoverable after the operation?**
   - If yes, capture it first

If all three are "yes", apply the pre-destruction capture pattern.

## Implementation Checklist

- [ ] Identify what data will be lost
- [ ] Capture data before destructive operation
- [ ] Store preserved data in result type
- [ ] Document why preservation is needed (comment)
- [ ] Test that preserved data is available to consumers

## Common Mistake: Forgetting to Pass Data Through

```python
# ❌ WRONG: Data captured but not returned
def preflight(ops):
    commit_messages = ops.git.get_commit_messages_since(...)
    squash_commits(...)

    # Forgot to include in result!
    return PreflightResult(
        parent_branch=parent_branch,
        diff_file=diff_file,
    )  # commit_messages lost

# ✅ CORRECT: Data captured AND passed through
def preflight(ops):
    commit_messages = ops.git.get_commit_messages_since(...)
    squash_commits(...)

    return PreflightResult(
        parent_branch=parent_branch,
        diff_file=diff_file,
        commit_messages=commit_messages,  # ← Preserved and passed through
    )
```

## Related Patterns

- **Event Progress Pattern**: Often combined with pre-destruction capture in multi-phase pipelines
- **Result Types**: Use typed results to carry preserved data through phases
- **Rollback/Undo**: Preserved data enables reverting destructive operations

## Related Documentation

- [Event Progress Pattern](event-progress-pattern.md) - Multi-phase pipelines with data flow
- [Erk Architecture](erk-architecture.md) - Result types and phase coordination
