---
title: Language Scope Auditing
read_when:
  - writing documentation that includes code examples
  - reviewing learned-docs for verbatim code violations
  - understanding what code blocks are forbidden in docs/learned/
---

# Language Scope Auditing

The learned-docs skill expanded from prohibiting "no Python code" to "no code from any language" in its verbatim copy rules. This document captures the audit checklist for detecting verbatim source copies across all programming languages used in the erk codebase.

## Scope Evolution

**Original rule** (before expansion):

- Prohibit verbatim Python code copied from `src/erk/` or `packages/`

**Expanded rule** (current):

- Prohibit verbatim code from **any language** copied from source files
- Applies to: Python, TypeScript, JavaScript, Bash, SQL, and any other language

**Rationale**: Stale code blocks are silent bugs regardless of language. The staleness problem isn't Python-specific—TypeScript interfaces, JavaScript React components, and Bash script excerpts all go stale when source changes.

## Audit Checklist

When reviewing documentation in `docs/learned/` for verbatim copies, check for these patterns:

### 1. Python Code

**Patterns to detect:**

- `class ClassName:`
- `def function_name(`
- `from erk` or `import erk`
- Type definitions (`TypedDict`, `@dataclass`)
- Method implementations (5+ lines)

**Example violation:**

```python
@dataclass(frozen=True)
class PlanState:
    status: str
    issue_number: int
    # ... 10 more lines copied from source
```

**Fix**: Replace with source pointer to actual class definition.

### 2. TypeScript Code

**Patterns to detect:**

- `interface InterfaceName {`
- `type TypeName =`
- `class ComponentName extends`
- `export function`
- React component definitions (5+ lines)

**Example violation:**

```typescript
interface PlanRow {
  issue_number: number;
  status: string;
  run_status: string | null;
  // ... 8 more lines copied from source
}
```

**Fix**: Replace with source pointer to interface definition.

### 3. JavaScript Code

**Patterns to detect:**

- Function definitions (`function foo()`, `const foo = ()`)
- React component implementations
- Event handlers with business logic
- State management patterns (5+ lines)

**Example violation:**

```javascript
const handleStatusChange = (newStatus) => {
  setPlanStatus(newStatus);
  updateBackend(planId, newStatus);
  // ... 6 more lines copied from source
};
```

**Fix**: Replace with source pointer to handler implementation.

### 4. Class Methods Across Languages

**Patterns to detect:**

- Method bodies (5+ lines) from any class
- Constructor implementations
- Lifecycle methods (React, Vue, Angular)

**Example violation:**

```typescript
async componentDidMount() {
  const plans = await fetchPlans();
  this.setState({ plans, loading: false });
  // ... 8 more lines copied from source
}
```

**Fix**: Replace with source pointer to component file.

### 5. Mock Implementations

**Patterns to detect:**

- Fake/mock class implementations copied from test fixtures
- Test helper functions (5+ lines)
- Stub data structures

**Example violation:**

```python
class FakeGitHub:
    def resolve_thread(self, thread_id: str) -> bool:
        if thread_id in self.resolve_failures:
            return False
        # ... 10 more lines copied from fake gateway
```

**Fix**: Replace with source pointer to fake implementation.

### 6. Function Definitions (5+ lines)

**Any language**, if the function body exceeds 5 lines and copies from source:

- Python functions
- TypeScript functions
- JavaScript functions
- Bash functions

**Fix**: Replace with source pointer, or extract key insight into ≤5 line snippet.

## Detection Process

The `.github/reviews/learned-docs.md` review automates Python detection. For other languages, manual review or expansion of the review script is needed.

### Current Automated Detection

<!-- Source: .github/reviews/learned-docs.md:20-69 -->

See `.github/reviews/learned-docs.md:20-69` for the current detection logic:

- Python: Fully automated (class/function extraction, source matching)
- Other languages: Not yet automated

### Manual Audit Process

For non-Python code blocks:

1. **Extract language tag** from fenced code block (`typescript, `javascript, ```bash)
2. **Identify definitions** (interface, type, class, function)
3. **Search source** for matching definition names
4. **Compare content** (3+ consecutive matching lines = verbatim copy)
5. **Suggest source pointer** if verbatim copy detected

## Related Documentation

- [stale-code-blocks-are-silent-bugs.md](stale-code-blocks-are-silent-bugs.md) - Why verbatim code is problematic
- [source-pointers.md](source-pointers.md) - How to replace verbatim code with pointers
- `.github/reviews/learned-docs.md` - Automated detection for Python code
