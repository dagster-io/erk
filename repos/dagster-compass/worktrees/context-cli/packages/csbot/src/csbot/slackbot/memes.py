import asyncio
import io
import json
import random
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING, Any

from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from csbot.agents.protocol import AsyncAgent


class BoxCoords(BaseModel):
    x: int
    y: int
    width: int
    height: int


class MemeTemplate(BaseModel):
    filename: str
    description: str
    example_box_name_to_text: dict[str, str]
    box_name_to_coords: dict[str, list[BoxCoords]]


MEME_TEMPLATES = [
    MemeTemplate(
        filename="Batman-Slapping-Robin.jpg",
        description="Batman slapping Robin mid-sentence for saying something wrong. Use when someone needs to be stopped or corrected for a bad take, wrong approach, or misguided statement.",
        example_box_name_to_text={
            "robin": "average revenue per customer is a core metric for our business",
            "batman": "our revenue is skewed by a few large customers, we should use median revenue per customer",
        },
        box_name_to_coords={
            "robin": [BoxCoords(x=10, y=10, width=180, height=80)],
            "batman": [BoxCoords(x=210, y=10, width=180, height=80)],
        },
    ),
    MemeTemplate(
        filename="Disaster-Girl.jpg",
        description="Young girl smiling mischievously in front of a burning house. Use when showing satisfaction or dark humor about a disaster, chaos, or something going terribly wrong.",
        example_box_name_to_text={
            "disaster": "40% of customer records have missing or invalid email addresses",
        },
        box_name_to_coords={
            "disaster": [BoxCoords(x=20, y=0, width=460, height=150)],
        },
    ),
    MemeTemplate(
        filename="Distracted-Boyfriend.jpg",
        description="Man checking out another woman while his girlfriend looks on in disapproval. Use when someone is distracted from what they should be focused on by something more attractive or interesting.",
        example_box_name_to_text={
            "other_girl": "99% drop in support tickets from the EU",
            "boyfriend": "data analyst reviewing the KPIs",
            "girlfriend": "expected 5% m/m growth in DAU",
        },
        box_name_to_coords={
            "other_girl": [BoxCoords(x=50, y=30, width=300, height=180)],
            "boyfriend": [BoxCoords(x=450, y=30, width=300, height=180)],
            "girlfriend": [BoxCoords(x=850, y=30, width=300, height=180)],
        },
    ),
    MemeTemplate(
        filename="Drake-Hotline-Bling.jpg",
        description="Drake disapprovingly turning away from something (top) then pointing approvingly at something else (bottom). Use when rejecting one option in favor of a better alternative.",
        example_box_name_to_text={
            "rejecting": "selling to directors and managers (20% win rate)",
            "accepting": "landing c-level buyers (29% win rate)",
        },
        box_name_to_coords={
            "rejecting": [BoxCoords(x=600, y=50, width=580, height=500)],
            "accepting": [BoxCoords(x=600, y=650, width=580, height=500)],
        },
    ),
    MemeTemplate(
        filename="Epic-Handshake.jpg",
        description="Two muscular arms from different sides clasping hands in agreement. Use when showing two different groups, opposing sides, or rivals finding common ground or shared interest.",
        example_box_name_to_text={
            "left_side": "corporate segment customers",
            "right_side": "enterprise segment customers",
            "handshake": "loving our observability features",
        },
        box_name_to_coords={
            "left_side": [BoxCoords(x=30, y=420, width=280, height=150)],
            "right_side": [BoxCoords(x=590, y=420, width=280, height=150)],
            "handshake": [BoxCoords(x=300, y=80, width=300, height=120)],
        },
    ),
    MemeTemplate(
        filename="Expanding-Brain.jpg",
        description="Brain getting progressively larger and more glowing across four panels. Use when showing escalating levels of intelligence, sophistication, or absurdity in thinking. Can be sincere or ironic.",
        example_box_name_to_text={
            "small_brain": "measuring monthly sales",
            "medium_brain": "segmenting by revenue segment",
            "big_brain": "segmenting by revenue segment and geo",
            "galaxy_brain": "segmenting by use case and revenue segment",
        },
        box_name_to_coords={
            "small_brain": [BoxCoords(x=20, y=922, width=420, height=260)],
            "medium_brain": [BoxCoords(x=20, y=615, width=420, height=260)],
            "big_brain": [BoxCoords(x=20, y=308, width=420, height=260)],
            "galaxy_brain": [BoxCoords(x=20, y=1, width=420, height=260)],
        },
    ),
    MemeTemplate(
        filename="Grus-Plan.jpg",
        description="Gru from Despicable Me presenting his plan on a board, then doing a double-take at the last step. Use when a plan seems good but has an unexpected twist or problem in the final stage.",
        example_box_name_to_text={
            "plan_step_1": "collect all customer data from multiple sources",
            "plan_step_2": "clean and standardize the data formats",
            "plan_step_3": "analyze customer behavior patterns",
            "plan_step_4": "the location field is 100% null",
        },
        box_name_to_coords={
            "plan_step_1": [BoxCoords(x=180, y=10, width=180, height=200)],
            "plan_step_2": [BoxCoords(x=550, y=10, width=150, height=200)],
            "plan_step_3": [BoxCoords(x=180, y=230, width=180, height=200)],
            "plan_step_4": [BoxCoords(x=550, y=230, width=150, height=200)],
        },
    ),
    MemeTemplate(
        filename="Is-This-A-Pigeon.jpg",
        description="Anime character pointing at a butterfly asking 'Is this a pigeon?' Use when someone is hilariously misidentifying something obvious or confusing two completely different things.",
        example_box_name_to_text={
            "person": "marketing team",
            "butterfly": "low ctr ppc campaigns",
            "question": "is this brand awareness",
        },
        box_name_to_coords={
            "person": [BoxCoords(x=100, y=200, width=600, height=100)],
            "butterfly": [BoxCoords(x=1000, y=400, width=500, height=120)],
            "question": [BoxCoords(x=100, y=1250, width=1400, height=150)],
        },
    ),
    MemeTemplate(
        filename="Left-Exit-12-Off-Ramp.jpg",
        description="Car swerving dramatically off highway exit despite having a clear straight path ahead. Use when someone chooses a difficult, illogical option over the obvious simple solution.",
        example_box_name_to_text={
            "straight_path": "continue to sell into segments with high win rates",
            "exit_path": "chase shiny logos that will never buy",
            "car_label": "our gtm strategy",
        },
        box_name_to_coords={
            "straight_path": [BoxCoords(x=50, y=50, width=300, height=200)],
            "exit_path": [BoxCoords(x=450, y=50, width=300, height=200)],
            "car_label": [BoxCoords(x=20, y=650, width=700, height=100)],
        },
    ),
    MemeTemplate(
        filename="Monkey-Puppet.jpg",
        description="Puppet monkey looking away nervously with side-eye. Use when someone is caught off guard, trying to act innocent, or awkwardly pretending not to notice something uncomfortable.",
        example_box_name_to_text={
            "reaction": "demo requests have 100% conversion rate to SAL but 0% closed won",
        },
        box_name_to_coords={
            "reaction": [BoxCoords(x=50, y=30, width=820, height=220)],
        },
    ),
    MemeTemplate(
        filename="One-Does-Not-Simply.jpg",
        description="Boromir from Lord of the Rings declaring 'One does not simply [do X]'. Use when emphasizing that something seemingly simple is actually difficult, dangerous, or impossible.",
        example_box_name_to_text={
            "top_text": "One does not simply",
            "bottom_text": "join dim_users on user_id",
        },
        box_name_to_coords={
            "top_text": [BoxCoords(x=50, y=10, width=470, height=100)],
            "bottom_text": [BoxCoords(x=50, y=220, width=470, height=100)],
        },
    ),
    MemeTemplate(
        filename="Running-Away-Balloon.jpg",
        description="Person (white) reaching for a balloon floating away while being held back by someone else (pink). Use when trying to achieve a goal but constantly distracted or blocked by something else.",
        example_box_name_to_text={
            "balloon": "our success rate goals",
            "person_white": "data engineering",
            "person_pink": "daily_user_snapshot unreliability",
        },
        box_name_to_coords={
            "balloon": [
                BoxCoords(x=400, y=50, width=300, height=200),
                BoxCoords(x=400, y=550, width=300, height=200),
            ],
            "person_white": [
                BoxCoords(x=80, y=400, width=200, height=100),
                BoxCoords(x=280, y=800, width=200, height=100),
            ],
            "person_pink": [BoxCoords(x=20, y=700, width=200, height=100)],
        },
    ),
    MemeTemplate(
        filename="Tuxedo-Winnie-The-Pooh.png",
        description="Winnie the Pooh in casual form (top) vs wearing a fancy tuxedo (bottom). Use when comparing a basic/crude version of something with a sophisticated/refined version of the same thing.",
        example_box_name_to_text={
            "casual_pooh": "linear regression",
            "tuxedo_pooh": "predictive ai model",
        },
        box_name_to_coords={
            "casual_pooh": [BoxCoords(x=345, y=20, width=435, height=260)],
            "tuxedo_pooh": [BoxCoords(x=345, y=300, width=435, height=260)],
        },
    ),
    MemeTemplate(
        filename="Two-Buttons.jpg",
        description="Person sweating nervously while deciding between two buttons. Use when facing a difficult choice between two conflicting options, both with significant consequences or trade-offs.",
        example_box_name_to_text={
            "left_button": "keep doing what west is doing (23% win rate)",
            "right_button": "do what east is doing (31% win rate)",
            "bottom_text": "sales leaders starting at q4 targets",
        },
        box_name_to_coords={
            "left_button": [BoxCoords(x=60, y=60, width=230, height=100)],
            "right_button": [BoxCoords(x=310, y=60, width=230, height=100)],
            "bottom_text": [BoxCoords(x=80, y=700, width=440, height=150)],
        },
    ),
]


def get_meme_template_by_filename(filename: str) -> MemeTemplate | None:
    """Get a meme template by its filename.

    Args:
        filename: The filename of the meme template (e.g., "Batman-Slapping-Robin.jpg")

    Returns:
        The MemeTemplate if found, None otherwise
    """
    for template in MEME_TEMPLATES:
        if template.filename == filename:
            return template
    return None


class MemeSelectionResult(BaseModel):
    """Result of meme selection by AI agent."""

    meme_id: str | None
    meme_box_name_to_text: dict[str, str] | None


async def call_agent_with_pydantic_model[T: BaseModel](
    agent: "AsyncAgent",
    system_prompt: str,
    user_message: str,
    model_class: type[T],
    tool_name: str = "return_result",
    max_tokens: int = 8192,
) -> T:
    """Call an agent with a tool that returns a validated Pydantic model instance.

    Args:
        agent: The async agent to use
        system_prompt: System prompt for the agent
        user_message: User message/prompt
        model_class: Pydantic model class to validate the result against
        tool_name: Name of the tool function (default: "return_result")
        max_tokens: Maximum tokens for the agent response

    Returns:
        Validated instance of the Pydantic model class

    Raises:
        ValueError: If the tool is not called or validation fails
    """
    from csbot.agents.messages import AgentTextMessage

    result: T | None = None

    async def return_result(result_dict: dict[str, Any]) -> dict[str, str]:
        """Return the result validated against the Pydantic model.

        Args:
            result_dict: A dictionary that must conform to the Pydantic model schema:
                {json.dumps(model_class.model_json_schema(), indent=2)}

        Returns:
            A status dictionary indicating success
        """
        nonlocal result
        parsed = model_class.model_validate(result_dict, strict=True)
        if result is not None:
            raise ValueError(f"{tool_name} may only be called once with a valid result")
        result = parsed
        return {"status": "ok"}

    return_result.__doc__ = dedent(f"""
        Return the result of the task.
        
        Args:
            result_dict: A dictionary containing the result. It must adhere to the following
                JSON schema: {json.dumps(model_class.model_json_schema(), indent=2)}
        
        Returns:
            A status dictionary indicating success
    """).strip()

    stream = agent.stream_messages_with_tools(
        model=agent.model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[
            AgentTextMessage(
                role="user",
                content=dedent(f"""
                {user_message}
                
                Return the result as a JSON object by calling the "{tool_name}" tool and
                ensure it conforms to the schema the tool expects. You must call this tool
                exactly once at the end of your analysis.
                """),
            ),
        ],
        tools={tool_name: return_result},
        on_history_added=None,
        on_token_usage=None,
    )

    deltas: list[Any] = []
    stopped = True
    async for event in stream:
        if event.type == "start":
            if not stopped:
                raise ValueError("Content block started after stop")
            deltas = []
            stopped = False
        elif event.type == "delta":
            if stopped:
                raise ValueError("Content block delta after stop")
            deltas.append(event.delta)
        elif event.type == "stop":
            if stopped:
                raise ValueError("Content block stop after stop")
            stopped = True
        else:
            raise ValueError(f"Unknown event type: {event.type}")

    if result is None:
        raise ValueError(f"Tool {tool_name} was not called or did not return a valid result")

    return result


class MemeTextResult(BaseModel):
    """Result containing text for meme boxes."""

    filename_to_meme_box_name_to_text: dict[str, dict[str, str]]


class MemeOption(BaseModel):
    """A meme option with template and text."""

    meme_id: str
    meme_box_name_to_text: dict[str, str]


class MemeRating(BaseModel):
    """Rating for a single meme option."""

    meme_id: str
    rating: int = Field(ge=0, le=10, description="Rating from 0-10 scale")


class MemeRatingsResult(BaseModel):
    """Result of rating all meme options."""

    ratings: list[MemeRating]


async def generate_meme_text(
    agent: "AsyncAgent", templates: list[MemeTemplate], daily_insight_text: str
) -> MemeTextResult:
    """Generate text for multiple meme templates in parallel.

    Args:
        agent: The async agent to use for filling out meme text
        templates: List of meme templates to generate text for
        daily_insight_text: The text of the daily insight message

    Returns:
        List of MemeTextResult, one for each template
    """

    system_prompt = dedent("""
        You are a helpful assistant that fills out meme text boxes for data analysis insights.
        Your goal is to make the insights more engaging and shareable by adding humor that's relevant
        to the content.
    """).strip()

    user_message = dedent(f"""
        Given this daily insight message:

        {daily_insight_text}

        Fill out all the boxes for the meme templates listed below with text that relates
        to this insight. Make it funny, cheeky, and dry, but not mean spirited or offensive.

        Meme templates:
        {
        json.dumps(
            [
                {
                    "filename": template.filename,
                    "description": template.description,
                    "box_name_to_example_text": template.example_box_name_to_text,
                }
                for template in templates
            ],
            indent=2,
        )
    }
    """).strip()

    return await call_agent_with_pydantic_model(
        agent=agent,
        system_prompt=system_prompt,
        user_message=user_message,
        model_class=MemeTextResult,
        tool_name="fill_meme_text",
        max_tokens=8192,
    )


async def select_meme_for_daily_insight(
    agent: "AsyncAgent", daily_insight_text: str
) -> MemeSelectionResult:
    """Use AI agent to fill out text boxes for randomly selected meme templates, then rate and pick the best.

    Args:
        agent: The async agent to use for filling out meme text
        daily_insight_text: The text of the daily insight message

    Returns:
        MemeSelectionResult with meme_id and box_name_to_text, or None if no meme meets quality threshold
    """
    # Randomly select 3 meme templates
    selected_templates = random.sample(MEME_TEMPLATES, min(3, len(MEME_TEMPLATES)))

    # Generate text for all templates in parallel
    meme_text_results = await generate_meme_text(agent, selected_templates, daily_insight_text)

    # Build options for selection
    meme_options: list[MemeOption] = []
    for template, (filename, meme_box_name_to_text) in zip(
        selected_templates, meme_text_results.filename_to_meme_box_name_to_text.items()
    ):
        # Validate box names
        expected_box_names = set(template.box_name_to_coords.keys())
        provided_box_names = set(meme_box_name_to_text.keys())

        if expected_box_names != provided_box_names:
            # Skip invalid options
            continue

        meme_options.append(
            MemeOption(meme_id=template.filename, meme_box_name_to_text=meme_box_name_to_text)
        )

    if not meme_options:
        # No valid options, return null
        return MemeSelectionResult(meme_id=None, meme_box_name_to_text=None)

    # Build options text for rating
    options_json = []
    for i, option in enumerate(meme_options, 1):
        template = get_meme_template_by_filename(option.meme_id)
        if not template:
            continue
        options_json.append(
            {
                "meme_id": option.meme_id,
                "description": template.description,
                "text": option.meme_box_name_to_text,
            }
        )

    # Have AI rate all options
    rating_system_prompt = dedent("""
        You are a helpful assistant that rates meme options on a 10-point scale.
        Rate each meme based on:
        1. How funny and engaging it is (0-10)
        2. Whether it's appropriate and not mean-spirited or offensive (0-10)
        3. How relevant it is to the daily insight (0-10)
        4. How likely it is to be shared and catch attention (0-10)
        
        Combine these factors into a single overall rating from 0-10 for each meme, where:
        - 0-3: Poor quality, not funny, inappropriate, or irrelevant
        - 4-6: Mediocre quality, somewhat funny but not great
        - 7-8: Good quality, funny and appropriate
        - 9-10: Excellent quality, very funny and highly engaging
        
        You must rate ALL memes provided.
    """).strip()

    rating_user_message = dedent(f"""
        Given this daily insight message:

        {daily_insight_text}

        And the following meme template options:

        {json.dumps(options_json, indent=2)}

        Rate each meme on a 10-point scale (0-10) based on how funny, appropriate, relevant, and engaging it is.
    """).strip()

    rating_result = await call_agent_with_pydantic_model(
        agent=agent,
        system_prompt=rating_system_prompt,
        user_message=rating_user_message,
        model_class=MemeRatingsResult,
        tool_name="rate_memes",
        max_tokens=8192,
    )

    # Find the highest rated meme
    if not rating_result.ratings:
        return MemeSelectionResult(meme_id=None, meme_box_name_to_text=None)

    # Create a dict mapping meme_id to rating for easy lookup
    rating_map = {rating.meme_id: rating.rating for rating in rating_result.ratings}

    # Find the highest rated option
    best_option = None
    best_rating = -1
    for option in meme_options:
        rating = rating_map.get(option.meme_id, 0)
        if rating > best_rating:
            best_rating = rating
            best_option = option

    # Only return the meme if it's rated 7 or above
    if best_option and best_rating >= 7:
        return MemeSelectionResult(
            meme_id=best_option.meme_id,
            meme_box_name_to_text=best_option.meme_box_name_to_text,
        )
    else:
        return MemeSelectionResult(meme_id=None, meme_box_name_to_text=None)


def _render_meme(meme_template: MemeTemplate, box_name_to_text: dict[str, str]) -> bytes:
    # Find the template file
    template_dir = Path(__file__).parent / "meme_data"
    template_path = template_dir / meme_template.filename
    if not template_path.exists():
        raise FileNotFoundError(f"Meme template not found: {template_path}")

    # Load the image and use its original dimensions
    with Image.open(template_path) as loaded_img:
        # Convert to RGB if necessary
        if loaded_img.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", loaded_img.size, (255, 255, 255))
            if loaded_img.mode == "P":
                loaded_img = loaded_img.convert("RGBA")
            background.paste(
                loaded_img,
                mask=loaded_img.split()[-1] if loaded_img.mode in ("RGBA", "LA") else None,
            )
            img = background.copy()
        elif loaded_img.mode != "RGB":
            img = loaded_img.convert("RGB").copy()
        else:
            img = loaded_img.copy()

    # Create drawing context
    draw = ImageDraw.Draw(img)

    # Load Impact font from meme_data directory
    font_path = template_dir / "impact.ttf"
    if not font_path.exists():
        raise FileNotFoundError(f"Font file not found: {font_path}")

    # Draw text in each box
    for box_name, text in box_name_to_text.items():
        text = text.upper()
        if box_name not in meme_template.box_name_to_coords:
            continue

        all_coords = meme_template.box_name_to_coords[box_name]
        for coords in all_coords:
            # Use coordinates directly (no scaling needed since we use original dimensions)
            box_x = coords.x
            box_y = coords.y
            box_width = coords.width
            box_height = coords.height

            # Find optimal font size that fits all text within the box
            # Start with a reasonable maximum and decrease until text fits
            max_font_size = max(12, min(80, int(box_height * 0.6)))
            min_font_size = 12
            font_size = max_font_size
            box_font = None
            lines = []

            # Binary search for optimal font size
            while min_font_size <= max_font_size:
                font_size = (min_font_size + max_font_size) // 2

                # Load font with current test size
                try:
                    test_font = ImageFont.truetype(str(font_path), size=font_size)
                except Exception:
                    test_font = ImageFont.load_default()
                    break

                # Wrap text to fit in box width with current font
                words = text.split()
                test_lines = []
                current_line = []
                for word in words:
                    test_line = " ".join([*current_line, word])
                    bbox = draw.textbbox((0, 0), test_line, font=test_font)
                    text_width = bbox[2] - bbox[0]
                    if text_width <= box_width - 20:  # 10px padding on each side
                        current_line.append(word)
                    else:
                        if current_line:
                            test_lines.append(" ".join(current_line))
                        current_line = [word]
                if current_line:
                    test_lines.append(" ".join(current_line))

                # Calculate total height needed for all lines
                line_height = font_size + 5
                total_height = len(test_lines) * line_height

                # Check if text fits within box height (with padding)
                if total_height <= box_height - 20:
                    # Text fits! Try larger font size
                    box_font = test_font
                    lines = test_lines
                    min_font_size = font_size + 1
                else:
                    # Text too big, try smaller font size
                    max_font_size = font_size - 1

            # Fallback if no font was found (shouldn't happen)
            if box_font is None:
                try:
                    box_font = ImageFont.truetype(str(font_path), size=12)
                except Exception:
                    box_font = ImageFont.load_default()
                # Re-wrap with minimum font size
                words = text.split()
                lines = []
                current_line = []
                for word in words:
                    test_line = " ".join([*current_line, word])
                    bbox = draw.textbbox((0, 0), test_line, font=box_font)
                    text_width = bbox[2] - bbox[0]
                    if text_width <= box_width - 20:
                        current_line.append(word)
                    else:
                        if current_line:
                            lines.append(" ".join(current_line))
                        current_line = [word]
                if current_line:
                    lines.append(" ".join(current_line))
                font_size = 12

            # Calculate text position (centered)
            line_height = font_size + 5
            total_text_height = len(lines) * line_height
            start_y = box_y + (box_height - total_text_height) // 2

            # Draw each line with stroke for readability
            for i, line in enumerate(lines):
                text_y = start_y + i * line_height
                # Center horizontally
                bbox = draw.textbbox((0, 0), line, font=box_font)
                text_width = bbox[2] - bbox[0]
                text_x = box_x + (box_width - text_width) // 2

                # Draw stroke (outline) in black
                for adj in [(-2, -2), (-2, 0), (-2, 2), (0, -2), (0, 2), (2, -2), (2, 0), (2, 2)]:
                    draw.text(
                        (text_x + adj[0], text_y + adj[1]),
                        line,
                        font=box_font,
                        fill=(0, 0, 0),
                    )
                # Draw text in white
                draw.text((text_x, text_y), line, font=box_font, fill=(255, 255, 255))

    # Add watermark at the bottom right with transparency
    watermark_text = "created by compass.dagster.io"
    watermark_font_size = max(12, min(24, int(img.height * 0.03)))  # Scale with image size
    try:
        watermark_font = ImageFont.truetype(str(font_path), size=watermark_font_size)
    except Exception:
        watermark_font = ImageFont.load_default()

    # Create a transparent overlay for the watermark
    overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
    overlay_draw = ImageDraw.Draw(overlay)

    # Calculate watermark position (bottom right)
    bbox = overlay_draw.textbbox((0, 0), watermark_text, font=watermark_font)
    watermark_width = bbox[2] - bbox[0]
    watermark_height = bbox[3] - bbox[1]
    watermark_x = img.width - watermark_width - 10  # 10px padding from right
    watermark_y = img.height - watermark_height - 10  # 10px padding from bottom

    # Draw watermark with subtle stroke for readability (semi-transparent black)
    for adj in [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]:
        overlay_draw.text(
            (watermark_x + adj[0], watermark_y + adj[1]),
            watermark_text,
            font=watermark_font,
            fill=(0, 0, 0, 128),  # Semi-transparent black stroke
        )
    # Draw watermark text in semi-transparent white
    overlay_draw.text(
        (watermark_x, watermark_y), watermark_text, font=watermark_font, fill=(255, 255, 255, 179)
    )

    # Composite the overlay onto the original image
    img = img.convert("RGBA")
    img = Image.alpha_composite(img, overlay)
    img = img.convert("RGB")

    # Convert to bytes
    output = io.BytesIO()
    img.save(output, format="PNG")
    return output.getvalue()


async def render_meme(meme_template: MemeTemplate, box_name_to_text: dict[str, str]) -> bytes:
    """Render a meme by overlaying text on a template image.

    Args:
        meme_template: The meme template with box coordinates
        box_name_to_text: Dictionary mapping box names to text to render

    Returns:
        PNG image bytes
    """
    return await asyncio.to_thread(_render_meme, meme_template, box_name_to_text)
