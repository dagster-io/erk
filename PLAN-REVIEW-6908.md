# Plan: Add Action Buttons to erkweb PlanDetail Panel

## Context

The erkweb PlanDetail panel (right column) currently shows read-only metadata about a selected plan. There's no way to take action on a plan from the web UI. We want two action buttons:

- **"Address PR Feedback"** — starts a fresh Claude session scoped to the plan's worktree, running `/erk:pr-address`
- **"Continue Implementation"** — starts a fresh Claude session scoped to the plan's worktree, prompting Claude to read `.impl/progress.md` and continue

These create **fresh sessions** (not resume) because each workflow phase benefits from a clean context window. The worktree is the real continuity mechanism.

## Changes

### 1. Add `newSession` to WebSocket protocol

**File: `erkweb/src/shared/types.ts`**

- Add `newSession?: boolean` to the `chat_send` variant of `ClientMessage`
- Add `worktreesBasePath?: string` to `FetchPlansResult`

### 2. Handle `newSession` on server

**File: `erkweb/src/server/ws/chat.ts`**

In the `chat_send` handler (~line 88), when `msg.newSession` is true, pass `resume: undefined` instead of `resume: sessionId`. The server's `sessionId` will be updated automatically when the new session's `system/init` message arrives (line 167).

```typescript
const resumeId = msg.newSession ? undefined : (sessionId ?? undefined);
// ... pass resumeId as resume option
```

### 3. Return `worktreesBasePath` from plans API

**File: `erkweb/src/server/routes/plans.ts`**

Compute the worktrees base directory from `ERKWEB_CWD` or `process.cwd()` (both point to a worktree). The parent directory contains sibling worktrees per erk's `~/.erk/repos/<repo>/worktrees/<name>/` convention.

```typescript
import {resolve} from 'path';
const worktreesBasePath = resolve(process.env.ERKWEB_CWD || process.cwd(), '..');
```

Include `worktreesBasePath` in the success response.

### 4. Extend `useChat.sendMessage` with options

**File: `erkweb/src/client/hooks/useChat.ts`**

Change signature from `(text: string)` to `(text: string, options?: {cwd?: string; newSession?: boolean})`.

- Include `cwd` and `newSession` in the WebSocket JSON payload
- When `newSession` is true, clear `messages` state for a clean UI

### 5. Surface `worktreesBasePath` from `usePlans`

**File: `erkweb/src/client/hooks/usePlans.ts`**

Store `worktreesBasePath` from the fetch response and return it from the hook.

### 6. Add action buttons to PlanDetail

**File: `erkweb/src/client/components/PlanDetail.tsx`**

Add new props: `onAddressFeedback: () => void`, `onContinueImpl: () => void`, `isStreaming: boolean`.

Add a `detail-actions` section below `detail-content` with two buttons:
- **"Address PR Feedback"**: visible when `plan.pr_number !== null && plan.exists_locally`
- **"Continue Implementation"**: visible when `plan.exists_locally && plan.local_impl_display !== '-'`

Both disabled when `isStreaming` is true (prevent sending while a query is active).

**File: `erkweb/src/client/components/PlanDetail.css`**

Add styles for `.detail-actions`, `.detail-action-btn`, `.feedback-btn`, `.continue-btn` matching the existing dark theme with accent colors (blue for feedback, teal for continue).

### 7. Wire everything in App.tsx

**File: `erkweb/src/client/App.tsx`**

- Get `worktreesBasePath` from `usePlans()`
- Add `handlePlanAction(command)` that computes `cwd` as `${worktreesBasePath}/${selectedPlan.worktree_name}` and calls `chat.sendMessage(command, {cwd, newSession: true})`
- Pass `onAddressFeedback` (sends `/erk:pr-address`) and `onContinueImpl` (sends a prompt to read progress and continue) to `PlanDetail`
- Pass `chat.isStreaming` to `PlanDetail` to disable buttons during active queries

## Implementation Order

1. `erkweb/src/shared/types.ts` — type changes
2. `erkweb/src/server/ws/chat.ts` — `newSession` handling
3. `erkweb/src/server/routes/plans.ts` — `worktreesBasePath`
4. `erkweb/src/client/hooks/useChat.ts` — sendMessage options
5. `erkweb/src/client/hooks/usePlans.ts` — surface worktreesBasePath
6. `erkweb/src/client/components/PlanDetail.tsx` + `.css` — buttons UI
7. `erkweb/src/client/App.tsx` — wiring

## Verification

1. Start erkweb: `cd erkweb && yarn dev`
2. Select a plan with a PR and local worktree — both buttons should appear
3. Select a plan without a PR — only "Continue Implementation" should appear (if it has local impl)
4. Select a plan without a local worktree — no buttons should appear
5. Click "Address PR Feedback" — chat should clear, show the user message `/erk:pr-address`, and Claude should start in the worktree's cwd
6. Click "Continue Implementation" — chat should clear and Claude should start reading `.impl/progress.md`
7. While streaming, both buttons should be disabled