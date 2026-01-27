---
title: GitHub Actions API Reference
read_when:
  - "working with GitHub Actions API"
  - "automating CI/CD workflows"
  - "managing workflow runs programmatically"
  - "writing GitHub Actions YAML workflows"
  - "configuring workflow triggers"
  - "using GitHub Actions expressions"
---

# GitHub Actions API Reference

## Overview

This document catalogs the GitHub Actions REST API surface area and the workflow YAML DSL syntax. Use this as a reference when building CI/CD automation or interacting with GitHub Actions programmatically.

## REST API Categories

The GitHub Actions REST API is organized into 12 main categories:

| Category                  | Purpose                                           |
| ------------------------- | ------------------------------------------------- |
| Artifacts                 | Download, delete, and retrieve workflow artifacts |
| Cache                     | Manage cache retention, storage limits, and usage |
| GitHub-hosted runners     | Manage GitHub-hosted runner infrastructure        |
| OIDC                      | Customize OpenID Connect subject claims           |
| Permissions               | Configure Actions permissions and access controls |
| Secrets                   | Manage secrets at org/repo/environment levels     |
| Self-hosted runner groups | Organize and manage runner groups                 |
| Self-hosted runners       | Individual runner management and labels           |
| Variables                 | Manage configuration variables                    |
| Workflow jobs             | View job logs and status                          |
| Workflow runs             | Execute, cancel, re-run workflows                 |
| Workflows                 | List, enable, disable, and dispatch workflows     |

---

## Artifacts API

Artifacts enable sharing data between jobs and storing data after workflow completion.

| Method | Endpoint                                                                 | Description                 |
| ------ | ------------------------------------------------------------------------ | --------------------------- |
| GET    | `/repos/{owner}/{repo}/actions/artifacts`                                | List repository artifacts   |
| GET    | `/repos/{owner}/{repo}/actions/artifacts/{artifact_id}`                  | Get an artifact             |
| DELETE | `/repos/{owner}/{repo}/actions/artifacts/{artifact_id}`                  | Delete an artifact          |
| GET    | `/repos/{owner}/{repo}/actions/artifacts/{artifact_id}/{archive_format}` | Download an artifact        |
| GET    | `/repos/{owner}/{repo}/actions/runs/{run_id}/artifacts`                  | List workflow run artifacts |

---

## Cache API

### Enterprise Level

| Method | Endpoint                                                  |
| ------ | --------------------------------------------------------- |
| GET    | `/enterprises/{enterprise}/actions/cache/retention-limit` |
| PUT    | `/enterprises/{enterprise}/actions/cache/retention-limit` |
| GET    | `/enterprises/{enterprise}/actions/cache/storage-limit`   |
| PUT    | `/enterprises/{enterprise}/actions/cache/storage-limit`   |

### Organization Level

| Method | Endpoint                                             |
| ------ | ---------------------------------------------------- |
| GET    | `/organizations/{org}/actions/cache/retention-limit` |
| PUT    | `/organizations/{org}/actions/cache/retention-limit` |
| GET    | `/organizations/{org}/actions/cache/storage-limit`   |
| PUT    | `/organizations/{org}/actions/cache/storage-limit`   |
| GET    | `/orgs/{org}/actions/cache/usage`                    |
| GET    | `/orgs/{org}/actions/cache/usage-by-repository`      |

### Repository Level

| Method | Endpoint                                              |
| ------ | ----------------------------------------------------- |
| GET    | `/repos/{owner}/{repo}/actions/cache/retention-limit` |
| PUT    | `/repos/{owner}/{repo}/actions/cache/retention-limit` |
| GET    | `/repos/{owner}/{repo}/actions/cache/storage-limit`   |
| PUT    | `/repos/{owner}/{repo}/actions/cache/storage-limit`   |
| GET    | `/repos/{owner}/{repo}/actions/cache/usage`           |
| GET    | `/repos/{owner}/{repo}/actions/caches`                |
| DELETE | `/repos/{owner}/{repo}/actions/caches`                |
| DELETE | `/repos/{owner}/{repo}/actions/caches/{cache_id}`     |

---

## OIDC API

Customize OpenID Connect subject claims for cloud provider authentication.

| Method | Endpoint                                               | Description            |
| ------ | ------------------------------------------------------ | ---------------------- |
| GET    | `/orgs/{org}/actions/oidc/customization/sub`           | Get org OIDC template  |
| PUT    | `/orgs/{org}/actions/oidc/customization/sub`           | Set org OIDC template  |
| GET    | `/repos/{owner}/{repo}/actions/oidc/customization/sub` | Get repo OIDC template |
| PUT    | `/repos/{owner}/{repo}/actions/oidc/customization/sub` | Set repo OIDC template |

---

## Permissions API

### Organization Level

| Method | Endpoint                                                          |
| ------ | ----------------------------------------------------------------- |
| GET    | `/orgs/{org}/actions/permissions`                                 |
| PUT    | `/orgs/{org}/actions/permissions`                                 |
| GET    | `/orgs/{org}/actions/permissions/artifact-and-log-retention`      |
| PUT    | `/orgs/{org}/actions/permissions/artifact-and-log-retention`      |
| GET    | `/orgs/{org}/actions/permissions/fork-pr-contributor-approval`    |
| PUT    | `/orgs/{org}/actions/permissions/fork-pr-contributor-approval`    |
| GET    | `/orgs/{org}/actions/permissions/fork-pr-workflows-private-repos` |
| PUT    | `/orgs/{org}/actions/permissions/fork-pr-workflows-private-repos` |
| GET    | `/orgs/{org}/actions/permissions/repositories`                    |
| PUT    | `/orgs/{org}/actions/permissions/repositories`                    |
| PUT    | `/orgs/{org}/actions/permissions/repositories/{repository_id}`    |
| DELETE | `/orgs/{org}/actions/permissions/repositories/{repository_id}`    |
| GET    | `/orgs/{org}/actions/permissions/selected-actions`                |
| PUT    | `/orgs/{org}/actions/permissions/selected-actions`                |
| GET    | `/orgs/{org}/actions/permissions/self-hosted-runners`             |
| PUT    | `/orgs/{org}/actions/permissions/self-hosted-runners`             |
| GET    | `/orgs/{org}/actions/permissions/workflow`                        |
| PUT    | `/orgs/{org}/actions/permissions/workflow`                        |

### Repository Level

| Method | Endpoint                                                               |
| ------ | ---------------------------------------------------------------------- |
| GET    | `/repos/{owner}/{repo}/actions/permissions`                            |
| PUT    | `/repos/{owner}/{repo}/actions/permissions`                            |
| GET    | `/repos/{owner}/{repo}/actions/permissions/access`                     |
| PUT    | `/repos/{owner}/{repo}/actions/permissions/access`                     |
| GET    | `/repos/{owner}/{repo}/actions/permissions/artifact-and-log-retention` |
| PUT    | `/repos/{owner}/{repo}/actions/permissions/artifact-and-log-retention` |
| GET    | `/repos/{owner}/{repo}/actions/permissions/selected-actions`           |
| PUT    | `/repos/{owner}/{repo}/actions/permissions/selected-actions`           |
| GET    | `/repos/{owner}/{repo}/actions/permissions/workflow`                   |
| PUT    | `/repos/{owner}/{repo}/actions/permissions/workflow`                   |

---

## Secrets API

### Organization Secrets

| Method | Endpoint                                                                 |
| ------ | ------------------------------------------------------------------------ |
| GET    | `/orgs/{org}/actions/secrets`                                            |
| GET    | `/orgs/{org}/actions/secrets/public-key`                                 |
| GET    | `/orgs/{org}/actions/secrets/{secret_name}`                              |
| PUT    | `/orgs/{org}/actions/secrets/{secret_name}`                              |
| DELETE | `/orgs/{org}/actions/secrets/{secret_name}`                              |
| GET    | `/orgs/{org}/actions/secrets/{secret_name}/repositories`                 |
| PUT    | `/orgs/{org}/actions/secrets/{secret_name}/repositories`                 |
| PUT    | `/orgs/{org}/actions/secrets/{secret_name}/repositories/{repository_id}` |
| DELETE | `/orgs/{org}/actions/secrets/{secret_name}/repositories/{repository_id}` |

### Repository Secrets

| Method | Endpoint                                              |
| ------ | ----------------------------------------------------- |
| GET    | `/repos/{owner}/{repo}/actions/organization-secrets`  |
| GET    | `/repos/{owner}/{repo}/actions/secrets`               |
| GET    | `/repos/{owner}/{repo}/actions/secrets/public-key`    |
| GET    | `/repos/{owner}/{repo}/actions/secrets/{secret_name}` |
| PUT    | `/repos/{owner}/{repo}/actions/secrets/{secret_name}` |
| DELETE | `/repos/{owner}/{repo}/actions/secrets/{secret_name}` |

### Environment Secrets

| Method | Endpoint                                                                      |
| ------ | ----------------------------------------------------------------------------- |
| GET    | `/repos/{owner}/{repo}/environments/{environment_name}/secrets`               |
| GET    | `/repos/{owner}/{repo}/environments/{environment_name}/secrets/public-key`    |
| GET    | `/repos/{owner}/{repo}/environments/{environment_name}/secrets/{secret_name}` |
| PUT    | `/repos/{owner}/{repo}/environments/{environment_name}/secrets/{secret_name}` |
| DELETE | `/repos/{owner}/{repo}/environments/{environment_name}/secrets/{secret_name}` |

---

## Self-Hosted Runner Groups API

| Method | Endpoint                                                                           | Description              |
| ------ | ---------------------------------------------------------------------------------- | ------------------------ |
| GET    | `/orgs/{org}/actions/runner-groups`                                                | List runner groups       |
| POST   | `/orgs/{org}/actions/runner-groups`                                                | Create runner group      |
| GET    | `/orgs/{org}/actions/runner-groups/{runner_group_id}`                              | Get runner group         |
| PATCH  | `/orgs/{org}/actions/runner-groups/{runner_group_id}`                              | Update runner group      |
| DELETE | `/orgs/{org}/actions/runner-groups/{runner_group_id}`                              | Delete runner group      |
| GET    | `/orgs/{org}/actions/runner-groups/{runner_group_id}/repositories`                 | List repos with access   |
| PUT    | `/orgs/{org}/actions/runner-groups/{runner_group_id}/repositories`                 | Set repo access          |
| PUT    | `/orgs/{org}/actions/runner-groups/{runner_group_id}/repositories/{repository_id}` | Add repo access          |
| DELETE | `/orgs/{org}/actions/runner-groups/{runner_group_id}/repositories/{repository_id}` | Remove repo access       |
| GET    | `/orgs/{org}/actions/runner-groups/{runner_group_id}/runners`                      | List runners in group    |
| PUT    | `/orgs/{org}/actions/runner-groups/{runner_group_id}/runners`                      | Set runners in group     |
| PUT    | `/orgs/{org}/actions/runner-groups/{runner_group_id}/runners/{runner_id}`          | Add runner to group      |
| DELETE | `/orgs/{org}/actions/runner-groups/{runner_group_id}/runners/{runner_id}`          | Remove runner from group |

---

## Self-Hosted Runners API

### Organization Level

| Method | Endpoint                                                |
| ------ | ------------------------------------------------------- |
| GET    | `/orgs/{org}/actions/runners`                           |
| GET    | `/orgs/{org}/actions/runners/downloads`                 |
| POST   | `/orgs/{org}/actions/runners/generate-jitconfig`        |
| POST   | `/orgs/{org}/actions/runners/registration-token`        |
| POST   | `/orgs/{org}/actions/runners/remove-token`              |
| GET    | `/orgs/{org}/actions/runners/{runner_id}`               |
| DELETE | `/orgs/{org}/actions/runners/{runner_id}`               |
| GET    | `/orgs/{org}/actions/runners/{runner_id}/labels`        |
| POST   | `/orgs/{org}/actions/runners/{runner_id}/labels`        |
| PUT    | `/orgs/{org}/actions/runners/{runner_id}/labels`        |
| DELETE | `/orgs/{org}/actions/runners/{runner_id}/labels`        |
| DELETE | `/orgs/{org}/actions/runners/{runner_id}/labels/{name}` |

### Repository Level

| Method | Endpoint                                                          |
| ------ | ----------------------------------------------------------------- |
| GET    | `/repos/{owner}/{repo}/actions/runners`                           |
| GET    | `/repos/{owner}/{repo}/actions/runners/downloads`                 |
| POST   | `/repos/{owner}/{repo}/actions/runners/generate-jitconfig`        |
| POST   | `/repos/{owner}/{repo}/actions/runners/registration-token`        |
| POST   | `/repos/{owner}/{repo}/actions/runners/remove-token`              |
| GET    | `/repos/{owner}/{repo}/actions/runners/{runner_id}`               |
| DELETE | `/repos/{owner}/{repo}/actions/runners/{runner_id}`               |
| GET    | `/repos/{owner}/{repo}/actions/runners/{runner_id}/labels`        |
| POST   | `/repos/{owner}/{repo}/actions/runners/{runner_id}/labels`        |
| PUT    | `/repos/{owner}/{repo}/actions/runners/{runner_id}/labels`        |
| DELETE | `/repos/{owner}/{repo}/actions/runners/{runner_id}/labels`        |
| DELETE | `/repos/{owner}/{repo}/actions/runners/{runner_id}/labels/{name}` |

---

## Variables API

### Organization Variables

| Method | Endpoint                                                            |
| ------ | ------------------------------------------------------------------- |
| GET    | `/orgs/{org}/actions/variables`                                     |
| POST   | `/orgs/{org}/actions/variables`                                     |
| GET    | `/orgs/{org}/actions/variables/{name}`                              |
| PATCH  | `/orgs/{org}/actions/variables/{name}`                              |
| DELETE | `/orgs/{org}/actions/variables/{name}`                              |
| GET    | `/orgs/{org}/actions/variables/{name}/repositories`                 |
| PUT    | `/orgs/{org}/actions/variables/{name}/repositories`                 |
| PUT    | `/orgs/{org}/actions/variables/{name}/repositories/{repository_id}` |
| DELETE | `/orgs/{org}/actions/variables/{name}/repositories/{repository_id}` |

### Repository Variables

| Method | Endpoint                                               |
| ------ | ------------------------------------------------------ |
| GET    | `/repos/{owner}/{repo}/actions/organization-variables` |
| GET    | `/repos/{owner}/{repo}/actions/variables`              |
| POST   | `/repos/{owner}/{repo}/actions/variables`              |
| GET    | `/repos/{owner}/{repo}/actions/variables/{name}`       |
| PATCH  | `/repos/{owner}/{repo}/actions/variables/{name}`       |
| DELETE | `/repos/{owner}/{repo}/actions/variables/{name}`       |

### Environment Variables

| Method | Endpoint                                                                 |
| ------ | ------------------------------------------------------------------------ |
| GET    | `/repos/{owner}/{repo}/environments/{environment_name}/variables`        |
| POST   | `/repos/{owner}/{repo}/environments/{environment_name}/variables`        |
| GET    | `/repos/{owner}/{repo}/environments/{environment_name}/variables/{name}` |
| PATCH  | `/repos/{owner}/{repo}/environments/{environment_name}/variables/{name}` |
| DELETE | `/repos/{owner}/{repo}/environments/{environment_name}/variables/{name}` |

---

## Workflow Jobs API

| Method | Endpoint                                                                     | Description           |
| ------ | ---------------------------------------------------------------------------- | --------------------- |
| GET    | `/repos/{owner}/{repo}/actions/jobs/{job_id}`                                | Get a job             |
| GET    | `/repos/{owner}/{repo}/actions/jobs/{job_id}/logs`                           | Download job logs     |
| GET    | `/repos/{owner}/{repo}/actions/runs/{run_id}/attempts/{attempt_number}/jobs` | List jobs for attempt |
| GET    | `/repos/{owner}/{repo}/actions/runs/{run_id}/jobs`                           | List jobs for run     |

---

## Workflow Runs API

| Method | Endpoint                                                                     | Description             |
| ------ | ---------------------------------------------------------------------------- | ----------------------- |
| POST   | `/repos/{owner}/{repo}/actions/jobs/{job_id}/rerun`                          | Re-run a job            |
| GET    | `/repos/{owner}/{repo}/actions/runs`                                         | List workflow runs      |
| GET    | `/repos/{owner}/{repo}/actions/runs/{run_id}`                                | Get a workflow run      |
| DELETE | `/repos/{owner}/{repo}/actions/runs/{run_id}`                                | Delete a workflow run   |
| GET    | `/repos/{owner}/{repo}/actions/runs/{run_id}/approvals`                      | Get approvals           |
| POST   | `/repos/{owner}/{repo}/actions/runs/{run_id}/approve`                        | Approve a run           |
| GET    | `/repos/{owner}/{repo}/actions/runs/{run_id}/attempts/{attempt_number}`      | Get run attempt         |
| GET    | `/repos/{owner}/{repo}/actions/runs/{run_id}/attempts/{attempt_number}/logs` | Download attempt logs   |
| POST   | `/repos/{owner}/{repo}/actions/runs/{run_id}/cancel`                         | Cancel a run            |
| POST   | `/repos/{owner}/{repo}/actions/runs/{run_id}/force-cancel`                   | Force cancel a run      |
| GET    | `/repos/{owner}/{repo}/actions/runs/{run_id}/logs`                           | Download run logs       |
| DELETE | `/repos/{owner}/{repo}/actions/runs/{run_id}/logs`                           | Delete run logs         |
| GET    | `/repos/{owner}/{repo}/actions/runs/{run_id}/pending_deployments`            | Get pending deployments |
| POST   | `/repos/{owner}/{repo}/actions/runs/{run_id}/pending_deployments`            | Review deployments      |
| POST   | `/repos/{owner}/{repo}/actions/runs/{run_id}/rerun`                          | Re-run a workflow       |
| POST   | `/repos/{owner}/{repo}/actions/runs/{run_id}/rerun-failed-jobs`              | Re-run failed jobs      |
| GET    | `/repos/{owner}/{repo}/actions/runs/{run_id}/usage`                          | Get usage               |
| GET    | `/repos/{owner}/{repo}/actions/workflows/{workflow_id}/runs`                 | List runs for workflow  |

---

## Workflows API

| Method | Endpoint                                                           | Description         |
| ------ | ------------------------------------------------------------------ | ------------------- |
| GET    | `/repos/{owner}/{repo}/actions/workflows`                          | List workflows      |
| GET    | `/repos/{owner}/{repo}/actions/workflows/{workflow_id}`            | Get a workflow      |
| PUT    | `/repos/{owner}/{repo}/actions/workflows/{workflow_id}/disable`    | Disable a workflow  |
| POST   | `/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches` | Dispatch a workflow |
| PUT    | `/repos/{owner}/{repo}/actions/workflows/{workflow_id}/enable`     | Enable a workflow   |
| GET    | `/repos/{owner}/{repo}/actions/workflows/{workflow_id}/timing`     | Get workflow usage  |

---

## Authentication

### Token Types

- **Personal Access Token (classic)**: Requires `repo` scope for private repos, `public_repo` for public
- **Fine-grained PAT**: Requires "Actions" repository permission
- **GitHub App**: Installation tokens with `actions` permission
- **GITHUB_TOKEN**: Built-in token in workflow context

### API Version Header

```
X-GitHub-Api-Version: 2022-11-28
```

---

# Workflow YAML DSL Reference

Workflow files must be stored in `.github/workflows/` with `.yml` or `.yaml` extension.

## Top-Level Keys

### Metadata

```yaml
name: CI Pipeline # Display name in Actions tab
run-name: Deploy to ${{ inputs.env }} # Dynamic run name (supports expressions)
```

### Triggers (`on`)

#### Single Event

```yaml
on: push
```

#### Multiple Events

```yaml
on: [push, pull_request, fork]
```

#### Event with Filters

```yaml
on:
  push:
    branches: [main, develop]
    branches-ignore: [feature/*]
    tags: [v*]
    tags-ignore: [v*-beta]
    paths: [src/**, tests/**]
    paths-ignore: [docs/**]
```

#### Scheduled

```yaml
on:
  schedule:
    - cron: "0 0 * * *" # Daily at midnight UTC
```

#### Manual Dispatch

```yaml
on:
  workflow_dispatch:
    inputs:
      environment:
        description: "Target environment"
        required: true
        default: "staging"
        type: choice
        options: [staging, production]
```

#### Workflow Call (Reusable)

```yaml
on:
  workflow_call:
    inputs:
      config:
        required: true
        type: string
    secrets:
      token:
        required: true
```

### All Trigger Events

| Event                         | Activity Types                                                                                                                                                                                                                     |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `branch_protection_rule`      | created, edited, deleted                                                                                                                                                                                                           |
| `check_run`                   | created, rerequested, completed, requested_action                                                                                                                                                                                  |
| `check_suite`                 | completed                                                                                                                                                                                                                          |
| `create`                      | —                                                                                                                                                                                                                                  |
| `delete`                      | —                                                                                                                                                                                                                                  |
| `deployment`                  | —                                                                                                                                                                                                                                  |
| `deployment_status`           | —                                                                                                                                                                                                                                  |
| `discussion`                  | created, edited, deleted, transferred, pinned, unpinned, labeled, unlabeled, locked, unlocked, category_changed, answered, unanswered                                                                                              |
| `discussion_comment`          | created, edited, deleted                                                                                                                                                                                                           |
| `fork`                        | —                                                                                                                                                                                                                                  |
| `gollum`                      | —                                                                                                                                                                                                                                  |
| `issue_comment`               | created, edited, deleted                                                                                                                                                                                                           |
| `issues`                      | opened, edited, deleted, transferred, pinned, unpinned, closed, reopened, assigned, unassigned, labeled, unlabeled, locked, unlocked, milestoned, demilestoned                                                                     |
| `label`                       | created, edited, deleted                                                                                                                                                                                                           |
| `merge_group`                 | checks_requested                                                                                                                                                                                                                   |
| `milestone`                   | created, closed, opened, edited, deleted                                                                                                                                                                                           |
| `page_build`                  | —                                                                                                                                                                                                                                  |
| `public`                      | —                                                                                                                                                                                                                                  |
| `pull_request`                | opened, edited, closed, reopened, synchronize, converted_to_draft, ready_for_review, locked, unlocked, review_requested, review_request_removed, auto_merge_enabled, auto_merge_disabled, labeled, unlabeled, assigned, unassigned |
| `pull_request_review`         | submitted, edited, dismissed                                                                                                                                                                                                       |
| `pull_request_review_comment` | created, edited, deleted                                                                                                                                                                                                           |
| `pull_request_target`         | (same as pull_request)                                                                                                                                                                                                             |
| `push`                        | —                                                                                                                                                                                                                                  |
| `registry_package`            | published, updated                                                                                                                                                                                                                 |
| `release`                     | published, unpublished, created, edited, deleted, prereleased, released                                                                                                                                                            |
| `repository_dispatch`         | —                                                                                                                                                                                                                                  |
| `schedule`                    | —                                                                                                                                                                                                                                  |
| `status`                      | —                                                                                                                                                                                                                                  |
| `watch`                       | started                                                                                                                                                                                                                            |
| `workflow_call`               | —                                                                                                                                                                                                                                  |
| `workflow_dispatch`           | —                                                                                                                                                                                                                                  |
| `workflow_run`                | completed, requested, in_progress                                                                                                                                                                                                  |

### Permissions

```yaml
permissions:
  contents: read
  pull-requests: write
  issues: write
  actions: read

# Or use shortcuts
permissions: read-all
permissions: write-all
permissions: {}  # No permissions
```

### Environment Variables

```yaml
env:
  NODE_ENV: production
  CI: true
```

### Defaults

```yaml
defaults:
  run:
    shell: bash
    working-directory: ./src
```

### Concurrency

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

---

## Jobs Configuration

```yaml
jobs:
  build:
    name: Build Application
    runs-on: ubuntu-latest
    needs: [setup] # Job dependencies
    if: github.event_name == 'push' # Conditional execution
    timeout-minutes: 30
    continue-on-error: false

    environment:
      name: production
      url: https://example.com

    outputs:
      artifact_id: ${{ steps.upload.outputs.id }}

    env:
      BUILD_TYPE: release

    defaults:
      run:
        shell: bash

    strategy:
      fail-fast: false
      max-parallel: 3
      matrix:
        os: [ubuntu-latest, macos-latest]
        node: [18, 20]
        exclude:
          - os: macos-latest
            node: 18
        include:
          - os: ubuntu-latest
            node: 20
            experimental: true

    container:
      image: node:18
      credentials:
        username: ${{ secrets.DOCKER_USER }}
        password: ${{ secrets.DOCKER_TOKEN }}
      env:
        NODE_ENV: test
      ports: [8080]
      volumes:
        - /data:/data
      options: --cpus 1

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s

    steps:
      # ... steps configuration
```

### Runner Specification

```yaml
runs-on: ubuntu-latest              # GitHub-hosted
runs-on: [self-hosted, linux, x64]  # Self-hosted with labels
runs-on: ${{ matrix.os }}           # Dynamic from matrix
```

---

## Steps Configuration

```yaml
steps:
  - name: Checkout code
    id: checkout
    uses: actions/checkout@v4
    with:
      fetch-depth: 0
      token: ${{ secrets.GITHUB_TOKEN }}

  - name: Run tests
    run: npm test
    working-directory: ./app
    shell: bash
    env:
      CI: true
    continue-on-error: true
    timeout-minutes: 10
    if: success()

  - name: Multi-line script
    run: |
      echo "Line 1"
      echo "Line 2"

  - name: Use output from previous step
    run: echo "${{ steps.checkout.outputs.ref }}"
```

---

## Expressions

### Syntax

```yaml
${{ <expression> }}
```

### Contexts

| Context    | Description                                                                         |
| ---------- | ----------------------------------------------------------------------------------- |
| `github`   | Workflow run info (`github.sha`, `github.ref`, `github.actor`, `github.repository`) |
| `env`      | Environment variables                                                               |
| `vars`     | Configuration variables                                                             |
| `secrets`  | Secret values                                                                       |
| `job`      | Current job info (`job.status`)                                                     |
| `steps`    | Step outputs (`steps.<id>.outputs`, `steps.<id>.outcome`)                           |
| `runner`   | Runner info (`runner.os`, `runner.arch`, `runner.temp`)                             |
| `needs`    | Dependent job outputs (`needs.<job_id>.outputs`)                                    |
| `strategy` | Matrix info (`strategy.job-index`, `strategy.fail-fast`)                            |
| `matrix`   | Current matrix values                                                               |
| `inputs`   | Workflow inputs                                                                     |

### Functions

#### String Functions

| Function                    | Description                                  |
| --------------------------- | -------------------------------------------- |
| `contains(search, item)`    | Returns true if search contains item         |
| `startsWith(string, value)` | Returns true if string starts with value     |
| `endsWith(string, value)`   | Returns true if string ends with value       |
| `format(string, ...)`       | Format string with placeholders `{0}`, `{1}` |
| `join(array, separator)`    | Join array elements                          |

#### JSON Functions

| Function           | Description            |
| ------------------ | ---------------------- |
| `toJSON(value)`    | Convert to JSON string |
| `fromJSON(string)` | Parse JSON string      |

#### Other Functions

| Function               | Description                   |
| ---------------------- | ----------------------------- |
| `hashFiles(path, ...)` | SHA-256 hash of file contents |

#### Status Check Functions

| Function      | Description                          |
| ------------- | ------------------------------------ |
| `success()`   | True if all previous steps succeeded |
| `failure()`   | True if any previous step failed     |
| `always()`    | Always true (step runs regardless)   |
| `cancelled()` | True if workflow was cancelled       |

### Operators

```yaml
# Comparison
==, !=, <, <=, >, >=

# Logical
&&, ||, !

# Indexing
github.event.commits[0].message
matrix['node-version']
```

### Common Patterns

```yaml
# Conditional step
if: github.event_name == 'push' && github.ref == 'refs/heads/main'

# Check for label
if: contains(github.event.pull_request.labels.*.name, 'deploy')

# Run on failure
if: failure()

# Run even if cancelled
if: always()

# Skip if cancelled
if: "!cancelled()"
```

---

## Reusable Workflows

### Caller Workflow

```yaml
jobs:
  call-workflow:
    uses: org/repo/.github/workflows/reusable.yml@main
    with:
      config: production
    secrets:
      token: ${{ secrets.DEPLOY_TOKEN }}
    # Or inherit all secrets
    secrets: inherit
```

### Reusable Workflow

```yaml
on:
  workflow_call:
    inputs:
      config:
        required: true
        type: string
    outputs:
      result:
        description: "The result"
        value: ${{ jobs.build.outputs.result }}
    secrets:
      token:
        required: true

jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      result: ${{ steps.step1.outputs.result }}
    steps:
      - run: echo "Config: ${{ inputs.config }}"
```

---

## Sources

- [REST API endpoints for GitHub Actions](https://docs.github.com/en/rest/actions)
- [Workflow syntax for GitHub Actions](https://docs.github.com/actions/using-workflows/workflow-syntax-for-github-actions)
- [Events that trigger workflows](https://docs.github.com/actions/learn-github-actions/events-that-trigger-workflows)
- [Contexts reference](https://docs.github.com/en/actions/reference/workflows-and-actions/contexts)
- [Expressions](https://docs.github.com/en/actions/learn-github-actions/expressions)
