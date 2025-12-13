"""Configuration models for Compass Bot."""

from typing import Literal

from pydantic import BaseModel, Field, SecretStr, model_validator


class AWSKmsConfig(BaseModel, frozen=True):
    """Configuration for AWS KMS-based envelope encryption."""

    type: Literal["aws_kms"] = "aws_kms"
    kms_key_id: str
    region: str

    # for testing locally with local-kms
    # https://github.com/nsmithuk/local-kms?tab=readme-ov-file
    endpoint_url: str | None = None
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None

    @model_validator(mode="after")
    def validate_model(self):
        if self.aws_access_key_id is None != self.aws_secret_access_key is None:
            raise ValueError(
                "if aws_access_key_id is specified, aws_secret_access_key must also be specified"
            )
        return self


class PlaintextKekConfig(BaseModel):
    """Configuration for plaintext KEK (local development only)."""

    type: Literal["plaintext"] = "plaintext"
    key: SecretStr


# this can be used when KEK is not used, ie the legacy "url" column is populated
# and not the new "encrypted_url" column
class UnsupportedKekConfig(BaseModel):
    type: Literal["unsupported"] = "unsupported"


KekConfig = AWSKmsConfig | PlaintextKekConfig | UnsupportedKekConfig


class DatabaseConfig(BaseModel):
    """Configuration for database connection.

    Supports both traditional password-based authentication and AWS IAM authentication.
    """

    database_uri: str
    use_iam_auth: bool = Field(
        default=False
    )  # If True, use AWS IAM authentication instead of password
    use_iam_auth_v2: bool = Field(
        default=False
    )  # If True, use AWS IAM authentication instead of password
    seed_database_from: str | None = Field(default=None)
    kek_config: KekConfig = Field(default_factory=UnsupportedKekConfig)

    # indicates whether the db should be initialized, ie schema applied, or not
    # this defaults to true mostly out of legacy consideration, we should probably
    # be more explicit about when we want this to happen and not just always initialize
    initialize_db: bool = Field(default=True)

    # When True, store connection URLs encrypted in the database using envelope encryption
    # When False, store URLs as Jinja templates and use Render secret store
    use_encrypted_connection_urls: bool = Field(default=False)

    @model_validator(mode="after")
    def validate_model(self):
        if self.seed_database_from and not self.initialize_db:
            raise ValueError("if seed_database_from is specified, the db must be re-initialized")
        return self

    @classmethod
    def from_sqlite_path(cls, path):
        return cls(database_uri=f"sqlite:///{path}")

    @classmethod
    def from_uri(cls, uri: str):
        return cls(database_uri=uri)
