# Plan: Soften ABC vs Protocol Guidance in Dignified Python

## Summary

Update the `dignified-python` skill to replace the absolute "NEVER use Protocol" rule with nuanced guidance that recommends:
- **ABCs** for internal interfaces where you control implementations and want strict enforcement
- **Protocols** for third-party library boundaries and loose coupling at system edges

## Research Findings

### Official Python Position

**[PEP 544 – Protocols: Structural subtyping](https://peps.python.org/pep-0544/)** explicitly states that Protocols are meant to **complement**, not replace, ABCs:

> "We do not propose to replace the nominal subtyping described by PEP 484 with structural subtyping completely. Instead, protocol classes... complement normal classes."

The **[Python typing specification](https://typing.python.org/en/latest/spec/protocol.html)** goes further:

> "We still slightly prefer nominal subtyping over structural subtyping in the static typing world."

And recommends: **"As a rule of thumb, we recommend using nominal classes where possible, and protocols where necessary."**

### Key Conceptual Distinction

From **[Justin Ellis's analysis](https://jellis18.github.io/post/2022-01-11-abc-vs-protocol/)**:

- **ABCs "belong to their subclasses"** - part of a strict class hierarchy, explicit opt-in
- **Protocols "belong where they are used"** - structural matching, no inheritance required

This maps to **ownership and coupling**:
- Use ABC when you own all implementations (internal code)
- Use Protocol when you don't control the code (third-party libraries)

### Third-Party Library Use Case

Multiple sources emphasize Protocols for external boundaries:

From **[Oleg Sinavski](https://sinavski.com/post/1_abc_vs_protocols/)**:
> "This allows you to make an interface for the code you don't control and loosen the dependencies between modules in your codebase."

From the **[mypy documentation](https://mypy.readthedocs.io/en/stable/protocols.html)**:
> "By allowing unrelated classes to satisfy a protocol without inheritance, protocols reduce coupling."

Ellis specifically recommends: **"Use Protocols for abstract interfaces for 3rd party libraries."**

### Runtime Validation Differences

A critical distinction from **[PEP 544](https://peps.python.org/pep-0544/)**:

> "isinstance() with protocols is not completely safe at runtime. For example, signatures of methods are not checked. The runtime implementation only checks that all protocol members exist, not that they have the correct type."

This means **ABCs are preferred for plugin systems** where you need reliable `isinstance()` checks.

### When ABCs Are Better

From multiple sources:
- **Code reuse**: ABCs can have concrete method implementations; Protocols should not
- **Runtime enforcement**: ABCs raise errors at instantiation if abstract methods aren't implemented
- **Complex interfaces**: "Use ABCs if you will need several implementations of a class with several methods"
- **Plugin discovery**: When you need `__subclasses__()` or MRO-based discovery

### When Protocols Are Better

- **Third-party facades**: Define what you need without forcing inheritance
- **Minimal contracts**: When you only need 1-2 methods (less boilerplate)
- **Duck typing alignment**: "Given Python's emphasis on duck typing... it makes sense to opt for Protocol"
- **Multiple inheritance**: Protocols don't impose limitations on inheritance hierarchies

### Fluent Python (Canonical Reference)

**[Fluent Python, 2nd Edition](https://www.oreilly.com/library/view/fluent-python-2nd/9781492056348/ch13.html)** by Luciano Ramalho dedicates Chapter 13 to "Interfaces, Protocols, and ABCs" - treating both as complementary tools with different use cases, not as competing alternatives.

### Community Consensus Summary

| Use Case | Recommended | Source |
|----------|-------------|--------|
| Internal interfaces you control | ABC | PEP 544, typing spec |
| Third-party library facades | Protocol | Ellis, Sinavski, mypy docs |
| Plugin systems with isinstance() | ABC | PEP 544 (runtime limitations) |
| Minimal contracts (1-2 methods) | Protocol | Multiple sources |
| Code reuse via inheritance | ABC | Ellis |
| Loose coupling at boundaries | Protocol | Sinavski, mypy docs |

### Key Sources

- [PEP 544 – Protocols: Structural subtyping](https://peps.python.org/pep-0544/)
- [Python typing spec: Protocols](https://typing.python.org/en/latest/spec/protocol.html)
- [mypy: Protocols and structural subtyping](https://mypy.readthedocs.io/en/stable/protocols.html)
- [Justin Ellis: ABC vs Protocol](https://jellis18.github.io/post/2022-01-11-abc-vs-protocol/)
- [Oleg Sinavski: Interfaces: abc vs. Protocols](https://sinavski.com/post/1_abc_vs_protocols/)
- [Fluent Python 2nd Ed, Ch 13](https://www.oreilly.com/library/view/fluent-python-2nd/9781492056348/ch13.html)

---

## Files to Modify

**Primary file:**
- `/Users/schrockn/code/erk/.claude/skills/dignified-python/dignified-python-core.md`

## Changes

### 1. Replace Absolute Rule (lines 519-525)

**From:**
```markdown
## Dependency Injection

### Core Rule

**Use ABC for interfaces, NEVER Protocol**
```

**To:**
```markdown
## Dependency Injection

### ABC vs Protocol: Choosing the Right Interface

**ABCs (nominal typing)** and **Protocols (structural typing)** serve different purposes. Choose based on ownership and coupling needs.

| Use Case | Recommended | Why |
|----------|-------------|-----|
| Internal interfaces you control | ABC | Explicit enforcement, runtime validation, code reuse |
| Third-party library boundaries | Protocol | No inheritance required, loose coupling |
| Plugin systems with isinstance checks | ABC | Reliable runtime type validation |
| Minimal interface contracts (1-2 methods) | Protocol | Less boilerplate, focused contracts |

**Default for erk internal code: ABC. Default for external library facades: Protocol.**
```

### 2. Remove "WRONG" Label from Protocol Example (lines 551-557)

**From:**
```python
# ❌ WRONG: Using Protocol
from typing import Protocol

class Repository(Protocol):
    def save(self, entity: Entity) -> None: ...
    def load(self, id: str) -> Entity: ...
```

**To:** Delete this block entirely (it will be replaced by a proper "When to Use Protocol" section).

### 3. Add "When to Use Protocol" Section

Insert after the ABC example (after line ~618):

```markdown
### When to Use Protocol

**Protocols excel at defining interfaces for code you don't control:**

```python
# ✅ CORRECT: Protocol for third-party library facade
from typing import Protocol

class HttpClient(Protocol):
    """Interface for HTTP operations - decouples from requests/httpx/aiohttp."""
    def get(self, url: str) -> Response: ...
    def post(self, url: str, data: dict) -> Response: ...

# Any HTTP library that has these methods works - no inheritance needed
def fetch_data(client: HttpClient, endpoint: str) -> dict:
    response = client.get(endpoint)
    return response.json()
```

**Protocols are also appropriate for minimal, focused interfaces:**

```python
# ✅ CORRECT: Protocol for structural typing with minimal interface
from typing import Protocol

class Closeable(Protocol):
    def close(self) -> None: ...

def cleanup_resources(resources: list[Closeable]) -> None:
    for r in resources:
        r.close()
```

### Protocol Limitations

1. **No runtime validation** - `@runtime_checkable` only checks method existence, not signatures
2. **No code reuse** - Protocols shouldn't have method implementations
3. **Weaker isinstance() checks** - ABCs provide more reliable runtime type checking
```

### 4. Update Benefits Section (lines 559-567)

**From:**
```markdown
### Benefits of ABC

1. **Explicit inheritance** - Clear class hierarchy
2. **Runtime validation** - Errors if abstract methods not implemented
3. **Better IDE support** - Autocomplete and refactoring work better
4. **Documentation** - Clear contract definition
```

**To:**
```markdown
### Benefits of ABC (Internal Interfaces)

1. **Explicit inheritance** - Clear class hierarchy, explicit opt-in
2. **Runtime validation** - Errors at instantiation if abstract methods missing
3. **Code reuse** - Can include concrete methods and shared logic
4. **Reliable isinstance()** - Full signature checking at runtime

### Benefits of Protocol (External Boundaries)

1. **No inheritance required** - Works with code you don't control
2. **Loose coupling** - Implementations don't know about the protocol
3. **Minimal contracts** - Define only the methods you need
4. **Duck typing** - Aligns with Python's philosophy
```

### 5. Add Decision Checklist Item

Add to the Decision Checklist section (around line 1196):

```markdown
### Before defining an interface (ABC or Protocol):

- [ ] Do I own all implementations? → Prefer ABC
- [ ] Am I wrapping a third-party library? → Prefer Protocol
- [ ] Do I need runtime isinstance() validation? → Use ABC
- [ ] Is this a minimal interface (1-2 methods)? → Protocol may be simpler
- [ ] Do I need shared method implementations? → Use ABC

**Default for erk internal code: ABC. Default for external library facades: Protocol.**
```

## Verification

1. Read the modified file to ensure formatting is correct
2. Run `make fast-ci` to verify no syntax errors in markdown
3. Review that the guidance aligns with the erk codebase's existing patterns (ABC for gateways, etc.)