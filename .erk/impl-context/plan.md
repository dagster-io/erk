# Add Print Statement to __main__.py

## Context
User requested adding a print statement to the first Python file found in the project.

## Target File
`src/erk/__main__.py`

## Change
Add `print("hello")` after the module docstring, before the import.

## Implementation
Edit `src/erk/__main__.py` to add:
```python
print("hello")
```
