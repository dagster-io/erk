# Context Preservation Examples

This document demonstrates the difference between poor and excellent context preservation in implementation plans. Good context helps implementing agents avoid costly re-discovery and prevents subtle bugs.

## What Makes Good Context?

Context should be preserved when it meets ANY of these criteria:

- **Took time to discover** during planning (non-obvious from code)
- **Would change implementation** if known vs. unknown
- **Would cause bugs if missed** (especially subtle or delayed bugs)
- **Not obvious from reading the code** (requires domain knowledge or experience)

## Poor vs. Excellent Context: Complete Examples

### Example 1: API Integration with Stripe Webhooks

#### Poor Context (Missing Critical Discoveries)

```markdown
## Implementation Plan: Add Stripe Payment Processing

### Objective

Integrate Stripe payment processing for subscription management.

### Implementation Steps

1. **Add Stripe SDK**: Install stripe-python package
   - Success: Package installed and importable

2. **Create payment endpoint**: Add POST /api/payments endpoint
   - Success: Endpoint returns 200 OK

3. **Add webhook handler**: Create POST /api/webhooks/stripe endpoint
   - Success: Webhook receives events

4. **Update database schema**: Add payment_status column
   - Success: Migration runs successfully
```

**Problems:**

- No mention of webhook timing race conditions
- Missing signature verification security requirement
- No guidance on idempotency handling
- Doesn't explain why certain approaches won't work

#### Excellent Context (Comprehensive Discovery Documentation)

```markdown
## Implementation Plan: Add Stripe Payment Processing

### Objective

Integrate Stripe payment processing for subscription management with proper webhook handling and race condition mitigation.

### Context & Understanding

#### API/Tool Quirks

- **Webhook Timing Race**: Stripe webhooks often arrive BEFORE the API response returns to the client. The webhook handler must handle "payment not found" gracefully rather than treating it as an error.
- **Signature Verification**: Stripe signatures use HMAC SHA256 with the raw request body. Reading the body for JSON parsing invalidates the signature check. Must verify BEFORE any body parsing.
- **Test Clock Limitations**: Stripe test clocks can't simulate webhook delays. Race conditions only appear in production or with manual webhook forwarding.

#### Architectural Insights

- Webhook handlers MUST be idempotent. Stripe retries failed webhooks with exponential backoff for up to 3 days.
- Payment status transitions should use a state machine pattern rather than boolean flags to prevent invalid state combinations.
- Database transactions must be scoped per-webhook-event, not per-API-call, to prevent partial updates on retries.

#### Domain Logic & Business Rules

- Subscription payments require 2-phase commit: create pending payment record synchronously, update to completed/failed asynchronously via webhook.
- Failed payments must trigger grace period logic (7 days) before service suspension, not immediate cutoff.
- Tax calculation must happen before payment intent creation to ensure correct charge amounts.

#### Complex Reasoning

- **Rejected**: Synchronous payment confirmation (waiting for webhook in API call)
  - Reason: Webhooks can take 1-30 seconds; creates timeout issues
  - Also: Connection failures would lose webhook delivery entirely
- **Rejected**: Polling payment status after intent creation
  - Reason: Race conditions if webhook arrives during polling interval
  - Introduces unnecessary API calls and complexity
- **Chosen**: Async webhook-driven flow with optimistic UI updates
  - Handles timing correctly regardless of webhook delay
  - Natural retry semantics via Stripe's webhook system

#### Known Pitfalls

- **DO NOT** use `payment_intent.succeeded` event alone - it fires even for zero-amount test payments. Use `payment_intent.amount > 0` check.
- **DO NOT** store Stripe objects directly in database - they change schema across API versions. Extract only needed fields.
- **DO NOT** assume webhook delivery order - `charge.succeeded` might arrive before `payment_intent.succeeded`. Use event timestamp for ordering.

### Implementation Steps

1. **Add Stripe SDK with security configuration**: Install stripe-python and configure API keys
   [CRITICAL: Must use restricted API keys with minimum required permissions, never full access keys]
   - Success: Package installed, keys configured in environment variables
   - On failure: Check Stripe dashboard for key restrictions

   Related Context:
   - Stripe SDK must be pinned to major version to prevent breaking changes in serialization
   - Use webhook signing secret from webhook settings page, not general API secret

2. **Create payment intent endpoint with 2-phase commit**: Add POST /api/payments/intents endpoint
   [CRITICAL: Must create database record BEFORE Stripe API call to handle webhook race]
   - Create payment record in "pending" state with idempotency key
   - Call stripe.PaymentIntent.create with metadata linking to record
   - Return client_secret for frontend processing
   - Success: Endpoint creates payment records and returns valid client_secret
   - On failure: Check idempotency key handling prevents duplicates

   Related Context:
   - Database record created first ensures webhook handler can find it
   - Idempotency key prevents duplicate charges if client retries
   - Metadata links Stripe object to local record for webhook matching

3. **Add webhook handler with signature verification**: Create POST /api/webhooks/stripe endpoint
   [CRITICAL: Verify signature BEFORE parsing JSON. Must use raw request body.]
   - Extract Stripe-Signature header
   - Verify signature using webhook signing secret and raw body
   - Parse event only after verification succeeds
   - Handle payment_intent.succeeded, payment_intent.failed, charge.refunded events
   - Update database with idempotent logic (check existing state before transition)
   - Success: Webhook processes events and updates payment status correctly
   - On failure: Check signature verification isn't using parsed body

   Related Context:
   - Signature verification must happen before body read to prevent replay attacks
   - Idempotent handling essential because Stripe retries failed webhooks
   - Grace period for "not found" allows race condition where webhook arrives first

4. **Implement payment state machine**: Add state transition validation to Payment model
   - Define valid state transitions (pending → succeeded/failed, succeeded → refunded)
   - Reject invalid transitions with clear error messages
   - Success: State machine prevents invalid transitions, logs transition history
   - On failure: Check transition validation doesn't block legitimate retries

   Related Context:
   - State machine prevents webhook retry bugs (e.g., succeeded → pending)
   - Audit log of transitions aids debugging production payment issues

5. **Add webhook event deduplication**: Create webhook_events table for tracking processed events
   - Store event ID, type, processed timestamp
   - Check for duplicate event IDs before processing
   - Success: Duplicate webhooks are safely ignored
   - On failure: Verify database unique constraint on event_id

   Related Context:
   - Stripe doesn't guarantee exactly-once delivery
   - Deduplication prevents double-processing during Stripe retry storms

### Success Criteria

- Payment intents can be created and return valid client_secret
- Webhooks successfully update payment status for succeeded/failed events
- Webhook signature verification rejects tampered or replayed events
- System handles race condition where webhook arrives before API response
- Duplicate webhook deliveries don't cause double-processing
- All state transitions follow state machine rules
- Failed payments trigger grace period, not immediate service cutoff

### Testing Approach

- Test race condition: manually trigger webhook before API call completes
- Test duplicate webhooks: send same event ID twice, verify second is ignored
- Test invalid transitions: attempt to transition succeeded payment to pending
- Test signature verification: send webhook with invalid signature, verify rejection
- Verify idempotency: create payment intent with same idempotency key twice
```

**What makes this excellent:**

- Documents discovered race conditions (webhook timing)
- Explains rejected approaches and why they don't work
- Links critical warnings directly to steps using `[CRITICAL:]` tags
- Provides detailed context in subsections without cluttering steps
- Includes specific gotchas that would cause subtle bugs
- Shows reasoning chain for architectural decisions

---

### Example 2: Database Migration with Foreign Key Dependencies

#### Poor Context (Missing Dependency Analysis)

```markdown
## Implementation Plan: Refactor User Permissions System

### Objective

Migrate from role-based to permission-based access control.

### Implementation Steps

1. **Create permissions table**: Add new permissions table with migration
   - Success: Table created

2. **Create user_permissions junction table**: Link users to permissions
   - Success: Table created

3. **Migrate existing roles to permissions**: Copy role data to new structure
   - Success: Data migrated

4. **Drop old roles table**: Remove deprecated table
   - Success: Table removed
```

**Problems:**

- Doesn't explain foreign key dependency order
- Missing rollback strategy
- No mention of production data considerations
- Doesn't document discovered constraints

#### Excellent Context (Detailed Dependency and Migration Logic)

```markdown
## Implementation Plan: Refactor User Permissions System

### Objective

Migrate from role-based to permission-based access control with zero-downtime deployment and safe rollback capability.

### Context & Understanding

#### API/Tool Quirks

- **PostgreSQL Foreign Key Ordering**: Foreign keys must be created in dependency order. Creating child table before parent fails with "relation does not exist" even in same migration.
- **Django Migration Dependencies**: Migrations run in file order within app, but cross-app dependencies require explicit `dependencies = [('app', 'migration')]` declaration.
- **SQLite Limitations**: SQLite doesn't support DROP COLUMN in older versions. Migration must check database backend.

#### Architectural Insights

- Zero-downtime deployment requires 4-phase migration: add new tables, dual-write, migrate data, remove old tables. Cannot do in single deployment.
- Rollback safety requires keeping old tables populated until new system is verified in production. Drop tables in separate migration after monitoring period.
- Permission checking logic must support both systems during transition to allow gradual rollout and fast rollback.

#### Domain Logic & Business Rules

- **Critical Permission Preservation**: Admin users must retain all permissions during migration. Partial permission loss creates security incidents.
- **Audit Trail Requirement**: Permission changes must be logged with timestamp and reason. Migration must preserve existing audit records and format.
- **Default Permissions**: New users during migration must get default permission set, not empty permissions (fails-closed security).

#### Complex Reasoning

- **Rejected**: One-step migration (drop old, create new, migrate data)
  - Reason: Requires downtime. Any migration failure leaves system unusable.
  - Rollback would require restoring database backup, losing interim data.
- **Rejected**: Application-level dual-write (write to both systems)
  - Reason: Race conditions if migration runs mid-request. Transactions don't span old/new models.
  - Complicated rollback: which system is source of truth?
- **Chosen**: Database-level triggers for dual-write during migration
  - Ensures consistency without application code changes
  - Can be enabled/disabled per-table for gradual migration
  - Clean rollback: disable triggers, continue using old tables

#### Known Pitfalls

- **DO NOT** migrate superuser permissions first - if migration fails, you've locked out recovery access. Migrate regular users first, superusers last.
- **DO NOT** assume role-to-permission mapping is 1:1. Some roles grant permissions conditionally based on user attributes (e.g., "manager of own department"). These require custom migration logic.
- **DO NOT** delete role definitions immediately after migration. Frontend and API docs reference role names. Need coordinated update.
- **DO NOT** use Django's `bulk_create` for permission migration - it bypasses signals needed for audit logging. Use `save()` loop despite performance cost.

### Implementation Steps

1. **Create permissions table with enum types**: Add migration 0001_create_permissions.py
   [CRITICAL: Must create enum types BEFORE table that uses them in PostgreSQL]
   - Define permission_type enum (read, write, delete, admin)
   - Create permissions table with columns: id, name, permission_type, resource_type, description
   - Add unique constraint on (name, resource_type) to prevent duplicates
   - Success: Migration runs, table exists, enum types created
   - On failure: Check enum type creation runs before CREATE TABLE

   Related Context:
   - Enum types are database-level objects in PostgreSQL, must exist before table creation
   - Unique constraint prevents duplicate permission definitions that would cause ambiguity

2. **Create user_permissions junction table with proper foreign keys**: Add migration 0002_create_user_permissions.py
   [CRITICAL: Foreign key to permissions table requires permissions migration to run first]
   - Create user_permissions table with user_id, permission_id, granted_at, granted_by
   - Add foreign key constraints with ON DELETE CASCADE
   - Add composite unique constraint on (user_id, permission_id)
   - Create indexes on foreign key columns for query performance
   - Success: Table created, foreign keys enforced, indexes exist
   - On failure: Verify migration dependency on 0001_create_permissions

   Related Context:
   - ON DELETE CASCADE ensures orphaned permissions are cleaned up if permission definitions change
   - Composite unique constraint prevents duplicate permission grants
   - Index on foreign keys critical for permission checking queries (run on every request)

3. **Define role-to-permission mapping**: Create permissions/mapping.py with mapping logic
   - Define ROLE_PERMISSION_MAP dictionary mapping old roles to new permission sets
   - Include special case handlers for conditional permissions
   - Document any roles that can't be directly mapped
   - Success: Mapping covers all existing roles, special cases documented
   - On failure: Check for roles without mappings, verify special case logic

   Related Context:
   - Mapping must be in code (not migration) so it can be tested independently
   - Special cases like "department manager" require checking user.department field
   - Some composite roles may map to multiple permission combinations

4. **Add dual-write database triggers**: Add migration 0003_add_dual_write_triggers.py
   [CRITICAL: Triggers must be idempotent - safe to apply if already exist]
   - Create trigger on role_assignments insert → insert to user_permissions
   - Create trigger on role_assignments delete → delete from user_permissions
   - Make triggers conditional: only fire if new system enabled (check feature flag)
   - Success: Triggers installed, dual-write verified in test database
   - On failure: Check trigger syntax for database backend (PostgreSQL vs MySQL)

   Related Context:
   - Triggers ensure consistency during migration without application changes
   - Feature flag allows enabling dual-write without deploying code changes
   - Idempotent design allows re-running migration if initial attempt fails

5. **Migrate existing role assignments to permissions**: Add management command migrate_permissions
   [CRITICAL: Process users in batches to avoid memory exhaustion on large datasets]
   - Fetch users in batches of 1000 using iterator()
   - For each user, lookup roles and map to permissions using mapping.py
   - Use transaction per batch for rollback capability
   - Log migration progress and any unmappable roles
   - Use .save() not .bulk_create() to trigger audit logging
   - Success: All users migrated, audit trail created, no unmappable roles
   - On failure: Check batch size, verify mapping covers all roles, review logs for errors

   Related Context:
   - Batch processing prevents OOM on databases with millions of users
   - Per-batch transactions allow partial progress if migration interrupted
   - Audit logging required for compliance, even though it slows migration

6. **Deploy application code with dual-read logic**: Update permission checking to try new system first, fallback to old
   - Modify has_permission() to check user_permissions table
   - Add fallback to role_assignments if permission not found
   - Add logging to track which system answered each check
   - Success: Permission checks work with both systems, logs show distribution
   - On failure: Check fallback logic doesn't bypass security checks

   Related Context:
   - Dual-read allows gradual rollout per user or per feature
   - Logging provides confidence new system is working before removing old
   - Fallback ensures safety if migration missed edge cases

7. **Monitoring and verification period**: Monitor permission check logs for 1 week
   - Verify new system handles all checks correctly
   - Compare permission grant rates between systems for anomalies
   - Check for any permission denials that old system would have allowed
   - Success: No permission discrepancies, new system handles 100% of checks
   - On failure: Investigate discrepancies, fix mapping, re-run migration

   Related Context:
   - Week-long period chosen based on typical feature usage cycle
   - Discrepancies might indicate unmapped roles or incorrect mapping logic

8. **Remove old roles table and cleanup**: Add migration 0004_drop_old_roles.py
   [CRITICAL: Only run after verification period. Irreversible data loss.]
   - Drop triggers from step 4
   - Drop role_assignments table
   - Drop roles table
   - Remove fallback logic from has_permission()
   - Success: Old tables removed, application uses only new system
   - On failure: DO NOT proceed if any verification issues remain

   Related Context:
   - Delayed drop provides rollback window if production issues discovered
   - Removing fallback simplifies code and eliminates maintenance burden

### Success Criteria

- All users have equivalent permissions in new system as they had in old system
- Permission checks complete in <50ms (same performance as old system)
- Zero permission denials that old system would have allowed
- Audit trail preserved and continues in new system
- Migration can be safely rolled back during monitoring period
- No downtime during migration deployment

### Testing Approach

- Create test database with sample roles and users
- Run full migration sequence, verify permission preservation
- Test rollback at each phase, verify data integrity
- Load test permission checking with new system (benchmark against old)
- Test edge cases: users with no roles, users with all roles, conditionally-granted permissions
- Verify audit trail continuity across migration
```

**What makes this excellent:**

- Documents discovered foreign key ordering constraints
- Explains zero-downtime strategy and why alternatives were rejected
- Uses `[CRITICAL:]` tags for irreversible operations and security issues
- Links context to specific steps with "Related Context" subsections
- Includes specific gotchas about bulk_create, trigger syntax, etc.
- Provides clear rollback strategy at each phase

---

### Example 3: Race Condition Fix in Real-time Collaboration

#### Poor Context (No Explanation of Root Cause)

```markdown
## Implementation Plan: Fix Document Sync Race Condition

### Objective

Fix race condition in collaborative document editing.

### Implementation Steps

1. **Add version numbers to documents**: Add version field to Document model
   - Success: Field added

2. **Check version before saving**: Compare version in request with database
   - Success: Version check implemented

3. **Return conflict error if mismatch**: Return 409 status code
   - Success: Error returned
```

**Problems:**

- Doesn't explain what causes the race condition
- Missing explanation of why version numbers solve it
- No mention of merge conflict handling
- Doesn't document discovered timing constraints

#### Excellent Context (Root Cause Analysis and Solution Reasoning)

```markdown
## Implementation Plan: Fix Document Sync Race Condition

### Objective

Eliminate race condition in collaborative document editing where concurrent edits cause data loss, by implementing optimistic concurrency control with operational transformation fallback.

### Context & Understanding

#### API/Tool Quirks

- **WebSocket Message Ordering**: Browser WebSocket API doesn't guarantee message delivery order for messages sent rapidly (<10ms apart). Server must use sequence numbers, not timestamps.
- **Postgres SERIALIZABLE Limitations**: SERIALIZABLE isolation level in Postgres uses predicate locking. Concurrent edits to same document cause serialization failures requiring retry. Not suitable for real-time collaboration.
- **Browser Tab Sync**: localStorage events only fire in OTHER tabs, not the tab that made the change. Need separate BroadcastChannel for same-tab communication.

#### Architectural Insights

- Race condition root cause: Two users load document at version N, both edit, both save. Second save overwrites first user's changes.
- Version numbers provide optimistic concurrency control: detect conflicts without locking. Better for real-time collaboration than pessimistic locking.
- Operational Transformation (OT) allows automatic merge of non-conflicting concurrent edits (user A edits paragraph 1, user B edits paragraph 2). Version conflict only triggers for true conflicts.

#### Domain Logic & Business Rules

- **Conflict Resolution Priority**: In case of true conflict, more recent edit wins but conflict must be logged for potential manual review.
- **Grace Period for Idle Connections**: User who was idle >5 minutes should see warning before overwriting recent edits, even if they technically have an old version.
- **Undo Across Versions**: User must be able to undo their own edits even if other users' edits have incremented version. Requires per-user operation history.

#### Complex Reasoning

- **Rejected**: Database-level locking (SELECT FOR UPDATE)
  - Reason: Lock held during user's entire edit session causes head-of-line blocking
  - One slow user blocks all other users from even loading document
- **Rejected**: Last-write-wins without version check
  - Reason: Guaranteed data loss when concurrent edits occur
  - No way for users to know their changes were lost
- **Rejected**: Full operational transformation for all edits
  - Reason: OT algorithms are complex and brittle. Only use for auto-mergeable cases.
  - True conflicts should be surfaced to user, not silently merged
- **Chosen**: Hybrid approach - version check + OT for auto-mergeable + user conflict resolution
  - Detects conflicts reliably with version numbers
  - Auto-merges when edits don't overlap (best UX)
  - Surfaced conflicts when automatic merge isn't safe

#### Known Pitfalls

- **DO NOT** use document.updated_at timestamp for version checking. Server clock skew and race conditions within same millisecond cause false positives.
- **DO NOT** increment version on every keystroke. Rate limit version increments to every 2 seconds of active editing to reduce conflict false positives.
- **DO NOT** show conflict error immediately when detected. Buffer for 100ms to allow racing save operations to complete, then show merged state.
- **DO NOT** assume WebSocket connection alive means user is active. Check for heartbeat to detect backgrounded tabs before applying edits.

### Implementation Steps

1. **Add version and edit tracking fields to Document model**: Modify models/document.py
   [CRITICAL: Use integer version, NOT timestamp. Version must increment atomically with content update.]
   - Add version INTEGER NOT NULL DEFAULT 1 field
   - Add last_edit_by_user_id for conflict attribution
   - Add last_edit_at timestamp separate from version
   - Create database constraint: version must increase monotonically
   - Success: Migration runs, constraints enforced
   - On failure: Check constraint syntax for monotonic increase

   Related Context:
   - Integer version avoids timestamp race conditions and clock skew
   - Atomic increment with content update critical for consistency
   - last_edit_by helps show conflicts: "Your edit conflicts with Alice's edit 2 minutes ago"

2. **Implement optimistic locking in save endpoint**: Update POST /api/documents/:id
   [CRITICAL: Version check and increment must be in single atomic database operation]
   - Accept expected_version in request body
   - Use UPDATE documents SET version = version + 1, content = $1 WHERE id = $2 AND version = $3
   - Check affected rows = 1 to detect conflict
   - Return 409 with current version and last editor if conflict
   - Success: Concurrent saves with same version trigger conflict
   - On failure: Verify atomic compare-and-swap using WHERE clause

   Related Context:
   - WHERE version = expected prevents lost update
   - Single UPDATE statement ensures atomicity without transaction overhead
   - Returning current state lets client decide to retry or show conflict

3. **Add operational transformation for auto-merge**: Create utils/ot.py with OT logic
   - Implement diff3-style merge for non-overlapping paragraph edits
   - Detect true conflicts: edits to same paragraph
   - Return merged content for auto-mergeable, null for conflicts
   - Success: Non-overlapping edits merge automatically, overlapping edits return null
   - On failure: Test with sample conflict cases, verify detection logic

   Related Context:
   - Paragraph granularity chosen as good balance of auto-merge vs safety
   - Character-level merge too aggressive (silently creates nonsense)
   - Document-level merge too conservative (false conflicts)

4. **Implement conflict resolution UI**: Update frontend editor component
   - On 409 response, attempt operational transformation merge
   - If auto-mergeable, apply merge and retry save with new version
   - If true conflict, show diff view with current content vs. user's edit
   - Provide options: keep yours, keep theirs, manual merge
   - Success: Auto-merge works for non-conflicting edits, manual resolution for conflicts
   - On failure: Check OT integration, verify diff display shows changes clearly

   Related Context:
   - Auto-merge provides seamless UX for majority case (non-overlapping edits)
   - Manual resolution required for true conflicts to prevent data loss
   - Showing diff helps user make informed decision

5. **Add idle detection and staleness warning**: Implement activity tracking
   [CRITICAL: Detect idle BEFORE user tries to save to prevent frustration]
   - Track last user interaction timestamp in memory
   - On editor focus after >5 min idle, check if document version changed
   - If version changed, show banner: "This document was edited by Alice 3 minutes ago. Review changes before saving."
   - Provide "Show changes" button to view diff
   - Success: Idle users warned about intervening edits before they make changes
   - On failure: Test with simulated idle period, verify warning appears

   Related Context:
   - Proactive warning better UX than conflict error after user has edited
   - 5 minute threshold balances helpful warning vs. annoying false positives
   - Users can choose to review changes or proceed with edit

6. **Implement per-user operation history for undo**: Add operations table
   - Create table: user_id, document_id, operation_type, operation_data, created_at
   - Store each user's edit operations with content diffs
   - Implement undo: reverse operation and create new forward operation
   - Success: Users can undo their own edits even after other users edit document
   - On failure: Check operation reversal logic, verify doesn't affect other users' edits

   Related Context:
   - Per-user history allows undo without rolling back other users
   - Forward operation for undo maintains version progression
   - Operation log also useful for debugging conflicts

7. **Add WebSocket sequence numbers**: Update real-time sync protocol
   [CRITICAL: Sequence numbers must be connection-scoped, reset on reconnect]
   - Add seq number to each WebSocket message
   - Track expected next seq on server
   - Reject out-of-order messages, request resync
   - Success: Out-of-order delivery detected and corrected
   - On failure: Test with simulated network reordering

   Related Context:
   - Sequence numbers detect message reordering from WebSocket layer
   - Connection-scoped prevents issues with reconnection
   - Resync request allows recovery from dropped messages

### Success Criteria

- Concurrent edits to same document detected and prevented
- Non-conflicting concurrent edits (different paragraphs) auto-merge successfully
- True conflicts show clear diff and resolution options
- Users idle >5 minutes warned before overwriting recent edits
- Users can undo their own edits without affecting others
- WebSocket message reordering detected and corrected
- Zero data loss from race conditions in production

### Testing Approach

- Simulate concurrent edits using multiple browser instances
- Test auto-merge with edits to different paragraphs
- Test conflict detection with edits to same paragraph
- Test idle warning with simulated 5-minute delay
- Test undo after another user's edit has been applied
- Load test with 50+ concurrent users editing same document
- Test WebSocket message reordering with network simulation
```

**What makes this excellent:**

- Explains root cause of race condition clearly
- Documents why alternatives were rejected (locking, last-write-wins, full OT)
- Uses `[CRITICAL:]` tags for atomicity requirements and UX timing
- Links architectural decisions to specific implementation steps
- Includes discovered quirks (WebSocket ordering, localStorage events)
- Provides detailed rationale for chosen approach (hybrid OT + manual resolution)

---

## Key Patterns for Excellent Context

### 1. Hybrid Linking Approach

Use inline `[CRITICAL:]` tags for must-not-miss items directly in steps:

```markdown
1. **Do the thing**: In file.py
   [CRITICAL: Must do X before Y or Z will break]
   - Success: Thing works
```

Use "Related Context" subsections for detailed explanations:

```markdown
Related Context:

- Why this approach was chosen
- What alternatives were considered
- What constraints apply
```

### 2. Document Discovery Process

Show what you learned and how:

- "Discovered during testing that..."
- "Analysis revealed that..."
- "Investigation of codebase showed..."

### 3. Explain Rejected Alternatives

Document approaches that WON'T work and why:

- **Rejected**: [Approach]
  - Reason: [Specific technical reason]
  - Also: [Additional concern]

### 4. Include Specific Examples

Abstract: "Handle edge cases properly"
Specific: "WebSocket messages sent <10ms apart may arrive out of order"

Abstract: "Check for errors"
Specific: "Zero-amount test payments trigger payment_intent.succeeded event"

### 5. Link Context to Steps

Every context item should map to at least one implementation step.
Every complex implementation step should reference relevant context.

Orphaned context = context without steps = probably not relevant.
Context-less complex step = likely to be implemented incorrectly.

## Anti-Patterns to Avoid

### Vague Generalizations

Bad: "Handle errors properly"
Good: "Verify webhook signature BEFORE parsing JSON to prevent replay attacks"

### Unlinked Context

Bad: Context sections that don't connect to any implementation steps
Good: Each context item referenced by relevant steps

### Missing "Why"

Bad: "Use optimistic locking"
Good: "Use optimistic locking because pessimistic locking blocks all users during edit session"

### No Discovery Attribution

Bad: Stating facts without explaining they were discovered
Good: "Testing revealed that webhooks arrive before API responses 70% of the time"

### Inline-Only or Subsection-Only

Bad: All critical info buried in subsections (requires scrolling)
Bad: All context inline (clutters steps, loses detail)
Good: Hybrid - critical warnings inline, detailed explanations in subsections
