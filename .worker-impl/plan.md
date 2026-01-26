# Plan: Remove ai-generated label mentions

## Summary
Remove all references to the non-existent "ai-generated" label from documentation and examples.

## Files to Modify

### 1. `.claude/commands/erk/plan-implement.md` (line 277)
**Current:**
```bash
gh pr create --fill --label "ai-generated" || gh pr edit --add-label "ai-generated"
```
**Change to:**
```bash
gh pr create --fill || gh pr edit
```

### 2. `.claude/skills/fake-driven-testing/references/quick-reference.md` (line 283)
**Current:**
```python
fake_issues = FakeGitHubIssues(labels={"erk-plan", "ai-generated"})
```
**Change to:**
```python
fake_issues = FakeGitHubIssues(labels={"erk-plan"})
```

## Verification
- Run `rg "ai-generated"` to confirm no remaining mentions