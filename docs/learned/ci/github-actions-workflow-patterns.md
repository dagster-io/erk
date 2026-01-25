---
title: GitHub Actions Workflow Patterns
read_when:
  - "writing GitHub Actions workflows"
  - "debugging workflow conditions"
  - "composing step conditions"
tripwires:
  - action: "composing conditions across multiple GitHub Actions workflow steps"
    warning: "Verify each `steps.step_id.outputs.key` reference exists and matches actual step IDs."
---

# GitHub Actions Workflow Patterns

Patterns and gotchas for writing reliable GitHub Actions workflows.

## Compound Condition Validation

Complex step conditions that reference multiple outputs are prone to silent failures.

### The Problem

```yaml
- name: Conditional step
  if: steps.build.outputs.success == 'true' && steps.test.outcome == 'success'
  run: echo "This might never run due to typos"
```

If `steps.build` doesn't exist or doesn't output `success`, the condition silently evaluates to false.

### Validation Checklist

Before using compound conditions:

1. **Step ID exists**: Each referenced step has `id: <name>`
2. **Spelling matches**: Step IDs are case-sensitive
3. **Output key correct**: Use `outputs.<key>` for custom outputs, `outcome` for step status
4. **Default handling**: Consider what happens if a step is skipped

### Step Outcome vs Outputs

| Property  | Type   | Values                               | Use Case                |
| --------- | ------ | ------------------------------------ | ----------------------- |
| `outcome` | string | success, failure, cancelled, skipped | Check if step ran       |
| `outputs` | object | Custom key-value pairs               | Pass data between steps |

### Example: Robust Conditional

```yaml
- name: Build
  id: build
  run: |
    npm run build
    echo "artifact_path=dist/" >> $GITHUB_OUTPUT

- name: Deploy
  if: |
    steps.build.outcome == 'success' &&
    steps.build.outputs.artifact_path != ''
  run: deploy ${{ steps.build.outputs.artifact_path }}
```

## Step ID Best Practices

### Naming Conventions

- Use `kebab-case`: `run-tests`, `build-docker`
- Be descriptive: `validate-pr-title` not `step1`
- Avoid abbreviations: `implementation` not `impl`

### When to Add IDs

Add `id:` to steps that:

- Output values other steps need
- Are referenced in conditions
- Might fail and need status checks

### Example: Complete Step Pattern

```yaml
- name: Human-readable description
  id: machine-readable-id
  run: |
    # Do work
    echo "key=value" >> $GITHUB_OUTPUT
  continue-on-error: true # If step failure shouldn't fail job
```

## Silent Failures to Avoid

### Missing Step ID

```yaml
# WRONG: No id, can't reference this step
- name: Run tests
  run: npm test

- name: Deploy if tests pass
  if: steps.run-tests.outcome == 'success' # Always false!
  run: deploy
```

### Typo in Step Reference

```yaml
- name: Build
  id: build-step

- name: Deploy
  if: steps.build.outcome == 'success' # Wrong! Should be 'build-step'
  run: deploy
```

### Wrong Output Key

```yaml
- name: Check
  id: check
  run: echo "result=pass" >> $GITHUB_OUTPUT

- name: Use result
  if: steps.check.outputs.outcome == 'pass' # Wrong! Key is 'result'
  run: echo "passed"
```

## Related Documentation

- [GitHub Actions Output Patterns](github-actions-output-patterns.md) - Multi-line outputs
- [GitHub Actions Security](github-actions-security.md) - Input sanitization
- [erk-impl Workflow Patterns](erk-impl-workflow-patterns.md) - erk-specific patterns
