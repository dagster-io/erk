"""Mock data generation command for Hooli Corporation CRM datasets."""

from pathlib import Path

import click

from csbot.compass_dev.generate_mock_data_logic import generate_mock_data_files


@click.command()
@click.option(
    "--output-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Output directory for CSV files (defaults to data/ in project root)",
)
@click.option(
    "--preview",
    is_flag=True,
    help="Show statistics about what data would be generated without creating files",
)
def generate_mock_data(output_dir: Path | None, preview: bool):
    """Generate realistic CRM mock data for Hooli Corporation.

    Creates comprehensive datasets including:

    **Accounts Dataset:**
    - Account information (name, industry, revenue, employees)
    - Geographic distribution (US regions + international)
    - Revenue segmentation (SMB, midmarket, enterprise)

    **Opportunities Dataset:**
    - Sales opportunities (new business, renewals, upsells)
    - Opportunity stages and pipeline progression
    - Account executives and customer success managers
    - Realistic win rates and deal amounts

    **Sales Call Notes:**
    - Detailed call notes for each opportunity
    - Stage-appropriate conversation content
    - Customer seniority levels and pain points
    - Competitive analysis and objection handling

    **Support Tickets:**
    - Customer support requests and resolutions
    - Realistic technical issues and descriptions
    - Response times and resolution tracking
    - Associated opportunity context

    **Web Traffic Analytics:**
    - Website visit patterns by account
    - Device types and traffic sources
    - Engagement levels and session data
    - Customer vs prospect behavior patterns

    The generated data follows realistic business patterns:
    - Account executives manage accounts by segment
    - Win rates vary by representative and segment
    - Support ticket volume correlates with deal size
    - Web traffic reflects customer lifecycle stage

    Output files (CSV format):
    - accounts.csv (~7,000 accounts)
    - opportunities.csv (~2,000+ opportunities)
    - sales_call_notes.csv (~8,000+ call records)
    - support_tickets.csv (~5,000+ tickets)
    - web_traffic.csv (~50,000+ visits)

    All data uses a fixed random seed (42) for reproducible generation.
    """
    if preview:
        click.echo(
            "Mock data generation preview:\n\n"
            "📊 Dataset Statistics:\n"
            "- ~7,000 accounts across SMB, midmarket, and enterprise segments\n"
            "- ~2,000+ opportunities (new business, renewals, upsells)\n"
            "- ~8,000+ sales call notes with realistic conversation content\n"
            "- ~5,000+ support tickets with technical issues and resolutions\n"
            "- ~50,000+ web traffic records with engagement analytics\n\n"
            "🏢 Account Distribution:\n"
            "- Industries: Technology (50%), Financial Services (30%), Healthcare, "
            "Manufacturing, etc.\n"
            "- Regions: West US (50%), East US (30%), International (20%)\n"
            "- Revenue segments: SMB (1x), Midmarket (4x), Enterprise (3x weight)\n\n"
            "💼 Sales Team Structure:\n"
            "- SMB AEs: Jake Morgan, Samantha Lee\n"
            "- Midmarket AEs: Carlos Rivera, Tina Patel  \n"
            "- Enterprise AEs: Brian Chen, Donna Moriarty\n"
            "- CSMs: Sarah Brown, David Lee\n"
            "- Support Engineers: Emily Zhang, Nate Brooks, Priya Desai\n\n"
            "📈 Business Logic:\n"
            "- Realistic win rates by representative (20-30% for new business)\n"
            "- Higher win rates for renewals/upsells (70-80%)\n"
            "- Deal sizes scale with company segment\n"
            "- Support tickets increase with successful deals\n"
            "- Web traffic patterns differ for customers vs prospects"
        )
        return

    # Ensure data directory exists
    if output_dir is None:
        output_dir = Path("data")

    click.echo("🚀 Starting mock data generation...")
    click.echo(f"📁 Output directory: {output_dir.absolute()}")

    try:
        file_stats = generate_mock_data_files(output_dir)

        click.echo("✅ Mock data generation completed successfully!")
        click.echo(f"\n📂 Generated files in {output_dir.absolute()}:")

        for filename, record_count in file_stats.items():
            click.echo(f"  - {filename}: {record_count:,} records")

    except Exception as e:
        click.echo(f"❌ Mock data generation failed: {e}", err=True)
        raise click.ClickException(f"Mock data generation failed: {e}")
