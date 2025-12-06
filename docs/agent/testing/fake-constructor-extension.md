---
title: Extending Fake Constructors
read_when:
  - "adding new methods to ABC interfaces"
  - "extending fake implementations"
  - "updating test fakes for new behavior"
---

# Extending Fake Constructors

When adding methods to an ABC that require fake behavior configuration:

## Pattern

1. **Add constructor parameters** for controlling behavior:
   - `_<feature>_raises: bool = False` - Control exception behavior
   - `_<feature>_return_value: T | None = None` - Control return values

2. **Add tracking lists** for test assertions:
   - `_<feature>_calls: list[tuple[...]] = []` - Track invocations

3. **Initialize in `__init__`**:

   ```python
   def __init__(
       self,
       *,
       # ...existing params...
       feature_raises: bool = False,
       feature_return_value: str | None = None,
   ):
       # ...existing initialization...
       self._feature_calls: list[tuple[Path]] = []
       self._feature_raises = feature_raises
       self._feature_return_value = feature_return_value
   ```

4. **Expose via properties** for test assertions:
   ```python
   @property
   def feature_calls(self) -> list[tuple[Path]]:
       return self._feature_calls.copy()
   ```

## Example: FakeShell.run_claude_extraction_plan

From commit c1be84a02:

```python
def __init__(
    self,
    *,
    # ...
    claude_extraction_raises: bool = False,
    extraction_plan_url: str | None = None,
):
    self._extraction_calls: list[tuple[Path]] = []
    self._claude_extraction_raises = claude_extraction_raises
    self._extraction_plan_url = extraction_plan_url

def run_claude_extraction_plan(self, cwd: Path) -> str | None:
    self._extraction_calls.append((cwd,))
    if self._claude_extraction_raises:
        raise subprocess.CalledProcessError(...)
    return self._extraction_plan_url
```
