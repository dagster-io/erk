"""JSON utilities for safe serialization."""

import datetime
import json
from decimal import Decimal
from typing import Any


class SafeEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal, datetime, and other common types safely."""

    def default(self, o: Any) -> Any:
        if isinstance(o, Decimal):
            return float(o)
        elif isinstance(o, datetime.datetime):
            return o.isoformat()
        return super().default(o)


def safe_json_dumps(obj: Any) -> str:
    """Safely serialize an object to JSON, handling Decimal and other special types."""
    return json.dumps(obj, cls=SafeEncoder, default=str)
