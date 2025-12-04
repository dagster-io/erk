# Documentation Extraction Plan

Extracted from 6 sessions in worktree `2179-restore-exit-plan-mode-hoo-12-04-1125`.

## Source Sessions

- 554cc5cf-dd6a-41b6-adf4-95ac432b73f7
- 8a7cbbc4-a9b6-4c00-beba-4c66bac9cce5
- 4d04e1cd-3985-4628-86be-ad93792edc44
- 7ee42baa-90a6-47dd-8710-ef6b0cbca43a
- 22ee85a3-1dc6-41ee-bb7d-18a602dcea89
- d7af6f6b-d7c5-40f6-b651-a998ea58bec4

---

## Suggestion 1: Hook Exit Code Decision Patterns

**Category:** A (Learning Gap)
**Type:** Agent doc addition to `docs/agent/hooks/hooks.md`
**Effort:** Small

### Problem Observed

Sessions showed confusion about hook exit codes. The common assumption is:
- Exit 0 = success = allow the tool
- Exit 2 = failure = block the tool

But the actual pattern is more nuanced:
- Exit 0 = "proceed with the tool's normal flow"
- Exit 2 = "stop here, don't run the tool"

The key insight: **blocking can be the correct "success" path** when you want to prevent a tool's default behavior.

### Draft Content

Add to `docs/agent/hooks/hooks.md` after the "Output and Decision Control" section:

~~~markdown
### Exit Code Decision Patterns

Hook exit codes control whether the tool proceeds, but the semantics are about **flow control**, not success/failure:

| Exit Code | Meaning | When to Use |
|-----------|---------|-------------|
| 0 | Allow tool to proceed | Tool should run its normal flow |
| 2 | Block tool execution | You've handled the situation; tool's default flow is unwanted |

**Key Insight: Blocking as Success**

Exit 2 (block) is often the RIGHT choice for successful terminal states:

```python
# Example: Plan already saved to GitHub
if saved_marker.exists():
    saved_marker.unlink()
    click.echo("✅ Plan saved to GitHub. Session complete.")
    sys.exit(2)  # BLOCK - prevents ExitPlanMode's plan approval dialog
```

Why block here? Because:
1. The user's goal (save plan) is already accomplished
2. The tool's default behavior (show plan approval dialog) serves no purpose
3. Blocking prevents unwanted UI while the message communicates completion

**Decision Framework:**

Ask: "What happens if I allow the tool to proceed?"

- If the tool's normal flow is helpful → Exit 0 (allow)
- If the tool's normal flow is unnecessary/harmful → Exit 2 (block)

The exit code is about **what should happen next**, not whether your hook succeeded.
~~~

---

## Suggestion 2: Plan Save Workflow UX Pattern

**Category:** B (Teaching Gap)
**Type:** Agent doc update to `docs/agent/planning/workflow.md`
**Effort:** Small

### Problem Observed

After implementing plan save to GitHub, the user was still prompted with the plan approval dialog. The fix: don't call ExitPlanMode after saving - stay in plan mode and let the user exit manually.

### Draft Content

Add new section to `docs/agent/planning/workflow.md`:

~~~markdown
## Plan Save Workflow

When a user saves their plan to GitHub (via `/erk:save-plan`), the workflow should end cleanly without additional prompts.

### Flow Diagram

```
┌─────────────────┐
│  Plan Mode      │
│  (plan created) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ User: "Save to  │
│ GitHub"         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ /erk:save-plan  │
│ - Create issue  │
│ - Create marker │
│ - Show success  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ STOP            │  ← Do NOT call ExitPlanMode
│ Stay in plan    │
│ mode            │
└─────────────────┘
```

### Key Principle: Don't Call ExitPlanMode After Saving

After saving to GitHub:
1. The marker file `plan-saved-to-github` is created
2. Success message is displayed with next steps
3. **Session stays in plan mode** - no ExitPlanMode call

Why? ExitPlanMode shows a plan approval dialog. After saving, this dialog:
- Serves no purpose (plan is already saved)
- Requires unnecessary user interaction
- Confuses the workflow

### Safety Net: Hook Blocks ExitPlanMode

If ExitPlanMode is called anyway (e.g., by mistake), the `exit-plan-mode-hook` detects the saved marker and blocks with exit 2:

```python
if saved_marker.exists():
    saved_marker.unlink()
    click.echo("✅ Plan saved to GitHub. Session complete.")
    sys.exit(2)  # Block to prevent plan approval dialog
```

This ensures the plan dialog never appears after a successful save.
~~~

---

## Implementation Notes

Both suggestions are small additions to existing docs:
1. **Suggestion 1**: ~30 lines added to hooks.md
2. **Suggestion 2**: ~50 lines added to workflow.md

No new files needed - these extend existing documentation.