import asyncio
from collections.abc import Iterable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from csbot.slackbot.channel_bot.bot import CompassChannelBaseBotInstance


async def get_connection_dataset_map(
    bot: "CompassChannelBaseBotInstance", connection_names: Iterable[str]
) -> dict[str, list[str]]:
    """Return datasets available for each connection by inspecting the context store."""
    # TODO this is wrong, this should use context store directly, not path traversal
    connection_name_set = {name for name in connection_names if name}
    if len(connection_name_set) == 0:
        return {}

    local_context_store = getattr(bot, "local_context_store", None)
    if local_context_store is None:
        return {}

    latest_file_tree_method = getattr(local_context_store, "latest_file_tree", None)
    if latest_file_tree_method is None:
        return {}

    dataset_map: dict[str, list[str]] = {}

    def _scan_context_store() -> dict[str, list[str]]:
        result: dict[str, list[str]] = {}
        context_manager = latest_file_tree_method()
        if not hasattr(context_manager, "__enter__") or not hasattr(context_manager, "__exit__"):
            return result

        with context_manager as tree:
            if not tree.is_dir("docs"):
                return result

            for connection_name in sorted(connection_name_set):
                docs_path = f"docs/{connection_name}"
                if not tree.is_dir(docs_path):
                    continue

                datasets: list[str] = []
                for entry in tree.listdir(docs_path):
                    # V1 layout: docs/{connection}/{table}.md
                    if entry.endswith(".md"):
                        file_path = f"{docs_path}/{entry}"
                        if tree.is_file(file_path):
                            # Strip .md extension to get fully qualified table name
                            datasets.append(entry[:-3])
                    # V2 layout: docs/{connection}/{table}/context/summary.md
                    else:
                        table_dir = f"{docs_path}/{entry}"
                        summary_path = f"{table_dir}/context/summary.md"
                        if tree.is_dir(table_dir) and tree.is_file(summary_path):
                            # Directory name is the fully qualified table name
                            datasets.append(entry)

                if len(datasets) > 0:
                    result[connection_name] = sorted(datasets)

        return result

    dataset_map = await asyncio.to_thread(_scan_context_store)
    return dataset_map
