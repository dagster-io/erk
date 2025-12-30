---
title: Kit CLI Push Down Pattern
read_when:
  - "deciding what belongs in kit CLI vs agent markdown"
  - "moving bash logic from agent prompts to Python"
  - "reducing token usage in agent prompts"
  - "designing kit CLI commands for agents"
---

# Kit CLI Push Down Pattern

Push mechanical computation from agent prompts down to kit CLI commands where it's more efficient and testable.

**Analogy**: Like database query optimizers that "push down" predicates closer to the data layer, this pattern moves computation from LLM prompts to Python CLI commands.

## The Decision Rule

**If it requires understanding meaning → use LLM. If it's mechanical transformation → use kit CLI.**

### Use Kit CLI For

- **Parsing/Validation**: URL parsing, input format validation, path encoding
- **Data Extraction**: JSON/YAML parsing, filtering, computing derived values
- **Deterministic Operations**: File system queries, string transforms, math
- **Token Reduction**: Compressing verbose data, pre-filtering large datasets

### Keep in Agent For

- **Semantic Analysis**: Summarizing, generating names, subjective decisions
- **Content Generation**: Commit messages, documentation, code
- **Complex Reasoning**: Trade-off decisions, interpreting ambiguous requirements

## Before/After Example

### Before (Bash in Agent Markdown)

Problems: Hard to test, permission prompts, fragile regex, verbose error handling.

```bash
# Parse issue number from input
if [[ "$issue_arg" =~ github\.com/[^/]+/[^/]+/issues/([0-9]+) ]]; then
    issue_number="${BASH_REMATCH[1]}"
elif [[ "$issue_arg" =~ ^[0-9]+$ ]]; then
    issue_number="$issue_arg"
else
    echo "Error: Invalid input format"
    exit 1
fi
```

### After (Kit CLI Command)

Benefits: Testable, no permission prompt, structured output.

```bash
# Agent markdown invocation - simple output
filename=$(erk exec issue-title-to-filename "$title")

# Agent markdown invocation - JSON output with error handling
result=$(erk exec impl-init --json)

if ! echo "$result" | jq -e '.valid' > /dev/null; then
    error_msg=$(echo "$result" | jq -r '.error')
    echo "Error: $error_msg"
    exit 1
fi

phases=$(echo "$result" | jq -r '.phases')
```

## Implementation Checklist

1. **Create command file**: `packages/erk-kits/.../kit_cli_commands/{kit}/{command}.py`
2. **Use dataclasses for output**: Success and error types with structured fields
3. **Return JSON**: Use `json.dumps(asdict(result))` for consistent output
4. **Write unit tests**: Test success cases, edge cases, and error handling
5. **Register in kit.yaml**: Add entry under `kit_cli_commands`
6. **Update agent markdown**: Replace bash logic with kit CLI invocation
7. **Parse JSON in agent**: Use `jq` to extract fields and check `success`

## Anti-Patterns

- **Using kit CLI for semantic tasks**: Don't push content generation to Python
- **Complex business logic**: Keep commands simple; orchestration belongs in agent
- **Tight coupling**: Design commands to be reusable across agents
- **Unstructured output**: Always use structured JSON with success indicators

## Related Topics

- [cli-commands.md](cli-commands.md) - How to build kit CLI commands
- [code-architecture.md](code-architecture.md) - Kit module structure
- [Agent Delegation](../planning/agent-delegation.md) - How commands delegate to agents
