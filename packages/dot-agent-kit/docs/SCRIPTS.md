# Kit Scripts

## Definition & Purpose

**Kit scripts** are Python scripts that handle mechanical git/gh/gt operations in isolated subprocess contexts, outputting structured JSON results. They exist as a **performance and cost-optimization pattern** for Claude Code interactions.

### Why Kit Scripts Exist

Traditional approach:

```
User → Claude → Multiple git/gh/gt commands in main context → Parse outputs
```

- Each command requires LLM orchestration (slow)
- Each command output pollutes main Claude context
- Token costs accumulate quickly
- Large outputs waste context space

Kit script approach:

```
User → Claude → Single kit script (subprocess) → JSON output
```

- **Performance**: Deterministic Python execution is much faster than LLM-based orchestration
- **Cost**: All mechanical operations run in isolated subprocess, dramatically reducing token usage
- **Determinism**: Known workflows execute reliably without AI overhead
- **Clarity**: Only final JSON result enters main Claude context
- **Maintainability**: Cleaner conversation flow and easier to test

## When to Use Kit Scripts

Create a kit script when:

- **Performance and cost benefits**: Multiple git/gh/gt commands that can be executed deterministically (faster than LLM orchestration)
- **Workflow is repeatable**: The same sequence of operations will be used regularly
- **Structure is beneficial**: JSON output makes parsing and decision-making cleaner

Do NOT create a kit script when:

- **Single operation**: One git command is sufficient
- **Highly variable**: Workflow changes significantly each time
- **Interactive required**: User input needed mid-workflow (use two-phase pattern instead)

## Architecture Patterns

Kit scripts follow two distinct patterns based on complexity:

### Single-Phase Pattern

**When to use**: Straightforward workflows without AI analysis between steps

**Canonical example**: [`update_pr.py`](../src/dot_agent_kit/data/kits/gt/scripts/gt/update_pr.py)

**Structure**:

1. Define Result/Error dataclasses
2. Implement helper functions (one per operation)
3. Implement execute function that orchestrates workflow
4. Add Click command wrapper
5. Output JSON

**Characteristics**:

- Linear workflow: Step 1 → Step 2 → Step 3 → Done
- All steps can be determined upfront
- No external input needed mid-workflow
- Single entry point

### Two-Phase Pattern

**When to use**: Complex workflows requiring AI analysis between mechanical steps

**Canonical example**: [`submit_branch.py`](../src/dot_agent_kit/data/kits/gt/scripts/gt/submit_branch.py)

**Characteristics**:

- Pre-analysis: Gather context and prepare (squash commits, collect diffs)
- AI analysis: Claude analyzes results and generates content (commit messages, PR descriptions)
- Post-analysis: Apply AI-generated content and complete workflow
- Two entry points (subcommands)

**Why two phases?**

- AI analysis (slow, context-heavy, requires LLM) happens in main Claude context
- Mechanical operations (fast, deterministic, pure Python) happen in isolated subprocesses
- Clear separation of concerns

## Code Structure

### Canonical Examples

**Study these files to understand patterns - they are the authoritative implementations**:

- **Single-phase**: [`update_pr.py`](../src/dot_agent_kit/data/kits/gt/scripts/gt/update_pr.py) - Complete workflow example
- **Two-phase**: [`submit_branch.py`](../src/dot_agent_kit/data/kits/gt/scripts/gt/submit_branch.py) - Complex workflow with AI integration
- **Testing**: [`test_update_pr.py`](../tests/kits/gt/test_update_pr.py) - Comprehensive test patterns

**IMPORTANT**: Follow these examples to avoid pattern drift. All patterns below are demonstrated in these files.

### Structure Overview

See [`update_pr.py`](../src/dot_agent_kit/data/kits/gt/scripts/gt/update_pr.py) for single-phase implementation and [`submit_branch.py`](../src/dot_agent_kit/data/kits/gt/scripts/gt/submit_branch.py) for two-phase implementation.

All scripts output JSON with `success` field and appropriate data/error fields. See canonical examples for complete structure.

## Registration

Kit scripts must be registered in the kit's `kit.yaml` file in the `scripts` section (not `artifacts`). See existing kit.yaml files for examples.

## Testing

**Follow the canonical testing pattern in [`test_update_pr.py`](../tests/kits/gt/test_update_pr.py)** - it demonstrates all required patterns.

## Step-by-Step Workflow

### 1. Create Python File

Location: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/<kit-name>/scripts/<kit-name>/my_script.py`

### 2. Implement Following Canonical Pattern

Study and follow the structure from [`update_pr.py`](../src/dot_agent_kit/data/kits/gt/scripts/gt/update_pr.py) for single-phase or [`submit_branch.py`](../src/dot_agent_kit/data/kits/gt/scripts/gt/submit_branch.py) for two-phase.

### 3. Register in kit.yaml

Add entry to `scripts` section (see Registration section above).

### 4. Create Slash Command

Create `.claude/commands/<kit>/<name>.md` to invoke the script and parse JSON response.

### 5. Write Tests

Follow [`test_update_pr.py`](../tests/kits/gt/test_update_pr.py) pattern - three test classes covering helpers, execute function, and CLI.

### 6. Run Tests

```bash
uv run pytest tests/kits/<kit>/test_<name>.py
```

### 7. Verify Registration

```bash
erk kit exec <kit> --help
```

## Common Patterns

Common helper function patterns are demonstrated in the canonical examples:

- **Git state checks**: `get_current_branch()`, `has_uncommitted_changes()` - see `update_pr.py`
- **GitHub PR operations**: `check_pr_exists()` - see `update_pr.py`
- **Git operations**: `stage_and_commit_changes()`, `restack_branch()`, `submit_updates()` - see `update_pr.py`
- **Graphite operations**: `get_parent_branch()`, `count_commits_in_branch()`, `squash_commits()` - see `submit_branch.py`

All follow the LBYL pattern: check returncode, return simple types, no exceptions.

## Best Practices

### Do

- **Follow canonical examples**: `update_pr.py` and `submit_branch.py` are authoritative
- **Use LBYL pattern**: Check conditions before acting
- **Return simple types from helpers**: `bool`, `str | None`, `tuple | None`
- **Use `check=False` in subprocess.run**: Handle errors explicitly
- **Provide comprehensive docstrings**: Purpose, usage, exit codes, error types, examples
- **Test all code paths**: Success and all error types
- **Use typed error literals**: `Literal["error_type_1", "error_type_2"]`

### Don't

- **Don't use exceptions for control flow**: Return None/False instead
- **Don't use `check=True` in subprocess.run**: Defeats the purpose of LBYL
- **Don't deviate from patterns**: Causes drift and maintenance issues
- **Don't skip docstrings**: Future maintainers need context
- **Don't skip tests**: Ensures reliability

## Relationship to Slash Commands

**Kit scripts** and **slash commands** work together:

- **Kit script**: Handles mechanical operations, outputs JSON
- **Slash command**: Invokes kit script, parses JSON, interprets for user

**Example flow**:

1. User runs: `/gt:pr-update`
2. Slash command invokes: `erk kit exec gt update-pr`
3. Kit script executes git/gh/gt operations
4. Kit script outputs JSON: `{"success": true, "pr_number": 123, ...}`
5. Slash command parses JSON and reports to user: "Successfully updated PR #123"

**Why this split?**

- **Performance and cost**: Deterministic operations execute in fast Python, stay out of slow LLM context
- **Reusability**: Kit scripts can be used by multiple slash commands
- **Testability**: Kit scripts can be tested independently
- **Clarity**: Clear separation between mechanical operations and AI interpretation

## Related Documentation

- [GLOSSARY.md](GLOSSARY.md) - Terminology and core concepts
- [DEVELOPING.md](../DEVELOPING.md) - Development workflow
