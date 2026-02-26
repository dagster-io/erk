# Plan: Migrate erkweb + erkdesk submit → dispatch (Phase 1 remainder)

**Part of Objective #8241, Nodes 1.2 + 1.3**

## Context

Objective #8241 migrates "submit" terminology to "dispatch" across the codebase. Node 1.1 (erkdesk ActionToolbar.tsx) is marked in-progress but has no PR. This plan covers the rest of Phase 1:

- **Node 1.2**: Update erkweb `plans.ts` route and `PlanDetail.tsx`
- **Node 1.3**: Update erkdesk/erkweb test assertions

Since node 1.1 has no PR and the test changes in 1.3 depend on the implementation changes in 1.1, this plan also includes the 1.1 erkdesk ActionToolbar.tsx changes to ship a complete, testable Phase 1 PR.

## Changes

### 1. erkdesk ActionToolbar.tsx (Node 1.1)

**File:** `erkdesk/src/renderer/components/ActionToolbar.tsx` (lines 20-25)

- `id: "submit_to_queue"` → `id: "dispatch_to_queue"`
- `label: "Submit"` → `label: "Dispatch"`
- `args: ["plan", "submit", ...]` → `args: ["pr", "dispatch", ...]`

### 2. erkweb plans.ts route (Node 1.2)

**File:** `erkweb/src/server/routes/plans.ts` (lines 214-219)

- Comment: `// Submit plan to queue` → `// Dispatch plan to queue`
- Route path: `/plans/:issueNumber/submit` → `/plans/:issueNumber/dispatch`
- CLI args: `['plan', 'submit', req.params.issueNumber, '-f']` → `['pr', 'dispatch', req.params.issueNumber, '-f']`

### 3. erkweb PlanDetail.tsx (Node 1.2)

**File:** `erkweb/src/client/components/PlanDetail.tsx` (lines 178-182)

- `label="Submit to Queue"` → `label="Dispatch"`
- `actionKey="submit"` → `actionKey="dispatch"`
- `status={actionStatuses['submit']}` → `status={actionStatuses['dispatch']}`
- `executeAction('submit')` → `executeAction('dispatch')`

### 4. erkdesk ActionToolbar.test.tsx (Node 1.3)

**File:** `erkdesk/src/renderer/components/ActionToolbar.test.tsx`

11 references to update:
- Button text assertions: `"Submit"` → `"Dispatch"` (lines 47, 91, 117, 125, 139, 148, 258)
- Running state text: `"Submit..."` → `"Dispatch..."` (line 241)
- Action ID: `"submit_to_queue"` → `"dispatch_to_queue"` (lines 150-153, 236)
- CLI args: `["plan", "submit", "100"]` → `["pr", "dispatch", "100"]` (line 153)

### 5. erkdesk App.test.tsx (Node 1.3)

**File:** `erkdesk/src/renderer/App.test.tsx`

7 references to update:
- Button text assertions: `"Submit"` → `"Dispatch"` (lines 94, 277, 281, 307, 311, 328)
- CLI args assertion: `["plan", "submit", "1"]` → `["pr", "dispatch", "1"]` (lines 283-287)

## Verification

1. Run erkdesk tests: `cd erkdesk && npm test`
2. Run erkweb build: `cd erkweb && npm run build` (no erkweb tests exist)
3. Verify no remaining "plan submit" references: `grep -r "plan.*submit\|Submit" erkweb/src erkdesk/src`
