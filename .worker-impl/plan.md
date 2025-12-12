# Plan: Update Claude CLI Integration Documentation

## Objective

Add documentation for stdin-based prompt passing to avoid `OSError: [Errno 7] Argument list too long` when invoking Claude CLI with large prompts.

## Context

- **Source**: Bug fix session 16d0a8f3-535d-45d2-a348-ce54498be45d
- **Problem**: Command-line arguments are limited by OS (~128KB on Linux/macOS)
- **Solution**: Pass prompts via `input=` parameter to `subprocess.run()` instead of as command-line arguments

## Files to Modify

1. `/Users/schrockn/code/erk/docs/agent/architecture/claude-cli-integration.md`

## Implementation Steps

### Step 1: Update claude-cli-integration.md

Add the following new sections to the existing document:

**1. Add to frontmatter `read_when`:**
```yaml
  - Passing large prompts to Claude CLI
  - Avoiding argument list too long errors
```

**2. Add tripwire (after frontmatter):**
```yaml
tripwires:
  - action: "passing prompt as command-line argument to Claude CLI"
    warning: "Use input= parameter for stdin to avoid OSError with large prompts."
```

**3. Add new section "Input Methods" after the overview:**

```markdown
## Input Methods

The Claude CLI accepts prompts via two methods:

### Command-line Argument (Limited)

```python
subprocess.run(["claude", "--print", "Your prompt here"], ...)
```

- Subject to OS argument list size limit (~128KB on Linux/macOS)
- Will fail with `OSError: [Errno 7] Argument list too long` for large prompts
- Acceptable only for short, fixed prompts

### Stdin (Preferred for Variable-Size Prompts)

```python
subprocess.run(
    ["claude", "--print", "--model", model],
    input=prompt,  # Pass via stdin, not as argument
    capture_output=True,
    text=True,
)
```

- No size limit (stdin is not subject to kernel arg limits)
- **Preferred** for subprocess invocation with variable-size prompts
- Required when prompt size cannot be guaranteed small
```

**4. Add "Key Flags Reference" table:**

```markdown
## Key Flags

| Flag | Purpose |
|------|---------|
| `--print` | Non-interactive mode, print response and exit |
| `--model <name>` | Model selection (e.g., "haiku", "sonnet", "opus") |
| `--dangerously-skip-permissions` | Bypass permission prompts (for automation) |
| `--output-format json` | Structured JSON output |
| `--verbose` | Required with `--print --output-format stream-json` |
```

**5. Update "Reference Implementation" section to note the stdin pattern:**

Point to `packages/erk-shared/src/erk_shared/prompt_executor/real.py` as an example that should use stdin for robustness (currently uses command-line args).

### Step 2: Regenerate index

Run `erk docs sync` to regenerate the index files with updated frontmatter.

## Related Documentation

- Skills to load: None (documentation-only task)
- Related docs: `docs/agent/architecture/subprocess-wrappers.md`

## Verification

After implementation:
1. Read the updated doc to verify formatting
2. Run `erk docs sync` to update index
3. Verify tripwire appears in `docs/agent/tripwires.md`