# Plan Enrichment Process

This document contains the shared enrichment process used by erk commands that enhance implementation plans for autonomous execution. Commands that reference this document apply a comprehensive enrichment workflow to transform basic plans into detailed, context-rich specifications.

## When to Use This Process

Use this enrichment process when:

- Creating plans that will be executed by AI agents autonomously
- You want to preserve valuable context discovered during planning discussions
- Plans need interactive enhancement to clarify ambiguities
- You want to apply optional guidance to refine a plan
- Complex plans would benefit from structured context sections

## Overview

This enrichment process consists of three main steps:

1. **Apply Optional Guidance** - Merge user guidance into the plan contextually
2. **Extract Semantic Understanding** - Capture valuable context from planning discussion
3. **Interactive Enhancement** - Ask clarifying questions and improve plan structure

---

### Step 1: Apply Optional Guidance to Plan

🔴 **REMINDER: YOU ARE ONLY WRITING MARKDOWN**

- DO NOT use Edit or Write tools except for the final plan file
- DO NOT implement any code from the plan
- DO NOT modify any files in the codebase
- ONLY save ONE markdown file at `<repo-root>/<name>-plan.md`

**Check for guidance argument:**

If guidance text is provided as an argument to this command:

**Guidance Classification and Merging Algorithm:**

1. **Correction** - Fixes errors in approach
   - Pattern: "Fix:", "Correct:", "Use X instead of Y"
   - Action: Update relevant sections in-place
   - Example: "Fix: Use LBYL not try/except" → Replace exception handling approaches throughout

2. **Addition** - New requirements or features
   - Pattern: "Add:", "Include:", "Also implement"
   - Action: Add new subsections or steps
   - Example: "Add retry logic to API calls" → Insert new step or enhance existing API steps

3. **Clarification** - More detail or specificity
   - Pattern: "Make X more", "Ensure", "Specifically"
   - Action: Enhance existing steps with details
   - Example: "Make error messages user-friendly" → Add detail to error handling sections

4. **Reordering** - Priority or sequence changes
   - Pattern: "Do X before Y", "Prioritize", "Start with"
   - Action: Restructure order of steps
   - Example: "Do validation before processing" → Move validation steps earlier

**Integration Process:**

1. Parse guidance to identify type(s)
2. Find relevant sections in plan
3. Apply transformations contextually (not just appending)
4. Preserve plan structure and formatting
5. Maintain coherent flow

**Edge cases:**

**Guidance without plan in context:**

```
❌ Error: Cannot apply guidance - no plan found in context

Details: Guidance provided: "[first 100 chars of guidance]"

Suggested action:
  1. First create or present an implementation plan
  2. Then run: /erk:save-context-enriched-plan "your guidance here"
```

**Multi-line guidance limitation:**
Note: Guidance must be provided as a single-line string in quotes. Multi-line guidance is not supported.

If no guidance provided: use the original plan as-is

**Output:** Final plan content (original or modified) ready for Step 2 processing

### Step 2: Extract and Preserve Semantic Understanding

🔴 **REMINDER: YOU ARE ONLY WRITING MARKDOWN**

- DO NOT use Edit or Write tools except for the final plan file
- DO NOT implement any code from the plan
- DO NOT modify any files in the codebase
- ONLY save ONE markdown file at `<repo-root>/<name>-plan.md`

Analyze the planning discussion to extract valuable context that implementing agents would find expensive to rediscover. Use the structured template sections to organize discoveries.

**Context Preservation Criteria:**
Include items that meet ANY of these:

- Took ANY time to discover (even 30 seconds of research)
- MIGHT influence implementation decisions
- Could POSSIBLY cause bugs or confusion
- Wasn't immediately obvious on first glance
- Required any clarification or discussion
- Involved ANY decision between alternatives
- Required looking at documentation or examples

**Extraction Process:**

1. **Extract EVERYTHING first** - Do a complete pass capturing every single discovery, decision, clarification, or piece of information learned
2. **Organize into categories** - Sort the raw extractions into the appropriate sections
3. **Apply minimal filtering** - Only remove true duplicates and completely irrelevant items (like "user said hello")
4. **Add a catch-all section** - Include "Other Discoveries" for items that don't fit categories
5. **Document the planning process itself** - What research was done, what sources were consulted, what experiments were run

**For each dimension, systematically check the planning discussion:**

#### 1. API/Tool Quirks

Look for discoveries about external systems, libraries, or tools:

Questions to ask:

- Did we discover undocumented behaviors or edge cases?
- Are there timing issues, race conditions, or ordering constraints?
- Did we find version-specific gotchas or compatibility issues?
- Are there performance characteristics that affect design?

Examples to extract:

- "Stripe webhooks often arrive BEFORE API response returns to client"
- "PostgreSQL foreign keys must be created in dependency order within same migration"
- "WebSocket API doesn't guarantee message order for sends <10ms apart"
- "SQLite doesn't support DROP COLUMN in versions before 3.35"

#### 2. Architectural Insights

Look for WHY behind design decisions:

Questions to ask:

- Why was this architectural pattern chosen over alternatives?
- What constraints led to this design?
- How do components interact in non-obvious ways?
- What's the reasoning behind the sequencing or phasing?

Examples to extract:

- "Zero-downtime deployment requires 4-phase migration to maintain rollback capability"
- "State machine pattern prevents invalid state transitions from webhook retries"
- "Webhook handlers MUST be idempotent because Stripe retries for up to 3 days"
- "Database transactions scoped per-webhook-event, not per-API-call, to prevent partial updates"

#### 3. Domain Logic & Business Rules

Look for non-obvious requirements and rules:

Questions to ask:

- Are there business rules that aren't obvious from code?
- What edge cases or special conditions apply?
- Are there compliance, security, or regulatory requirements?
- What assumptions about user behavior or data affect implementation?

Examples to extract:

- "Failed payments trigger 7-day grace period before service suspension, not immediate cutoff"
- "Admin users must retain ALL permissions during migration - partial loss creates security incident"
- "Default permissions for new users during migration must be fail-closed, not empty"
- "Tax calculation must happen before payment intent creation to ensure correct amounts"

#### 4. Complex Reasoning

Look for alternatives considered and decision rationale:

Questions to ask:

- What approaches were considered but rejected?
- Why were certain solutions ruled out?
- What tradeoffs were evaluated?
- How did we arrive at the chosen approach?

Format as:

- **Rejected**: [Approach]
  - Reason: [Why it doesn't work]
  - Also: [Additional concerns]
- **Chosen**: [Selected approach]
  - [Why this works better]

Examples to extract:

- "**Rejected**: Synchronous payment confirmation (waiting for webhook in API call)
  - Reason: Webhooks can take 1-30 seconds, creates timeout issues
  - Also: Connection failures would lose webhook delivery entirely"
- "**Rejected**: Database-level locking (SELECT FOR UPDATE)
  - Reason: Lock held during entire edit session causes head-of-line blocking"
- "**Chosen**: Optimistic locking with version numbers
  - Detects conflicts without blocking, better for real-time collaboration"

#### 5. Known Pitfalls

Look for specific gotchas and anti-patterns:

Questions to ask:

- What looks correct but actually causes problems?
- Are there subtle bugs waiting to happen?
- What mistakes did we avoid during planning?
- What would be easy to get wrong during implementation?

Format as "DO NOT [anti-pattern] - [why it breaks]"

Examples to extract:

- "DO NOT use payment_intent.succeeded event alone - fires even for zero-amount test payments. Check amount > 0."
- "DO NOT store Stripe objects directly in database - schema changes across API versions. Extract needed fields only."
- "DO NOT assume webhook delivery order - charge.succeeded might arrive before payment_intent.succeeded"
- "DO NOT use document.updated_at for version checking - clock skew and same-ms races cause false conflicts"
- "DO NOT migrate superuser permissions first - if migration fails, you've locked out recovery access"

#### 6. Raw Discoveries Log

Capture EVERYTHING discovered during planning, even if it seems minor:

Questions to ask:

- What did we look up or verify?
- What assumptions did we validate?
- What small details did we clarify?
- What documentation did we reference?
- What examples did we examine?

Format as bullet points without filtering:

- Discovered: SQLite version on system is 3.39
- Confirmed: pytest is already in requirements.txt
- Learned: The codebase uses pathlib, not os.path
- Checked: No existing rate limiting on API endpoints
- Found: Tests use unittest not pytest style
- Verified: Python 3.11 is the minimum version
- Noted: All configs are YAML not JSON
- Observed: Error messages follow RFC7807 format
- Clarified: User model is in models/user.py not auth/models.py
- Researched: Stripe webhook signature verification requires raw body bytes
- Discovered: Project uses Black formatter with 88 char line length
- Found: All API responses use snake_case not camelCase
- Verified: Database migrations run automatically on deploy
- Learned: Redis is used for caching but not sessions

#### 7. Planning Artifacts

Preserve any code snippets, commands, or configurations discovered during planning:

**Commands Run:**

- `pip list | grep stripe` → Found stripe==5.4.0
- `git log --oneline -5` → Verified recent commit patterns
- `python --version` → Python 3.11.6

**Code Examined:**

- Looked at auth.py lines 45-67 for validation pattern
- Reviewed test_utils.py for test fixture approach
- Checked settings.py for database configuration

**Config Samples:**

- Database connection: `postgresql://user:pass@localhost/db`
- Redis settings: `{"host": "localhost", "port": 6379}`
- API rate limit: 100 requests per minute

**Error Messages Encountered:**

- "ImportError: circular import" when trying direct import
- "TypeError: can't pickle" with multiprocessing approach
- "ValidationError: field required" for missing user_id

#### 8. Implementation Risks & Concerns

Document any worries, uncertainties, or potential issues identified during planning:

**Technical Debt:**

- The auth system is tightly coupled to user model
- No abstraction layer between API and database
- Tests are not parallelizable due to shared fixtures

**Uncertainty Areas:**

- Not sure if webhook endpoint needs CSRF protection
- Unclear if rate limiting applies to admin users
- Don't know if database can handle expected load

**Performance Concerns:**

- Bulk operations might timeout with current 30s limit
- No caching layer could cause issues at scale
- N+1 queries likely in user list endpoint

**Security Considerations:**

- API keys stored in plain text in dev config
- No audit logging for permission changes
- CORS settings might be too permissive

**Output:** Enhanced plan with populated Context & Understanding sections, ready for Step 3 interactive enhancement

### Step 3: Interactive Plan Enhancement

🔴 **REMINDER: YOU ARE ONLY WRITING MARKDOWN**

- DO NOT use Edit or Write tools except for the final plan file
- DO NOT implement any code from the plan
- DO NOT modify any files in the codebase
- ONLY save ONE markdown file at `<repo-root>/<name>-plan.md`

Analyze the plan for common ambiguities and ask clarifying questions when helpful. Focus on practical improvements that make implementation clearer.

#### Code in Plans: Behavioral, Not Literal

**Rule:** Plans describe WHAT to do, not HOW to code it.

**Include in plans:**

- File paths and function names
- Behavioral requirements
- Success criteria
- Error handling approaches

**Only include code snippets for:**

- Security-critical implementations
- Public API signatures
- Bug fixes showing exact before/after
- Database schema changes

**Example:**
❌ Wrong: `def validate_user(user_id: str | None) -> User: ...`
✅ Right: "Update validate_user() in src/auth.py to use LBYL pattern, check for None, raise appropriate errors"

#### Analyze Plan for Gaps

Examine the plan for common ambiguities:

**Common gaps to look for:**

1. **Vague file references**: "the config file", "update the model", "modify the API"
   - Need: Exact file paths

2. **Unclear operations**: "improve", "optimize", "refactor", "enhance"
   - Need: Specific actions and metrics

3. **Missing success criteria**: Steps without clear completion conditions
   - Need: Testable outcomes

4. **Unspecified dependencies**: External services, APIs, packages mentioned without details
   - Need: Availability, versions, fallbacks

5. **Large scope indicators**:
   - Multiple distinct features
   - Multiple unrelated components
   - Complex interdependencies
   - Need: Consider phase decomposition

6. **Missing reasoning context**: "use the better approach", "handle carefully"
   - Need: Which approach was chosen and WHY
   - Need: What "carefully" means specifically

7. **Vague constraints**: "ensure compatibility", "maintain performance"
   - Need: Specific versions, standards, or metrics
   - Need: Quantifiable requirements

8. **Hidden complexity**: Steps that seem simple but aren't
   - Need: Document discovered complexity
   - Need: Explain non-obvious requirements

#### Ask Clarifying Questions

For gaps identified, ask the user specific questions. Use the AskUserQuestion tool to get answers.

**Question format examples:**

```markdown
I need to clarify a few details to improve the plan:

**File Locations:**
The plan mentions "update the user model" - which specific file contains this model?

- Example: `models/user.py` or `src/database/models.py`

**Success Criteria:**
Phase 2 mentions "improve performance" - what specific metrics should I target?

- Example: "Response time < 200ms" or "Memory usage < 100MB"

**External Dependencies:**
The plan references "the payments API" - which service is this?

- Example: "Stripe API v2" or "Internal billing service at /api/billing"
```

**Context Mining Questions:**

To ensure we've captured all valuable discoveries from our planning discussion:

**What did we learn about the codebase?**

- Any patterns, conventions, or structures we discovered?
- Example: "All services inherit from BaseService class"
- Example: "Database queries use raw SQL, not ORM"

**What external resources did we reference?**

- Documentation, examples, or discussions we looked at?
- Example: "Checked Stripe docs for webhook retry behavior"
- Example: "Referenced Stack Overflow for datetime handling"

**What assumptions did we validate or invalidate?**

- Things that turned out different than expected?
- Example: "Thought we could use async but parent is sync"
- Example: "Expected JSON configs but found YAML"

**What small details matter?**

- Minor things that could trip up implementation?
- Example: "Import order matters due to circular deps"
- Example: "Must use double quotes in SQL, not single"

**Important:**

- Ask all clarifying questions in one interaction (batch them)
- Make questions specific and provide examples
- Allow user to skip questions if they prefer ambiguity
- Context questions should focus on discoveries made during planning, not theoretical concerns

#### Check for Semantic Understanding

After clarifying questions, check if you discovered valuable context during planning (see "Semantic Understanding & Context Preservation" section). If relevant, include it in the plan's "Context & Understanding" section.

#### Suggest Phase Decomposition (When Helpful)

For complex plans with multiple distinct features or components, suggest breaking into phases:

**IMPORTANT - Testing and validation:**

- Testing and validation are ALWAYS bundled within implementation phases
- Never create separate phases for "add tests" or "run validation"
- Each phase is an independently testable commit with its own tests
- Only decompose when business logic complexity genuinely requires it
- Tests are part of the deliverable for each phase, not afterthoughts

**Phase structure suggestion:**

```markdown
This plan would benefit from phase-based implementation. Here's a suggested breakdown:

**Phase 1: Data Layer** [branch: feature-data]

- Create models and migrations
- Add unit tests
- Deliverable: Working database schema with tests

**Phase 2: API Endpoints** [branch: feature-api]

- Implement REST endpoints
- Add integration tests
- Deliverable: Functional API with test coverage

**Phase 3: Frontend Integration** [branch: feature-ui]

- Update UI components
- Add e2e tests
- Deliverable: Complete feature with UI

Each phase will be a separate branch that can be tested independently.
Would you like to structure the plan this way? (I can adjust the phases if needed)
```

#### Incorporate Enhancements

Based on user responses:

1. **Update file references** with exact paths
2. **Replace vague terms** with specific actions
3. **Add success criteria** to each major step
4. **Structure into phases** if helpful
5. **Include test requirements** where appropriate

#### Plan Templates

**For Single-Phase Plans:**

```markdown
## Implementation Plan: [Title]

### Objective

[Clear goal statement]

### Context & Understanding

Preserve valuable context discovered during planning. Include items that:

- Took time to discover and aren't obvious from code
- Would change implementation if known vs. unknown
- Could cause bugs if missed (especially subtle or delayed bugs)

#### API/Tool Quirks

[Undocumented behaviors, timing issues, version constraints, edge cases]

Example:

- Stripe webhooks often arrive BEFORE API response returns
- PostgreSQL foreign keys must be created in dependency order

#### Architectural Insights

[Why design decisions were made, not just what was decided]

Example:

- Zero-downtime deployment requires 4-phase migration to allow rollback
- State machine pattern prevents invalid state transitions from retries

#### Domain Logic & Business Rules

[Non-obvious requirements, edge cases, compliance rules]

Example:

- Failed payments trigger 7-day grace period, not immediate suspension
- Admin users must retain all permissions during migration (security)

#### Complex Reasoning

[Alternatives considered and why some were rejected]

Example:

- **Rejected**: Synchronous payment confirmation (waiting for webhook)
  - Reason: Webhooks take 1-30s, creates timeout issues
- **Chosen**: Async webhook-driven flow
  - Handles timing correctly regardless of webhook delay

#### Known Pitfalls

[What looks right but causes problems - specific gotchas]

Example:

- DO NOT use payment_intent.succeeded alone - fires for zero-amount tests
- DO NOT store Stripe objects directly - schema changes across API versions

#### Raw Discoveries Log

[Everything discovered during planning, even minor details]

Example:

- Discovered: SQLite version is 3.39
- Confirmed: pytest is in requirements.txt
- Learned: Codebase uses pathlib not os.path
- Verified: Python 3.11 is minimum version
- Noted: All configs are YAML not JSON

#### Planning Artifacts

[Code examined, commands run, configurations discovered]

Example:

**Commands Run:**

- `pip list | grep stripe` → Found stripe==5.4.0

**Code Examined:**

- Looked at auth.py lines 45-67 for validation pattern

**Config Samples:**

- Database: `postgresql://user:pass@localhost/db`

#### Implementation Risks

[Technical debt, uncertainties, performance and security concerns]

Example:

**Technical Debt:**

- Auth system tightly coupled to user model

**Uncertainty Areas:**

- Not sure if webhook needs CSRF protection

### Implementation Steps

Use hybrid context linking:

- Inline [CRITICAL:] tags for must-not-miss warnings
- "Related Context:" subsections for detailed explanations

1. **[Action]**: [What to do] in `[exact/file/path]`
   [CRITICAL: Any security or breaking change warnings]
   - Success: [How to verify]
   - On failure: [Recovery action]

   Related Context:
   - [Why this approach was chosen]
   - [What constraints or gotchas apply]
   - [Link to relevant Context & Understanding sections above]

2. [Continue pattern...]

### Testing

- Tests are integrated within implementation steps
- Final validation: Run project CI/validation checks

---

## Progress Tracking

**Current Status:** [Status description]

**Last Updated:** [Date]

### Implementation Progress

- [ ] Step 1: [Description from Implementation Steps]
- [ ] Step 2: [Description from Implementation Steps]
- [ ] Step 3: [Description from Implementation Steps]

### Overall Progress

**Steps Completed:** 0 / N
```

**For Multi-Phase Plans:**

```markdown
## Implementation Plan: [Title]

### Context & Understanding

Preserve valuable context discovered during planning. Include items that:

- Took time to discover and aren't obvious from code
- Would change implementation if known vs. unknown
- Could cause bugs if missed (especially subtle or delayed bugs)

#### API/Tool Quirks

[Undocumented behaviors, timing issues, version constraints, edge cases]

#### Architectural Insights

[Why design decisions were made, not just what was decided]

#### Domain Logic & Business Rules

[Non-obvious requirements, edge cases, compliance rules]

#### Complex Reasoning

[Alternatives considered and why some were rejected]

#### Known Pitfalls

[What looks right but causes problems - specific gotchas]

#### Raw Discoveries Log

[Everything discovered during planning, even minor details]

#### Planning Artifacts

[Code examined, commands run, configurations discovered]

#### Implementation Risks

[Technical debt, uncertainties, performance and security concerns]

### Phase 1: [Name]

**Branch**: feature-1 (base: main)
**Goal**: [Single objective]

**Steps:**

Use hybrid context linking:

- Inline [CRITICAL:] tags for must-not-miss warnings
- "Related Context:" subsections for detailed explanations

1. **[Action]**: [What to do] in `[exact/file/path]`
   [CRITICAL: Any security or breaking change warnings]
   - Success: [How to verify]
   - On failure: [Recovery action]

   Related Context:
   - [Why this approach was chosen]
   - [What constraints or gotchas apply]
   - [Link to relevant Context & Understanding sections above]

2. Add tests in [test file]
3. Validate with project CI/validation checks

### Phase 2: [Name]

**Branch**: feature-2 (stacks on: feature-1)
[Continue pattern...]

---

## Progress Tracking

**Current Status:** [Status description]

**Last Updated:** [Date]

### Phase 1: [Phase Name]

**Status:** ⏸️ NOT STARTED

- [ ] Step 1: [Description from Phase 1 Steps]
- [ ] Step 2: [Description from Phase 1 Steps]
- [ ] Step 3: [Description from Phase 1 Steps]

### Phase 2: [Phase Name]

**Status:** ⏸️ NOT STARTED

- [ ] Step 1: [Description from Phase 2 Steps]
- [ ] Step 2: [Description from Phase 2 Steps]

### Overall Progress

**Phases Complete:** 0 / N
**Total Steps:** 0 / M
```

#### Apply Hybrid Context Linking

Before finalizing the plan, ensure context is properly linked to implementation steps:

**Linking Strategy:**

1. **Inline [CRITICAL:] tags** - For must-not-miss warnings in steps
   - Security vulnerabilities
   - Breaking changes
   - Data loss risks
   - Irreversible operations
   - Race conditions or timing requirements

   Example:

   ```markdown
   1. **Create database migration**: Add migration 0001_initial.py
      [CRITICAL: Run backup BEFORE migration. Irreversible schema change.]
   ```

2. **"Related Context:" subsections** - For detailed explanations
   - Link to relevant Context & Understanding sections
   - Explain WHY this approach was chosen
   - Document discovered constraints or gotchas
   - Reference rejected alternatives

   Example:

   ```markdown
   Related Context:

   - Migration is 4-phase to allow rollback (see Architectural Insights)
   - Foreign keys must be created in dependency order (see API/Tool Quirks)
   - See Known Pitfalls for DROP COLUMN version constraint
   ```

**Validation Checklist:**

Before proceeding, verify:

- [ ] EVERY implementation step has at least one context reference (even if minor)
- [ ] Any step touching external services references relevant quirks
- [ ] Any step with alternatives documents why this approach was chosen
- [ ] Security-critical operations have inline [CRITICAL:] warnings
- [ ] Each Context & Understanding item is referenced by at least one step
- [ ] No orphaned context (context without corresponding steps)
- [ ] Context items are specific and actionable, not vague generalizations

**Orphaned Context Handling:**

If context items don't map to any implementation step:

- Either: Add implementation steps that use this context
- Or: Remove the context item (it's probably not relevant)

Context should drive implementation. If context doesn't connect to steps, it's either missing steps or irrelevant.

#### Final Review

Present a final review of potential execution issues (not a quality score):

```markdown
## Plan Review - Potential Execution Issues

🟡 **Ambiguous reference: "the main configuration"**
Impact: Agent won't know which file to modify
Suggested fix: Specify exact path (e.g., `config/settings.py`)
[Fix Now] [Continue Anyway]

🟡 **No test coverage specified for new endpoints**
Impact: Can't verify implementation works correctly
Suggested fix: Add test requirements for each endpoint
[Add Tests] [Skip]

🔴 **Database migration lacks rollback strategy**
Impact: Failed migration could leave database in broken state
Suggested fix: Include rollback procedure or backup strategy
[Add Rollback] [Accept Risk]
```

**Key principles:**

- Only flag issues that would genuinely block execution
- Provide concrete impact statements
- Let users dismiss warnings
- Don't use percentages or scores
- Focus on actionability

**Output:** Final enhanced plan content ready for subsequent processing
