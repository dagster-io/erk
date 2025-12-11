"""BigQuery service account provisioning command."""

import subprocess
import sys

import click


def run_bq_provision_script():
    """Run the BigQuery provisioning bash script."""
    script_path = "scripts/bq-provision.sh"
    try:
        # Run the bash script directly
        result = subprocess.run(["/bin/bash", script_path], check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        click.echo(f"Error: BigQuery provisioning failed with exit code {e.returncode}", err=True)
        return False
    except FileNotFoundError:
        click.echo(
            f"Error: Script not found at {script_path}. "
            "Make sure you're running from the project root.",
            err=True,
        )
        return False


@click.command()
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be done without executing (not implemented in underlying script)",
)
def bq_provision(dry_run: bool):
    """Provision BigQuery service account with interactive setup.

    This command provides an interactive wizard to:
    - Create Google Cloud service accounts
    - Configure BigQuery permissions (dataset or table level)
    - Set up metadata viewer access for information schema
    - Generate and download service account keys
    - Provide usage examples and manual setup instructions

    Prerequisites:
    - gcloud CLI installed and authenticated
    - Active Google Cloud project configured
    - Appropriate IAM permissions to create service accounts

    The script will guide you through:
    1. Service account configuration (name, description)
    2. BigQuery access level selection (dataset vs individual tables)
    3. Permission setup with conditional IAM bindings
    4. Key file generation (optional)
    5. Usage examples and troubleshooting steps
    """
    if dry_run:
        click.echo(
            "Dry run mode would show the following steps:\n"
            "1. Verify gcloud CLI is installed and authenticated\n"
            "2. Get current Google Cloud project\n"
            "3. Prompt for service account details\n"
            "4. Prompt for BigQuery dataset and access level\n"
            "5. Create service account with specified configuration\n"
            "6. Grant BigQuery permissions (jobUser, metadataViewer, dataViewer)\n"
            "7. Optionally create and download service account key\n"
            "8. Display usage examples and manual setup instructions"
        )
        return

    click.echo("🚀 Starting BigQuery service account provisioning...")
    success = run_bq_provision_script()

    if success:
        click.echo("✅ BigQuery provisioning completed successfully!")
    else:
        click.echo("❌ BigQuery provisioning failed. Check the output above for details.")
        sys.exit(1)
