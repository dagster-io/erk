"""Generic forms engine for warehouse config pydantic models"""

from dataclasses import dataclass
from typing import Literal, get_args, get_origin

import pydantic
from pydantic.fields import FieldInfo


@dataclass
class FormField:
    """Represents a single form field"""

    name: str
    label: str
    field_type: str  # text, textarea, password, select, radio
    required: bool
    placeholder: str | None = None
    help_text: str | None = None
    options: list[str] | None = None  # for select/radio fields
    rows: int | None = None  # for textarea
    default_value: str | None = None


@dataclass
class FormGroup:
    """Represents a group of related form fields"""

    name: str
    label: str
    fields: list[FormField]
    is_union: bool = False  # True if this represents a tagged union choice


@dataclass
class WarehouseFormConfig:
    """Complete form configuration for a warehouse type"""

    warehouse_name: str
    display_name: str
    icon_html: str
    color_scheme: str  # CSS color class prefix (e.g., "green", "blue", "red")
    groups: list[FormGroup]


def get_field_display_name(field_name: str, field_info: FieldInfo) -> str:
    """Get display name from pydantic field metadata or convert snake_case"""
    # Use title from pydantic field if available
    if field_info.title:
        return field_info.title

    # Handle special cases for fields without explicit titles
    special_cases = {
        "credential_type": "Authentication Method",
    }

    if field_name in special_cases:
        return special_cases[field_name]

    # Convert snake_case to Title Case as fallback
    return field_name.replace("_", " ").title()


def get_field_placeholder(field_info: FieldInfo) -> str | None:
    """Get placeholder text from pydantic field metadata"""
    if field_info.examples:
        return str(field_info.examples[0])
    return None


def get_field_help_text(field_info: FieldInfo) -> str | None:
    """Get help text from pydantic field metadata"""
    return field_info.description


def get_field_widget_type(field_info: FieldInfo, field_type: type | None) -> str:
    """Get widget type from pydantic field metadata or determine from type"""
    # Check for explicit widget type in json_schema_extra
    if field_info.json_schema_extra and isinstance(field_info.json_schema_extra, dict):
        widget = field_info.json_schema_extra.get("widget")
        if widget and isinstance(widget, str):
            return widget

    # Default based on Python type
    if field_type is int:
        return "text"  # HTML5 number input can be finicky
    else:
        return "text"


def introspect_pydantic_model(model_class: type[pydantic.BaseModel]) -> list[FormField]:
    """Extract form fields from a pydantic model"""
    fields = []

    for field_name, field_info in model_class.model_fields.items():
        field_type = field_info.annotation
        is_optional = False

        # Handle Union types (tagged unions)
        origin = get_origin(field_type)
        if origin is not None:
            args = get_args(field_type)

            # Check if it's a Union with None (Optional)
            if origin is type(None) or (len(args) == 2 and type(None) in args):
                # This is Optional[T], get the non-None type
                is_optional = True
                field_type = args[0] if args[1] is type(None) else args[1]
                origin = get_origin(field_type)
                args = get_args(field_type) if origin else []

            # Handle Literal types (for enum-like choices)
            if origin is Literal:
                literal_values = get_args(field_type)
                form_field = FormField(
                    name=field_name,
                    label=get_field_display_name(field_name, field_info),
                    field_type="select" if len(literal_values) > 3 else "radio",
                    required=not is_optional and field_info.is_required(),
                    options=list(literal_values),
                    help_text=get_field_help_text(field_info),
                    default_value=literal_values[0] if literal_values else None,
                )
                fields.append(form_field)
                continue

        # Determine form field type from metadata or Python type
        form_field_type = get_field_widget_type(field_info, field_type)

        form_field = FormField(
            name=field_name,
            label=get_field_display_name(field_name, field_info),
            field_type=form_field_type,
            required=not is_optional and field_info.is_required(),
            placeholder=get_field_placeholder(field_info),
            help_text=get_field_help_text(field_info),
            rows=8 if form_field_type == "textarea" else None,
        )

        fields.append(form_field)

    return fields


def handle_union_types(model_class: type[pydantic.BaseModel]) -> list[FormGroup]:
    """Handle tagged union types in pydantic models (like Snowflake credentials)"""
    groups = []
    union_fields = []
    regular_fields = []

    for field_name, field_info in model_class.model_fields.items():
        field_type = field_info.annotation
        origin = get_origin(field_type)

        # Check if this is a Union type (not Optional)
        if origin is not None:
            args = get_args(field_type)
            if len(args) > 1 and type(None) not in args:
                # This is a true Union, likely a tagged union
                union_fields.append((field_name, field_info, args))
            else:
                regular_fields.append((field_name, field_info))
        else:
            regular_fields.append((field_name, field_info))

    # Add regular fields as the main group
    if regular_fields:
        regular_form_fields = []
        for field_name, field_info in regular_fields:
            if field_name == "credential":  # Skip the union field itself
                continue

            field_type = field_info.annotation
            is_optional = False

            # Handle Optional types
            if get_origin(field_type) is not None:
                args = get_args(field_type)
                if len(args) == 2 and type(None) in args:
                    is_optional = True
                    field_type = args[0] if args[1] is type(None) else args[1]

            # Handle Literal types
            if get_origin(field_type) is Literal:
                literal_values = get_args(field_type)
                form_field = FormField(
                    name=field_name,
                    label=get_field_display_name(field_name, field_info),
                    field_type="radio",
                    required=not is_optional and field_info.is_required(),
                    options=list(literal_values),
                    help_text=get_field_help_text(field_info),
                    default_value=literal_values[0] if literal_values else None,
                )
                regular_form_fields.append(form_field)
                continue

            # Regular field processing - determine field type from metadata
            form_field_type = get_field_widget_type(field_info, field_type)

            form_field = FormField(
                name=field_name,
                label=get_field_display_name(field_name, field_info),
                field_type=form_field_type,
                required=not is_optional and field_info.is_required(),
                placeholder=get_field_placeholder(field_info),
                help_text=get_field_help_text(field_info),
                rows=8 if form_field_type == "textarea" else None,
            )
            regular_form_fields.append(form_field)

        groups.append(
            FormGroup(name="main", label="Connection Details", fields=regular_form_fields)
        )

    # Handle union fields (like Snowflake credential types)
    for field_name, field_info, union_args in union_fields:
        if field_name == "credential":
            # Create radio button for credential type selection
            # Create a dummy field info for the credential_type field
            dummy_field_info = FieldInfo(title=None)
            credential_type_field = FormField(
                name="credential_type",
                label=get_field_display_name("credential_type", dummy_field_info),
                field_type="radio",
                required=True,
                options=["password", "private_key"],
                help_text="Choose your authentication method",
            )

            # Create conditional fields for each credential type
            # Import credential classes to get their field metadata
            from csbot.slackbot.webapp.add_connections.models import (
                SnowflakePasswordCredential,
                SnowflakePrivateKeyCredential,
            )

            # Get password field metadata from SnowflakePasswordCredential
            password_field_info = SnowflakePasswordCredential.model_fields["password"]
            password_field = FormField(
                name="password",
                label="Password",
                field_type="password",
                required=True,
                placeholder=get_field_placeholder(password_field_info),
                help_text=get_field_help_text(password_field_info),
            )

            # Get private key field metadata from SnowflakePrivateKeyCredential
            private_key_field_info = SnowflakePrivateKeyCredential.model_fields["private_key_file"]
            private_key_field = FormField(
                name="private_key",
                label="Private Key",
                field_type="textarea",
                required=True,
                placeholder=get_field_placeholder(private_key_field_info),
                help_text=get_field_help_text(private_key_field_info),
                rows=4,
            )

            # Get key password field metadata from SnowflakePrivateKeyCredential
            key_password_field_info = SnowflakePrivateKeyCredential.model_fields["key_password"]
            key_password_field = FormField(
                name="key_password",
                label="Private Key Password",
                field_type="password",
                required=False,
                placeholder=get_field_placeholder(key_password_field_info),
                help_text=get_field_help_text(key_password_field_info),
            )

            groups.append(
                FormGroup(
                    name="credential",
                    label="Authentication",
                    fields=[
                        credential_type_field,
                        password_field,
                        private_key_field,
                        key_password_field,
                    ],
                    is_union=True,
                )
            )

    return groups


# Warehouse-specific configurations
WAREHOUSE_CONFIGS = {
    "bigquery": {
        "display_name": "BigQuery",
        "icon_html": """<div class="mx-auto flex items-center justify-center h-16 w-16 mb-4">
            <img src="/static/bigquery.svg" alt="BigQuery" class="h-16 w-16" />
        </div>""",
        "color_scheme": "green",
    },
    "snowflake": {
        "display_name": "Snowflake",
        "icon_html": """<div class="mx-auto flex items-center justify-center h-16 w-16 mb-4">
            <img src="/static/snowflake.svg" alt="Snowflake" class="h-16 w-16" />
        </div>""",
        "color_scheme": "blue",
    },
    "athena": {
        "display_name": "AWS Athena",
        "icon_html": """<div class="mx-auto flex items-center justify-center h-16 w-16 mb-4">
            <img src="/static/Athena.svg" alt="AWS Athena" class="h-16 w-16" />
        </div>""",
        "color_scheme": "orange",
    },
    "redshift": {
        "display_name": "AWS Redshift",
        "icon_html": """<div class="mx-auto flex items-center justify-center h-16 w-16 mb-4">
            <img src="/static/redshift.svg" alt="AWS Redshift" class="h-16 w-16" />
        </div>""",
        "color_scheme": "red",
    },
    "postgres": {
        "display_name": "PostgreSQL",
        "icon_html": """<div class="mx-auto flex items-center justify-center h-16 w-16 mb-4">
            <img src="/static/postgresql.svg" alt="PostgreSQL" class="h-16 w-16" />
        </div>""",
        "color_scheme": "blue",
    },
    "motherduck": {
        "display_name": "MotherDuck",
        "icon_html": """<div class="mx-auto flex items-center justify-center h-16 w-16 mb-4">
            <img src="/static/motherduck.svg" alt="MotherDuck" class="h-16 w-16" />
        </div>""",
        "color_scheme": "yellow",
    },
    "databricks": {
        "display_name": "Databricks",
        "icon_html": """<div class="mx-auto flex items-center justify-center h-16 w-16 mb-4">
            <img src="/static/databricks.svg" alt="Databricks" class="h-16 w-16" />
        </div>""",
        "color_scheme": "red",
    },
}


def generate_form_config(
    warehouse_name: str, model_class: type[pydantic.BaseModel]
) -> WarehouseFormConfig:
    """Generate complete form configuration for a warehouse type"""
    warehouse_info = WAREHOUSE_CONFIGS.get(
        warehouse_name,
        {
            "display_name": warehouse_name.title(),
            "icon_html": '<div class="mx-auto w-16 h-16 bg-gray-100 rounded-full mb-4"></div>',
            "color_scheme": "gray",
        },
    )

    # Check if this model has union types (like Snowflake)
    # Exclude Literal types from union detection since they are handled differently
    has_unions = any(
        get_origin(field_info.annotation) is not None
        and get_origin(field_info.annotation) is not Literal
        and len(get_args(field_info.annotation)) > 1
        and type(None) not in get_args(field_info.annotation)
        for field_info in model_class.model_fields.values()
    )

    if has_unions:
        groups = handle_union_types(model_class)
    else:
        fields = introspect_pydantic_model(model_class)
        groups = [FormGroup(name="main", label="Connection Details", fields=fields)]

    return WarehouseFormConfig(
        warehouse_name=warehouse_name,
        display_name=warehouse_info["display_name"],
        icon_html=warehouse_info["icon_html"],
        color_scheme=warehouse_info["color_scheme"],
        groups=groups,
    )
