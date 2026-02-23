<div align="center">
  <img width="64" height="64" alt="erk-oneshot" src="https://github.com/user-attachments/assets/d50143c7-bb42-49d7-8af9-f189fbe80f79" />
</div>

## Erk Slack Bot

### Prerequisites

- Slack app configured by following [SETUP.md](./SETUP.md)

### Setup

```bash
cp .env.example .env
uv sync
```

Fill in `.env` with your real Slack tokens:

```bash
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
```

### Run

```bash
make dev
```

`make dev` will automatically use a local editable `erk` from `~/src/erk` when present.
If that directory is missing, it falls back to the `erk` version installed from PyPI.

### Develop

Use a local `erk` checkout explicitly:

```bash
ERK_LOCAL_PATH=~/src/erk make dev
```

Check which `erk` version is being used (local editable if present, otherwise PyPI):

```bash
ERK_LOCAL_PATH=~/src/erk make erk-version
```

If you change Slack app config (scopes, bot events, or Socket Mode), reinstall the app and restart `make dev`.

### Slack Commands

- `@erk plan list`
- `@erk one-shot <message>`

The one-shot message is passed to `erk` as a single CLI argument via Click's in-process runner (`CliRunner`) and is never executed through a shell command string.
