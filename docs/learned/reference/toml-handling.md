---
title: TOML File Handling
read_when:
  - "reading TOML files"
  - "writing TOML files"
  - "generating TOML configuration"
  - "working with config.toml"
  - "working with pyproject.toml"
---

# TOML File Handling

This document defines the standard patterns for reading and writing TOML files in erk.

## Reading: Use tomllib (stdlib)

For reading TOML files, use Python's built-in `tomllib` module (available since Python 3.11):

```python
import tomllib
from pathlib import Path

def load_config(path: Path) -> dict:
    content = path.read_text(encoding="utf-8")
    return tomllib.loads(content)
```

## Writing: Use tomlkit (preserves formatting)

For writing TOML files, use `tomlkit` to produce well-formatted, human-readable output:

```python
import tomlkit

def build_config() -> str:
    doc = tomlkit.document()
    doc.add(tomlkit.comment("Configuration file"))
    doc["key"] = "value"
    doc["enabled"] = True

    # Add a section/table
    section = tomlkit.table()
    section["nested_key"] = "nested_value"
    doc["section"] = section

    return tomlkit.dumps(doc)
```

### Why tomlkit over f-strings?

1. **Proper escaping**: tomlkit handles special characters correctly
2. **Consistent formatting**: Produces valid TOML with proper quoting
3. **Maintainability**: Structure is explicit in code, not hidden in string templates
4. **Comments**: Can add comments programmatically

### Common Patterns

**Adding a header comment:**

```python
doc = tomlkit.document()
doc.add(tomlkit.comment("Header comment"))
```

**Adding a blank line:**

```python
doc.add(tomlkit.nl())
```

**Creating a table with comments:**

```python
table = tomlkit.table()
table.add(tomlkit.comment("Description of this section"))
table["key"] = "value"
doc["section_name"] = table
```

**Writing commented-out example values:**

```python
table = tomlkit.table()
table.add(tomlkit.comment(' key = "value"'))  # Note the leading space for alignment
doc["section"] = table
```

## Reference Implementation

See `src/erk/core/planner/registry_real.py` for a complete example of reading with tomllib and writing with tomlkit.

## Dependency

tomlkit is a dependency of `erk-shared` package. Import it as:

```python
import tomlkit
```
