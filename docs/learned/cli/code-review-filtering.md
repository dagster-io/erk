---
title: Code Review Filtering
read_when:
  - "debugging false positives in code review"
  - "understanding keyword-only parameter exceptions"
  - "working with ABC/Protocol method validation"
---

# Code Review Filtering

The dignified-python code review filters certain patterns to avoid false positive violations.

## Keyword-Only Parameter Exceptions

The 5+ parameters rule requires keyword-only arguments (`*` separator) for functions with many parameters. However, certain patterns are explicitly excluded.

### ABC/Protocol Method Signatures

Methods defined in abstract base classes (ABC) or Protocol interfaces are **exempt** from the keyword-only parameter rule.

**Rationale:** ABC/Protocol methods define contracts that implementations must follow. The signature is constrained by the interface, not the implementation.

```python
# EXEMPT - ABC method (no violation)
class GitHub(ABC):
    @abstractmethod
    def create_pr(
        self,
        repo_root: Path,
        title: str,
        body: str,
        base: str,
        head: str,
        draft: bool,
    ) -> PRDetails:
        ...

# EXEMPT - Protocol method (no violation)
class Executor(Protocol):
    def execute(
        self,
        command: str,
        args: list[str],
        cwd: Path,
        timeout: int,
        capture: bool,
    ) -> Result:
        ...
```

### Click Command Callbacks

Click command callbacks are **exempt** because Click injects parameters positionally based on decorator order.

```python
# EXEMPT - Click callback (no violation)
@click.command()
@click.option("--title")
@click.option("--body")
@click.option("--labels", multiple=True)
@click.option("--draft", is_flag=True)
@click.option("--auto-merge", is_flag=True)
@click.pass_obj
def create_pr(ctx, title, body, labels, draft, auto_merge):
    ...
```

## Detection Logic

The code review checks for violations using this logic:

1. Count function parameters (excluding `self`, `cls`)
2. If count >= 5, check for `*` or `*,` on its own line in signature
3. **Before flagging**, verify no exception applies:
   - Is this an `@abstractmethod` in an ABC class?
   - Is this a method in a `Protocol` class?
   - Is this decorated with `@click.command()` or `@click.group()`?

If any exception applies, skip without flagging.

## Docstring Convention for Exceptions

When documenting why a function is exempt from a rule, use this format in the docstring:

```python
def some_method(
    self,
    param1: str,
    param2: int,
    param3: bool,
    param4: Path,
    param5: list[str],
) -> Result:
    """Do something important.

    Note: Exempt from keyword-only rule (ABC method signature).
    """
    ...
```

This helps future reviewers understand why the pattern was allowed.

## Reference Implementation

The exception filtering is implemented in `.github/reviews/dignified-python.md`:

- Lines 80-88 document the exceptions
- The review prompt explicitly instructs to check exceptions before flagging

## Related Documentation

- [Dignified Python Skill](../../.claude/skills/dignified-python/) - Full coding standards
- [Convention-Based Code Reviews](../ci/convention-based-reviews.md) - Review system overview
