---
title: Dual Handler Pattern for Context-Agnostic Commands
read_when:
  - "implementing TUI commands that work in multiple contexts"
  - "working with Textual CommandRegistry"
  - "designing commands that operate on selected items"
  - "planning desktop dashboard command handlers"
tripwires:
  - action: "implementing separate command handlers for list and detail views"
    warning: "Use dual handler pattern: single handler operates on 'selected plan' regardless of context. CommandRegistry routes list context and detail context to same handler."
---

# Dual Handler Pattern for Context-Agnostic Commands

The dual handler pattern allows TUI commands to work identically from both list and detail contexts by operating on the concept of "the selected plan" rather than specific UI state.

## The Pattern

Instead of implementing separate handlers for "delete from list" and "delete from detail", implement one handler that operates on "delete the selected plan":

```python
# Single handler for both contexts
@dataclass(frozen=True)
class DeletePlanHandler:
    """Delete the currently selected plan."""

    async def handle(self, selected_plan: Plan) -> None:
        """Delete the given plan.

        Args:
            selected_plan: The plan to delete (from list selection or detail view)
        """
        # Implementation doesn't care which context we came from
        await self.plan_service.delete(selected_plan.id)
```

## How It Works

The CommandRegistry dispatches the same handler from different contexts:

```python
class PlanListScreen:
    """List view of plans."""

    def register_commands(self) -> None:
        """Register commands available in list view."""
        self.command_registry.register(
            key="d",
            handler=DeletePlanHandler(),
            context=lambda: self.get_selected_plan()  # Selected from list
        )


class PlanDetailScreen:
    """Detail view of a single plan."""

    def register_commands(self) -> None:
        """Register commands available in detail view."""
        self.command_registry.register(
            key="d",
            handler=DeletePlanHandler(),
            context=lambda: self.current_plan  # Currently viewed plan
        )
```

Both screens use the same handler, but provide different sources for "the selected plan".

## Benefits

### 1. No Code Duplication

```python
# ❌ BAD: Separate handlers
class DeleteFromListHandler: ...
class DeleteFromDetailHandler: ...

# ✅ GOOD: One handler
class DeletePlanHandler: ...
```

### 2. Consistent Behavior

The delete operation works identically from list or detail - same confirmation, same error handling, same success message.

### 3. Easier Testing

Test the handler once, regardless of context:

```python
def test_delete_plan_handler():
    """Verify delete handler works with any plan."""
    handler = DeletePlanHandler()
    await handler.handle(selected_plan=fake_plan)
    assert fake_plan_service.deleted == [fake_plan.id]
```

### 4. Clearer Intent

Handler signature makes it obvious: "I operate on a plan, I don't care where it came from."

## CommandRegistry Abstraction

The CommandRegistry handles the context resolution:

```python
@dataclass(frozen=True)
class CommandRegistry:
    """Maps keys to handlers with context resolution."""

    def register(
        self,
        key: str,
        handler: CommandHandler,
        context: Callable[[], Plan]
    ) -> None:
        """Register a command with context provider.

        Args:
            key: Keyboard shortcut
            handler: The command handler
            context: Function that returns the selected plan for this context
        """
        ...

    async def dispatch(self, key: str) -> None:
        """Execute handler for key with resolved context."""
        handler, context_fn = self._handlers[key]
        selected_plan = context_fn()  # Resolve context
        await handler.handle(selected_plan)  # Execute handler
```

## Implications for Desktop

When implementing the desktop dashboard, this pattern suggests:

- **Single handler implementations** for commands like delete, archive, view details
- **Context providers** in each view (list widget, detail panel) that resolve "the selected plan"
- **Command palette** can work identically in any view

For example, the desktop command palette can show the same "Delete Plan" command whether you're in the list view or detail view, and it will operate on the contextually-appropriate plan.

## When NOT to Use This Pattern

This pattern works when commands operate on "the selected thing". It doesn't work for:

- **View-specific commands**: "Sort list by date" only makes sense in list view
- **Navigation commands**: "Next plan" is list-specific, "Close detail" is detail-specific
- **Batch operations**: "Delete all completed plans" operates on multiple items, not the selected one

## Related Documentation

- [Interaction Model](../desktop-dash/interaction-model.md) - Desktop dashboard interaction patterns
- [Backend Communication](../desktop-dash/backend-communication.md) - How desktop communicates with backend
