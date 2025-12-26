"""Calculator tool for recording scenarios."""

import asyncio
import math
from collections.abc import Awaitable, Callable
from typing import Any


async def calculate(operation: str, a: float, b: float) -> dict[str, Any]:
    """Perform basic arithmetic calculations.

    Args:
        operation: The operation to perform (add, subtract, multiply, divide)
        a: First number
        b: Second number

    Returns:
        Dictionary with calculation result and details
    """
    operations = {
        "add": lambda x, y: x + y,
        "subtract": lambda x, y: x - y,
        "multiply": lambda x, y: x * y,
        "divide": lambda x, y: x / y if y != 0 else None,
    }

    if operation not in operations:
        raise ValueError(f"Unknown operation: {operation}")

    result = operations[operation](a, b)

    if result is None:
        return {"operation": operation, "a": a, "b": b, "result": None, "error": "Division by zero"}

    return {
        "operation": operation,
        "a": a,
        "b": b,
        "result": result,
        "formatted": f"{a} {operation} {b} = {result}",
    }


async def advanced_calculate(operation: str, numbers: list[float]) -> dict[str, Any]:
    """Perform advanced calculations on a list of numbers.

    This is an async function to test async tool execution.

    Args:
        operation: The operation to perform (sum, product, average, max, min)
        numbers: List of numbers to operate on

    Returns:
        Dictionary with calculation result
    """
    # Simulate some async work
    await asyncio.sleep(0.01)

    if not numbers:
        raise ValueError("Numbers list cannot be empty")

    operations = {
        "sum": sum,
        "product": lambda nums: math.prod(nums),
        "average": lambda nums: sum(nums) / len(nums),
        "max": max,
        "min": min,
    }

    if operation not in operations:
        raise ValueError(f"Unknown operation: {operation}")

    result = operations[operation](numbers)

    return {
        "operation": operation,
        "numbers": numbers,
        "count": len(numbers),
        "result": result,
        "formatted": f"{operation}({numbers}) = {result}",
    }


async def solve_quadratic(a: float, b: float, c: float) -> dict[str, Any]:
    """Solve quadratic equation ax² + bx + c = 0.

    Args:
        a: Coefficient of x²
        b: Coefficient of x
        c: Constant term

    Returns:
        Dictionary with solutions and details
    """
    if a == 0:
        if b == 0:
            return {
                "equation": f"{c} = 0",
                "type": "constant",
                "solutions": [] if c != 0 else ["all real numbers"],
                "error": None if c == 0 else "No solution",
            }
        else:
            # Linear equation: bx + c = 0
            solution = -c / b
            return {
                "equation": f"{b}x + {c} = 0",
                "type": "linear",
                "solutions": [solution],
                "error": None,
            }

    discriminant = b**2 - 4 * a * c

    if discriminant < 0:
        return {
            "equation": f"{a}x² + {b}x + {c} = 0",
            "type": "quadratic",
            "discriminant": discriminant,
            "solutions": [],
            "error": "No real solutions (discriminant < 0)",
        }
    elif discriminant == 0:
        solution = -b / (2 * a)
        return {
            "equation": f"{a}x² + {b}x + {c} = 0",
            "type": "quadratic",
            "discriminant": discriminant,
            "solutions": [solution],
            "error": None,
        }
    else:
        sqrt_discriminant = math.sqrt(discriminant)
        solution1 = (-b + sqrt_discriminant) / (2 * a)
        solution2 = (-b - sqrt_discriminant) / (2 * a)
        return {
            "equation": f"{a}x² + {b}x + {c} = 0",
            "type": "quadratic",
            "discriminant": discriminant,
            "solutions": [solution1, solution2],
            "error": None,
        }


# Tool specifications
CALCULATOR_TOOLS: dict[str, Callable[..., Awaitable[Any]]] = {
    "calculate": calculate,
    "advanced_calculate": advanced_calculate,
    "solve_quadratic": solve_quadratic,
}
