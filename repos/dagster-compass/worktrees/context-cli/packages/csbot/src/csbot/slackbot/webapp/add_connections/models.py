import base64
import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Any, Literal

import pydantic
from cryptography.hazmat.primitives import serialization
from ddtrace.trace import tracer

from csbot.slackbot.webapp.add_connections.run_snowflake_query import run_snowflake_query
from csbot.utils.check_async_context import ensure_not_in_async_context

if TYPE_CHECKING:
    from duckdb import DuckDBPyConnection


class UserFacingDataError(Exception):
    pass


@dataclass
class TableInfo:
    """Information about a database table"""

    name: str
    description: str | None


@dataclass
class SchemaTablesResult:
    """Result of attempting to discover tables in a single schema"""

    schema_name: str
    success: bool
    tables: list[TableInfo]
    error: str | None


@dataclass
class ListTablesResult:
    """Overall result of table discovery across multiple schemas"""

    success: bool
    schema_results: list[SchemaTablesResult]
    error: str | None

    @property
    def all_tables(self) -> list[TableInfo]:
        """Get all successfully discovered tables"""
        tables = []
        for result in self.schema_results:
            if result.success:
                tables.extend(result.tables)
        return tables

    @property
    def failed_schemas(self) -> list[str]:
        """Get list of schemas that failed"""
        return [r.schema_name for r in self.schema_results if not r.success]

    @property
    def has_any_success(self) -> bool:
        """Check if at least one schema succeeded"""
        return any(r.success for r in self.schema_results)


@dataclass
class WarehouseNetworkInfo:
    """Network access information for warehouse connections"""

    connection_method: str
    port: str | None = None
    ip_addresses: list[str] | None = None
    additional_info: str | None = None


@dataclass
class WarehousePermissionInfo:
    """Permission requirements for warehouse operations"""

    header: str
    permissions: list[str]


@dataclass
class WarehouseHelpInfo:
    """Help information for warehouse setup and operations"""

    setup_instructions: list[str] | None = None
    network_info: WarehouseNetworkInfo | None = None
    connection_permissions: WarehousePermissionInfo | None = None
    schema_permissions: WarehousePermissionInfo | None = None


class JsonConfig(pydantic.BaseModel):
    type: str
    config: dict[str, Any]

    @classmethod
    def from_url(cls, url: str) -> "JsonConfig":
        if not url.startswith("jsonconfig:"):
            raise ValueError("Invalid URL")
        json_base64 = url.split(":")[1]
        json_data = json.loads(base64.b64decode(json_base64).decode())
        return cls(type=json_data["type"], config=json_data["config"])

    def to_url(self) -> str:
        json_base64 = base64.b64encode(json.dumps(self.model_dump()).encode()).decode()
        return f"jsonconfig:{json_base64}"


Dialect = Literal[
    "snowflake",
    "bigquery",
    "duckdb",
    "aws_athena_trino_sql",
    "aws_athena_spark_sql",
    "redshift",
    "postgres",
    "databricks",
]


class BigQueryWarehouseConfig(pydantic.BaseModel):
    location: str = pydantic.Field(
        title="Location", description="Examples: us, eu, us-east1, us-west2", examples=["us"]
    )
    service_account_json_string: str = pydantic.Field(
        title="Service Account JSON",
        description="Paste your Google Cloud service account JSON key",
        examples=[
            '{\n  "type": "service_account",\n  "project_id": "your-project-id",\n  "private_key_id": "...",\n  "private_key": "...",\n  ...\n}'
        ],
        json_schema_extra={"widget": "textarea", "rows": 10, "validator": "bigquery_json"},
    )

    @property
    def project_id(self) -> str:
        service_account_json = json.loads(self.service_account_json_string)
        return service_account_json["project_id"]

    @classmethod
    def from_location_and_service_account_json(
        cls, location: str, service_account_json_string: str
    ):
        service_account_json = json.loads(service_account_json_string)
        if service_account_json.get("type") != "service_account":
            raise ValueError(
                "Provided service account JSON is not a valid Google Cloud service account"
            )

        if "project_id" not in service_account_json:
            raise ValueError("project_id not found in service account JSON")

        return cls(
            location=location,
            service_account_json_string=service_account_json_string,
        )

    def to_url(self) -> str:
        return JsonConfig(
            type="bigquery",
            config=self.model_dump(mode="json"),
        ).to_url()

    @tracer.wrap()
    def run_sql_query(self, query: str) -> list[dict[str, Any]]:
        from google.cloud import bigquery
        from google.oauth2 import service_account

        # figure out rbac with datadog
        # try_set_tag("query", query)

        credentials = service_account.Credentials.from_service_account_info(
            json.loads(self.service_account_json_string)
        )

        # Create client
        client = bigquery.Client(
            credentials=credentials, project=self.project_id, location=self.location
        )

        query_job = client.query(query)
        return [dict(row.items()) for row in query_job.result()]

    def list_schemas(self) -> list[str]:
        """List all accessible datasets (schemas) in BigQuery project"""
        from google.cloud import bigquery
        from google.oauth2 import service_account

        credentials = service_account.Credentials.from_service_account_info(
            json.loads(self.service_account_json_string)
        )

        # Create client
        client = bigquery.Client(
            credentials=credentials, project=self.project_id, location=self.location
        )

        try:
            datasets = list(client.list_datasets())
            return [dataset.dataset_id for dataset in datasets]
        except Exception:
            # If we can't list datasets, return empty list
            raise UserFacingDataError(
                "Failed to list datasets in BigQuery project. Do you have the roles/bigquery.dataViewer role?"
            )

    def list_tables(self, selected_schemas: list[str] | None) -> ListTablesResult:
        """List all accessible tables in BigQuery project with per-schema error handling"""
        from google.cloud import bigquery
        from google.oauth2 import service_account

        credentials = service_account.Credentials.from_service_account_info(
            json.loads(self.service_account_json_string)
        )

        # Create client
        client = bigquery.Client(
            credentials=credentials,
            project=self.project_id,
            location=self.location,
        )

        schema_results = []

        try:
            # List all datasets in the project
            datasets = list(client.list_datasets())

            # Filter datasets by selected schemas if provided
            if selected_schemas is not None:
                datasets = [ds for ds in datasets if ds.dataset_id in selected_schemas]

            for dataset in datasets:
                try:
                    # List all tables in each dataset
                    table_rows = client.query(f"""
SELECT t.table_name,
       o.option_value AS comment
FROM {dataset.dataset_id}.INFORMATION_SCHEMA.TABLES t
LEFT JOIN {dataset.dataset_id}.INFORMATION_SCHEMA.TABLE_OPTIONS o
  ON t.table_name = o.table_name
 AND o.option_name = 'table_comment'
""").result()
                    tables = []
                    for row in table_rows:
                        row_data = dict(row.items())
                        tables.append(
                            TableInfo(
                                name=f"{self.project_id}.{dataset.dataset_id}.{row_data['table_name']}",
                                description=row_data["comment"],
                            )
                        )
                    schema_results.append(
                        SchemaTablesResult(
                            schema_name=dataset.dataset_id, success=True, tables=tables, error=None
                        )
                    )
                except Exception:
                    # Record failure for this dataset
                    schema_results.append(
                        SchemaTablesResult(
                            schema_name=dataset.dataset_id,
                            success=False,
                            tables=[],
                            error=f"Failed to list tables or datasets in `{dataset.dataset_id}`. Make sure you have the bigquery.dataViewer and bigquery.metadataViewer roles.",
                        )
                    )

        except Exception:
            # If we can't list datasets at all, return failure
            return ListTablesResult(
                success=False,
                schema_results=[],
                error="Failed to list tables or datasets in BigQuery project. Do you have the roles/bigquery.dataViewer and roles/bigquery.metadataViewer roles?",
            )

        # Determine overall success
        has_any_success = any(r.success for r in schema_results)
        return ListTablesResult(success=has_any_success, schema_results=schema_results, error=None)

    def get_connection_name(self) -> str:
        """Generate connection name for BigQuery"""
        return clean_string_for_connection_name(f"bigquery_{self.project_id}_{self.location}")

    @classmethod
    def get_help_info(cls) -> WarehouseHelpInfo:
        """Get help information for BigQuery setup"""
        return WarehouseHelpInfo(
            setup_instructions=[
                "Sign in to Google Cloud Console",
                "Create a service account with BigQuery permissions",
                "Download the service account JSON key",
                "Copy and paste the JSON content above",
            ],
            network_info=WarehouseNetworkInfo(
                connection_method="HTTPS over port 443",
                ip_addresses=[
                    "100.20.92.101",
                    "44.225.181.72",
                    "44.227.217.144",
                    "74.220.48.0/24",
                    "74.220.56.0/24",
                    "52.25.53.27",
                    "44.242.128.111",
                    "52.35.195.86",
                ],
            ),
            connection_permissions=WarehousePermissionInfo(
                header="Required BigQuery IAM Roles",
                permissions=[
                    "BigQuery Job User",
                    "BigQuery Metadata Viewer",
                    "BigQuery Data Viewer",
                ],
            ),
            schema_permissions=WarehousePermissionInfo(
                header="Dataset Discovery Permissions",
                permissions=[
                    "BigQuery Job User",
                    "BigQuery Metadata Viewer",
                    "BigQuery Data Viewer",
                ],
            ),
        )


class SnowflakePasswordCredential(pydantic.BaseModel):
    type: Literal["password"]
    password: str = pydantic.Field(
        title="Password",
        description="Database password",
        examples=["Your password"],
        json_schema_extra={"widget": "password"},
    )


class SnowflakePrivateKeyCredential(pydantic.BaseModel):
    type: Literal["private_key"]
    private_key_file: str = pydantic.Field(
        title="Private Key",
        description="RSA private key in PEM format",
        examples=["-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"],
        json_schema_extra={"widget": "textarea", "rows": 8, "validator": "snowflake_private_key"},
    )
    key_password: str | None = pydantic.Field(
        default=None,
        title="Private Key Password",
        description="Password for encrypted private key (if applicable)",
        examples=["Your key password"],
        json_schema_extra={"widget": "password"},
    )


class SnowflakeWarehouseConfig(pydantic.BaseModel):
    account_id: str = pydantic.Field(
        title="Account Locator",
        description="Your Snowflake account locator",
        examples=["abc12345"],
    )
    username: str = pydantic.Field(
        title="Username", description="Database username", examples=["admin"]
    )
    credential: Annotated[
        SnowflakePasswordCredential | SnowflakePrivateKeyCredential,
        pydantic.Field(discriminator="type"),
    ]
    warehouse: str = pydantic.Field(
        title="Warehouse",
        description="The compute warehouse to use for queries",
        examples=["COMPUTE_WH"],
    )
    role: str = pydantic.Field(
        title="Role",
        description="A role with access to the tables you want to analyze",
        examples=["ANALYST"],
    )
    region: str | None = pydantic.Field(
        default="",
        title="Region",
        description="AWS region where your Snowflake account is located (optional)",
        examples=["us-east-1"],
    )

    def to_url(self) -> str:
        return JsonConfig(
            type="snowflake",
            config=self.model_dump(mode="json"),
        ).to_url()

    @tracer.wrap()
    def run_sql_query(self, query: str) -> list[dict[str, Any]]:
        # figure out rbac with datadog
        # try_set_tag("query", query)

        ensure_not_in_async_context()

        account_locator = self.account_id
        if self.region:
            account_locator += f".{self.region}"

        password = None
        private_key = None
        if self.credential.type == "password":
            password = self.credential.password
        elif self.credential.type == "private_key":
            # Parse the PEM formatted private key to base64 encoded DER format
            try:
                # Prepare password for key loading
                key_password = None
                if self.credential.key_password and self.credential.key_password.strip():
                    key_password = self.credential.key_password.encode("utf-8")

                # Load the private key from PEM format
                private_key_obj = serialization.load_pem_private_key(
                    self.credential.private_key_file.encode("utf-8"),
                    password=key_password,
                )
                # Convert to DER format
                der_private_key = private_key_obj.private_bytes(
                    encoding=serialization.Encoding.DER,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption(),
                )
                # Encode as base64 string
                private_key = base64.b64encode(der_private_key).decode("utf-8")
            except Exception as e:
                raise ValueError(f"Failed to parse private key: {str(e)}") from e

        connect_args = {
            "account": account_locator,
            "user": self.username,
            "password": password,
            "private_key": private_key,
            "warehouse": self.warehouse,
            "role": self.role,
        }

        return run_snowflake_query(connect_args, query)

    def list_schemas(self) -> list[str]:
        """List all accessible database.schema combinations in Snowflake"""
        try:
            schemas = []
            all_databases = [row["name"] for row in self.run_sql_query("SHOW DATABASES")]
            for database in all_databases:
                database_schemas = [
                    row["name"] for row in self.run_sql_query(f"SHOW SCHEMAS IN {database}")
                ]
                for schema in database_schemas:
                    schemas.append(f"{database}.{schema}")
            return schemas
        except Exception as e:
            raise UserFacingDataError(f"Failed to list schemas in Snowflake: {str(e)}")

    def list_tables(self, selected_schemas: list[str] | None) -> ListTablesResult:
        """List all accessible tables in Snowflake warehouse with per-schema error handling"""
        schema_results = []

        try:
            if selected_schemas is not None:
                # Use only selected schemas
                for schema_path in selected_schemas:
                    try:
                        database, schema = schema_path.split(".", 1)
                        table_rows = self.run_sql_query(f"SHOW TABLES IN {database}.{schema}")
                        view_rows = self.run_sql_query(f"SHOW VIEWS IN {database}.{schema}")
                        rows = table_rows + view_rows
                        tables = []
                        for row in rows:
                            table_name = row["name"]
                            table_comment = row["comment"]
                            tables.append(
                                TableInfo(
                                    name=f"{database}.{schema}.{table_name}",
                                    description=table_comment,
                                )
                            )
                        schema_results.append(
                            SchemaTablesResult(
                                schema_name=schema_path, success=True, tables=tables, error=None
                            )
                        )
                    except Exception as e:
                        # Record failure for this schema
                        schema_results.append(
                            SchemaTablesResult(
                                schema_name=schema_path, success=False, tables=[], error=str(e)
                            )
                        )
            else:
                # Original behavior - get all tables
                all_databases = [row["name"] for row in self.run_sql_query("SHOW DATABASES")]
                for database in all_databases:
                    schemas = [
                        row["name"] for row in self.run_sql_query(f"SHOW SCHEMAS IN {database}")
                    ]
                    for schema in schemas:
                        schema_path = f"{database}.{schema}"
                        try:
                            table_rows = self.run_sql_query(f"SHOW TABLES IN {database}.{schema}")
                            view_rows = self.run_sql_query(f"SHOW VIEWS IN {database}.{schema}")
                            rows = table_rows + view_rows
                            tables = []
                            for row in rows:
                                table_name = row["name"]
                                table_comment = row["comment"]
                                tables.append(
                                    TableInfo(
                                        name=f"{database}.{schema}.{table_name}",
                                        description=table_comment,
                                    )
                                )
                            schema_results.append(
                                SchemaTablesResult(
                                    schema_name=schema_path, success=True, tables=tables, error=None
                                )
                            )
                        except Exception as e:
                            schema_results.append(
                                SchemaTablesResult(
                                    schema_name=schema_path, success=False, tables=[], error=str(e)
                                )
                            )

        except Exception as e:
            # If we can't query Snowflake at all, return failure
            return ListTablesResult(
                success=False, schema_results=[], error=f"Failed to list Snowflake tables: {str(e)}"
            )

        # Determine overall success
        has_any_success = any(r.success for r in schema_results)
        return ListTablesResult(success=has_any_success, schema_results=schema_results, error=None)

    def get_connection_name(self) -> str:
        """Generate connection name for Snowflake"""
        # Clean username for use in connection name
        clean_username = self.username.replace("@", "_").replace(".", "_")
        return clean_string_for_connection_name(f"snowflake_{clean_username}")

    @classmethod
    def get_field_groups(cls) -> list[dict[str, Any]]:
        """Get field groups for organizing the form"""
        return [
            {
                "label": "Connection Details",
                "fields": ["account_id", "username", "warehouse", "role", "region"],
            },
            {
                "label": "Authentication",
                "fields": ["credential_type", "password", "private_key_file", "key_password"],
            },
        ]

    @classmethod
    def get_help_info(cls) -> WarehouseHelpInfo:
        """Get help information for Snowflake setup"""
        return WarehouseHelpInfo(
            setup_instructions=[
                "Contact your Snowflake administrator to create an account",
                "Get your account locator from the Snowflake console URL",
                "Set up password or private key authentication",
                "Request the required Snowflake Privileges (see below)",
            ],
            network_info=WarehouseNetworkInfo(
                connection_method="HTTPS over port 443",
                ip_addresses=[
                    "100.20.92.101",
                    "44.225.181.72",
                    "44.227.217.144",
                    "74.220.48.0/24",
                    "74.220.56.0/24",
                    "52.25.53.27",
                    "44.242.128.111",
                    "52.35.195.86",
                ],
                additional_info="Connects to <account>.snowflakecomputing.com - may require firewall allowlisting",
            ),
            connection_permissions=WarehousePermissionInfo(
                header="Required Snowflake Privileges",
                permissions=[
                    "USAGE on warehouse",
                    "USAGE on schema - Access schema objects",
                    "SELECT on tables - Query table data for analysis",
                    "SHOW privilege - View table metadata and structure",
                ],
            ),
            schema_permissions=WarehousePermissionInfo(
                header="Schema Discovery Privileges",
                permissions=[
                    "USAGE on schema - Access schema objects",
                    "SELECT on tables - Query table data for analysis",
                    "SHOW privilege - View table metadata and structure",
                ],
            ),
        )


class AthenaWarehouseConfig(pydantic.BaseModel):
    aws_access_key_id: str = pydantic.Field(
        title="AWS Access Key ID", description="AWS Access Key ID", examples=["AKIA..."]
    )
    aws_secret_access_key: str = pydantic.Field(
        title="AWS Secret Access Key",
        description="AWS Secret Access Key",
        examples=["..."],
        json_schema_extra={"widget": "password"},
    )
    region: str = pydantic.Field(
        title="Region", description="AWS region where your data is located", examples=["us-east-1"]
    )
    s3_staging_dir: str = pydantic.Field(
        title="S3 Staging Directory",
        description="S3 location where query results will be stored",
        examples=["s3://your-bucket/athena-results/"],
    )
    query_engine: Literal["aws_athena_trino_sql", "aws_athena_spark_sql"] = pydantic.Field(
        title="Query Engine", description="Choose the SQL engine for query execution"
    )

    def to_url(self) -> str:
        return JsonConfig(
            type="athena",
            config=self.model_dump(mode="json"),
        ).to_url()

    @tracer.wrap()
    def run_sql_query(self, query: str) -> list[dict[str, Any]]:
        import pyathena
        from pyathena.cursor import DictCursor

        # figure out rbac with datadog
        # try_set_tag("query", query)

        conn = pyathena.connect(
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.region,
            s3_staging_dir=self.s3_staging_dir,
        )
        cursor = conn.cursor(DictCursor)
        cursor.execute(query)
        return [row for row in cursor.fetchall()]  # type: ignore

    def list_schemas(self) -> list[str]:
        """List all accessible databases in Athena"""
        import boto3

        try:
            glue_client = boto3.client(
                "glue",
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.region,
            )
            databases = glue_client.get_databases()
            return [db["Name"] for db in databases["DatabaseList"]]
        except Exception as e:
            raise UserFacingDataError(f"Failed to list Athena databases: {str(e)}")

    def list_tables(self, selected_schemas: list[str] | None) -> ListTablesResult:
        """List all accessible tables in Athena with per-schema error handling"""
        import boto3

        schema_results = []

        try:
            glue_client = boto3.client(
                "glue",
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.region,
            )
            if selected_schemas is not None:
                # Get tables for specific databases
                for database_name in selected_schemas:
                    try:
                        glue_tables = glue_client.get_tables(DatabaseName=database_name)
                        tables = []
                        for glue_table in glue_tables["TableList"]:
                            table_name = glue_table["Name"]
                            description = glue_table["Description"] or glue_table["Parameters"].get(
                                "comment"
                            )
                            tables.append(
                                TableInfo(
                                    name=f"{database_name}.{table_name}", description=description
                                )
                            )
                        schema_results.append(
                            SchemaTablesResult(
                                schema_name=database_name, success=True, tables=tables, error=None
                            )
                        )
                    except Exception:
                        # Record failure for this database
                        schema_results.append(
                            SchemaTablesResult(
                                schema_name=database_name,
                                success=False,
                                tables=[],
                                error=f"Failed to list tables for {database_name}. Please check that this service account has glue:GetDatabases, glue:GetTables, and glue:GetTable permissions.",
                            )
                        )
            else:
                # Get all tables from all databases
                glue_tables = glue_client.get_tables()
                for glue_table in glue_tables["TableList"]:
                    database_name = glue_table["DatabaseName"]
                    table_name = glue_table["Name"]
                    description = glue_table["Description"] or glue_table["Parameters"].get(
                        "comment"
                    )
                    # Group by database
                    existing = next(
                        (r for r in schema_results if r.schema_name == database_name), None
                    )
                    if existing and existing.success:
                        existing.tables.append(
                            TableInfo(name=f"{database_name}.{table_name}", description=description)
                        )
                    else:
                        schema_results.append(
                            SchemaTablesResult(
                                schema_name=database_name,
                                success=True,
                                tables=[
                                    TableInfo(
                                        name=f"{database_name}.{table_name}",
                                        description=description,
                                    )
                                ],
                                error=None,
                            )
                        )
        except Exception:
            # If we can't connect to Glue at all, return failure
            return ListTablesResult(
                success=False,
                schema_results=[],
                error="Failed to list tables for Athena. Please check that this service account has glue:GetDatabases, glue:GetTables, and glue:GetTable permissions.",
            )

        # Determine overall success
        has_any_success = any(r.success for r in schema_results)
        return ListTablesResult(success=has_any_success, schema_results=schema_results, error=None)

    def get_connection_name(self) -> str:
        """Generate connection name for Athena"""
        return clean_string_for_connection_name(f"athena_{self.region}_{self.aws_access_key_id}")

    @classmethod
    def get_help_info(cls) -> WarehouseHelpInfo:
        """Get help information for Athena setup"""
        return WarehouseHelpInfo(
            setup_instructions=[
                "Create an IAM user in AWS Console",
                "Attach appropriate Athena and Glue policies",
                "Generate access keys for the IAM user",
                "Create an S3 bucket for query results",
            ],
            network_info=WarehouseNetworkInfo(
                connection_method="HTTPS over port 443",
                additional_info="Connects to AWS API endpoints - no specific firewall rules needed",
            ),
            connection_permissions=WarehousePermissionInfo(
                header="Required AWS IAM Permissions",
                permissions=[
                    "athena:StartQueryExecution - Run SQL queries",
                    "athena:GetQueryExecution - Monitor query status",
                    "athena:GetQueryResults - Retrieve query results",
                    "s3:ListBucket - Browse data locations",
                    "s3:PutObject - Write query results to S3",
                    "s3:GetObject - Read query results from S3",
                    "glue:GetDatabases - List available databases",
                    "glue:GetDatabase - Read database metadata",
                    "glue:GetTables - List tables in databases",
                    "glue:GetTable - Read table schema and metadata",
                ],
            ),
            schema_permissions=WarehousePermissionInfo(
                header="Database Discovery Permissions",
                permissions=[
                    "athena:StartQueryExecution - Run SQL queries",
                    "athena:GetQueryExecution - Monitor query status",
                    "athena:GetQueryResults - Retrieve query results",
                    "s3:ListBucket - Browse data locations",
                    "s3:PutObject - Write query results to S3",
                    "s3:GetObject - Read query results from S3",
                    "glue:GetDatabases - List available databases",
                    "glue:GetDatabase - Read database metadata",
                    "glue:GetTables - List tables in databases",
                    "glue:GetTable - Read table schema and metadata",
                ],
            ),
        )


class RedshiftWarehouseConfig(pydantic.BaseModel):
    host: str = pydantic.Field(
        title="Host",
        description="Your Redshift cluster endpoint",
        examples=["my-cluster.abcd1234.us-west-2.redshift.amazonaws.com"],
    )
    port: int = pydantic.Field(
        default=5439, title="Port", description="Redshift port (default: 5439)", examples=[5439]
    )
    username: str = pydantic.Field(
        title="Username", description="Database username", examples=["admin"]
    )
    password: str = pydantic.Field(
        title="Password",
        description="Database password",
        examples=["Your password"],
        json_schema_extra={"widget": "password"},
    )
    database: str = pydantic.Field(title="Database", description="Database name", examples=["dev"])

    def to_url(self) -> str:
        return JsonConfig(
            type="redshift",
            config=self.model_dump(mode="json"),
        ).to_url()

    @tracer.wrap()
    def run_sql_query(self, query: str) -> list[dict[str, Any]]:
        import redshift_connector

        # figure out rbac with datadog
        # try_set_tag("query", query)

        conn = redshift_connector.connect(
            host=self.host,
            port=self.port,
            user=self.username,
            password=self.password,
            database=self.database,
        )
        cursor = conn.cursor()
        cursor.execute(query)
        return [
            dict(zip([description[0] for description in cursor.description], row))
            for row in cursor.fetchall()
        ]

    def list_schemas(self) -> list[str]:
        """List all accessible schemas in Redshift"""
        import redshift_connector

        try:
            conn = redshift_connector.connect(
                host=self.host,
                port=self.port,
                user=self.username,
                password=self.password,
                database=self.database,
            )

            rv = []
            cursor = conn.cursor()
            cursor.execute(
                """
            select distinct schema_name from svv_all_schemas
            where database_name = %s
            """,
                (self.database,),
            )
            for (schema,) in cursor.fetchall():
                rv.append(f"{self.database}.{schema}")
            return rv
        except Exception as e:
            raise UserFacingDataError(f"Failed to list Redshift schemas: {str(e)}")

    def list_tables(self, selected_schemas: list[str] | None) -> ListTablesResult:
        """List all accessible tables in Redshift with per-schema error handling"""
        import redshift_connector

        schema_results = []

        try:
            # Query information_schema for table information including descriptions
            if selected_schemas is None:
                return ListTablesResult(
                    success=False, schema_results=[], error="selected_schemas is required"
                )

            for full_schema in selected_schemas:
                try:
                    database, schema = full_schema.split(".", 1)
                    conn = redshift_connector.connect(
                        host=self.host,
                        port=self.port,
                        user=self.username,
                        password=self.password,
                        database=database,
                    )
                    cursor = conn.cursor()
                    # Filter by selected schemas
                    query = """
                        SELECT
                            database_name || '.' || schema_name || '.' || table_name as full_table_name,
                            remarks as table_comment
                        FROM svv_all_tables
                        where schema_name = %s
                    """
                    cursor.execute(query, (schema,))

                    rows = cursor.fetchall()
                    tables = []
                    for row in rows:
                        full_table_name = row[0]
                        table_comment = row[1]

                        tables.append(
                            TableInfo(
                                name=full_table_name,
                                description=table_comment,
                            )
                        )
                    schema_results.append(
                        SchemaTablesResult(
                            schema_name=full_schema, success=True, tables=tables, error=None
                        )
                    )
                except Exception:
                    # Record failure for this schema
                    schema_results.append(
                        SchemaTablesResult(
                            schema_name=full_schema,
                            success=False,
                            tables=[],
                            error=f"Failed to list tables in `{full_schema}`. Please check that this account has read access to pg_tables and information_schema.tables.",
                        )
                    )

        except Exception:
            # If we can't connect to Redshift at all, return failure
            return ListTablesResult(
                success=False,
                schema_results=[],
                error="Failed to list tables in Redshift database. Please check that this account has read access to pg_tables and information_schema.tables.",
            )

        # Determine overall success
        has_any_success = any(r.success for r in schema_results)
        return ListTablesResult(success=has_any_success, schema_results=schema_results, error=None)

    def get_connection_name(self) -> str:
        """Generate connection name for Redshift"""
        # Clean hostname for use in connection name
        return clean_string_for_connection_name(f"redshift_{self.username}_{self.database}")

    @classmethod
    def get_help_info(cls) -> WarehouseHelpInfo:
        """Get help information for Redshift setup"""
        return WarehouseHelpInfo(
            setup_instructions=[
                "Contact your AWS administrator for cluster endpoint",
                "Request a database user account with appropriate permissions",
                "Ensure your network can reach the Redshift cluster",
                "Test connection using standard PostgreSQL tools",
            ],
            network_info=WarehouseNetworkInfo(
                connection_method="PostgreSQL protocol over port 5439",
                port="5439",
                ip_addresses=[
                    "100.20.92.101",
                    "44.225.181.72",
                    "44.227.217.144",
                    "74.220.48.0/24",
                    "74.220.56.0/24",
                    "52.25.53.27",
                    "44.242.128.111",
                    "52.35.195.86",
                ],
                additional_info="May require VPN access or IP allowlisting depending on cluster configuration",
            ),
            connection_permissions=WarehousePermissionInfo(
                header="Required Redshift Permissions",
                permissions=[
                    "CONNECT privilege on database - Establish connections",
                    "Valid username and password - Authentication credentials",
                    "USAGE on schema - Access schema objects",
                    "SELECT on information_schema.schemata - List available schemas",
                    "SELECT on pg_tables - List tables in schemas",
                    "SELECT on information_schema.tables - Access table metadata",
                    "SELECT privilege on tables - Query table data for analysis",
                    "SELECT on pg_class and pg_namespace - Access table descriptions",
                ],
            ),
            schema_permissions=WarehousePermissionInfo(
                header="Schema Discovery Permissions",
                permissions=[
                    "CONNECT privilege on database - Establish connections",
                    "Valid username and password - Authentication credentials",
                    "USAGE on schema - Access schema objects",
                    "SELECT on information_schema.schemata - List available schemas",
                    "SELECT on pg_tables - List tables in schemas",
                    "SELECT on information_schema.tables - Access table metadata",
                    "SELECT privilege on tables - Query table data for analysis",
                    "SELECT on pg_class and pg_namespace - Access table descriptions",
                ],
            ),
        )


class DatabricksPersonalAccessTokenCredential(pydantic.BaseModel):
    type: Literal["personal_access_token"]
    personal_access_token: str = pydantic.Field(
        title="Personal Access Token",
        description="Databricks personal access token",
        examples=["dapi..."],
        json_schema_extra={"widget": "password"},
    )


class DatabricksOAuthCredential(pydantic.BaseModel):
    type: Literal["oauth"]
    client_id: str = pydantic.Field(
        title="OAuth Client ID",
        description="Databricks OAuth M2M client ID",
        examples=["..."],
    )
    client_secret: str = pydantic.Field(
        title="OAuth Client Secret",
        description="Databricks OAuth M2M client secret",
        examples=["..."],
        json_schema_extra={"widget": "password"},
    )


class DatabricksWarehouseConfig(pydantic.BaseModel):
    server_hostname: str = pydantic.Field(
        title="Server Hostname",
        description="Databricks workspace URL (e.g., your-workspace.cloud.databricks.com)",
        examples=["your-workspace.cloud.databricks.com"],
    )
    http_path: str = pydantic.Field(
        title="HTTP Path",
        description="SQL warehouse HTTP path (e.g., /sql/1.0/warehouses/abc123)",
        examples=["/sql/1.0/warehouses/abc123"],
    )
    credential: Annotated[
        DatabricksPersonalAccessTokenCredential | DatabricksOAuthCredential,
        pydantic.Field(discriminator="type"),
    ]

    def to_url(self) -> str:
        return JsonConfig(
            type="databricks",
            config=self.model_dump(mode="json"),
        ).to_url()

    @tracer.wrap()
    def run_sql_query(self, query: str) -> list[dict[str, Any]]:
        from databricks import sql
        from databricks.sdk.core import Config, oauth_service_principal

        ensure_not_in_async_context()

        connection_params: dict[str, Any] = {
            "server_hostname": self.server_hostname,
            "http_path": self.http_path,
        }

        if self.credential.type == "personal_access_token":
            connection_params["access_token"] = self.credential.personal_access_token
        elif self.credential.type == "oauth":
            # https://github.com/databricks/databricks-sql-python/issues/423#issuecomment-2288373154
            client_id = self.credential.client_id
            client_secret = self.credential.client_secret

            def credentials_provider():
                config = Config(
                    host=f"https://{self.server_hostname}",
                    client_id=client_id,
                    client_secret=client_secret,
                )

                return oauth_service_principal(config)

            connection_params["credentials_provider"] = credentials_provider

        with sql.connect(**connection_params) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            return [dict(zip(columns, row)) for row in rows]

    def list_schemas(self) -> list[str]:
        """List all accessible catalogs.schemas in Databricks"""
        try:
            schemas = []
            catalogs_result = self.run_sql_query("SHOW CATALOGS")
            catalogs = [row["catalog"] for row in catalogs_result]
            for catalog in catalogs:
                schemas_result = self.run_sql_query(f"SHOW SCHEMAS IN {catalog}")
                for row in schemas_result:
                    schema_name = row["databaseName"]
                    schemas.append(f"{catalog}.{schema_name}")
            return schemas
        except Exception as e:
            raise UserFacingDataError(f"Failed to list schemas in Databricks: {str(e)}")

    def list_tables(self, selected_schemas: list[str] | None) -> ListTablesResult:
        """List all accessible tables in Databricks with per-schema error handling"""
        schema_results = []

        try:
            if selected_schemas is not None:
                for schema_path in selected_schemas:
                    try:
                        catalog, schema = schema_path.split(".", 1)
                        tables_result = self.run_sql_query(f"SHOW TABLES IN {catalog}.{schema}")
                        tables = []
                        for row in tables_result:
                            table_name = row["tableName"]
                            table_comment = row.get("comment")
                            tables.append(
                                TableInfo(
                                    name=f"{catalog}.{schema}.{table_name}",
                                    description=table_comment,
                                )
                            )
                        schema_results.append(
                            SchemaTablesResult(
                                schema_name=schema_path, success=True, tables=tables, error=None
                            )
                        )
                    except Exception as e:
                        schema_results.append(
                            SchemaTablesResult(
                                schema_name=schema_path, success=False, tables=[], error=str(e)
                            )
                        )
            else:
                catalogs_result = self.run_sql_query("SHOW CATALOGS")
                catalogs = [row["catalog"] for row in catalogs_result]
                for catalog in catalogs:
                    schemas_result = self.run_sql_query(f"SHOW SCHEMAS IN {catalog}")
                    for row in schemas_result:
                        schema = row["databaseName"]
                        schema_path = f"{catalog}.{schema}"
                        try:
                            tables_result = self.run_sql_query(f"SHOW TABLES IN {catalog}.{schema}")
                            tables = []
                            for row in tables_result:
                                table_name = row["tableName"]
                                table_comment = row.get("comment")
                                tables.append(
                                    TableInfo(
                                        name=f"{catalog}.{schema}.{table_name}",
                                        description=table_comment,
                                    )
                                )
                            schema_results.append(
                                SchemaTablesResult(
                                    schema_name=schema_path, success=True, tables=tables, error=None
                                )
                            )
                        except Exception as e:
                            schema_results.append(
                                SchemaTablesResult(
                                    schema_name=schema_path, success=False, tables=[], error=str(e)
                                )
                            )

        except Exception as e:
            return ListTablesResult(
                success=False,
                schema_results=[],
                error=f"Failed to list Databricks tables: {str(e)}",
            )

        has_any_success = any(r.success for r in schema_results)
        return ListTablesResult(success=has_any_success, schema_results=schema_results, error=None)

    def get_connection_name(self) -> str:
        """Generate connection name for Databricks"""
        clean_hostname = self.server_hostname.replace(".", "_").replace("-", "_")
        return clean_string_for_connection_name(f"databricks_{clean_hostname}")

    @classmethod
    def get_field_groups(cls) -> list[dict[str, Any]]:
        """Get field groups for organizing the form"""
        return [
            {
                "label": "Connection Details",
                "fields": ["server_hostname", "http_path"],
            },
            {
                "label": "Authentication",
                "fields": [
                    "credential_type",
                    "personal_access_token",
                    "client_id",
                    "client_secret",
                ],
            },
        ]

    @classmethod
    def get_help_info(cls) -> WarehouseHelpInfo:
        """Get help information for Databricks setup"""
        return WarehouseHelpInfo(
            setup_instructions=[
                "Sign in to Databricks workspace",
                "Navigate to SQL Warehouses in the workspace",
                "Copy the server hostname and HTTP path from your SQL warehouse",
                "Create either a Personal Access Token or OAuth M2M application for authentication",
            ],
            network_info=WarehouseNetworkInfo(
                connection_method="HTTPS over port 443",
                ip_addresses=[
                    "100.20.92.101",
                    "44.225.181.72",
                    "44.227.217.144",
                    "74.220.48.0/24",
                    "74.220.56.0/24",
                    "52.25.53.27",
                    "44.242.128.111",
                    "52.35.195.86",
                ],
                additional_info="Connects to Databricks workspace - may require firewall allowlisting",
            ),
            connection_permissions=None,
            schema_permissions=WarehousePermissionInfo(
                header="Schema Discovery Permissions",
                permissions=[
                    "USE CATALOG - Access to catalogs",
                    "USE SCHEMA - Access to schemas",
                    "SELECT - Query table data for analysis",
                    "READ VOLUME - Access to data volumes",
                    "EXECUTE - Run SQL queries",
                    "BROWSE - Browse data volumes",
                ],
            ),
        )


class PostgresWarehouseConfig(pydantic.BaseModel):
    host: str = pydantic.Field(
        title="Host",
        description="Your PostgreSQL server hostname or IP address",
        examples=["localhost", "db.example.com", "192.168.1.100"],
    )
    port: int = pydantic.Field(
        default=5432, title="Port", description="PostgreSQL port (default: 5432)", examples=[5432]
    )
    username: str = pydantic.Field(
        title="Username", description="Database username", examples=["postgres", "admin"]
    )
    password: str = pydantic.Field(
        title="Password",
        description="Database password",
        examples=["Your password"],
        json_schema_extra={"widget": "password"},
    )
    database: str = pydantic.Field(
        title="Database", description="Database name", examples=["postgres", "analytics"]
    )

    def to_url(self) -> str:
        return JsonConfig(
            type="postgres",
            config=self.model_dump(mode="json"),
        ).to_url()

    @tracer.wrap()
    def run_sql_query(self, query: str) -> list[dict[str, Any]]:
        import psycopg
        from psycopg.rows import dict_row

        # figure out rbac with datadog
        # try_set_tag("query", query)

        conn = psycopg.connect(
            host=self.host,
            port=self.port,
            user=self.username,
            password=self.password,
            database=self.database,
        )
        cursor = conn.cursor(row_factory=dict_row)
        cursor.execute(query)  # type: ignore[arg-type]
        return [dict(row) for row in cursor.fetchall()]

    def list_schemas(self) -> list[str]:
        """List all accessible schemas in PostgreSQL"""
        import psycopg

        try:
            conn = psycopg.connect(
                host=self.host,
                port=self.port,
                user=self.username,
                password=self.password,
                database=self.database,
            )

            rv = []
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT schema_name 
                FROM information_schema.schemata 
                WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
                ORDER BY schema_name
                """
            )
            for (schema,) in cursor.fetchall():
                rv.append(f"{self.database}.{schema}")
            return rv
        except Exception as e:
            raise UserFacingDataError(f"Failed to list PostgreSQL schemas: {str(e)}")

    def list_tables(self, selected_schemas: list[str] | None) -> ListTablesResult:
        """List all accessible tables in PostgreSQL with per-schema error handling"""
        import psycopg

        schema_results = []

        try:
            if selected_schemas is None:
                return ListTablesResult(
                    success=False, schema_results=[], error="selected_schemas is required"
                )

            for full_schema in selected_schemas:
                try:
                    database, schema = full_schema.split(".", 1)
                    conn = psycopg.connect(
                        host=self.host,
                        port=self.port,
                        user=self.username,
                        password=self.password,
                        database=database,
                    )
                    cursor = conn.cursor()
                    # Query for tables and views with descriptions
                    query = """
                        SELECT
                            table_schema || '.' || table_name as full_table_name,
                            obj_description(c.oid) as table_comment
                        FROM information_schema.tables t
                        LEFT JOIN pg_class c ON c.relname = t.table_name
                        LEFT JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = t.table_schema
                        WHERE table_schema = %s
                        AND table_type IN ('BASE TABLE', 'VIEW')
                        ORDER BY table_schema, table_name
                    """
                    cursor.execute(query, (schema,))

                    rows = cursor.fetchall()
                    tables = []
                    for row in rows:
                        full_table_name = row[0]
                        table_comment = row[1]

                        tables.append(
                            TableInfo(
                                name=f"{database}.{full_table_name}",
                                description=table_comment,
                            )
                        )
                    schema_results.append(
                        SchemaTablesResult(
                            schema_name=full_schema, success=True, tables=tables, error=None
                        )
                    )
                except Exception:
                    # Record failure for this schema
                    schema_results.append(
                        SchemaTablesResult(
                            schema_name=full_schema,
                            success=False,
                            tables=[],
                            error=f"Failed to list tables in `{full_schema}`. Please check that this account has read access to information_schema.tables and pg_class.",
                        )
                    )

        except Exception:
            # If we can't connect to PostgreSQL at all, return failure
            return ListTablesResult(
                success=False,
                schema_results=[],
                error="Failed to list tables in PostgreSQL database. Please check that this account has read access to information_schema.tables and pg_class.",
            )

        # Determine overall success
        has_any_success = any(r.success for r in schema_results)
        return ListTablesResult(success=has_any_success, schema_results=schema_results, error=None)

    def get_connection_name(self) -> str:
        """Generate connection name for PostgreSQL"""
        # Clean hostname for use in connection name
        clean_host = self.host.replace(".", "_").replace("-", "_")
        return clean_string_for_connection_name(
            f"postgres_{self.username}_{self.database}_{clean_host}"
        )

    @classmethod
    def get_help_info(cls) -> WarehouseHelpInfo:
        """Get help information for PostgreSQL setup"""
        return WarehouseHelpInfo(
            setup_instructions=[
                "Ensure PostgreSQL server is running and accessible",
                "Create a database user with appropriate permissions",
                "Grant necessary privileges for data access",
                "Test connection using standard PostgreSQL tools",
            ],
            network_info=WarehouseNetworkInfo(
                connection_method="PostgreSQL protocol over port 5432",
                port="5432",
                ip_addresses=[
                    "100.20.92.101",
                    "44.225.181.72",
                    "44.227.217.144",
                    "74.220.48.0/24",
                    "74.220.56.0/24",
                    "52.25.53.27",
                    "44.242.128.111",
                    "52.35.195.86",
                ],
                additional_info="May require VPN access or IP allowlisting depending on server configuration",
            ),
            connection_permissions=WarehousePermissionInfo(
                header="Required PostgreSQL Permissions",
                permissions=[
                    "CONNECT privilege on database - Establish connections",
                    "Valid username and password - Authentication credentials",
                    "USAGE on schema - Access schema objects",
                    "SELECT on information_schema.schemata - List available schemas",
                    "SELECT on information_schema.tables - List tables in schemas",
                    "SELECT on pg_class and pg_namespace - Access table descriptions",
                    "SELECT privilege on tables - Query table data for analysis",
                ],
            ),
            schema_permissions=WarehousePermissionInfo(
                header="Schema Discovery Permissions",
                permissions=[
                    "CONNECT privilege on database - Establish connections",
                    "Valid username and password - Authentication credentials",
                    "USAGE on schema - Access schema objects",
                    "SELECT on information_schema.schemata - List available schemas",
                    "SELECT on information_schema.tables - List tables in schemas",
                    "SELECT on pg_class and pg_namespace - Access table descriptions",
                    "SELECT privilege on tables - Query table data for analysis",
                ],
            ),
        )


class MotherduckWarehouseConfig(pydantic.BaseModel):
    database_name: str = pydantic.Field(
        title="Database Name",
        description="MotherDuck database name",
        examples=["my_database"],
    )
    access_token: str = pydantic.Field(
        title="Access Token",
        description="MotherDuck access token",
        examples=["your_token_here"],
        json_schema_extra={"widget": "password"},
    )

    def to_url(self) -> str:
        return JsonConfig(
            type="motherduck",
            config=self.model_dump(mode="json"),
        ).to_url()

    def _connect(self) -> "DuckDBPyConnection":
        import duckdb

        connection_string = (
            f"md:{self.database_name}?motherduck_token={self.access_token}&saas_mode=true"
        )
        conn = duckdb.connect(connection_string)
        # conn.execute("SET enable_external_access=false;")
        # conn.execute("SET lock_configuration=true;")
        return conn

    @tracer.wrap()
    def run_sql_query(self, query: str) -> list[dict[str, Any]]:
        # figure out rbac with datadog
        # try_set_tag("query", query)

        conn = self._connect()
        result = conn.execute(query)
        rows = result.fetchall()
        column_names = [desc[0] for desc in result.description] if result.description else []
        conn.close()
        return [dict(zip(column_names, row)) for row in rows]

    def list_schemas(self) -> list[str]:
        """List all accessible schemas in MotherDuck"""

        try:
            conn = self._connect()
            schemas = conn.execute(
                "SELECT catalog_name, schema_name FROM information_schema.schemata"
            ).fetchall()
            conn.close()
            return [f"{catalog}.{schema}" for catalog, schema in schemas]
        except Exception as e:
            raise UserFacingDataError(f"Failed to list schemas in MotherDuck: {str(e)}")

    def list_tables(self, selected_schemas: list[str] | None) -> ListTablesResult:
        """List all accessible tables in MotherDuck with per-schema error handling"""

        schema_results = []

        try:
            conn = self._connect()

            if selected_schemas is not None:
                # Use only selected schemas
                for fully_qualified_schema_name in selected_schemas:
                    catalog_name, schema_name = fully_qualified_schema_name.split(".", 1)
                    try:
                        query = """
                            SELECT table_catalog || '.' || table_schema || '.' || table_name as full_table_name,
                                   table_comment
                            FROM information_schema.tables
                            WHERE table_catalog = ?
                            AND table_schema = ?
                            AND table_type IN ('BASE TABLE', 'VIEW')
                        """
                        rows = conn.execute(
                            query,
                            (
                                catalog_name,
                                schema_name,
                            ),
                        ).fetchall()
                        tables = []
                        for row in rows:
                            full_table_name = row[0]
                            table_comment = row[1]
                            tables.append(
                                TableInfo(
                                    name=full_table_name,
                                    description=table_comment,
                                )
                            )
                        schema_results.append(
                            SchemaTablesResult(
                                schema_name=schema_name, success=True, tables=tables, error=None
                            )
                        )
                    except Exception as e:
                        # Record failure for this schema
                        schema_results.append(
                            SchemaTablesResult(
                                schema_name=schema_name, success=False, tables=[], error=str(e)
                            )
                        )
            else:
                # Get all tables from all schemas
                query = """
                    SELECT table_catalog, table_schema, table_name, table_comment
                    FROM information_schema.tables
                    WHERE table_type IN ('BASE TABLE', 'VIEW')
                    ORDER BY table_schema, table_name
                """
                rows = conn.execute(query).fetchall()
                # Group by schema
                schema_dict: dict[str, list[TableInfo]] = {}
                for row in rows:
                    catalog = row[0]
                    schema_name = row[1]
                    table_name = row[2]
                    table_comment = row[3]
                    if schema_name not in schema_dict:
                        schema_dict[f"{catalog}.{schema_name}"] = []
                    schema_dict[f"{catalog}.{schema_name}"].append(
                        TableInfo(
                            name=f"{catalog}.{schema_name}.{table_name}",
                            description=table_comment,
                        )
                    )
                for fully_qualified_schema_name, tables in schema_dict.items():
                    schema_results.append(
                        SchemaTablesResult(
                            schema_name=fully_qualified_schema_name,
                            success=True,
                            tables=tables,
                            error=None,
                        )
                    )
            conn.close()

        except Exception as e:
            # If we can't connect to MotherDuck at all, return failure
            return ListTablesResult(
                success=False,
                schema_results=[],
                error=f"Failed to list MotherDuck tables: {str(e)}",
            )

        # Determine overall success
        has_any_success = any(r.success for r in schema_results)
        return ListTablesResult(success=has_any_success, schema_results=schema_results, error=None)

    def get_connection_name(self) -> str:
        """Generate connection name for MotherDuck"""
        clean_db_name = clean_string_for_connection_name(self.database_name)
        return f"motherduck_{clean_db_name}"

    @classmethod
    def get_help_info(cls) -> WarehouseHelpInfo:
        """Get help information for MotherDuck setup"""
        return WarehouseHelpInfo(
            setup_instructions=[
                "Sign in to MotherDuck",
                "Create or select a database",
                "Get your access token from MotherDuck settings",
                "Enter your database name and access token above",
            ],
            network_info=None,
            connection_permissions=None,
            schema_permissions=None,
        )


def clean_string_for_connection_name(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", s)


CompassWarehouseConfig = (
    SnowflakeWarehouseConfig
    | BigQueryWarehouseConfig
    | AthenaWarehouseConfig
    | RedshiftWarehouseConfig
    | PostgresWarehouseConfig
    | MotherduckWarehouseConfig
    | DatabricksWarehouseConfig
)


def get_sql_dialect_from_compass_warehouse_config(config: CompassWarehouseConfig) -> str:
    if isinstance(config, SnowflakeWarehouseConfig):
        return "snowflake"
    elif isinstance(config, BigQueryWarehouseConfig):
        return "bigquery"
    elif isinstance(config, AthenaWarehouseConfig):
        return config.query_engine
    elif isinstance(config, RedshiftWarehouseConfig):
        return "redshift"
    elif isinstance(config, PostgresWarehouseConfig):
        return "postgres"
    elif isinstance(config, MotherduckWarehouseConfig):
        return "duckdb"
    elif isinstance(config, DatabricksWarehouseConfig):
        return "databricks"
    else:
        raise ValueError(f"Unsupported CompassWarehouseConfig type: {type(config)}")


def compass_warehouse_config_from_json_config(json_config: JsonConfig) -> CompassWarehouseConfig:
    if json_config.type == "snowflake":
        return SnowflakeWarehouseConfig.model_validate(json_config.config)
    elif json_config.type == "bigquery":
        return BigQueryWarehouseConfig.model_validate(json_config.config)
    elif json_config.type == "athena":
        return AthenaWarehouseConfig.model_validate(json_config.config)
    elif json_config.type == "redshift":
        return RedshiftWarehouseConfig.model_validate(json_config.config)
    elif json_config.type == "postgres":
        return PostgresWarehouseConfig.model_validate(json_config.config)
    elif json_config.type == "motherduck":
        return MotherduckWarehouseConfig.model_validate(json_config.config)
    elif json_config.type == "databricks":
        return DatabricksWarehouseConfig.model_validate(json_config.config)
    else:
        raise ValueError(f"Unsupported SQL JSON config type: {json_config.type}")
