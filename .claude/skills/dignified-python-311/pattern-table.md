---
erk:
  kit: dignified-python
---

## Pattern Detection & Reference Loading

When you detect these patterns in code, load the corresponding reference file:

| Pattern Detected                                                               | Load Reference                    |
| ------------------------------------------------------------------------------ | --------------------------------- |
| `try:`, `except:`, exception handling                                          | → Load `dignified-python-core.md` |
| Type hints: `List[`, `Dict[`, `Optional[`, `Union[`, `from __future__`, `Self` | → Load `type-annotations.md`      |
| `path.resolve()`, `path.is_relative_to()`, `Path(`, pathlib operations         | → Load `dignified-python-core.md` |
| `Protocol`, `ABC`, `abstractmethod`, interfaces                                | → Load `dignified-python-core.md` |
| Import statements, `from .`, relative imports                                  | → Load `dignified-python-core.md` |
| `click.`, `@click.`, CLI commands, `print()` in CLI                            | → Load `cli-patterns.md`          |
| `subprocess.run`, `subprocess.Popen`, shell commands                           | → Load `subprocess.md`            |
| Need core standards                                                            | → Load `dignified-python-core.md` |
