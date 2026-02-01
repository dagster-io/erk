---
title: erkdesk Action Toolbar
read_when:
  - "adding new actions to the erkdesk toolbar"
  - "modifying action availability predicates"
  - "understanding action button state logic"
tripwires:
  - action: "adding a new action without updating ACTIONS array"
    warning: "ACTIONS is exported and can be reused in context menus. Add new ActionDef entries to the ACTIONS array, not as separate one-offs."
  - action: "implementing blocking action execution"
    warning: "Actions use streaming execution (startStreamingAction), not blocking. Never await or block the UI thread on action completion."
---

# erkdesk Action Toolbar

The `ActionToolbar` component provides a horizontal button bar for common plan operations. It uses an `ActionDef` interface to declaratively define actions with availability predicates and command generation.

## ActionDef Interface

```tsx
interface ActionDef {
  id: string;
  label: string;
  isAvailable: (plan: PlanRow) => boolean;
  getCommand: (plan: PlanRow) => { command: string; args: string[] };
}
```

**Pattern**: Each action is a pure function that takes a `PlanRow` and returns availability + command.

## Available Actions

The `ACTIONS` array defines 5 actions:

### 1. Submit (id: `submit_to_queue`)

**Availability**: Plan has an issue URL

```tsx
isAvailable: (plan) => plan.issue_url !== null;
```

**Command**: `erk plan submit <issue_number>`

**Use case**: Submit a plan to the remote implementation queue

### 2. Land (id: `land_pr`)

**Availability**: PR exists, is open, and has a workflow run

```tsx
isAvailable: (plan) =>
  plan.pr_number !== null && plan.pr_state === "OPEN" && plan.run_url !== null;
```

**Command**: `erk exec land-execute --pr-number=<N> --branch=<B> -f`

**Use case**: Land a PR that passed CI checks

### 3. Address (id: `address_remote`)

**Availability**: PR exists

```tsx
isAvailable: (plan) => plan.pr_number !== null;
```

**Command**: `erk launch pr-address --pr <N>`

**Use case**: Address review comments on a PR

### 4. Fix Conflicts (id: `fix_conflicts_remote`)

**Availability**: PR exists

```tsx
isAvailable: (plan) => plan.pr_number !== null;
```

**Command**: `erk launch pr-fix-conflicts --pr <N>`

**Use case**: Resolve merge conflicts in a PR

### 5. Close (id: `close_plan`)

**Availability**: Always available

```tsx
isAvailable: () => true;
```

**Command**: `erk exec close-plan <issue_number>`

**Use case**: Close a plan issue (abandon work)

## Availability Predicates Table

| Action        | Requires PR | Requires Issue URL | Extra Conditions      |
| ------------- | ----------- | ------------------ | --------------------- |
| Submit        | No          | Yes                | -                     |
| Land          | Yes         | No                 | PR open + has run_url |
| Address       | Yes         | No                 | -                     |
| Fix Conflicts | Yes         | No                 | -                     |
| Close         | No          | No                 | Always available      |

## Button State Logic

Buttons have three states:

```tsx
const available = selectedPlan !== null && action.isAvailable(selectedPlan);
const disabled = !available || runningActionId !== null;
const isRunning = runningActionId === action.id;
```

1. **Disabled** (`disabled === true`):
   - No plan selected, OR
   - Action not available for this plan, OR
   - Another action is currently running

2. **Running** (`isRunning === true`):
   - This specific action is currently executing
   - Shows "Label..." (e.g., "Submit...")
   - CSS class `action-toolbar__button--running` (opacity: 0.6, cursor: wait)

3. **Active** (neither disabled nor running):
   - Plan selected, action available, no running action
   - Clickable with hover effects

## Streaming Execution Pattern

Actions use streaming execution, NOT blocking:

```tsx
const handleClick = useCallback(
  (action: ActionDef) => {
    if (runningActionId !== null || selectedPlan === null) return;

    const { command, args } = action.getCommand(selectedPlan);
    onActionStart(action.id, command, args);
  },
  [runningActionId, selectedPlan, onActionStart],
);
```

**Key insight**: `onActionStart` triggers IPC streaming, does NOT wait for completion. The parent (App.tsx) listens to `onActionOutput` and `onActionCompleted` events to update log state.

## Exported ACTIONS Array

```tsx
export { ACTIONS, type ActionDef };
```

The `ACTIONS` array is exported for reuse in other components (e.g., context menus). When adding a new action, add it to this array—don't create duplicate action definitions elsewhere.

## CSS Styling Reference

### Container (`.action-toolbar`)

- Flexbox horizontal layout with 6px gaps
- Background: `#2d2d2d` (dark gray)
- Border-bottom: `#404040`
- Padding: `6px 10px`

### Button (`.action-toolbar__button`)

- Background: `#3c3c3c`
- Color: `#d4d4d4` (light gray text)
- Border: `1px solid #555`
- Font: Menlo/Consolas monospace, 11px
- Border-radius: 3px

### Button States

| State    | CSS Class                          | Visual Effect            |
| -------- | ---------------------------------- | ------------------------ |
| Hover    | `:hover:not(:disabled)`            | Lighter bg + border      |
| Disabled | `:disabled`                        | Opacity 0.4, no pointer  |
| Running  | `.action-toolbar__button--running` | Opacity 0.6, cursor wait |

## Adding a New Action

1. Add entry to `ACTIONS` array with id, label, `isAvailable`, `getCommand`
2. Implement `isAvailable` predicate based on `PlanRow` fields
3. Return command + args in `getCommand`
4. Test availability logic with different plan states
5. CSS styling is automatic (no changes needed)

## Related Documentation

- [App Architecture](app-architecture.md) — How App.tsx coordinates action state
- [IPC Actions](ipc-actions.md) — IPC handler pattern for streaming execution
- [erkdesk Tripwires](tripwires.md) — Critical patterns to follow
