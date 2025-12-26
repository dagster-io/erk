"""Serializer for ContextStore to filesystem representation.

This module provides the inverse operation of loader.py - it takes a ContextStore
object and writes it to a filesystem tree following the expected layout conventions.

File System Layout:
-------------------
contextstore_project.yaml           # Project configuration
system_prompt.md                    # Optional global system prompt
cronjobs.yaml                       # Optional global cron jobs

docs/                               # Dataset documentation
  {connection}/                     # One dir per connection
    {table}.md                      # V1: Direct markdown files
    {table}/context/summary.md      # V2: Nested structure with manifest

context/                            # General context entries
  {group}/                          # Context category/group
    {name}.yaml                     # Individual context files

channels/                           # Channel-specific configuration
  {channel}/                        # One dir per channel
    system_prompt.md                # Optional channel system prompt
    cronjobs.yaml                   # Optional channel cron jobs
    context/                        # Channel-specific context
      {group}/                      # Context category/group
        {name}.yaml                 # Individual context files
"""

from pathlib import Path

import yaml

from csbot.contextengine.contextstore_protocol import ContextStore, TableFrontmatter
from csbot.utils.check_async_context import ensure_not_in_async_context


def _add_frontmatter_to_markdown(summary: str, frontmatter: TableFrontmatter) -> str:
    """Add frontmatter to markdown summary.

    Args:
        summary: Markdown content without frontmatter
        frontmatter: TableFrontmatter to add

    Returns:
        Complete markdown with frontmatter header
    """
    if summary.startswith("---"):
        raise ValueError("Summary already contains frontmatter")

    frontmatter_yaml = yaml.dump(
        frontmatter.model_dump(exclude_none=True),
        sort_keys=True,
        default_flow_style=False,
        allow_unicode=True,
    )
    return f"---\n{frontmatter_yaml}\n---\n{summary}"


def serialize_context_store(context_store: ContextStore, root_path: Path) -> None:
    """Serialize a ContextStore to filesystem representation.

    Args:
        context_store: ContextStore object to serialize
        root_path: Root directory path to write files to

    The function creates all necessary directories and files to represent
    the context store on disk following the expected layout conventions.
    """
    ensure_not_in_async_context()

    # Ensure root directory exists
    root_path.mkdir(parents=True, exist_ok=True)

    # 1. Write project configuration
    _write_project_config(context_store, root_path)

    # 2. Write system prompt if present
    _write_system_prompt(context_store, root_path)

    # 3. Write general cronjobs if present
    _write_general_cronjobs(context_store, root_path)

    # 4. Write dataset documentation
    _write_datasets(context_store, root_path)

    # 5. Write general context
    _write_general_context(context_store, root_path)

    # 6. Write channel-specific data
    _write_channels(context_store, root_path)


def _write_project_config(context_store: ContextStore, root_path: Path) -> None:
    """Write contextstore_project.yaml file."""
    config_path = root_path / "contextstore_project.yaml"
    config_data = context_store.project.model_dump(exclude_none=True)
    with open(config_path, "w") as f:
        yaml.safe_dump(
            config_data, f, sort_keys=False, default_flow_style=False, allow_unicode=True
        )


def _write_system_prompt(context_store: ContextStore, root_path: Path) -> None:
    """Write system_prompt.md file if present."""
    if context_store.system_prompt:
        prompt_path = root_path / "system_prompt.md"
        prompt_path.write_text(context_store.system_prompt)


def _write_general_cronjobs(context_store: ContextStore, root_path: Path) -> None:
    """Write general cronjobs to cronjobs/<name>.yaml files."""
    if not context_store.general_cronjobs:
        return

    cronjobs_dir = root_path / "cronjobs"
    cronjobs_dir.mkdir(exist_ok=True)

    for name, job in context_store.general_cronjobs.items():
        cronjob_path = cronjobs_dir / f"{name}.yaml"
        job_data = job.model_dump(exclude_none=True)
        with open(cronjob_path, "w") as f:
            yaml.safe_dump(
                job_data,
                f,
                sort_keys=False,
                default_flow_style=False,
                allow_unicode=True,
            )


def _write_datasets(context_store: ContextStore, root_path: Path) -> None:
    """Write dataset documentation files.

    Layout depends on project version:
    - V1: docs/{connection}/{table}.md
    - V2: docs/{connection}/{table}/context/summary.md
    """
    if not context_store.datasets:
        return

    docs_dir = root_path / "docs"
    docs_dir.mkdir(exist_ok=True)

    for dataset, documentation in context_store.datasets:
        connection_dir = docs_dir / dataset.connection
        connection_dir.mkdir(exist_ok=True)

        if context_store.project.version == 1:
            # V1 layout: docs/{connection}/{table}.md
            doc_path = connection_dir / f"{dataset.table_name}.md"
        elif context_store.project.version == 2:
            # V2 layout: docs/{connection}/{table}/context/summary.md
            table_context_dir = connection_dir / dataset.table_name / "context"
            table_context_dir.mkdir(parents=True, exist_ok=True)
            doc_path = table_context_dir / "summary.md"
        else:
            raise ValueError(f"Unsupported project version: {context_store.project.version}")

        # Write the documentation content with frontmatter
        if documentation.frontmatter:
            markdown_with_frontmatter = _add_frontmatter_to_markdown(
                documentation.summary, documentation.frontmatter
            )
        else:
            markdown_with_frontmatter = documentation.summary

        doc_path.write_text(markdown_with_frontmatter)


def _write_general_context(context_store: ContextStore, root_path: Path) -> None:
    """Write general context files to context/{group}/{name}.yaml."""
    if not context_store.general_context:
        return

    context_dir = root_path / "context"
    context_dir.mkdir(exist_ok=True)

    for named_context in context_store.general_context:
        group_dir = context_dir / named_context.group
        group_dir.mkdir(exist_ok=True)

        context_path = group_dir / f"{named_context.name}.yaml"
        context_data = named_context.context.model_dump(exclude_none=True)

        with open(context_path, "w") as f:
            yaml.safe_dump(
                context_data, f, sort_keys=False, default_flow_style=False, allow_unicode=True
            )


def _write_channels(context_store: ContextStore, root_path: Path) -> None:
    """Write channel-specific data to channels/{channel}/..."""
    if not context_store.channels:
        return

    channels_dir = root_path / "channels"
    channels_dir.mkdir(exist_ok=True)

    for channel_name, channel_context in context_store.channels.items():
        channel_dir = channels_dir / channel_name
        channel_dir.mkdir(exist_ok=True)

        # Write channel system prompt if present
        if channel_context.system_prompt:
            prompt_path = channel_dir / "system_prompt.md"
            prompt_path.write_text(channel_context.system_prompt)

        # Write channel cronjobs if present
        if channel_context.cron_jobs:
            cronjobs_dir = channel_dir / "cronjobs"
            cronjobs_dir.mkdir(exist_ok=True)

            for name, job in channel_context.cron_jobs.items():
                cronjob_path = cronjobs_dir / f"{name}.yaml"
                job_data = job.model_dump(exclude_none=True)
                with open(cronjob_path, "w") as f:
                    yaml.safe_dump(
                        job_data, f, sort_keys=False, default_flow_style=False, allow_unicode=True
                    )

        # Write channel-specific context
        if channel_context.context:
            context_dir = channel_dir / "context"
            context_dir.mkdir(exist_ok=True)

            for named_context in channel_context.context:
                group_dir = context_dir / named_context.group
                group_dir.mkdir(exist_ok=True)

                context_path = group_dir / f"{named_context.name}.yaml"
                context_data = named_context.context.model_dump(exclude_none=True)

                with open(context_path, "w") as f:
                    yaml.safe_dump(
                        context_data,
                        f,
                        sort_keys=False,
                        default_flow_style=False,
                        allow_unicode=True,
                    )
