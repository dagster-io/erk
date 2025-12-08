# GitHub CLI API Backend Audit

## Audit Metadata

| Field               | Value                                                   |
| ------------------- | ------------------------------------------------------- |
| **Analysis Date**   | 2025-12-08                                              |
| **gh CLI Version**  | v2.83.1                                                 |
| **Source Commit**   | `c8ab18323ee47721cba857bf82d55a21143566cb` (2025-12-02) |
| **Repository**      | https://github.com/cli/cli                              |
| **Source Location** | `/Users/schrockn/code/githubs/cli`                      |

## Quick Reference Summary

| Command Family   | Primary API | Notes                                              |
| ---------------- | ----------- | -------------------------------------------------- |
| `gh pr`          | **GraphQL** | All PR operations use GraphQL for rich nested data |
| `gh issue`       | **GraphQL** | Issue queries and mutations via GraphQL            |
| `gh repo`        | **Mixed**   | GraphQL for queries, REST for some mutations       |
| `gh release`     | **Mixed**   | GraphQL for listing, REST for create/edit/delete   |
| `gh run`         | **REST**    | All workflow run operations use REST               |
| `gh workflow`    | **REST**    | Workflow management via REST                       |
| `gh gist`        | **REST**    | All gist operations use REST                       |
| `gh project`     | **GraphQL** | Projects V2 requires GraphQL exclusively           |
| `gh search`      | **REST**    | Search API is REST-only                            |
| `gh secret`      | **REST**    | Secrets management via REST                        |
| `gh variable`    | **REST**    | Variables management via REST                      |
| `gh cache`       | **REST**    | Actions cache management via REST                  |
| `gh label`       | **Mixed**   | GraphQL for list, REST for create/edit/delete      |
| `gh ruleset`     | **Mixed**   | GraphQL for list, REST for view/check              |
| `gh codespace`   | **REST**    | Codespaces API via REST                            |
| `gh ssh-key`     | **REST**    | SSH key management via REST                        |
| `gh gpg-key`     | **REST**    | GPG key management via REST                        |
| `gh org`         | **GraphQL** | Organization listing via GraphQL                   |
| `gh status`      | **Mixed**   | GraphQL for search, REST for notifications         |
| `gh extension`   | **REST**    | Extension discovery via REST                       |
| `gh attestation` | **REST**    | Attestation verification via REST                  |

## Rate Limit Guidance

### GitHub REST API Rate Limits

- **Authenticated requests**: 5,000 requests/hour
- **Unauthenticated requests**: 60 requests/hour
- **Search API**: 30 requests/minute (authenticated)
- **Rate limit is per-user**, not per-token

**Checking rate limit status:**

```bash
gh api rate_limit --jq '.resources'
```

### GitHub GraphQL API Rate Limits

- **Point-based system**: 5,000 points/hour
- **Cost calculation**: Based on query complexity
  - Each connection costs 1 point + (first/last \* node cost)
  - Nested connections multiply costs
- **Minimum cost**: 1 point per query

**Checking GraphQL rate limit:**

```bash
gh api graphql -f query='{ rateLimit { cost remaining resetAt } }'
```

### Key Differences

| Aspect            | REST                  | GraphQL                       |
| ----------------- | --------------------- | ----------------------------- |
| Counting          | Per request           | Per query complexity          |
| Predictability    | Highly predictable    | Varies by query structure     |
| Pagination impact | Each page = 1 request | Deep pagination = higher cost |
| Bulk operations   | Multiple requests     | Single request, higher cost   |

### Rate Limit Strategies by API Type

**For REST-heavy workflows (run, workflow, gist, search):**

- Implement exponential backoff on 403/429 responses
- Use conditional requests (`If-None-Match`) for caching
- Batch operations where possible (e.g., delete multiple caches)

**For GraphQL-heavy workflows (pr, issue, project):**

- Request only needed fields to reduce query cost
- Use pagination efficiently (smaller page sizes for nested data)
- Avoid deeply nested queries when possible
- Consider `--paginate` flag overhead

---

## Command Family Details

### Pull Request Commands (`gh pr`)

All PR commands use **GraphQL** for the primary operations, leveraging its ability to fetch nested data (reviews, checks, comments) efficiently.

| Subcommand      | API Type | Query/Mutation/Endpoint                   | Notes                                        |
| --------------- | -------- | ----------------------------------------- | -------------------------------------------- |
| `list`          | GraphQL  | `PullRequestList` query                   | Paginated, supports search filters           |
| `view`          | GraphQL  | `PullRequest` query                       | Fetches nested reviews, checks, comments     |
| `create`        | GraphQL  | `PullRequestCreate` mutation              | Plus metadata mutations for labels/reviewers |
| `edit`          | GraphQL  | `PullRequestUpdate` mutation              | Updates title, body, base branch             |
| `close`         | GraphQL  | `ClosePullRequest` mutation               |                                              |
| `reopen`        | GraphQL  | `ReopenPullRequest` mutation              |                                              |
| `merge`         | GraphQL  | `MergePullRequest` mutation               | Supports auto-merge enable/disable           |
| `ready`         | GraphQL  | `MarkPullRequestReadyForReview` mutation  | Removes draft status                         |
| `review`        | GraphQL  | `AddPullRequestReview` mutation           | Comment, approve, or request changes         |
| `comment`       | GraphQL  | `AddComment` mutation                     |                                              |
| `checks`        | GraphQL  | `StatusCheckRollup` query                 | Fetches CI status and check runs             |
| `status`        | GraphQL  | `PullRequestStatus` query                 | Shows PRs needing attention                  |
| `diff`          | REST     | `GET repos/{owner}/{repo}/pulls/{number}` | Accept: `application/vnd.github.diff`        |
| `checkout`      | GraphQL  | `PullRequest` query                       | Fetches head ref for git checkout            |
| `update-branch` | GraphQL  | `UpdatePullRequestBranch` mutation        | Updates branch with base                     |

**Source files:** `pkg/cmd/pr/*/`, `api/queries_pr.go`

---

### Issue Commands (`gh issue`)

Issue commands primarily use **GraphQL**, with some REST for specific operations.

| Subcommand | API Type | Query/Mutation/Endpoint       | Notes                           |
| ---------- | -------- | ----------------------------- | ------------------------------- |
| `list`     | GraphQL  | `IssueList` query             | Paginated with filters          |
| `view`     | GraphQL  | `Issue` query                 | Rich nested data                |
| `create`   | GraphQL  | `CreateIssue` mutation        | With label/assignee mutations   |
| `edit`     | GraphQL  | `UpdateIssue` mutation        |                                 |
| `close`    | GraphQL  | `CloseIssue` mutation         |                                 |
| `reopen`   | GraphQL  | `ReopenIssue` mutation        |                                 |
| `comment`  | GraphQL  | `AddComment` mutation         |                                 |
| `delete`   | GraphQL  | `DeleteIssue` mutation        |                                 |
| `transfer` | GraphQL  | `TransferIssue` mutation      |                                 |
| `pin`      | GraphQL  | `PinIssue` mutation           |                                 |
| `unpin`    | GraphQL  | `UnpinIssue` mutation         |                                 |
| `lock`     | GraphQL  | `LockLockable` mutation       |                                 |
| `unlock`   | GraphQL  | `UnlockLockable` mutation     |                                 |
| `status`   | GraphQL  | `IssueStatus` query           | Shows assigned/mentioned issues |
| `develop`  | GraphQL  | `CreateLinkedBranch` mutation | Creates branch linked to issue  |

**Source files:** `pkg/cmd/issue/*/`, `api/queries_issue.go`

---

### Repository Commands (`gh repo`)

Repository commands use a **mix** of GraphQL and REST.

| Subcommand          | API Type | Query/Mutation/Endpoint                      | Notes                                  |
| ------------------- | -------- | -------------------------------------------- | -------------------------------------- |
| `view`              | Mixed    | GraphQL query + REST for README              | `GET repos/{owner}/{repo}/readme`      |
| `list`              | GraphQL  | `RepositoryList` query                       | Paginated                              |
| `create`            | Mixed    | GraphQL `CreateRepository` or REST           | REST for user repos, GraphQL for orgs  |
| `clone`             | GraphQL  | `Repository` query                           | Fetches clone URL                      |
| `fork`              | GraphQL  | `ForkRepository` mutation                    |                                        |
| `edit`              | REST     | `PATCH repos/{owner}/{repo}`                 | Plus `PUT repos/{owner}/{repo}/topics` |
| `delete`            | GraphQL  | `DeleteRepository` mutation                  |                                        |
| `rename`            | REST     | `PATCH repos/{owner}/{repo}`                 |                                        |
| `archive`           | GraphQL  | `ArchiveRepository` mutation                 |                                        |
| `unarchive`         | GraphQL  | `UnarchiveRepository` mutation               |                                        |
| `sync`              | REST     | `POST repos/{owner}/{repo}/merge-upstream`   | Plus ref operations                    |
| `set-default`       | GraphQL  | `RepositoryNetwork` query                    | Detects forks/parents                  |
| `credits`           | REST     | `GET repos/{owner}/{repo}/contributors`      | Hidden command                         |
| `deploy-key list`   | REST     | `GET repos/{owner}/{repo}/keys`              |                                        |
| `deploy-key add`    | REST     | `POST repos/{owner}/{repo}/keys`             |                                        |
| `deploy-key delete` | REST     | `DELETE repos/{owner}/{repo}/keys/{id}`      |                                        |
| `autolink list`     | REST     | `GET repos/{owner}/{repo}/autolinks`         |                                        |
| `autolink create`   | REST     | `POST repos/{owner}/{repo}/autolinks`        |                                        |
| `autolink view`     | REST     | `GET repos/{owner}/{repo}/autolinks/{id}`    |                                        |
| `autolink delete`   | REST     | `DELETE repos/{owner}/{repo}/autolinks/{id}` |                                        |
| `gitignore list`    | REST     | `GET gitignore/templates`                    |                                        |
| `gitignore view`    | REST     | `GET gitignore/templates/{name}`             |                                        |
| `license list`      | REST     | `GET licenses`                               |                                        |
| `license view`      | REST     | `GET licenses/{key}`                         |                                        |

**Source files:** `pkg/cmd/repo/*/`, `api/queries_repo.go`

---

### Release Commands (`gh release`)

Release commands use a **mix** of GraphQL for querying and REST for mutations.

| Subcommand | API Type | Query/Mutation/Endpoint                         | Notes                                          |
| ---------- | -------- | ----------------------------------------------- | ---------------------------------------------- |
| `list`     | GraphQL  | `RepositoryReleaseList` query                   | Paginated                                      |
| `view`     | Mixed    | GraphQL query, REST fallback                    | `GET repos/{owner}/{repo}/releases/tags/{tag}` |
| `create`   | REST     | `POST repos/{owner}/{repo}/releases`            | Plus asset uploads                             |
| `edit`     | REST     | `PATCH repos/{owner}/{repo}/releases/{id}`      |                                                |
| `delete`   | REST     | `DELETE repos/{owner}/{repo}/releases/{id}`     |                                                |
| `download` | REST     | `GET repos/{owner}/{repo}/releases/assets/{id}` | Binary download                                |
| `upload`   | REST     | `POST uploads.github.com/.../assets`            | Multipart upload                               |

**Source files:** `pkg/cmd/release/*/`

---

### Workflow Run Commands (`gh run`)

All workflow run commands use **REST** API.

| Subcommand | API Type | Endpoint                                               | Notes                  |
| ---------- | -------- | ------------------------------------------------------ | ---------------------- |
| `list`     | REST     | `GET repos/{owner}/{repo}/actions/runs`                | Paginated              |
| `view`     | REST     | `GET repos/{owner}/{repo}/actions/runs/{id}`           | Plus jobs endpoint     |
| `watch`    | REST     | `GET repos/{owner}/{repo}/actions/runs/{id}`           | Polling                |
| `rerun`    | REST     | `POST repos/{owner}/{repo}/actions/runs/{id}/rerun`    | Or rerun-failed-jobs   |
| `cancel`   | REST     | `POST repos/{owner}/{repo}/actions/runs/{id}/cancel`   |                        |
| `delete`   | REST     | `DELETE repos/{owner}/{repo}/actions/runs/{id}`        |                        |
| `download` | REST     | `GET repos/{owner}/{repo}/actions/runs/{id}/artifacts` | Plus artifact download |

**Source files:** `pkg/cmd/run/*/`

---

### Workflow Commands (`gh workflow`)

All workflow commands use **REST** API.

| Subcommand | API Type | Endpoint                                                      | Notes |
| ---------- | -------- | ------------------------------------------------------------- | ----- |
| `list`     | REST     | `GET repos/{owner}/{repo}/actions/workflows`                  |       |
| `view`     | REST     | `GET repos/{owner}/{repo}/actions/workflows/{id}`             |       |
| `run`      | REST     | `POST repos/{owner}/{repo}/actions/workflows/{id}/dispatches` |       |
| `enable`   | REST     | `PUT repos/{owner}/{repo}/actions/workflows/{id}/enable`      |       |
| `disable`  | REST     | `PUT repos/{owner}/{repo}/actions/workflows/{id}/disable`     |       |

**Source files:** `pkg/cmd/workflow/*/`

---

### Project Commands (`gh project`)

All project commands use **GraphQL** exclusively (Projects V2 has no REST API).

| Subcommand      | API Type | Mutation/Query                           | Notes                 |
| --------------- | -------- | ---------------------------------------- | --------------------- |
| `list`          | GraphQL  | `ProjectV2List` query                    | User or org projects  |
| `view`          | GraphQL  | `ProjectV2` query                        | With items and fields |
| `create`        | GraphQL  | `CreateProjectV2` mutation               |                       |
| `edit`          | GraphQL  | `UpdateProjectV2` mutation               |                       |
| `close`         | GraphQL  | `CloseProjectV2` mutation                |                       |
| `delete`        | GraphQL  | `DeleteProjectV2` mutation               |                       |
| `copy`          | GraphQL  | `CopyProjectV2` mutation                 |                       |
| `mark-template` | GraphQL  | `MarkProjectV2AsTemplate` mutation       |                       |
| `field-list`    | GraphQL  | `ProjectV2Fields` query                  |                       |
| `field-create`  | GraphQL  | `CreateProjectV2Field` mutation          |                       |
| `field-delete`  | GraphQL  | `DeleteProjectV2Field` mutation          |                       |
| `item-list`     | GraphQL  | `ProjectV2Items` query                   | Paginated             |
| `item-add`      | GraphQL  | `AddProjectV2ItemById` mutation          |                       |
| `item-create`   | GraphQL  | `AddProjectV2DraftIssue` mutation        |                       |
| `item-edit`     | GraphQL  | `UpdateProjectV2ItemFieldValue` mutation |                       |
| `item-delete`   | GraphQL  | `DeleteProjectV2Item` mutation           |                       |
| `item-archive`  | GraphQL  | `ArchiveProjectV2Item` mutation          |                       |
| `link`          | GraphQL  | `LinkProjectV2ToRepository` mutation     |                       |
| `unlink`        | GraphQL  | `UnlinkProjectV2FromRepository` mutation |                       |

**Source files:** `pkg/cmd/project/*/`, `pkg/cmd/project/shared/queries/`

---

### Search Commands (`gh search`)

All search commands use **REST** API (GitHub Search API).

| Subcommand | API Type | Endpoint                  | Notes               |
| ---------- | -------- | ------------------------- | ------------------- |
| `repos`    | REST     | `GET search/repositories` | 30 req/min limit    |
| `issues`   | REST     | `GET search/issues`       | Includes PRs        |
| `prs`      | REST     | `GET search/issues`       | With `is:pr` filter |
| `commits`  | REST     | `GET search/commits`      |                     |
| `code`     | REST     | `GET search/code`         | Requires repo scope |

**Rate limit:** Search API has a separate rate limit of 30 requests/minute (authenticated).

**Source files:** `pkg/cmd/search/*/`, `pkg/search/`

---

### Secret Commands (`gh secret`)

All secret commands use **REST** API.

| Subcommand | API Type | Endpoint                                             | Notes               |
| ---------- | -------- | ---------------------------------------------------- | ------------------- |
| `list`     | REST     | `GET repos/{owner}/{repo}/actions/secrets`           | Or org/env secrets  |
| `set`      | REST     | `PUT repos/{owner}/{repo}/actions/secrets/{name}`    | Requires public key |
| `delete`   | REST     | `DELETE repos/{owner}/{repo}/actions/secrets/{name}` |                     |

**Source files:** `pkg/cmd/secret/*/`

---

### Variable Commands (`gh variable`)

All variable commands use **REST** API.

| Subcommand | API Type | Endpoint                                                   | Notes     |
| ---------- | -------- | ---------------------------------------------------------- | --------- |
| `list`     | REST     | `GET repos/{owner}/{repo}/actions/variables`               | Paginated |
| `get`      | REST     | `GET repos/{owner}/{repo}/actions/variables/{name}`        |           |
| `set`      | REST     | `POST/PATCH repos/{owner}/{repo}/actions/variables/{name}` |           |
| `delete`   | REST     | `DELETE repos/{owner}/{repo}/actions/variables/{name}`     |           |

**Source files:** `pkg/cmd/variable/*/`

---

### Cache Commands (`gh cache`)

All cache commands use **REST** API.

| Subcommand | API Type | Endpoint                                          | Notes     |
| ---------- | -------- | ------------------------------------------------- | --------- |
| `list`     | REST     | `GET repos/{owner}/{repo}/actions/caches`         | Paginated |
| `delete`   | REST     | `DELETE repos/{owner}/{repo}/actions/caches/{id}` | Or by key |

**Source files:** `pkg/cmd/cache/*/`

---

### Label Commands (`gh label`)

Label commands use a **mix** of GraphQL and REST.

| Subcommand | API Type | Endpoint/Query                              | Notes                       |
| ---------- | -------- | ------------------------------------------- | --------------------------- |
| `list`     | GraphQL  | `LabelList` query                           | Paginated                   |
| `create`   | REST     | `POST repos/{owner}/{repo}/labels`          |                             |
| `edit`     | REST     | `PATCH repos/{owner}/{repo}/labels/{name}`  |                             |
| `delete`   | REST     | `DELETE repos/{owner}/{repo}/labels/{name}` |                             |
| `clone`    | Mixed    | GraphQL list + REST create                  | Copies labels between repos |

**Source files:** `pkg/cmd/label/`

---

### Gist Commands (`gh gist`)

All gist commands use **REST** API.

| Subcommand | API Type | Endpoint            | Notes                 |
| ---------- | -------- | ------------------- | --------------------- |
| `list`     | REST     | `GET gists`         | Paginated             |
| `view`     | REST     | `GET gists/{id}`    |                       |
| `create`   | REST     | `POST gists`        |                       |
| `edit`     | REST     | `PATCH gists/{id}`  |                       |
| `delete`   | REST     | `DELETE gists/{id}` |                       |
| `clone`    | REST     | `GET gists/{id}`    | Fetches for git clone |
| `rename`   | REST     | `PATCH gists/{id}`  |                       |

**Source files:** `pkg/cmd/gist/*/`

---

### Ruleset Commands (`gh ruleset`)

Ruleset commands use a **mix** of GraphQL and REST.

| Subcommand | API Type | Endpoint/Query                                     | Notes |
| ---------- | -------- | -------------------------------------------------- | ----- |
| `list`     | GraphQL  | `RepositoryRulesets` query                         |       |
| `view`     | REST     | `GET repos/{owner}/{repo}/rulesets/{id}`           |       |
| `check`    | REST     | `GET repos/{owner}/{repo}/rules/branches/{branch}` |       |

**Source files:** `pkg/cmd/ruleset/*/`

---

### Codespace Commands (`gh codespace`)

All codespace commands use **REST** API via the Codespaces API.

| Subcommand | API Type | Endpoint                              | Notes |
| ---------- | -------- | ------------------------------------- | ----- |
| `list`     | REST     | `GET user/codespaces`                 |       |
| `view`     | REST     | `GET user/codespaces/{name}`          |       |
| `create`   | REST     | `POST user/codespaces`                |       |
| `delete`   | REST     | `DELETE user/codespaces/{name}`       |       |
| `edit`     | REST     | `PATCH user/codespaces/{name}`        |       |
| `stop`     | REST     | `POST user/codespaces/{name}/stop`    |       |
| `rebuild`  | REST     | `POST user/codespaces/{name}/rebuild` |       |
| `code`     | REST     | Fetches codespace URL                 |       |
| `ssh`      | REST     | Fetches SSH details                   |       |
| `ports`    | REST     | `GET user/codespaces/{name}/ports`    |       |
| `logs`     | REST     | Fetches log stream URL                |       |
| `jupyter`  | REST     | Fetches Jupyter URL                   |       |

**Source files:** `pkg/cmd/codespace/*/`

---

### SSH Key Commands (`gh ssh-key`)

All SSH key commands use **REST** API.

| Subcommand | API Type | Endpoint                | Notes                      |
| ---------- | -------- | ----------------------- | -------------------------- |
| `list`     | REST     | `GET user/keys`         |                            |
| `add`      | REST     | `POST user/keys`        | Or `user/ssh_signing_keys` |
| `delete`   | REST     | `DELETE user/keys/{id}` |                            |

**Source files:** `pkg/cmd/ssh-key/*/`

---

### GPG Key Commands (`gh gpg-key`)

All GPG key commands use **REST** API.

| Subcommand | API Type | Endpoint                    | Notes |
| ---------- | -------- | --------------------------- | ----- |
| `list`     | REST     | `GET user/gpg_keys`         |       |
| `add`      | REST     | `POST user/gpg_keys`        |       |
| `delete`   | REST     | `DELETE user/gpg_keys/{id}` |       |

**Source files:** `pkg/cmd/gpg-key/*/`

---

### Organization Commands (`gh org`)

Organization commands use **GraphQL**.

| Subcommand | API Type | Query                    | Notes       |
| ---------- | -------- | ------------------------ | ----------- |
| `list`     | GraphQL  | `OrganizationList` query | User's orgs |

**Source files:** `pkg/cmd/org/*/`

---

### Status Command (`gh status`)

The status command uses a **mix** of GraphQL and REST.

| Operation       | API Type | Endpoint/Query                                  | Notes                      |
| --------------- | -------- | ----------------------------------------------- | -------------------------- |
| Search mentions | GraphQL  | Search query                                    | Finds mentions/assignments |
| Notifications   | REST     | `GET notifications`                             | Paginated                  |
| Comment details | REST     | `GET repos/{owner}/{repo}/issues/comments/{id}` |                            |

**Source files:** `pkg/cmd/status/`

---

### Extension Commands (`gh extension`)

Extension commands use **REST** for GitHub API access.

| Subcommand | API Type | Endpoint                                   | Notes                 |
| ---------- | -------- | ------------------------------------------ | --------------------- |
| `search`   | REST     | `GET search/repositories`                  | Topic: `gh-extension` |
| `browse`   | REST     | `GET search/repositories`                  |                       |
| `install`  | REST     | `GET repos/{owner}/{repo}/releases`        |                       |
| `upgrade`  | REST     | `GET repos/{owner}/{repo}/releases/latest` |                       |

**Source files:** `pkg/cmd/extension/*/`

---

### Auth Commands (`gh auth`)

Auth commands primarily use **REST** for validation.

| Subcommand  | API Type | Endpoint       | Notes                            |
| ----------- | -------- | -------------- | -------------------------------- |
| `login`     | REST     | `GET /` (root) | Validates token scopes           |
| `status`    | REST     | `GET /` (root) | Checks auth and scopes           |
| `token`     | N/A      | Local only     | Retrieves stored token           |
| `refresh`   | OAuth    | OAuth flow     | Re-authenticates                 |
| `logout`    | N/A      | Local only     | Removes stored credentials       |
| `setup-git` | N/A      | Local only     | Configures git credential helper |
| `switch`    | N/A      | Local only     | Switches active account          |

**Source files:** `pkg/cmd/auth/*/`

---

### Attestation Commands (`gh attestation`)

Attestation commands use **REST** API.

| Subcommand    | API Type | Endpoint        | Notes |
| ------------- | -------- | --------------- | ----- |
| `download`    | REST     | Attestation API |       |
| `inspect`     | REST     | Attestation API |       |
| `verify`      | REST     | Attestation API |       |
| `trustedroot` | REST     | Attestation API |       |

**Source files:** `pkg/cmd/attestation/*/`

---

## API Detection Methodology

This audit was performed by analyzing the gh CLI source code:

### Patterns Used

**REST API detection:**

```go
client.REST(hostname, method, path, body, data)
client.RESTWithNext(...)  // Paginated REST
ghinstance.RESTPrefix(host) + path  // Direct HTTP
```

**GraphQL API detection:**

```go
client.GraphQL(hostname, query, variables, data)  // Raw query
client.Query(hostname, name, query, variables)    // Structured query
client.Mutate(hostname, name, mutation, variables) // Mutations
gql.Query(...) / gql.Mutate(...)  // Via gql client
```

### File Naming Conventions

- `http.go` - HTTP/API layer implementation
- `queries_*.go` - GraphQL query definitions (in `api/`)
- `*_test.go` - Test files with mock API patterns

### Source Code Locations

| Package                | Purpose                             |
| ---------------------- | ----------------------------------- |
| `api/`                 | Core API client and GraphQL queries |
| `pkg/cmd/*/`           | Command implementations             |
| `pkg/search/`          | Search API implementation           |
| `internal/ghinstance/` | API endpoint URL construction       |

---

## Rate Limit Optimization Strategies

### Commands to Avoid in Tight Loops

**High-cost operations:**

- `gh pr view` with `--comments` or `--json` (deep nested GraphQL)
- `gh project item-list` with many fields
- `gh search` commands (30 req/min limit)
- Any `--paginate` operation with large datasets

### Commands Safe for Bulk Operations

**Efficient REST operations:**

- `gh run list` / `gh workflow list`
- `gh cache list`
- `gh secret list` / `gh variable list`
- `gh gist list`

### Batch Operation Alternatives

**Instead of multiple single queries:**

```bash
# Bad: Multiple API calls
for pr in 1 2 3 4 5; do gh pr view $pr; done

# Better: Single GraphQL query with aliases (via gh api graphql)
gh api graphql -f query='
  query {
    pr1: repository(owner:"owner", name:"repo") { pullRequest(number:1) { title } }
    pr2: repository(owner:"owner", name:"repo") { pullRequest(number:2) { title } }
  }
'
```

### Caching Strategies

**Use `--cache` flag where available:**

```bash
gh api /repos/{owner}/{repo} --cache 1h
```

**Conditional requests (automatic with gh api):**

- gh CLI sends `If-None-Match` headers automatically
- 304 responses don't count against primary rate limit

### Pagination Best Practices

**For GraphQL (pr, issue, project):**

- Use smaller `--limit` values for nested data
- Prefer `--json` with specific fields over full view

**For REST (run, workflow, search):**

- Use `--limit` to avoid fetching unnecessary pages
- Consider `--jq` filtering before pagination to reduce data

---

## See Also

- `gh.md` - Command reference and workflows
- `graphql.md` - GraphQL API patterns
- `graphql-schema-core.md` - GraphQL schema reference
- [GitHub REST API docs](https://docs.github.com/en/rest)
- [GitHub GraphQL API docs](https://docs.github.com/en/graphql)
