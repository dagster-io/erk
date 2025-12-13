import hashlib
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from urllib.parse import urlparse

import boto3
import yaml
from pydantic import BaseModel

from csbot.agents.protocol import AsyncAgent
from csbot.agents.sync import sync_generate_dataset_summary
from csbot.contextengine.contextstore_protocol import (
    ContextStore,
    Dataset,
    DatasetDocumentation,
    TableFrontmatter,
)
from csbot.csbot_client.csbot_client import SqlClient, get_connection_profile, get_sql_client
from csbot.csbot_client.csbot_profile import ProjectProfile
from csbot.slackbot.webapp.add_connections.models import JsonConfig


def quote_identifier(dialect: str, identifier: str) -> str:
    """
    Quote an identifier (column name, table name) according to the SQL dialect's rules.

    Args:
        dialect: The SQL dialect ('snowflake', 'bigquery', 'duckdb', 'aws_athena_trino_sql', 'aws_athena_spark_sql', 'redshift', 'postgres', 'databricks')
        identifier: The identifier to quote

    Returns:
        The properly quoted identifier
    """
    if dialect == "snowflake":
        # Snowflake uses double quotes and is case-sensitive when quoted
        return f'"{identifier}"'
    elif dialect == "bigquery":
        # BigQuery uses backticks for identifiers
        return f"`{identifier}`"
    elif dialect == "duckdb":
        # DuckDB uses double quotes like standard SQL
        return f'"{identifier}"'
    elif dialect in ["aws_athena_trino_sql", "aws_athena_spark_sql"]:
        return f'"{identifier}"'
    elif dialect == "redshift":
        return f'"{identifier}"'
    elif dialect == "postgres":
        # PostgreSQL uses double quotes like standard SQL
        return f'"{identifier}"'
    elif dialect == "databricks":
        # Databricks uses backticks for identifiers
        return f"`{identifier}`"
    else:
        raise ValueError(f"Unsupported dialect for identifier quoting: {dialect}")


def _get_bigquery_sample_with_fallback(sql_client, table_name, sample_percentage, num_sample_rows):
    """
    Try BigQuery TABLESAMPLE, fallback for views.

    BigQuery's TABLESAMPLE doesn't work on views, so we use exception handling
    to detect this case. This is acceptable because there's no reliable way
    to determine a priori whether a table supports TABLESAMPLE.
    """
    try:
        return sql_client.run_sql_query(
            f"SELECT * FROM {table_name} TABLESAMPLE SYSTEM ({sample_percentage} PERCENT) "
            f"order by rand() limit {num_sample_rows}"
        )
    except Exception:
        return sql_client.run_sql_query(
            f"SELECT * FROM {table_name} ORDER BY RAND() LIMIT {num_sample_rows}"
        )


def _get_duckdb_sample_with_fallback(sql_client, table_name, sample_percentage, num_sample_rows):
    """
    Try DuckDB USING SAMPLE, fallback to ORDER BY RANDOM.

    DuckDB's USING SAMPLE may not work in all contexts, so we fall back
    to ORDER BY RANDOM when it fails.
    """
    try:
        return sql_client.run_sql_query(
            f"SELECT * FROM {table_name} USING SAMPLE {sample_percentage}% ORDER BY RANDOM() "
            f"LIMIT {num_sample_rows}"
        )
    except Exception:
        return sql_client.run_sql_query(
            f"SELECT * FROM {table_name} ORDER BY RANDOM() LIMIT {num_sample_rows}"
        )


class ColumnAnalysis(BaseModel):
    name: str
    type: str
    column_comment: str | None
    null_percentage: float
    min: Any | None = None
    max: Any | None = None
    unique_values: list[Any] | None = None
    unique_values_count: int | None = None
    is_enum: bool | None = None
    enum_values: list[Any] | None = None
    sample_values: list[Any] | None = None


class TableAnalysis(BaseModel):
    table_name: str
    table_comment: str | None
    row_count: int
    columns: list[ColumnAnalysis]
    sample_rows: list[dict[str, Any]]


class ColumnDescription(BaseModel):
    name: str
    type: str
    column_comment: str | None


class TableSchemaAnalysis(BaseModel):
    table_name: str
    columns: list[ColumnDescription]
    schema_hash: str
    table_comment: str | None


def add_frontmatter_to_markdown(summary: str, frontmatter: TableFrontmatter) -> str:
    """
    Add the frontmatter to the markdown.
    """
    if summary.startswith("---"):
        raise ValueError("Frontmatter already exists")
    return f"---\n{yaml.dump(frontmatter.model_dump())}\n---\n{summary}"


def get_boto3_glue_client(profile: ProjectProfile, dataset: Dataset):
    connection_profile = get_connection_profile(profile, dataset.connection)
    url_parts = urlparse(connection_profile.url)

    # Handle jsonconfig URLs (new format)
    if url_parts.scheme == "jsonconfig":
        json_config = JsonConfig.from_url(connection_profile.url)
        if json_config.type != "athena":
            raise ValueError(f"Expected Athena connection type; got: {json_config.type}")

        athena_config = json_config.config
        return boto3.client(
            "glue",
            aws_access_key_id=athena_config["aws_access_key_id"],
            aws_secret_access_key=athena_config["aws_secret_access_key"],
            region_name=athena_config["region"],
        )

    # Handle legacy awsathena+rest URLs (old format)
    elif url_parts.scheme != "awsathena+rest":
        raise ValueError(f"Unsupported Athena URL scheme; got: {url_parts.scheme}")

    if url_parts.hostname is None:
        raise ValueError("Invalid PyAthena URL")

    literal_athena, region, literal_amazonaws_com = url_parts.hostname.split(".", 2)
    if literal_athena != "athena" or literal_amazonaws_com != "amazonaws.com":
        raise ValueError(f"Expected Athena hostname; got: {url_parts.hostname}")

    return boto3.client(
        "glue",
        aws_access_key_id=url_parts.username,
        aws_secret_access_key=url_parts.password,
        region_name=region,
    )


def analyze_table_schema(
    logger: logging.Logger | logging.LoggerAdapter,
    profile: ProjectProfile,
    dataset: Dataset,
) -> TableSchemaAnalysis:
    """
    Analyze the schema of a table in Snowflake, BigQuery, DuckDB, Athena, Redshift, PostgreSQL, or Databricks.
    """
    sql_client = get_sql_client(profile, dataset.connection)
    logger.debug(
        f"Getting column information for `{dataset.table_name}` in `{dataset.connection}`..."
    )
    table_comment = None
    if sql_client.dialect == "snowflake":
        # DESCRIBE VIEW works for tables or views
        columns = sql_client.run_sql_query(f"DESCRIBE VIEW {dataset.table_name}")
        columns = lowercase_keys(columns)
        column_descriptions = [
            ColumnDescription(
                name=column["name"], type=column["type"], column_comment=column["comment"]
            )
            for column in columns
        ]
        prefix, suffix = dataset.table_name.rsplit(".", 1)
        table_rows = sql_client.run_sql_query(f"SHOW TABLES IN {prefix}")
        view_rows = sql_client.run_sql_query(f"SHOW VIEWS IN {prefix}")
        all_rows = lowercase_keys(table_rows + view_rows)
        for row in all_rows:
            if row["name"].lower() == suffix.lower():
                table_comment = row["comment"]
                break

    elif sql_client.dialect == "bigquery":
        # replace the final dotted portion with INFORMATION_SCHEMA.COLUMNS
        dataset_name, nonqualified_table_name = dataset.table_name.rsplit(".", 1)
        columns = sql_client.run_sql_query(
            f"SELECT * FROM {dataset_name}.INFORMATION_SCHEMA.COLUMN_FIELD_PATHS WHERE table_name = "
            f"'{nonqualified_table_name}' and field_path = column_name"
        )
        column_descriptions = [
            ColumnDescription(
                name=column["column_name"],
                type=column["data_type"],
                column_comment=column["description"],
            )
            for column in columns
        ]

        option_rows = sql_client.run_sql_query(f"""
        SELECT option_value FROM {dataset_name}.INFORMATION_SCHEMA.TABLE_OPTIONS
        WHERE lower(table_name) = '{nonqualified_table_name.lower()}' AND option_name = 'table_comment'
        """)
        if len(option_rows) > 0:
            table_comment = option_rows[0]["option_value"]

    elif sql_client.dialect == "duckdb":
        # DuckDB uses PRAGMA table_info for schema information
        if "." not in dataset.table_name:
            # Test data
            columns = sql_client.run_sql_query(
                f"select column_name, data_type, comment from duckdb_columns() where lower(table_name)='{dataset.table_name.lower()}'"
            )
        else:
            # motherduck
            if dataset.table_name.count(".") != 2:
                raise ValueError(
                    f"Invalid table name: {dataset.table_name}. MotherDuck tables must be in the format <database_name>.<schema_name>.<table_name>"
                )
            database_name, schema_name, table_name = dataset.table_name.split(".")
            columns = sql_client.run_sql_query(
                f"select column_name, data_type, comment from duckdb_columns() where lower(table_name)='{table_name.lower()}' and lower(schema_name)='{schema_name.lower()}' and lower(database_name)='{database_name.lower()}'"
            )
        column_descriptions = [
            ColumnDescription(
                name=column["column_name"],
                type=column["data_type"],
                column_comment=column["comment"],
            )
            for column in columns
        ]

        if "." not in dataset.table_name:
            table_metadata_rows = sql_client.run_sql_query(f"""
            select TABLE_COMMENT from information_schema.tables where lower(table_name) = '{dataset.table_name.lower()}'
            """)
        else:
            if dataset.table_name.count(".") != 2:
                raise ValueError(
                    f"Invalid table name: {dataset.table_name}. MotherDuck tables must be in the format <database_name>.<schema_name>.<table_name>"
                )
            database_name, schema_name, table_name = dataset.table_name.split(".")
            table_metadata_rows = sql_client.run_sql_query(f"""
            select TABLE_COMMENT from information_schema.tables where lower(table_name) = '{table_name.lower()}' and lower(table_schema)='{schema_name.lower()}'
            """)
        if len(table_metadata_rows) > 0:
            table_comment = table_metadata_rows[0]["TABLE_COMMENT"]

    elif sql_client.dialect in ["aws_athena_trino_sql", "aws_athena_spark_sql"]:
        # Athena uses INFORMATION_SCHEMA for both Trino and Spark engines
        if dataset.table_name.count(".") != 1:
            raise ValueError(
                f"Invalid table name: {dataset.table_name}. Athena tables must be in the format <database_name>.<table_name>"
            )

        database_name, table_name_only = dataset.table_name.rsplit(".", 1)

        client = get_boto3_glue_client(profile, dataset)
        response = client.get_table(DatabaseName=database_name, Name=table_name_only)
        table_comment = response["Table"].get("Description")
        if table_comment is None or len(table_comment.strip()) == 0:
            table_comment = response["Table"]["Parameters"].get("comment")

        column_descriptions: list[ColumnDescription] = []
        for column in response["Table"]["StorageDescriptor"]["Columns"]:
            comment = column.get("Comment")
            if comment is None or len(comment.strip()) == 0:
                comment = None
            column_descriptions.append(
                ColumnDescription(
                    name=column["Name"],
                    type=column["Type"],
                    column_comment=comment,
                )
            )

    elif sql_client.dialect == "redshift":
        parts = dataset.table_name.split(".")
        schema = parts[-2]
        table = parts[-1]

        rows = sql_client.run_sql_query(
            f"""
            SELECT remarks
            FROM svv_all_tables
            WHERE schema_name = '{schema}' AND table_name = '{table}'
            """
        )
        if len(rows) > 0:
            table_comment = rows[0]["remarks"]

        rows = sql_client.run_sql_query(
            f"""
            SELECT ordinal_position, column_name, data_type, remarks
            FROM SVV_COLUMNS
            WHERE table_schema = '{schema}' AND table_name = '{table}'
            ORDER BY ordinal_position
            """
        )
        column_descriptions = [
            ColumnDescription(
                name=column["column_name"],
                type=column["data_type"],
                column_comment=column["remarks"],
            )
            for column in rows
        ]

    elif sql_client.dialect == "postgres":
        parts = dataset.table_name.split(".")
        schema = parts[-2]
        table = parts[-1]

        # Get table comment
        rows = sql_client.run_sql_query(
            f"""
            SELECT obj_description(c.oid) as table_comment
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = '{schema}' AND c.relname = '{table}'
            """
        )
        if len(rows) > 0 and rows[0]["table_comment"]:
            table_comment = rows[0]["table_comment"]

        # Get column information
        rows = sql_client.run_sql_query(
            f"""
            SELECT 
                ordinal_position,
                column_name,
                data_type,
                is_nullable,
                column_default,
                obj_description(pgc.oid) as column_comment
            FROM information_schema.columns c
            LEFT JOIN pg_class pgc ON pgc.relname = c.table_name
            LEFT JOIN pg_namespace pgn ON pgn.oid = pgc.relnamespace AND pgn.nspname = c.table_schema
            WHERE table_schema = '{schema}' AND table_name = '{table}'
            ORDER BY ordinal_position
            """
        )
        column_descriptions = [
            ColumnDescription(
                name=column["column_name"],
                type=column["data_type"],
                column_comment=column["column_comment"],
            )
            for column in rows
        ]

    elif sql_client.dialect == "databricks":
        # Databricks uses Unity Catalog format: catalog.schema.table
        if dataset.table_name.count(".") != 2:
            raise ValueError(
                f"Invalid table name: {dataset.table_name}. Databricks tables must be in the format <catalog>.<schema>.<table>"
            )
        catalog, schema, table = dataset.table_name.split(".", 2)

        # Get column information using DESCRIBE TABLE
        columns = sql_client.run_sql_query(f"DESCRIBE TABLE {dataset.table_name}")
        columns = lowercase_keys(columns)
        column_descriptions = [
            ColumnDescription(
                name=column["col_name"],
                type=column["data_type"],
                column_comment=column.get("comment"),
            )
            for column in columns
            if column["col_name"] != ""  # Skip empty rows that separate sections in DESCRIBE output
        ]

        # Get table comment from SHOW TABLES
        try:
            tables_result = sql_client.run_sql_query(f"SHOW TABLES IN {catalog}.{schema}")
            # Databricks returns camelCase field names (tableName, comment)
            for row in tables_result:
                table_name = row.get("tableName") or row.get("tablename")
                if table_name and table_name.lower() == table.lower():
                    table_comment = row.get("comment")
                    break
        except Exception:
            # If SHOW TABLES fails, try INFORMATION_SCHEMA
            try:
                rows = sql_client.run_sql_query(
                    f"""
                    SELECT comment
                    FROM {catalog}.information_schema.tables
                    WHERE table_schema = '{schema}' AND table_name = '{table}'
                    """
                )
                if len(rows) > 0 and rows[0].get("comment"):
                    table_comment = rows[0]["comment"]
            except Exception:
                table_comment = None

    else:
        raise ValueError(f"Unsupported dialect: {sql_client.dialect}")
    if len(column_descriptions) == 0:
        raise ValueError(f"No columns found for {dataset.table_name}")
    schema = hashlib.sha256(
        json.dumps(
            [
                (column_description.name, column_description.type)
                for column_description in sorted(column_descriptions, key=lambda x: x.name)
            ],
            sort_keys=True,
        ).encode()
    ).hexdigest()
    return TableSchemaAnalysis(
        table_name=dataset.table_name,
        columns=column_descriptions,
        schema_hash=schema,
        table_comment=table_comment,
    )


def lowercase_keys(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [dict((k.lower(), v) for k, v in row.items()) for row in rows]


def analyze_table(
    logger: logging.Logger,
    sql_client: SqlClient,
    table_schema_analysis: TableSchemaAnalysis,
    column_analysis_threadpool: ThreadPoolExecutor,
) -> TableAnalysis:
    """
    Analyze a table in Snowflake, BigQuery, DuckDB, Athena, Redshift, PostgreSQL, or Databricks to understand its structure and data.

    Args:
        table_name: Name of the table to analyze

    Returns:
        TableAnalysis object containing the analysis results
    """
    if sql_client.dialect not in [
        "snowflake",
        "bigquery",
        "duckdb",
        "aws_athena_trino_sql",
        "aws_athena_spark_sql",
        "redshift",
        "postgres",
        "databricks",
    ]:
        raise ValueError(
            f"analyze_table only supports Snowflake, BigQuery, DuckDB, Athena, Redshift, PostgreSQL, and Databricks, got {sql_client.dialect}"
        )

    table_name = table_schema_analysis.table_name

    logger.info("Getting table row count...")
    # Get basic table info
    row_count_result = sql_client.run_sql_query(f"SELECT COUNT(*) as count FROM {table_name}")
    row_count_result = lowercase_keys(row_count_result)
    row_count = row_count_result[0]["count"]

    logger.info("Getting sample rows...")
    # Get sample rows
    num_sample_rows = 5
    if sql_client.dialect == "snowflake":
        sample_rows = sql_client.run_sql_query(
            f"SELECT * FROM {table_name} SAMPLE ({num_sample_rows} ROWS)"
        )
    elif sql_client.dialect == "bigquery":
        if row_count == 0:
            sample_percentage = 100
        else:
            sample_percentage = min(
                100, (2 * (num_sample_rows / row_count) * 100)
            )  # we probably don't need the overfetch but better safe than sorry!
        sample_rows = _get_bigquery_sample_with_fallback(
            sql_client, table_name, sample_percentage, num_sample_rows
        )
    elif sql_client.dialect == "duckdb":
        # DuckDB uses USING SAMPLE for sampling
        if row_count == 0:
            sample_percentage = 100
        else:
            sample_percentage = min(100, (2 * (num_sample_rows / row_count) * 100))
        sample_rows = _get_duckdb_sample_with_fallback(
            sql_client, table_name, sample_percentage, num_sample_rows
        )
    elif sql_client.dialect in ["aws_athena_trino_sql", "aws_athena_spark_sql"]:
        # Athena doesn't have built-in sampling, use ORDER BY RANDOM() with LIMIT
        sample_rows = sql_client.run_sql_query(
            f"SELECT * FROM {table_name} ORDER BY RANDOM() LIMIT {num_sample_rows}"
        )
    elif sql_client.dialect == "redshift":
        if row_count == 0:
            sample_percentage = 100
        else:
            sample_percentage = min(100, (2 * (num_sample_rows / row_count) * 100))
        try:
            sample_rows = sql_client.run_sql_query(
                f"SELECT * FROM {table_name} TABLESAMPLE BERNOULLI ({sample_percentage}) ORDER BY RANDOM() LIMIT {num_sample_rows}"
            )
        except Exception:
            sample_rows = sql_client.run_sql_query(
                f"SELECT * FROM {table_name} ORDER BY RANDOM() LIMIT {num_sample_rows}"
            )

    elif sql_client.dialect == "postgres":
        # PostgreSQL uses TABLESAMPLE for sampling
        if row_count == 0:
            sample_percentage = 100
        else:
            sample_percentage = min(100, (2 * (num_sample_rows / row_count) * 100))
        try:
            sample_rows = sql_client.run_sql_query(
                f"SELECT * FROM {table_name} TABLESAMPLE BERNOULLI ({sample_percentage}) ORDER BY RANDOM() LIMIT {num_sample_rows}"
            )
        except Exception:
            # Fallback to simple random sampling if TABLESAMPLE is not supported
            sample_rows = sql_client.run_sql_query(
                f"SELECT * FROM {table_name} ORDER BY RANDOM() LIMIT {num_sample_rows}"
            )

    elif sql_client.dialect == "databricks":
        # Databricks supports TABLESAMPLE or ORDER BY RAND() with LIMIT
        if row_count == 0:
            sample_percentage = 100
        else:
            sample_percentage = min(100, (2 * (num_sample_rows / row_count) * 100))
        try:
            sample_rows = sql_client.run_sql_query(
                f"SELECT * FROM {table_name} TABLESAMPLE ({sample_percentage} PERCENT) ORDER BY RAND() LIMIT {num_sample_rows}"
            )
        except Exception:
            # Fallback to simple random sampling if TABLESAMPLE is not supported
            sample_rows = sql_client.run_sql_query(
                f"SELECT * FROM {table_name} ORDER BY RAND() LIMIT {num_sample_rows}"
            )

    else:
        raise ValueError(f"Unsupported dialect: {sql_client.dialect}")

    logger.info(
        f"Analyzing {len(table_schema_analysis.columns)} columns (this may take a while)..."
    )

    # Analyze each column
    def analyze_column(i: int, col: ColumnDescription) -> ColumnAnalysis:
        logger.debug(
            f"Analyzing column {col.name} ({i + 1}/{len(table_schema_analysis.columns)})..."
        )
        analysis = ColumnAnalysis(
            name=col.name, type=col.type, column_comment=col.column_comment, null_percentage=0.0
        )

        # Calculate null percentage
        quoted_col_name = quote_identifier(sql_client.dialect, col.name)
        null_count_result = sql_client.run_sql_query(
            f"SELECT COUNT(*) as null_count FROM {table_name} WHERE {quoted_col_name} IS NULL",
        )
        null_count_result = lowercase_keys(null_count_result)
        null_count = null_count_result[0]["null_count"]
        if row_count == 0:
            analysis.null_percentage = 0.0
        else:
            analysis.null_percentage = (null_count / row_count) * 100

        # For numeric types, get min/max
        numeric_types = [
            "NUMBER",
            "DECIMAL",
            "INTEGER",
            "INT",
            "BIGINT",
            "SMALLINT",
            "TINYINT",
            "FLOAT",
            "DOUBLE",
            "REAL",
        ]
        if any(t in col.type.upper() for t in numeric_types):
            try:
                stats_result = sql_client.run_sql_query(
                    f"SELECT MIN({quoted_col_name}) as min_val, MAX({quoted_col_name}) as max_val "
                    f"FROM {table_name}",
                )
                stats_result = lowercase_keys(stats_result)
                stats = stats_result[0]
                analysis.min = stats["min_val"]
                analysis.max = stats["max_val"]
            except Exception as e:
                logger.debug(f"Could not compute min/max for column {col.name}: {e}")
                # Skip min/max for problematic columns (e.g., struct types)

        # Check if column might be an enum by looking at unique values
        try:
            unique_values_count_result = sql_client.run_sql_query(
                f"SELECT COUNT(DISTINCT {quoted_col_name}) as unique_count FROM {table_name}",
            )
            unique_values_count_result = lowercase_keys(unique_values_count_result)
            unique_values_count = unique_values_count_result[0]["unique_count"]
            analysis.unique_values_count = unique_values_count

            unique_values_result = sql_client.run_sql_query(
                f"SELECT DISTINCT {quoted_col_name} as v FROM {table_name} "
                f"ORDER BY {quoted_col_name} LIMIT 10",
            )
            unique_values_result = lowercase_keys(unique_values_result)
            unique_values = [r["v"] for r in unique_values_result]
        except Exception as e:
            logger.debug(f"Could not compute distinct values for column {col.name}: {e}")
            # Set defaults for problematic columns (e.g., JSON types)
            unique_values_count = row_count  # Assume all values are unique
            analysis.unique_values_count = unique_values_count
            unique_values = []

        # If there are few unique values relative to total rows, treat it as a potential enum
        max_unique_values = max(20, int(row_count * 0.05))
        if unique_values_count <= max_unique_values:
            analysis.is_enum = True
            analysis.enum_values = unique_values

        # Get some sample values
        num_value_sample_rows = 3
        if sql_client.dialect == "snowflake":
            sample_values_result = sql_client.run_sql_query(
                f"SELECT {quoted_col_name} as v FROM {table_name} "
                f"SAMPLE ({num_value_sample_rows} ROWS)",
            )
        elif sql_client.dialect == "bigquery":
            if row_count == 0:
                percent_to_sample = 100
            else:
                percent_to_sample = min(100, 2 * (num_value_sample_rows / row_count) * 100)
            try:
                sample_values_result = sql_client.run_sql_query(
                    f"SELECT {quoted_col_name} as v FROM {table_name} TABLESAMPLE SYSTEM "
                    f"({percent_to_sample} PERCENT) order by rand() limit {num_value_sample_rows}",
                )
            except Exception:
                # might be a view so we fallback to the naive approach
                sample_values_result = sql_client.run_sql_query(
                    f"SELECT {quoted_col_name} as v FROM {table_name} ORDER BY RAND() LIMIT "
                    f"{num_value_sample_rows}",
                )
        elif sql_client.dialect == "duckdb":
            if row_count == 0:
                percent_to_sample = 100
            else:
                percent_to_sample = min(100, 2 * (num_value_sample_rows / row_count) * 100)
            try:
                sample_values_result = sql_client.run_sql_query(
                    f"SELECT {quoted_col_name} as v FROM {table_name} "
                    f"USING SAMPLE {percent_to_sample}% "
                    f"ORDER BY RANDOM() LIMIT {num_value_sample_rows}",
                )
            except Exception:
                # fallback to naive approach if sampling fails
                sample_values_result = sql_client.run_sql_query(
                    f"SELECT {quoted_col_name} as v FROM {table_name} ORDER BY RANDOM() LIMIT "
                    f"{num_value_sample_rows}",
                )
        elif sql_client.dialect in ["aws_athena_trino_sql", "aws_athena_spark_sql"]:
            # Athena doesn't have advanced sampling, use simple ORDER BY RANDOM() with LIMIT
            sample_values_result = sql_client.run_sql_query(
                f"SELECT {quoted_col_name} as v FROM {table_name} ORDER BY RANDOM() LIMIT "
                f"{num_value_sample_rows}",
            )
        elif sql_client.dialect == "redshift":
            if row_count == 0:
                percent_to_sample = 100
            else:
                percent_to_sample = min(100, 2 * (num_value_sample_rows / row_count) * 100)
            try:
                sample_values_result = sql_client.run_sql_query(
                    f"SELECT {quoted_col_name} as v FROM {table_name} TABLESAMPLE BERNOULLI "
                    f"({percent_to_sample}) order by random() limit {num_value_sample_rows}",
                )
            except Exception:
                sample_values_result = sql_client.run_sql_query(
                    f"SELECT {quoted_col_name} as v FROM {table_name} ORDER BY RANDOM() LIMIT "
                    f"{num_value_sample_rows}",
                )
        elif sql_client.dialect == "postgres":
            if row_count == 0:
                percent_to_sample = 100
            else:
                percent_to_sample = min(100, 2 * (num_value_sample_rows / row_count) * 100)
            try:
                sample_values_result = sql_client.run_sql_query(
                    f"SELECT {quoted_col_name} as v FROM {table_name} TABLESAMPLE BERNOULLI "
                    f"({percent_to_sample}) ORDER BY RANDOM() LIMIT {num_value_sample_rows}",
                )
            except Exception:
                # Fallback to simple random sampling if TABLESAMPLE is not supported
                sample_values_result = sql_client.run_sql_query(
                    f"SELECT {quoted_col_name} as v FROM {table_name} ORDER BY RANDOM() LIMIT "
                    f"{num_value_sample_rows}",
                )
        elif sql_client.dialect == "databricks":
            # Databricks supports TABLESAMPLE or ORDER BY RAND() with LIMIT
            if row_count == 0:
                percent_to_sample = 100
            else:
                percent_to_sample = min(100, 2 * (num_value_sample_rows / row_count) * 100)
            try:
                sample_values_result = sql_client.run_sql_query(
                    f"SELECT {quoted_col_name} as v FROM {table_name} TABLESAMPLE "
                    f"({percent_to_sample} PERCENT) ORDER BY RAND() LIMIT {num_value_sample_rows}",
                )
            except Exception:
                # Fallback to simple random sampling if TABLESAMPLE is not supported
                sample_values_result = sql_client.run_sql_query(
                    f"SELECT {quoted_col_name} as v FROM {table_name} ORDER BY RAND() LIMIT "
                    f"{num_value_sample_rows}",
                )
        else:
            raise ValueError(f"Unsupported dialect: {sql_client.dialect}")
        sample_values_result = lowercase_keys(sample_values_result)
        analysis.sample_values = [r["v"] for r in sample_values_result]
        return analysis

    column_analyses = []
    futures = [
        column_analysis_threadpool.submit(analyze_column, i, col)
        for i, col in enumerate(table_schema_analysis.columns)
    ]
    for future in as_completed(futures):
        column_analyses.append(future.result())

    logger.info("Table analysis complete")
    return TableAnalysis(
        table_name=table_name,
        table_comment=table_schema_analysis.table_comment,
        row_count=row_count,
        columns=column_analyses,
        sample_rows=sample_rows,
    )


def truncate(string: str, length: int) -> str:
    if len(string) > length:
        return string[:length] + "... (truncated)"
    return string


def truncate_row(row: dict[str, Any], length: int) -> dict[str, Any]:
    return {k: truncate(v, length) if isinstance(v, str) else v for k, v in row.items()}


def generate_markdown_report(logger: logging.Logger, analysis: TableAnalysis) -> str:
    """
    Generate a markdown report from the table analysis.

    Args:
        analysis: TableAnalysis object containing the analysis results

    Returns:
        Markdown formatted report string
    """
    markdown = f"# Table Analysis: {analysis.table_name}\n\n"
    markdown += f"Total Rows: {analysis.row_count}\n\n"

    if analysis.table_comment and len(analysis.table_comment.strip()) > 0:
        markdown += f"## Table Comment\n\n{analysis.table_comment}\n\n"

    markdown += "## Columns\n\n"
    for col in analysis.columns:
        markdown += f"### {col.name} ({col.type})\n"
        if col.column_comment and len(col.column_comment.strip()) > 0:
            markdown += f"- Column Comment: {col.column_comment}\n"
        markdown += f"- Null Percentage: {col.null_percentage:.2f}%\n"
        markdown += f"- Unique Values: {col.unique_values_count}\n"

        if col.min is not None and col.max is not None:
            markdown += f"- Range: {col.min} to {col.max}\n"

        if col.is_enum and col.enum_values:
            markdown += (
                f"- Possible Values: {', '.join(truncate(str(v), 128) for v in col.enum_values)}\n"
            )

        if col.sample_values:
            markdown += (
                f"- Sample Values: {', '.join(truncate(str(v), 128) for v in col.sample_values)}\n"
            )

        markdown += "\n"

    markdown += "## Sample Rows\n\n"
    markdown += "```json\n"
    markdown += json.dumps(
        [truncate_row(row, 1024) for row in analysis.sample_rows], default=str, indent=2
    )
    markdown += "\n```\n"

    return markdown


def generate_summary(logger: logging.Logger, agent, markdown: str) -> str:
    """
    Generate a comprehensive summary of the table analysis using agent.

    Args:
        logger: Logger instance
        agent: AsyncAgent instance
        markdown: Markdown formatted table analysis

    Returns:
        Summary string generated by agent
    """
    return sync_generate_dataset_summary(agent, markdown)


def update_dataset(
    logger: logging.Logger,
    context_store: ContextStore,
    profile: ProjectProfile,
    dataset: Dataset,
    table_schema_analysis: TableSchemaAnalysis,
    agent: AsyncAgent,
    column_analysis_threadpool: ThreadPoolExecutor,
) -> ContextStore:
    """Update dataset documentation with version-aware file writing."""

    # Analyze the table data
    logger.info(f"Analyzing table data: `{dataset.table_name}`...")
    sql_client = get_sql_client(profile, dataset.connection)
    analysis = analyze_table(logger, sql_client, table_schema_analysis, column_analysis_threadpool)
    logger.debug(f"Found {analysis.row_count} rows and {len(analysis.columns)} columns")

    # Generate markdown report
    logger.info("Generating markdown documentation...")
    markdown = generate_markdown_report(logger, analysis)

    # Generate summary using agent
    logger.debug("Generating AI summary...")
    summary = generate_summary(logger, agent, markdown)
    documentation = DatasetDocumentation(
        frontmatter=TableFrontmatter(
            schema_hash=table_schema_analysis.schema_hash,
            columns=[
                f"{col.name} ({col.type})"
                for col in sorted(table_schema_analysis.columns, key=lambda x: x.name)
            ],
        ),
        summary=summary,
    )

    logger.info("Documentation generated successfully")

    return context_store.add_or_update_dataset(dataset, documentation)


def list_bigquery_table_names(sql_client: SqlClient, dataset_names: list[str]) -> list[str]:
    """
    List all tables in a BigQuery dataset.
    """
    if sql_client.dialect != "bigquery":
        raise ValueError(
            f"list_bigquery_table_names only supports BigQuery, got {sql_client.dialect}"
        )

    # Query BigQuery's INFORMATION_SCHEMA.TABLES to get all tables in the dataset
    results = []
    for dataset_name in dataset_names:
        query = f"""
        SELECT table_name
        FROM `{dataset_name}.INFORMATION_SCHEMA.TABLES`
        WHERE table_type = 'BASE TABLE'
        ORDER BY table_name
        """

        result = sql_client.run_sql_query(query)
        results.extend([f"{dataset_name}.{row['table_name']}" for row in result])
    return results


def has_recent_data_activity(
    sql_client: SqlClient, table_name: str, days_threshold: int = 60
) -> bool:
    """
    Check if a BigQuery table has any date/timestamp columns with data within the last N days.

    Args:
        sql_client: SQL client for BigQuery
        table_name: Full table name (dataset.table)
        days_threshold: Number of days to look back (default 60)

    Returns:
        True if any date/timestamp column has data within the threshold, False otherwise
    """
    if sql_client.dialect != "bigquery":
        raise ValueError(
            f"has_recent_data_activity only supports BigQuery, got {sql_client.dialect}"
        )

    # Get all date/timestamp columns from the table
    dataset_name, table_name_only = table_name.rsplit(".", 1)
    columns_query = f"""
    SELECT column_name, data_type
    FROM `{dataset_name}.INFORMATION_SCHEMA.COLUMNS`
    WHERE table_name = '{table_name_only}'
    AND data_type IN ('DATE', 'DATETIME', 'TIMESTAMP')
    ORDER BY column_name
    """

    columns = sql_client.run_sql_query(columns_query)

    if not columns:
        # No date/timestamp columns found, consider it as having recent activity
        return True

    # Check each date/timestamp column for recent data
    for column in columns:
        column_name = column["column_name"]
        data_type = column["data_type"]
        quoted_column_name = quote_identifier(sql_client.dialect, column_name)

        # Build the appropriate date comparison based on data type
        if data_type == "DATE":
            date_condition = (
                f"DATE({quoted_column_name}) >= "
                f"DATE_SUB(CURRENT_DATE(), INTERVAL {days_threshold} DAY)"
            )
        elif data_type == "DATETIME":
            date_condition = (
                f"{quoted_column_name} >= "
                f"DATETIME_SUB(CURRENT_DATETIME(), INTERVAL {days_threshold} DAY)"
            )
        elif data_type == "TIMESTAMP":
            date_condition = (
                f"{quoted_column_name} >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), "
                f"INTERVAL {days_threshold} DAY)"
            )
        else:
            continue

        # Check if there's any data in this column within the threshold
        check_query = f"""
        SELECT COUNT(*) as recent_count
        FROM `{table_name}`
        WHERE {quoted_column_name} IS NOT NULL
        AND {date_condition}
        LIMIT 1
        """

        try:
            result = sql_client.run_sql_query(check_query)
            if result and result[0]["recent_count"] > 0:
                return True
        except Exception:
            # If there's an error checking this column, continue to the next one
            continue

    # No recent data found in any date/timestamp column
    return False
