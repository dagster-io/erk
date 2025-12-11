# contextstore: AI Context Management System

contextstore is a sophisticated AI context management system that helps organizations maintain, organize, and retrieve contextual information for data platform AI assistants. It provides a structured approach to storing domain knowledge, user feedback, and data documentation with intelligent categorization and search capabilities.

Today, contextstore is backing the Company Data AI bot, which is a Slackbot that can answer questions about the data platform.

Eventually, contextstore will be an integrated part of the company's data catalog, allowing all context in the catalog to be managed through git, as well as being available to all AI assistants that have access to the contextstore.

## 🔑 Key features and design principles

1. **Engineers are in control.** Context is managed through a real SDLC, and updates are made entirely through a pull request workflow and may have `CODEOWNERS`, CI/CD, etc.
2. **There is continuous implicit feedback from agents.** When a human corrects an agent, the agent automatically submits a PR to update the context. And when the agent needs data that isn't available, it will open a ticket requesting that data.
3. **Chatops and gitops.** The main interfaces to contextstore are CLIs, Slack bots, and git to appeal to both data analysts and hardcore engineers, neither of whom want yet another SaaS tool.
4. **Enterprise ready.** contextstore maintains the benefits of the hybrid architecture. Snowflake queries are issued on customer infrastructure using a user-specific credential if desired.

## 🏗️ Architecture Overview

contextstore consists of several key components:

- **Web Service Frontend**: A FastAPI-based REST API with JSON-RPC endpoints, providing an authenticated wrapper over the contextstore backend.
- **GitHub Storage**: All context is stored in a GitHub repository and can be directly manipulated by engineers. Changes via the API come in through a real pull request workflow. Missing data tickets are automatically filed via GitHub issues. This backend is pluggable and could easily be replaced with, say, Gitlab and Linear.
- **Command-Line Interface**: A command-line interface `csadmin` is provided for administration.

## 📁 Repository structure

contextstore repositories follow a "convention over configuration" approach, making it easy to get started while remaining flexible for advanced use cases:

- `contextstore_project.yaml`: A YAML file that serves as the anchor of the contextstore repository.
- `docs/`: A directory containing documentation for all tables available in the data platform. This can be automatically generated from a data platform instance with the `csadmin` tool.
- `system_prompt.md`: A file containing the system prompt for the contextstore. Use this to add any globally important context. For cost reasons, this file should be kept short.
- `context/`: Directory containing additional context that is not data documentation. Changes to this directory often come in from a live agent via a pull request.
- `context/project/`: Context that is relevant to the entire organization.
- `context/team/`: Context that is relevant to a specific team.
- `context/user/`: Context that is relevant to a specific user.

Also note that the contextstore repository has several GitHub issues that are automatically created by agents.

## 📚 Tutorial

Let's start by creating a brand new contextstore. First, be sure the `aidc` repo is set up and activated.

```bash
git checkout https://github.com/petehunt/aidc
cd aidc && uv sync && . venv/bin/activate
```

Next, let's create a new contextstore project.

```bash
$ git init mycontextstore

$ csadmin init mycontextstore --org-name "dagsterlabs" --project-name "mycontextstore"
Initializing new contextstore project...
Project initialized successfully!

$ tree mycontextstore
tree mycontextstore
mycontextstore
├── context
│   └── project
│       └── uncategorized
├── contextstore_project.yaml
├── docs
└── system_prompt.md

5 directories, 2 files
```

OK, we have a new contextstore project. Let's add some context about the former planet Pluto. We'll provide the `--project` flag to indicate that this context is relevant to the entire organization.

```bash
$ cd mycontextstore

$ csadmin add-context --topic "Pluto" --incorrect-understanding "Pluto is a planet" --correct-understanding "Pluto is a dwarf planet" --project
Generating context with AI...
✅ Context saved to ['context/project/uncategorized/20250630_Pluto-is-commonly-misunderstood-as-a-planet-but-it-is-actually-classified-as-a-dwarf-planet-according-to-current-astronomical-standards.yaml']

tree
.
├── context
│   └── project
│       └── uncategorized
│           └── 20250630_Pluto-is-commonly-misunderstood-as-a-planet-but-it-is-actually-classified-as-a-dwarf-planet-according-to-current-astronomical-standards.yaml
├── contextstore_project.yaml
├── docs
└── system_prompt.md

5 directories, 3 files

$ cat context/project/uncategorized/20250630_Pluto-is-commonly-misunderstood-as-a-planet-but-it-is-actually-classified-as-a-dwarf-planet-according-to-current-astronomical-standards.yaml
topic: Pluto
incorrect_understanding: Pluto is a planet
correct_understanding: Pluto is a dwarf planet
search_keywords: Pluto, dwarf planet, planet classification, astronomy, solar system,
  planetary status, astronomical reclassification, celestial bodies
```

Some users or teams may want to operate under a different set of assumptions about Pluto. Let's add some context scoped to a specific user.

```bash
$ csadmin add-context --topic "Pluto" --incorrect-understanding "Pluto is a planet" --correct-understanding "Pluto is actually flat" --user "crazybob"
...
```

OK, we have some context about Pluto. Let's run a few test searches to make sure everything is working properly.

```bash
$ csadmin search-context -q'Pluto'
Searching context...
File: context/project/uncategorized/20250630_Pluto-is-commonly-misunderstood-as-a-planet-but-it-is-actually-classified-as-a-dwarf-planet-according-to-current-astronomical-standards.yaml
Topic: Pluto
Incorrect Understanding: Pluto is a planet
Correct Understanding: Pluto is a dwarf planet
---
```

As you can see, the search results are scoped to the project context. We can also search for context scoped to a specific user.

```bash
$ csadmin search-context -q'Pluto' --user crazybob
Searching context...
File: context/user/crazybob/20250630_Pluto-was-reclassified-from-planet-to-dwarf-planet-in-2006-by-the-IAU-due-to-not-clearing-its-orbital-neighborhood-though-it-remains-spherical.yaml
Topic: Pluto
Incorrect Understanding: Pluto is a planet
Correct Understanding: Pluto is actually flat
---
File: context/project/uncategorized/20250630_Pluto-is-commonly-misunderstood-as-a-planet-but-it-is-actually-classified-as-a-dwarf-planet-according-to-current-astronomical-standards.yaml
Topic: Pluto
Incorrect Understanding: Pluto is a planet
Correct Understanding: Pluto is a dwarf planet
---
```

You can also create subfolders under `project/` other than `uncategorized` to organize your context. The contextstore server will use AI to make its best guess as to which folder a new piece of context should go into (don't worry, these changes come in via a pull request, so you'll have the ability to make changes before they land).

### Adding data documentation

Let's add some data documentation for a table in a Snowflake connection.

First, we need to create an `~/.aidc/.aidc_profile.yaml` file to store our Snowflake credentials.

```bash
$ cat - > ~/.aidc/.aidc_profile.yaml
projects:
  dagsterlabs/mycontextstore:
    connections:
      purina_snowflake:
        url: snowflake://na94824.us-east-1/SOFTWARE_ENGINEER?warehouse=PURINA&role=SOFTWARE_ENGI\
NEER&user=YOUR_EMAIL_HERE@example.com&authenticator=externalbrowser

$ csadmin add-dataset --connection purina_snowflake --table 'DWH_REPORTING.BUSINESS.OPPORTUNITIES'
Starting documentation generation for table 'DWH_REPORTING.BUSINESS.OPPORTUNITIES' in connection 'purina_snowflake'...
Loading project configuration...
Analyzing table structure and data...
  Getting table row count...
  Getting column information...
  Getting sample rows...
  Analyzing columns  [####################################]  100%
  ✓ Table analysis complete
Found 2536 rows and 76 columns
Generating markdown report...
Generating AI summary using Claude...
Creating documentation directory: docs/purina_snowflake
Writing documentation to docs/purina_snowflake/DWH_REPORTING.BUSINESS.OPPORTUNITIES.md...
✅ Documentation generated successfully in docs/purina_snowflake/DWH_REPORTING.BUSINESS.OPPORTUNITIES.md
```

After a quick OAuth with Snowflake, you will get a file that looks like this:

```markdown
$ head -n 20 docs/purina_snowflake/DWH_REPORTING.BUSINESS.OPPORTUNITIES.md

# Opportunities Table Analysis Summary

## Overall Dataset Characteristics

- **Total Rows**: 2,536 opportunities
- **Data Quality**: Generally good with most core fields populated, though many optional fields have high null rates
- **Notable Patterns**:
  - High proportion of closed lost opportunities (based on stage distribution)
  - Strong tracking of sales process stages and timeline data
  - Comprehensive revenue and forecasting fields
  - Rich attribution and campaign tracking data

## Core Opportunity Fields

### **OPPORTUNITY_ID** (VARCHAR(18))

- **Data Type**: Salesforce-style ID (18 characters)
- **Completeness**: 100% populated (primary key)
- **Usage**: Unique identifier for each opportunity

### **OPPORTUNITY_NAME** (VARCHAR(360))

- **Data Type**: Text, typically company/prospect names
```

You can also do this in bulk from a Dagster asset group:

```bash
$ csadmin add-datasets-from-dagster --url https://elementl.dagster.cloud/prod --asset-group business --code-location dagster_open_platform --connection purina_snowflake
```

### Deploying the contextstore server

Now that we have built a little contextstore repo, let's deploy it.

First, land the changes in the repo and push them to GitHub.

```bash
$ git add . && git commit -am'init' && git push origin HEAD:master
```

Next, put together a `.env` file with some credentials:

```
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
JWT_SECRET=<random string>
GITHUB_TOKEN=ghp_...
ANTHROPIC_API_KEY=sk-ant-api...
```

And start Redis:

```bash
$ docker run -d --name redis -p 6379:6379 redis:latest
```

And finally, start the contextstore JSON-RPC server:

```bash
contextstore-server start --github-repo owner/repo
```

### Connecting via MCP

Let's use Claude Desktop to query our data. The `aidc` - the AI Data Connector - is the tool that offers an MCP that combines both contextstore services and data warehouse access. It runs locally on your machine so no sensitive data is shared to the cloud.

First, let's log into our contextstore server. We can either do it with Google OAuth:

```bash
$ aidc login --server http://localhost:8000
Initiating login process...

Please visit this URL in your browser to login:
http://localhost:8000/auth/login?code=Y0zDGZfReQw6a9NwsP8wSNf291MkGIM_zAyI3cd95FE
```

Alternatively, you can use the CLI to generate an access token directly (useful for service accounts)

```bash
$ contextstore-server generate-token --email 'foo@bar.com' --days 90
<JWT TOKEN>

$ aidc login --server http://localhost:8000 --token '<JWT TOKEN>'
```

Now confirm everything worked:

```
$ aidc whoami
Logged in as: user@example.com
Server: http://localhost:8000/

$ aidc serverinfo
Getting server information...
Git Repository Information:
  Repository: ...
  Branch: refs/heads/master

Last Commit:
  Hash: ff05a3cf910f373be8c8d72f55c13a9e2b2e6885
  Author: ...
  Message: ...

$ aidc test-connection --connection purina_snowflake
✅ SQL connection OK
```

OK everything looks good, let's install it into Claude Desktop. Edit your `claude_desktop_config.json` to look something like this:

```json
{
  "mcpServers": {
    "aidc": {
      "command": "/path/to/aidc/.venv/bin/aidc",
      "args": ["mcp-server", "--envfile", "/path/to/aidc/.env"]
    }
  }
}
```

And now you can interact with your data, with all the proper business context!

![Claude Desktop with contextstore integration](./claude_desktop.png)

## contextstore JSON-RPC API definition

The contextstore API is responsible for abstracting away the storage backend and providing authentication and authorization. It also provides a full-text search service so the client doesn't have to pull down the whole context repo all the time.

Here's a Python representation of the JSON-RPC API used by contextstore. Auth is handled by a Bearer token.

```python
class ContextStoreServiceABC(ABC):
    """Abstract base class for AIDC service implementations."""

    @abstractmethod
    async def add_context(self, topic: str, incorrect_understanding: str, correct_understanding: str,
                         automatically_add_for_user: bool, comment_for_reviewer: str = "") -> AddContextResult:
        """Add context to the project."""
        pass

    @abstractmethod
    async def search_context(self, query: str) -> List[SearchContextResult]:
        """Search for context in the project."""
        pass

    @abstractmethod
    async def search_datasets(self, query: str, full: bool) -> List[DatasetSearchResult]:
        """Search datasets."""
        pass

    @abstractmethod
    async def server_info(self) -> ServerInfo:
        """Get server information including project config and git repo details."""
        pass

    @abstractmethod
    async def open_data_request_ticket(self, title: str, body: str) -> str:
        """Open a data request ticket in the GitHub repository. Returns the URL of the ticket."""
        pass

    @abstractmethod
    async def get_system_prompt(self) -> Optional[str]:
        """Get the system prompt for the project."""
        pass
```
