---
title: Gateway vs Backend ABC Pattern
read_when:
  - "creating a new ABC interface"
  - "deciding between gateway and backend patterns"
  - "understanding PlanBackend vs Git gateway architecture"
  - "choosing the right abstraction pattern for a new service"
tripwires:
  - action: "creating a new ABC without deciding gateway vs backend pattern"
    warning: "Read gateway-vs-backend.md first. Gateways wrap external tools (4-place: abc, real, fake, dry_run). Backends abstract business logic (3-place: abc, real, fake). Wrong choice creates unnecessary boilerplate or missing test support."
  - action: "constructing PlannedPRBackend with positional arguments or wrong parameter order"
    warning: "PlannedPRBackend constructor takes keyword-only gateway dependencies. Check the current __init__ signature — it evolves as gateways are added. Use keyword arguments explicitly."
last_audited: "2026-02-17 00:00 PT"
audit_result: clean
---

# Gateway vs Backend ABC Pattern

Erk uses two distinct ABC patterns for dependency injection. Choosing the wrong one creates unnecessary boilerplate (gateway for business logic) or missing dry-run support (backend for external tools).

## Gateway ABCs: External System Wrappers

Gateways wrap external tools and system calls (subprocess, CLI, HTTP). They follow a **4-place implementation pattern**:

| Place        | Purpose                                 | Example File             |
| ------------ | --------------------------------------- | ------------------------ |
| `abc.py`     | Abstract interface definition           | `gateway/git/abc.py`     |
| `real.py`    | Production implementation (subprocess)  | `gateway/git/real.py`    |
| `fake.py`    | In-memory test double with shared state | `gateway/git/fake.py`    |
| `dry_run.py` | Records operations without side effects | `gateway/git/dry_run.py` |

**Key characteristics:**

- Wrap subprocess calls, CLI tools, or HTTP APIs
- `dry_run.py` enables `--dry-run` flags without conditional logic
- Fake implementations share mutable state containers for cross-gateway assertions
- Error handling uses discriminated unions (not exceptions) in the ABC

**Example:** `Git` at `packages/erk-shared/src/erk_shared/gateway/git/abc.py` — wraps git subprocess calls with subgateways for branch_ops, commit_ops, remote_ops, etc.

**See:** [Gateway ABC Implementation Checklist](gateway-abc-implementation.md) for the full 4-place implementation guide.

## Backend ABCs: Business Logic Abstractions

Backends abstract over business logic that may have multiple storage or provider implementations. They follow a **3-place pattern**:

| Place        | Purpose                                          | Example File                       |
| ------------ | ------------------------------------------------ | ---------------------------------- |
| `backend.py` | Abstract interface definition                    | `plan_store/backend.py`            |
| `github.py`  | Provider-specific implementation                 | `plan_store/github.py`             |
| `fake_*.py`  | Fake for testing ABC design (validates contract) | _(add when second backend exists)_ |

**Key characteristics:**

- No `dry_run.py` — business logic doesn't need this
- Compose gateways internally (e.g., `PlannedPRBackend` composes `GitHub` gateway)
- To test code that uses a backend, inject fake **gateways** into the **real** backend
- Fake backends exist only to validate the ABC contract works across different providers

**Example:** `PlanBackend` at `packages/erk-shared/src/erk_shared/plan_store/backend.py` — abstracts plan CRUD with `PlannedPRBackend` implementation backed by `GitHub` gateway.

**Testing pattern:** See [Backend Testing Composition](../testing/backend-testing-composition.md) for the full pattern (real backend + fake gateways).

## Decision Guide

| Question                                         | Gateway | Backend |
| ------------------------------------------------ | ------- | ------- |
| Does it wrap subprocess/CLI/HTTP calls?          | Yes     | No      |
| Does it need `--dry-run` support?                | Yes     | No      |
| Does it compose other gateways?                  | No      | Yes     |
| Should tests use fake gateways inside real impl? | No      | Yes     |
| Does it need 4-place implementation?             | Yes     | No      |

**When uncertain:** If the code calls subprocess or external APIs directly, it's a gateway. If it orchestrates gateway calls to implement business rules, it's a backend.

## Related Documentation

- [Gateway ABC Implementation Checklist](gateway-abc-implementation.md) — 4-place implementation pattern
- [Gateway Hierarchy](gateway-hierarchy.md) — Relationships between gateways
- [Gateway Inventory](gateway-inventory.md) — Complete list of available gateways
