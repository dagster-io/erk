"""
Data Visualization DSL using Pydantic for easy LLM configuration.
Supports bar charts, line charts, donut charts, and wordclouds with multiple series.
"""

import matplotlib

# Force matplotlib to use the Anti-Grain Geometry (Agg) backend before any other imports.
# This is critical for the Slack bot because:
#
# 1. Thread Safety: The bot runs matplotlib in background threads via @sync_to_async.
#    GUI backends like 'MacOSX', 'Qt5Agg', 'TkAgg' are not thread-safe and will crash
#    when trying to create windows/displays from non-main threads.
#
# 2. Headless Environments: Production deployments (Docker, CI/CD, servers) typically
#    run without display servers. GUI backends require $DISPLAY or equivalent and will
#    fail with "cannot connect to X server" or similar errors.
#
# 3. Platform Consistency: Agg backend works identically across macOS, Linux, and
#    Windows, ensuring consistent behavior in all deployment environments.
#
# The Agg backend is optimized for generating image files (PNG, SVG) rather than
# interactive displays, making it perfect for this use case where we export charts
# as bytes for Slack attachments.
matplotlib.use("Agg")

import io
from enum import Enum
from pathlib import Path
from typing import Literal

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from matplotlib.patches import Circle
from pydantic import BaseModel, Field
from wordcloud import WordCloud


class ChartType(str, Enum):
    """Supported chart types."""

    BAR = "bar"
    LINE = "line"
    DONUT = "donut"
    WORDCLOUD = "wordcloud"


class ColorScheme(str, Enum):
    """Predefined color schemes."""

    DEFAULT = "default"
    BLUES = "blues"
    GREENS = "greens"
    REDS = "reds"
    PURPLES = "purples"
    ORANGES = "oranges"
    PASTEL = "pastel"
    VIBRANT = "vibrant"


class SeriesConfig(BaseModel):
    """Configuration for a single data series."""

    name: str = Field(..., description="Name of the series")
    data: list[float | int] = Field(..., description="Data values for the series")
    color: str | None = Field(
        None, description="Color for this series (hex, name, or None for auto)"
    )
    line_style: str | None = Field(
        None, description="Line style for line charts (e.g., '-', '--', ':')"
    )
    marker: str | None = Field(
        None, description="Marker style for line charts (e.g., 'o', 's', '^')"
    )


class SeriesChartConfig(BaseModel):
    """Configuration for bar and line charts that use data series."""

    chart_type: Literal[ChartType.BAR, ChartType.LINE] = Field(
        ..., description="Type of chart to create"
    )
    x_label: str | None = Field(None, description="X-axis label")
    y_label: str | None = Field(None, description="Y-axis label")
    x_values: list[str] | None = Field(
        None, description="X-axis values (categories for bar, x-coords for line)"
    )
    series: list[SeriesConfig] = Field(..., description="Data series to plot")
    color_scheme: ColorScheme = Field(ColorScheme.DEFAULT, description="Color scheme to use")
    grid: bool = Field(True, description="Show grid lines")
    legend: bool = Field(True, description="Show legend")


class DonutChartConfig(BaseModel):
    """Configuration for donut charts."""

    chart_type: Literal[ChartType.DONUT] = Field(
        ChartType.DONUT, description="Type of chart to create"
    )
    labels: list[str] | None = Field(None, description="Labels for each segment")
    data: list[float | int] = Field(..., description="Data values for each segment")
    color_scheme: ColorScheme = Field(ColorScheme.DEFAULT, description="Color scheme to use")


class WordCloudChartConfig(BaseModel):
    """Configuration for wordcloud-specific settings.

    Takes a mapping of words to their frequencies (not raw text).
    Example: {"python": 100, "data": 85, "analysis": 70}

    Note: Width and height are automatically computed from the chart dimensions
    (chart width/height in inches * 100 = wordcloud width/height in pixels).
    """

    chart_type: Literal[ChartType.WORDCLOUD] = Field(
        ChartType.WORDCLOUD, description="Type of chart to create"
    )
    word_frequencies: dict[str, float] = Field(
        ..., description="Mapping of words to their frequencies (not raw text)"
    )
    max_words: int = Field(100, description="Maximum number of words to display")
    background_color: str = Field("white", description="Background color")
    colormap: str = Field("viridis", description="Matplotlib colormap for word colors")
    relative_scaling: float | str = Field(
        0.5, description="Relative scaling of word sizes (float or 'auto')"
    )
    prefer_horizontal: float = Field(
        0.9, description="Preference for horizontal words (0.0 to 1.0)"
    )
    min_font_size: int = Field(4, description="Minimum font size")
    max_font_size: int | None = Field(None, description="Maximum font size")
    random_state: int | None = Field(None, description="Random state for reproducibility")


# Union type for all chart configurations
class ChartConfig(BaseModel):
    """Main configuration for a chart."""

    title: str | None = Field(None, description="Chart title")
    width: int = Field(10, description="Chart width in inches")
    height: int = Field(6, description="Chart height in inches")
    style: str = Field("default", description="Matplotlib style to use")

    chart_specific_config: SeriesChartConfig | DonutChartConfig | WordCloudChartConfig = Field(
        ..., description="Chart-specific configuration", discriminator="chart_type"
    )


class DataVizDSL:
    """Data Visualization DSL for creating charts from configuration."""

    def __init__(self):
        self.color_palettes = {
            ColorScheme.DEFAULT: [
                "#1f77b4",
                "#ff7f0e",
                "#2ca02c",
                "#d62728",
                "#9467bd",
                "#8c564b",
            ],
            ColorScheme.BLUES: [
                "#1f77b4",
                "#aec7e8",
                "#ff7f0e",
                "#ffbb78",
                "#2ca02c",
                "#98df8a",
            ],
            ColorScheme.GREENS: [
                "#2ca02c",
                "#98df8a",
                "#d62728",
                "#ff9896",
                "#9467bd",
                "#c5b0d5",
            ],
            ColorScheme.REDS: [
                "#d62728",
                "#ff9896",
                "#1f77b4",
                "#aec7e8",
                "#2ca02c",
                "#98df8a",
            ],
            ColorScheme.PURPLES: [
                "#9467bd",
                "#c5b0d5",
                "#ff7f0e",
                "#ffbb78",
                "#2ca02c",
                "#98df8a",
            ],
            ColorScheme.ORANGES: [
                "#ff7f0e",
                "#ffbb78",
                "#1f77b4",
                "#aec7e8",
                "#2ca02c",
                "#98df8a",
            ],
            ColorScheme.PASTEL: [
                "#ffb3ba",
                "#baffc9",
                "#bae1ff",
                "#ffffba",
                "#ffb3f7",
                "#f7b3ff",
            ],
            ColorScheme.VIBRANT: [
                "#ff0000",
                "#00ff00",
                "#0000ff",
                "#ffff00",
                "#ff00ff",
                "#00ffff",
            ],
        }

    def _get_colors(
        self, config: SeriesChartConfig | DonutChartConfig, num_series: int
    ) -> list[str]:
        """Get colors for the series based on configuration."""
        palette = self.color_palettes[config.color_scheme]
        colors = []

        for i in range(num_series):
            colors.append(palette[i % len(palette)])

        return colors

    def _add_ai_warning(self, fig: Figure, ax):
        """Add AI-generated warning to the chart."""
        warning_text = "⚠️ AI-Generated Content - May Contain Inaccuracies"

        # Add warning text below all other content in the figure
        fig.text(
            0.5,
            -0.05,  # Position below the plot area
            warning_text,
            ha="center",
            va="top",
            fontsize=10,
            color="#d62728",  # Red color for warning
            fontweight="bold",
            bbox=dict(
                boxstyle="round,pad=0.3",
                facecolor="#fff3cd",  # Light yellow background
                edgecolor="#d62728",
                alpha=0.8,
            ),
        )

    def _setup_plot(self, config: ChartConfig):
        """Setup the matplotlib plot with styling."""
        plt.style.use(config.style)
        fig, ax = plt.subplots(figsize=(config.width, config.height))

        if config.title:
            ax.set_title(config.title, fontsize=14, fontweight="bold", pad=20)

        self._add_ai_warning(fig, ax)

        return fig, ax

    def create_bar_chart(self, chart_config: ChartConfig) -> Figure:
        """Create a bar chart."""
        fig, ax = self._setup_plot(chart_config)
        config = chart_config.chart_specific_config
        if not isinstance(config, SeriesChartConfig):
            raise ValueError("Chart configuration must be a SeriesChartConfig")

        colors = self._get_colors(config, len(config.series))

        if config.x_label:
            ax.set_xlabel(config.x_label, fontsize=12)

        if config.y_label:
            ax.set_ylabel(config.y_label, fontsize=12)

        if config.grid:
            ax.grid(True, alpha=0.3)

        x_values = config.x_values or [
            f"Category {i + 1}" for i in range(len(config.series[0].data))
        ]
        x_pos = np.arange(len(x_values))

        bar_width = 0.8 / len(config.series)

        for i, (series, color) in enumerate(zip(config.series, colors)):
            if series.color:
                color = series.color
            offset = (i - len(config.series) / 2 + 0.5) * bar_width
            ax.bar(
                x_pos + offset,
                series.data,
                bar_width,
                label=series.name,
                color=color,
                alpha=0.8,
            )

        ax.set_xticks(x_pos)
        ax.set_xticklabels(x_values, rotation=45, ha="right")

        if config.legend:
            ax.legend()

        # Use autofmt_xdate for better date formatting
        fig.autofmt_xdate()
        plt.tight_layout()
        return fig

    def create_line_chart(self, chart_config: ChartConfig) -> Figure:
        """Create a line chart."""
        fig, ax = self._setup_plot(chart_config)
        config = chart_config.chart_specific_config
        if not isinstance(config, SeriesChartConfig):
            raise ValueError("Chart configuration must be a SeriesChartConfig")

        colors = self._get_colors(config, len(config.series))

        if config.x_label:
            ax.set_xlabel(config.x_label, fontsize=12)

        if config.y_label:
            ax.set_ylabel(config.y_label, fontsize=12)

        if config.grid:
            ax.grid(True, alpha=0.3)

        x_values = config.x_values or list(range(len(config.series[0].data)))

        for i, (series, color) in enumerate(zip(config.series, colors)):
            if series.color:
                color = series.color
            line_style = series.line_style or "-"
            marker = series.marker or "o"

            ax.plot(
                x_values,
                series.data,
                color=color,
                linewidth=2,
                marker=marker,
                markersize=6,
                linestyle=line_style,
                label=series.name,
                alpha=0.8,
            )

        if config.legend:
            ax.legend()

        # Use autofmt_xdate for better date formatting
        fig.autofmt_xdate()
        plt.tight_layout()
        return fig

    def create_donut_chart(self, chart_config: ChartConfig) -> Figure:
        """Create a donut chart."""
        fig, ax = self._setup_plot(chart_config)
        config = chart_config.chart_specific_config
        if not isinstance(config, DonutChartConfig):
            raise ValueError("Chart configuration must be a DonutChartConfig")

        labels = config.labels or [f"Category {i + 1}" for i in range(len(config.data))]

        colors = self._get_colors(config, len(config.data))

        # Create donut chart
        ax.pie(
            config.data,
            labels=labels,
            colors=colors,
            autopct="%1.1f%%",
            startangle=90,
            pctdistance=0.85,
            labeldistance=1.1,
        )

        # Create donut hole
        centre_circle = Circle((0, 0), 0.70, fc="white")
        ax.add_patch(centre_circle)

        # Equal aspect ratio ensures that pie is drawn as a circle
        ax.axis("equal")

        plt.tight_layout()
        return fig

    def create_wordcloud(self, chart_config: ChartConfig) -> Figure:
        """Create a wordcloud chart."""
        wordcloud_config = chart_config.chart_specific_config
        if not isinstance(wordcloud_config, WordCloudChartConfig):
            raise ValueError("Chart configuration must be a WordCloudChartConfig")

        # Compute wordcloud dimensions from chart dimensions (convert inches to pixels)
        # Standard DPI is 100 for wordcloud, so multiply by 100
        wordcloud_width = int(chart_config.width * 100)
        wordcloud_height = int(chart_config.height * 100)

        # Create wordcloud
        wordcloud = WordCloud(
            width=wordcloud_width,
            height=wordcloud_height,
            background_color=wordcloud_config.background_color,
            colormap=wordcloud_config.colormap,
            max_words=wordcloud_config.max_words,
            relative_scaling=wordcloud_config.relative_scaling,  # type: ignore  # WordCloud relative_scaling accepts float | str but typed as Union
            prefer_horizontal=wordcloud_config.prefer_horizontal,
            min_font_size=wordcloud_config.min_font_size,
            max_font_size=wordcloud_config.max_font_size,
            random_state=wordcloud_config.random_state,
        )

        # Generate wordcloud from frequencies
        wordcloud.generate_from_frequencies(wordcloud_config.word_frequencies)

        # Create figure and axis
        fig, ax = plt.subplots(figsize=(chart_config.width, chart_config.height))

        # Display the wordcloud
        ax.imshow(wordcloud, interpolation="bilinear")
        ax.axis("off")

        if chart_config.title:
            ax.set_title(chart_config.title, fontsize=14, fontweight="bold", pad=20)

        # Add AI warning
        self._add_ai_warning(fig, ax)

        plt.tight_layout()
        return fig

    def create_chart(self, config: ChartConfig) -> Figure:
        """Create a chart based on the configuration."""
        if config.chart_specific_config.chart_type == ChartType.BAR:
            return self.create_bar_chart(config)
        elif config.chart_specific_config.chart_type == ChartType.LINE:
            return self.create_line_chart(config)
        elif config.chart_specific_config.chart_type == ChartType.DONUT:
            return self.create_donut_chart(config)
        elif config.chart_specific_config.chart_type == ChartType.WORDCLOUD:
            return self.create_wordcloud(config)
        else:
            raise ValueError(f"Unsupported chart type: {config.chart_specific_config.chart_type}")

    def save_chart(self, fig: Figure, filepath: str | Path, dpi: int = 300) -> None:
        """Save the chart to a file."""
        fig.savefig(str(filepath), dpi=dpi, bbox_inches="tight")
        fig.clf()
        plt.close(fig)

    def get_chart_as_bytes(self, fig: Figure, format: str = "png", dpi: int = 150) -> bytes:
        """Get the chart as bytes for easy transmission."""
        buffer = io.BytesIO()
        fig.savefig(buffer, format=format, dpi=dpi, bbox_inches="tight")
        buffer.seek(0)
        fig.clf()
        plt.close(fig)
        return buffer.getvalue()


# Convenience function for easy LLM usage
def create_visualization(config: ChartConfig, output_path: str):
    """
    Create a visualization from a configuration and save it to a file.

    Args:
        config: Chart configuration
        output_path: Path to save the chart
    """
    dsl = DataVizDSL()
    fig = dsl.create_chart(config)
    dsl.save_chart(fig, output_path)


# # Example usage and test functions
# def create_example_charts():
#     """Create example charts to demonstrate the DSL."""
#     dsl = DataVizDSL()

#     # Example 1: Bar chart
#     bar_config = SeriesChartConfig(
#         chart_type=ChartType.BAR,
#         title="Sales by Quarter",
#         x_label="Quarter",
#         y_label="Sales ($)",
#         x_values=["Q1", "Q2", "Q3", "Q4"],
#         series=[
#             SeriesConfig(
#                 name="2023",
#                 data=[100, 120, 140, 160],
#                 color=None,
#                 line_style=None,
#                 marker=None,
#             ),
#             SeriesConfig(
#                 name="2024",
#                 data=[110, 130, 150, 170],
#                 color=None,
#                 line_style=None,
#                 marker=None,
#             ),
#         ],
#         color_scheme=ColorScheme.BLUES,
#         width=10,
#         height=6,
#         grid=True,
#         legend=True,
#         style="default",
#     )

#     # Example 4: Wordcloud chart
#     wordcloud_config = WordCloudChartConfig(
#         chart_type=ChartType.WORDCLOUD,
#         title="Most Common Words",
#         width=12,
#         height=8,
#         style="default",
#         wordcloud_config=WordCloudConfig(
#             word_frequencies={
#                 "python": 100,
#                 "data": 85,
#                 "analysis": 70,
#                 "visualization": 65,
#                 "machine": 60,
#                 "learning": 55,
#                 "artificial": 50,
#                 "intelligence": 45,
#                 "algorithm": 40,
#                 "model": 35,
#                 "training": 30,
#                 "prediction": 25,
#                 "neural": 20,
#                 "network": 18,
#                 "deep": 15,
#             },
#             max_words=50,
#             background_color="white",
#             colormap="viridis",
#             relative_scaling=0.5,
#             prefer_horizontal=0.9,
#             min_font_size=4,
#             max_font_size=None,
#             random_state=42,
#         ),
#     )

#     # Example 2: Line chart
#     line_config = SeriesChartConfig(
#         chart_type=ChartType.LINE,
#         title="Temperature Over Time",
#         x_label="Month",
#         y_label="Temperature (°C)",
#         x_values=["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
#         series=[
#             SeriesConfig(
#                 name="High",
#                 data=[10, 12, 15, 18, 22, 25],
#                 color=None,
#                 line_style="-",
#                 marker="o",
#             ),
#             SeriesConfig(
#                 name="Low",
#                 data=[2, 4, 7, 10, 14, 17],
#                 color=None,
#                 line_style="--",
#                 marker="s",
#             ),
#         ],
#         color_scheme=ColorScheme.REDS,
#         width=10,
#         height=6,
#         grid=True,
#         legend=True,
#         style="default",
#     )

#     # Example 3: Donut chart
#     donut_config = DonutChartConfig(
#         chart_type=ChartType.DONUT,
#         title="Market Share",
#         labels=["Product A", "Product B", "Product C", "Product D"],
#         data=[30, 25, 20, 25],
#         color_scheme=ColorScheme.GREENS,
#         width=10,
#         height=6,
#         style="default",
#     )

#     # Create and save examples
#     charts = [
#         ("bar_chart_example.png", bar_config),
#         ("line_chart_example.png", line_config),
#         ("donut_chart_example.png", donut_config),
#         ("wordcloud_example.png", wordcloud_config),
#     ]

#     for filename, config in charts:
#         fig = dsl.create_chart(config)
#         dsl.save_chart(fig, filename)
#         print(f"Created {filename}")


# if __name__ == "__main__":
#     create_example_charts()
