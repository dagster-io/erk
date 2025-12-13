from typing import Any

SNOWFLAKE_PARTNER_APPLICATION = "DagsterLabs_CompassSnowflake"


def run_snowflake_query(connect_args: dict, query: str) -> list[dict[str, Any]]:
    import snowflake.connector

    params = dict(connect_args)
    params["application"] = SNOWFLAKE_PARTNER_APPLICATION

    conn = snowflake.connector.connect(
        **params,
    )
    with conn:
        conn.telemetry_enabled = False
        cursor = conn.cursor(snowflake.connector.DictCursor)
        cursor.execute(query)
        return [dict(row) for row in cursor.fetchall()]  # type: ignore
