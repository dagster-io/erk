---
title: GitHub Actions Claude Integration
read_when:
  - "running Claude in GitHub Actions workflows"
  - "configuring non-interactive Claude execution"
  - "capturing Claude output in CI"
---

# GitHub Actions Claude Integration

Running Claude Code in GitHub Actions requires specific flags for non-interactive, permission-skipped execution.

## Required Flags

```yaml
run: |
  claude --print \
    --verbose \
    --output-format stream-json \
    --dangerously-skip-permissions \
    "/your:command"
```

### Flag Breakdown

| Flag                             | Purpose                                           |
| -------------------------------- | ------------------------------------------------- |
| `--print`                        | Output to stdout (required for any output)        |
| `--verbose`                      | Enable detailed output (required for stream-json) |
| `--output-format stream-json`    | Structured JSON output per event                  |
| `--dangerously-skip-permissions` | Skip interactive permission prompts               |

### Critical: --verbose Is Required for stream-json

The `--output-format stream-json` option **requires** `--verbose`. Without it, the command fails silently or with a cryptic error. This is a Claude Code CLI requirement.

```bash
# WRONG: Fails with "stream-json requires --verbose"
claude --print --output-format stream-json ...

# CORRECT: Include --verbose
claude --print --verbose --output-format stream-json ...
```

## Environment Variables

```yaml
env:
  ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
  GH_TOKEN: ${{ secrets.ERK_QUEUE_GH_PAT }} # Or GITHUB_TOKEN
```

## Model Selection

For cost-sensitive CI jobs, specify a faster/cheaper model:

```yaml
claude --print \
--model claude-haiku-4-5 \
--verbose \
...
```

Models ranked by speed/cost (fastest first):

1. `claude-haiku-4-5` - Best for simple tasks
2. `claude-sonnet-4-5` - Good balance
3. `claude-opus-4-5` - Most capable, slowest

## Output Capture

The `stream-json` format outputs one JSON object per line (newline-delimited JSON). Parse with `jq`:

```yaml
- name: Run Claude
  id: claude
  run: |
    output=$(claude --print --verbose --output-format stream-json ...)
    echo "result=$output" >> "$GITHUB_OUTPUT"

- name: Parse Result
  run: |
    echo '${{ steps.claude.outputs.result }}' | jq -r '.text'
```

## Permissions Acknowledgment

The `--dangerously-skip-permissions` flag bypasses all interactive permission prompts. This is safe in CI because:

- The workflow already has explicit permissions (`permissions:` block)
- No human is available to approve prompts
- Repository access is controlled via GitHub secrets

## Canonical Example

See `.github/workflows/learn-dispatch.yml` for a complete working example.

## Common Errors

| Error                            | Cause                                    | Fix                    |
| -------------------------------- | ---------------------------------------- | ---------------------- |
| "stream-json requires --verbose" | Missing `--verbose` flag                 | Add `--verbose`        |
| "Permission denied"              | Missing `--dangerously-skip-permissions` | Add the flag           |
| No output captured               | Missing `--print`                        | Add `--print`          |
| Authentication failed            | Missing `ANTHROPIC_API_KEY`              | Add secret to workflow |

## Related Topics

- [CI Prompt Patterns](prompt-patterns.md) - How to structure prompts for CI
- [Claude CLI Integration](../architecture/claude-cli-integration.md) - General Claude CLI patterns
