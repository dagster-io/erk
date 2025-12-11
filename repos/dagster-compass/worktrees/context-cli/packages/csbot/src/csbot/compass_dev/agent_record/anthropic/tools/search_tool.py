"""Search tool for recording scenarios."""

import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import Any


async def search_web(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Search the web for information.

    This is a mock search tool that returns realistic-looking results
    for testing purposes.

    Args:
        query: Search query
        limit: Maximum number of results to return (1-10)

    Returns:
        List of search result dictionaries
    """
    if limit < 1 or limit > 10:
        limit = 5

    # Mock search results based on query keywords
    base_results = {
        "python": [
            {
                "title": "Python.org - Official Website",
                "url": "https://python.org",
                "snippet": "The official home of the Python Programming Language",
            },
            {
                "title": "Python Tutorial - W3Schools",
                "url": "https://w3schools.com/python",
                "snippet": "Learn Python programming with examples",
            },
            {
                "title": "Real Python Tutorials",
                "url": "https://realpython.com",
                "snippet": "Python tutorials for developers of all skill levels",
            },
        ],
        "weather": [
            {
                "title": "Weather.com - Weather Forecast",
                "url": "https://weather.com",
                "snippet": "Get current weather conditions and forecasts",
            },
            {
                "title": "AccuWeather - Weather News",
                "url": "https://accuweather.com",
                "snippet": "Local and global weather forecasting",
            },
            {
                "title": "National Weather Service",
                "url": "https://weather.gov",
                "snippet": "Official weather warnings and forecasts",
            },
        ],
        "machine learning": [
            {
                "title": "Introduction to Machine Learning",
                "url": "https://ml-intro.com",
                "snippet": "Comprehensive guide to ML concepts and algorithms",
            },
            {
                "title": "Scikit-learn Documentation",
                "url": "https://scikit-learn.org",
                "snippet": "Machine Learning in Python - simple and efficient tools",
            },
            {
                "title": "Machine Learning Course - Coursera",
                "url": "https://coursera.org/ml",
                "snippet": "Learn machine learning from Stanford University",
            },
        ],
    }

    # Find matching results based on query keywords
    query_lower = query.lower()
    matching_results = []

    for keyword, results in base_results.items():
        if keyword in query_lower:
            matching_results.extend(results)

    # If no specific matches, generate generic results
    if not matching_results:
        matching_results = [
            {
                "title": f"Search result {i + 1} for '{query}'",
                "url": f"https://example.com/result-{i + 1}",
                "snippet": f"This is result {i + 1} matching your query about {query}",
            }
            for i in range(10)
        ]

    # Randomize and limit results
    random.shuffle(matching_results)
    return matching_results[:limit]


async def search_knowledge_base(query: str, category: str = "all") -> dict[str, Any]:
    """Search internal knowledge base.

    This is an async mock search that simulates searching an internal
    knowledge base or documentation system.

    Args:
        query: Search query
        category: Category to search in (all, docs, tutorials, api)

    Returns:
        Dictionary with search results and metadata
    """
    # Simulate async search delay
    await asyncio.sleep(0.02)

    categories = ["all", "docs", "tutorials", "api", "examples"]
    if category not in categories:
        category = "all"

    # Mock knowledge base results
    docs_results = [
        {
            "title": "API Documentation",
            "type": "docs",
            "relevance": 0.95,
            "content": "Comprehensive API reference",
        },
        {
            "title": "Getting Started Guide",
            "type": "docs",
            "relevance": 0.88,
            "content": "Step-by-step setup instructions",
        },
        {
            "title": "Configuration Options",
            "type": "docs",
            "relevance": 0.82,
            "content": "All available configuration settings",
        },
    ]

    tutorial_results = [
        {
            "title": "Basic Tutorial",
            "type": "tutorials",
            "relevance": 0.90,
            "content": "Learn the fundamentals",
        },
        {
            "title": "Advanced Patterns",
            "type": "tutorials",
            "relevance": 0.85,
            "content": "Advanced usage patterns and best practices",
        },
        {
            "title": "Common Use Cases",
            "type": "tutorials",
            "relevance": 0.80,
            "content": "Real-world examples and solutions",
        },
    ]

    api_results = [
        {
            "title": "REST API Endpoints",
            "type": "api",
            "relevance": 0.92,
            "content": "Available REST API endpoints",
        },
        {
            "title": "Authentication Methods",
            "type": "api",
            "relevance": 0.87,
            "content": "How to authenticate API requests",
        },
        {
            "title": "Rate Limiting",
            "type": "api",
            "relevance": 0.75,
            "content": "API rate limiting and quotas",
        },
    ]

    all_results = docs_results + tutorial_results + api_results

    # Filter by category
    if category != "all":
        filtered_results = [r for r in all_results if r["type"] == category]
    else:
        filtered_results = all_results

    # Sort by relevance
    filtered_results.sort(key=lambda x: x["relevance"], reverse=True)

    return {
        "query": query,
        "category": category,
        "total_results": len(filtered_results),
        "results": filtered_results[:5],  # Top 5 results
        "search_time_ms": random.randint(50, 200),
        "suggestions": ["Try more specific terms", "Check spelling", "Use different keywords"]
        if len(filtered_results) < 2
        else [],
    }


async def find_code_examples(language: str, topic: str) -> list[dict[str, Any]]:
    """Find code examples for a specific language and topic.

    Args:
        language: Programming language (python, javascript, java, etc.)
        topic: Programming topic or concept

    Returns:
        List of code example dictionaries
    """
    languages = ["python", "javascript", "java", "c++", "go", "rust", "typescript"]
    if language.lower() not in languages:
        return [{"error": f"Language '{language}' not supported. Supported: {languages}"}]

    # Mock code examples
    examples = [
        {
            "title": f"{topic.title()} Example in {language.title()}",
            "language": language,
            "difficulty": "beginner",
            "code": f"# {topic} example in {language}\nprint('Hello, {topic}!')",
            "description": f"Basic example demonstrating {topic} concepts",
            "tags": [topic, language, "example"],
            "upvotes": random.randint(10, 100),
        },
        {
            "title": f"Advanced {topic.title()} Implementation",
            "language": language,
            "difficulty": "advanced",
            "code": f"// Advanced {topic} implementation\nconst result = advanced{topic.title()}();",
            "description": f"More complex implementation of {topic} with best practices",
            "tags": [topic, language, "advanced", "best-practices"],
            "upvotes": random.randint(5, 50),
        },
        {
            "title": f"{topic.title()} with Error Handling",
            "language": language,
            "difficulty": "intermediate",
            "code": f"try:\n    {topic}_function()\nexcept Exception as e:\n    handle_error(e)",
            "description": f"Robust {topic} implementation with proper error handling",
            "tags": [topic, language, "error-handling", "robust"],
            "upvotes": random.randint(15, 75),
        },
    ]

    return examples


# Tool specifications
SEARCH_TOOLS: dict[str, Callable[..., Awaitable[Any]]] = {
    "search_web": search_web,
    "search_knowledge_base": search_knowledge_base,
    "find_code_examples": find_code_examples,
}
