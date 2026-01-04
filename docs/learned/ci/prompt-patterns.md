---
title: CI Prompt Patterns
read_when:
  - Using Claude Code in GitHub Actions workflows
  - Creating multi-line prompts in CI YAML
  - Adding new prompts to the erk bundle
tripwires:
  - action: "using heredoc (<<) syntax in GitHub Actions YAML"
    warning: "Use `erk exec get-embedded-prompt` instead. Heredocs in YAML `run:` blocks have fragile indentation that causes silent failures."
---

# CI Prompt Patterns

## The Problem: Heredocs in GitHub Actions YAML

YAML heredocs (`<< 'EOF'`) in GitHub Actions `run:` blocks are fragile:

1. **Indentation sensitivity**: YAML requires consistent indentation, but heredocs treat leading whitespace as part of the content
2. **Delimiter handling**: The `EOF` delimiter can fail silently if indentation isn't exact
3. **Multi-part construction**: Building prompts with multiple heredocs (`cat >> file << 'EOF'`) compounds the fragility
4. **Silent failures**: When heredocs fail, the prompt is often empty or malformed, causing cryptic downstream errors

Example of the problematic pattern:

```yaml
# FRAGILE - avoid this pattern
run: |
  cat > /tmp/prompt.md << 'PROMPT_EOF'
  # My Prompt
  Some content here
  PROMPT_EOF
```

## The Solution: Embedded Prompts

Store prompts as separate files in `.github/prompts/` and retrieve them at runtime:

```yaml
# ROBUST - use this pattern
run: |
  prompt=$(erk exec get-embedded-prompt my-prompt)
  claude --print "$prompt"
```

### Benefits

1. **No indentation issues**: Prompt files have their own formatting rules
2. **Syntax highlighting**: Editors recognize `.md` files
3. **Easier maintenance**: Edit prompts without YAML escaping concerns
4. **Testable**: Can test prompt retrieval independently
5. **Reusable**: Same prompt can be used in multiple workflows

## How to Add a New Prompt

### Step 1: Create the Prompt File

Create `.github/prompts/<prompt-name>.md`:

```markdown
# My Prompt Title

Instructions for Claude here.

## Dynamic Values

Use shell-style placeholders that will be substituted at runtime:

- Job result: ${{ needs.job-name.result }}
- Inline content: $VARIABLE_NAME

## Rules

- Rule 1
- Rule 2
```

### Step 2: Register the Prompt

Add the prompt name to `AVAILABLE_PROMPTS` in:
`src/erk/cli/commands/exec/scripts/get_embedded_prompt.py`

```python
AVAILABLE_PROMPTS = frozenset(
    {
        "ci-autofix",
        "dignified-python-review",
        "my-new-prompt",  # Add here
    }
)
```

### Step 3: Use in Workflow

```yaml
run: |
  prompt=$(erk exec get-embedded-prompt my-new-prompt)
  # Substitute any placeholders
  prompt="${prompt//\$VARIABLE_NAME/$actual_value}"
  claude --print "$prompt"
```

## Placeholder Syntax

### GitHub Actions Expressions

Use literal `${{ ... }}` syntax in the prompt file. Substitute at runtime:

```yaml
prompt="${prompt//\$\{\{ needs.format.result \}\}/${{ needs.format.result }}}"
```

### Shell Variables

Use `$VARIABLE_NAME` syntax for values loaded at runtime:

```yaml
value=$(cat /tmp/some-file.txt)
prompt="${prompt//\$VARIABLE_NAME/$value}"
```

## Existing Prompts

| Prompt                    | Purpose                                                   |
| ------------------------- | --------------------------------------------------------- |
| `ci-autofix`              | Fix auto-fixable CI errors (format, lint, prettier, docs) |
| `dignified-python-review` | Review Python code against dignified-python standards     |
| `tripwires-review`        | Review changes against tripwire rules                     |
