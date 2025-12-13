import re
from pathlib import Path

import yaml

from csbot.contextengine.contextstore_protocol import (
    ChannelContext,
    ContextStore,
    ContextStoreProject,
    Dataset,
    DatasetDocumentation,
    NamedContext,
    ProvidedContext,
    TableFrontmatter,
    UserCronJob,
)
from csbot.local_context_store.git.file_tree import FilesystemFileTree, FileTree
from csbot.utils.check_async_context import ensure_not_in_async_context


def load_context_store(tree: FileTree) -> ContextStore:
    ensure_not_in_async_context()
    project = load_project_from_tree(tree)
    datasets = _get_datasets(tree, project)
    general_context = _load_general_context(tree)
    general_cronjobs = _load_general_cronjobs(tree)
    channels = _load_channels(tree)
    system_prompt = _load_system_prompt(tree)

    return ContextStore(
        project=project,
        datasets=[
            (dataset, _get_dataset_documentation(tree, project, dataset)) for dataset in datasets
        ],
        general_context=general_context,
        general_cronjobs=general_cronjobs,
        channels=channels,
        system_prompt=system_prompt,
    )


def load_project_from_tree(tree: FileTree) -> ContextStoreProject:
    """Load project configuration from a FileTree.

    Args:
        tree: FileTree instance to read from

    Returns:
        ContextStoreProject: The parsed project configuration
    """
    config_text = tree.read_text("contextstore_project.yaml")
    config = yaml.safe_load(config_text)
    return ContextStoreProject(**config)


def load_project_from_path(project_path: Path) -> ContextStoreProject:
    """Load project configuration from a filesystem path (cached).

    Args:
        project_path: Path to the directory containing contextstore_project.yaml

    Returns:
        ContextStoreProject: The parsed project configuration
    """
    return load_project_from_tree(FilesystemFileTree(project_path))


def get_dataset_schema_hash(
    tree: "FileTree",
    dataset: Dataset,
) -> str | None:
    """Get dataset schema hash from FileTree.

    Args:
        tree: FileTree instance to read from
        project: ContextStoreProject configuration
        dataset: Dataset to get schema hash for

    Returns:
        Schema hash string if found, None otherwise
    """
    context_store = load_context_store(tree)
    for ds, documentation in context_store.datasets:
        if ds == dataset:
            if documentation.frontmatter:
                return documentation.frontmatter.schema_hash
            else:
                return None

    return None


def _get_datasets(tree: FileTree, project: ContextStoreProject) -> list[Dataset]:
    datasets = []
    if not tree.is_dir("docs"):
        return datasets

    for connection_dir in tree.listdir("docs"):
        if not tree.is_dir(f"docs/{connection_dir}"):
            continue

        if project.version == 1:
            for dataset_file in tree.glob(f"docs/{connection_dir}", "*.md"):
                # Extract just the filename from the full path
                table_name = Path(dataset_file).stem
                dataset = Dataset(table_name=table_name, connection=connection_dir)
                datasets.append(dataset)
        elif project.version == 2:
            for table_dir in tree.listdir(f"docs/{connection_dir}"):
                if tree.is_dir(f"docs/{connection_dir}/{table_dir}") and tree.exists(
                    str(Path("docs") / connection_dir / table_dir / "context" / "summary.md")
                ):
                    dataset = Dataset(table_name=table_dir, connection=connection_dir)
                    datasets.append(dataset)
        else:
            raise ValueError(f"Unsupported project version: {project.version}")

    return datasets


def _get_dataset_documentation(
    tree: "FileTree",
    project: ContextStoreProject,
    dataset: Dataset,
) -> DatasetDocumentation:
    """Get dataset documentation (frontmatter + content) from FileTree.

    Args:
        tree: FileTree instance to read from
        project: ContextStoreProject configuration
        dataset: Dataset to get documentation for

    Returns:
        DatasetDocumentation with frontmatter and markdown content
    """
    if project.version == 1:
        # Legacy layout: docs/{connection}/{table}.md
        file_path = str(Path("docs") / dataset.connection / f"{dataset.table_name}.md")
    elif project.version == 2:
        # Manifest layout: docs/{connection}/{table}/context/summary.md
        file_path = str(
            Path("docs") / dataset.connection / dataset.table_name / "context" / "summary.md"
        )
    else:
        raise ValueError(f"Unsupported project version: {project.version}")

    # Read content
    if not tree.exists(file_path) or not tree.is_file(file_path):
        # Return empty documentation if file doesn't exist
        return DatasetDocumentation(frontmatter=None, summary="")

    content = tree.read_text(file_path)
    frontmatter, summary = _parse_frontmatter_and_summary(content)

    return DatasetDocumentation(frontmatter=frontmatter, summary=summary)


def _parse_frontmatter_and_summary(markdown: str) -> tuple[TableFrontmatter | None, str]:
    """Parse the frontmatter and summary from markdown content.

    Args:
        markdown: Full markdown content including frontmatter

    Returns:
        Tuple of (frontmatter, summary) where summary excludes the frontmatter
    """
    frontmatter_match = re.search(r"^---\n(.*?)\n---\n(.*)", markdown, re.DOTALL)
    if frontmatter_match:
        raw_frontmatter = frontmatter_match.group(1)
        summary = frontmatter_match.group(2)
        parsed_yaml = yaml.safe_load(raw_frontmatter)
        frontmatter = TableFrontmatter.model_validate(parsed_yaml)
        return frontmatter, summary
    return None, markdown


def _load_general_context(tree: FileTree) -> list[NamedContext]:
    """Load general context from context/**/*.yaml files.

    Args:
        tree: FileTree instance to read from

    Returns:
        List of NamedContext objects
    """
    contexts = []

    if not tree.exists("context") or not tree.is_dir("context"):
        return contexts

    for group_dir in tree.listdir("context"):
        group_path = f"context/{group_dir}"
        if not tree.is_dir(group_path):
            continue

        for context_file in tree.glob(group_path, "*.yaml"):
            file_path = f"{group_path}/{Path(context_file).name}"
            if not tree.is_file(file_path):
                continue

            content = tree.read_text(file_path)
            context_data = yaml.safe_load(content)
            provided_context = ProvidedContext.model_validate(context_data)

            name = Path(context_file).stem
            contexts.append(NamedContext(group=group_dir, name=name, context=provided_context))

    return contexts


def _load_general_cronjobs(tree: FileTree) -> dict[str, UserCronJob]:
    """Load general cronjobs from cronjobs/<name>.yaml files.

    Args:
        tree: FileTree instance to read from

    Returns:
        Dictionary mapping cronjob name to UserCronJob
    """
    cronjobs = {}

    if not tree.exists("cronjobs") or not tree.is_dir("cronjobs"):
        return cronjobs

    for cronjob_file in tree.glob("cronjobs", "*.yaml"):
        file_path = f"cronjobs/{Path(cronjob_file).name}"
        if not tree.is_file(file_path):
            continue

        content = tree.read_text(file_path)
        job_data = yaml.safe_load(content)
        name = Path(cronjob_file).stem
        cronjobs[name] = UserCronJob.model_validate(job_data)

    return cronjobs


def _load_channels(tree: FileTree) -> dict[str, ChannelContext]:
    """Load channel-specific contexts and cronjobs.

    Args:
        tree: FileTree instance to read from

    Returns:
        Dictionary mapping channel name to ChannelContext
    """
    channels = {}

    if not tree.exists("channels") or not tree.is_dir("channels"):
        return channels

    for channel_name in tree.listdir("channels"):
        channel_path = f"channels/{channel_name}"
        if not tree.is_dir(channel_path):
            continue

        channel_contexts = []
        channel_cronjobs = {}

        context_path = f"{channel_path}/context"
        if tree.exists(context_path) and tree.is_dir(context_path):
            for group_dir in tree.listdir(context_path):
                group_path = f"{context_path}/{group_dir}"
                if not tree.is_dir(group_path):
                    continue

                for context_file in tree.glob(group_path, "*.yaml"):
                    file_path = f"{group_path}/{Path(context_file).name}"
                    if not tree.is_file(file_path):
                        continue

                    content = tree.read_text(file_path)
                    context_data = yaml.safe_load(content)
                    provided_context = ProvidedContext.model_validate(context_data)

                    name = Path(context_file).stem
                    channel_contexts.append(
                        NamedContext(group=group_dir, name=name, context=provided_context)
                    )

        cronjobs_path = f"{channel_path}/cronjobs"
        if tree.exists(cronjobs_path) and tree.is_dir(cronjobs_path):
            for cronjob_file in tree.glob(cronjobs_path, "*.yaml"):
                file_path = f"{cronjobs_path}/{Path(cronjob_file).name}"
                if not tree.is_file(file_path):
                    continue

                content = tree.read_text(file_path)
                job_data = yaml.safe_load(content)
                name = Path(cronjob_file).stem
                channel_cronjobs[name] = UserCronJob.model_validate(job_data)

        # Load channel-specific system prompt
        channel_system_prompt = None
        system_prompt_file = f"{channel_path}/system_prompt.md"
        if tree.exists(system_prompt_file) and tree.is_file(system_prompt_file):
            channel_system_prompt = tree.read_text(system_prompt_file)

        channels[channel_name] = ChannelContext(
            cron_jobs=channel_cronjobs,
            context=channel_contexts,
            system_prompt=channel_system_prompt,
        )

    return channels


def _load_system_prompt(tree: FileTree) -> str | None:
    """Load general system prompt from system_prompt.md file.

    Args:
        tree: FileTree instance to read from

    Returns:
        System prompt content if found, None otherwise
    """
    if tree.exists("system_prompt.md") and tree.is_file("system_prompt.md"):
        return tree.read_text("system_prompt.md")
    return None
