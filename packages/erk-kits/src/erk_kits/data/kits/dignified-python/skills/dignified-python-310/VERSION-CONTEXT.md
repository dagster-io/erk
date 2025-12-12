# Python 3.10 Context

## New in 3.10

- PEP 604: Union Types via | operator (`str | int` instead of `Union[str, int]`)
- PEP 585: Generic types in standard collections (`list[str]` instead of `List[str]`)
- PEP 612: Parameter Specification Variables (advanced typing for decorators)
- Structural pattern matching (match/case statements)

## Type Annotation Features

Python 3.10 introduced modern type syntax that works in many contexts:

- Use `list[str]`, `dict[str, int]` instead of `List[str]`, `Dict[str, int]`
- Use `X | Y` instead of `Union[X, Y]`
- Use `X | None` instead of `Optional[X]`

However, `from __future__ import annotations` is sometimes still needed for:

- Forward references (referring to classes not yet defined)
- Circular type imports
- Complex recursive types

## Migrating to 3.10

If upgrading from 3.9:

- Replace `List[X]` with `list[X]`
- Replace `Dict[K, V]` with `dict[K, V]`
- Replace `Set[X]` with `set[X]`
- Replace `Tuple[X, Y]` with `tuple[X, Y]`
- Replace `Union[X, Y]` with `X | Y`
- Replace `Optional[X]` with `X | None`
- Consider adding `from __future__ import annotations` if needed

## References

- [PEP 604: Union Types](https://peps.python.org/pep-0604/)
- [PEP 585: Standard Collections](https://peps.python.org/pep-0585/)
- [Python 3.10 What's New](https://docs.python.org/3.10/whatsnew/3.10.html)
