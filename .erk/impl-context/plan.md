# Add Short Names to Testing Layers

## Context

The 5-layer testing architecture uses numbered layers (Layer 1-5) that are hard to remember. Adding short, memorable names makes it easier to refer to layers in conversation and code reviews.

## Short Names

| Layer | Long Name | Short Name | Mnemonic |
|-------|-----------|------------|----------|
| 1 | Fake Infrastructure Tests | **fake-check** | Checking the fakes work |
| 2 | Integration Sanity Tests | **real-sanity** | Sanity-checking the reals |
| 3 | Pure Unit Tests | **pure** | Pure functions, zero deps |
| 4 | Business Logic Tests | **logic** | The main logic tests |
| 5 | Business Logic Integration Tests | **smoke** | Smoke tests over real system |

## Approach

Add the short name in parentheses after the layer number everywhere layers are referenced. Pattern: `Layer N "short-name": Long Name`. This preserves the existing numbered scheme while adding the memorable alias.

Example: `Layer 4 "logic": Business Logic Tests (70%)`

## Files to Modify

### Skill files (primary — all references live here)

1. **`SKILL.md`** — Main overview diagrams, layer descriptions, selection guide (~21 references)
2. **`references/testing-strategy.md`** — Most comprehensive layer guide (~51 references)
3. **`references/quick-reference.md`** — Quick lookup tables and decision trees (~22 references)
4. **`references/workflows.md`** — Inline layer references in step-by-step guides (~2 references)
5. **`references/anti-patterns.md`** — Single Layer 5 reference (~1 reference)

### docs/learned files (secondary — only those referencing testing layers specifically)

These files use "Layer N" for *other* architectural concepts (defense-in-depth, parameter threading, etc.) and should NOT be changed. Only update files that explicitly reference the fake-driven-testing layer names:

6. **`docs/learned/testing/cli-testing.md`** — References Layer 4
7. **`docs/learned/testing/hook-testing.md`** — References Layer 3 and Layer 4

## Edit Pattern

For ASCII diagrams:
```
│  Layer 5 "smoke": Integration Tests (5%)     │
│  Layer 4 "logic": Business Logic Tests (70%)  │
│  Layer 3 "pure": Pure Unit Tests (10%)        │
│  Layer 2 "real-sanity": Sanity Tests (10%)    │
│  Layer 1 "fake-check": Fake Tests (5%)        │
```

For section headers:
```
## Layer 1 "fake-check": Unit Tests of Fakes
```

For inline references:
```
→ Layer 4 "logic" (tests over fakes)
```

For parenthetical mentions:
```
use Layer 3 "pure" for utilities
```

## Verification

1. Read each modified file to confirm short names appear consistently
2. Grep for bare "Layer [1-5]" references to ensure none were missed in the skill files
3. Confirm docs/learned files that use "Layer N" for non-testing concepts are untouched
