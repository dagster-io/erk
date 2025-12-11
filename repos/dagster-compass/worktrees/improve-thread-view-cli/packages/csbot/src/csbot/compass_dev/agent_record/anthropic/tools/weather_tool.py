"""Weather tool for recording scenarios."""

from collections.abc import Awaitable, Callable
from typing import Any


async def get_current_weather(location: str, unit: "str" = "fahrenheit") -> dict[str, Any]:
    """Get the current weather for a location.

    This is a mock weather tool that returns realistic-looking data
    for testing purposes.

    Args:
        location: The city/location to get weather for
        unit: Temperature unit (fahrenheit or celsius)

    Returns:
        Weather data dictionary
    """
    # Mock weather data based on location
    mock_data = {
        "paris": {"temp_f": 68, "temp_c": 20, "condition": "partly cloudy", "humidity": 65},
        "london": {"temp_f": 59, "temp_c": 15, "condition": "rainy", "humidity": 80},
        "tokyo": {"temp_f": 77, "temp_c": 25, "condition": "sunny", "humidity": 55},
        "new york": {"temp_f": 72, "temp_c": 22, "condition": "clear", "humidity": 45},
        "sydney": {"temp_f": 75, "temp_c": 24, "condition": "partly sunny", "humidity": 60},
    }

    location_lower = location.lower()
    base_data = mock_data.get(
        location_lower, {"temp_f": 70, "temp_c": 21, "condition": "unknown", "humidity": 50}
    )

    temp_key = "temp_c" if unit.lower() == "celsius" else "temp_f"

    return {
        "location": location,
        "temperature": base_data[temp_key],
        "unit": unit,
        "condition": base_data["condition"],
        "humidity": base_data["humidity"],
        "wind_speed": 8,
        "visibility": "10 miles" if unit == "fahrenheit" else "16 km",
    }


async def get_weather_forecast(location: str, days: int = 5) -> list[dict[str, Any]]:
    """Get weather forecast for multiple days.

    Args:
        location: The city/location to get forecast for
        days: Number of days to forecast (1-7)

    Returns:
        List of daily weather forecasts
    """
    if days < 1 or days > 7:
        raise ValueError("Days must be between 1 and 7")

    base_temp = 70
    conditions = ["sunny", "partly cloudy", "cloudy", "rainy", "partly sunny"]

    forecast = []
    for day in range(days):
        temp_variation = (day - 2) * 3  # Vary temperature by day
        forecast.append(
            {
                "day": day + 1,
                "date": f"2024-08-{24 + day}",
                "location": location,
                "high_temp": base_temp + temp_variation + 5,
                "low_temp": base_temp + temp_variation - 5,
                "condition": conditions[day % len(conditions)],
                "chance_of_rain": max(0, min(100, 20 + day * 15)),
                "humidity": 50 + (day * 5),
            }
        )

    return forecast


# Tool specifications
WEATHER_TOOLS: dict[str, Callable[..., Awaitable[Any]]] = {
    "get_weather": get_current_weather,
    "get_forecast": get_weather_forecast,
}
