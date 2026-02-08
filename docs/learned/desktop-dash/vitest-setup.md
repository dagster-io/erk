---
title: Vitest Configuration for erkdesk
category: desktop-dash
read_when:
  - setting up or modifying test infrastructure for erkdesk
  - adding new tests to erkdesk
  - debugging erkdesk test failures related to environment or mocking
tripwires:
  - action: "configuring vitest globals for erkdesk"
    warning: 'globals and tsconfig types must stay in sync — `globals: true` in vitest.config.ts without `"vitest/globals"` in tsconfig.json causes type errors at edit time but tests still pass, creating a confusing split'
  - action: "adding new IPC methods to erkdesk"
    warning: "the window.erkdesk mock in setup.ts must match the ErkdeskAPI interface — adding a new IPC method requires updating both the type definition and the mock or TypeScript will catch the mismatch"
  - action: "running erkdesk tests in CI"
    warning: "erkdesk tests run separately from the Python suite — `make fast-ci` and `make all-ci` do NOT include them; use `make erkdesk-test`"
last_audited: "2026-02-08"
audit_result: clean
---

# Vitest Configuration for erkdesk

## Why Vitest Over Jest?

Erkdesk uses Vite as its build tool (via `@electron-forge/plugin-vite`), making Vitest the natural testing choice. The key decision driver: Vitest reuses Vite's transformation pipeline, so the test environment transforms code identically to the production build. This eliminates the class of bugs where tests pass but production breaks due to different transpilation — no need for a parallel Babel or ts-jest configuration.

## The Three-File Coordination Problem

Erkdesk's test infrastructure spans three files that must stay coordinated. The danger is partial changes — editing one without updating the others creates confusing failure modes.

<!-- Source: erkdesk/vitest.config.ts -->
<!-- Source: erkdesk/tsconfig.json, compilerOptions.types -->
<!-- Source: erkdesk/src/test/setup.ts -->

| File                        | Role                                                                   | What Breaks Without It                                                                    |
| --------------------------- | ---------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| `erkdesk/vitest.config.ts`  | Activates jsdom environment and global test APIs at runtime            | Component rendering fails — no DOM APIs available                                         |
| `erkdesk/tsconfig.json`     | Declares `"vitest/globals"` in the `types` array for TypeScript        | Editor shows `describe`/`it`/`expect`/`vi` as undefined even though tests pass at runtime |
| `erkdesk/src/test/setup.ts` | Bootstraps jest-dom matchers, jsdom API stubs, and the IPC bridge mock | Every test must individually stub missing jsdom APIs and mock `window.erkdesk`            |

**The coordination trap:** The `globals: true` setting (vitest.config.ts) and the `"vitest/globals"` type entry (tsconfig.json) solve different halves of the same problem — runtime availability vs. type awareness. Missing either one produces a state where tests either fail or have type errors, but not both, making it hard to diagnose.

## Why the window.erkdesk Mock Is Cross-Cutting

<!-- Source: erkdesk/src/test/setup.ts, mockErkdesk -->
<!-- Source: erkdesk/src/types/erkdesk.d.ts, ErkdeskAPI -->

The setup file creates a typed global mock of `window.erkdesk`. This matters as a cross-cutting concern because:

1. **Universal dependency** — every renderer component communicates with the main process exclusively through `window.erkdesk` (the preload bridge), so no component test can render without it
2. **Type-enforced contract** — the mock is typed against the `ErkdeskAPI` interface, so adding a new IPC method to the interface forces the mock to be updated at compile time
3. **Default-safe, override-friendly** — the global mock provides safe defaults (empty plans, successful actions) that individual tests can selectively override

See [Window Mock Patterns](../testing/window-mock-patterns.md) for the discipline around per-test overrides vs global defaults.

## CI Isolation

Erkdesk tests are **not** part of `make fast-ci` or `make all-ci`. They run via `make erkdesk-test` (or `pnpm test` from `erkdesk/`). This separation exists because the erkdesk test runner (Vitest + jsdom) is entirely independent of pytest — different runtime, different dependency tree, different failure modes. Forgetting this means erkdesk regressions go undetected during normal CI iteration.

## Test Colocation

Tests live next to their source files (`ComponentName.test.tsx` alongside `ComponentName.tsx`), not in a separate `tests/` directory. This means deleting a component automatically deletes its tests, and no directory mapping is needed to locate tests.

## Related

- [jsdom DOM API Stubs](../testing/vitest-jsdom-stubs.md) — why jsdom needs runtime stubs and which APIs are missing
- [Window Mock Patterns](../testing/window-mock-patterns.md) — discipline for overriding the global IPC mock
- [Erkdesk Component Testing Patterns](../testing/erkdesk-component-testing.md) — rendering, async state, user interaction
- [Makefile Testing Targets](../cli/erkdesk-makefile-targets.md) — CI integration and make targets
