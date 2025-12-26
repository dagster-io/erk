#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if gcloud is installed
check_gcloud() {
    if ! command -v gcloud &> /dev/null; then
        print_error "gcloud CLI is not installed. Please install it first."
        exit 1
    fi
}

# Get current project
get_project() {
    CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null)
    if [ -z "$CURRENT_PROJECT" ]; then
        print_error "No active Google Cloud project found. Please run 'gcloud auth login' and 'gcloud config set project PROJECT_ID'"
        exit 1
    fi
    print_info "Current project: $CURRENT_PROJECT"
}

# Interactive prompts
prompt_service_account_details() {
    echo
    print_info "=== Service Account Configuration ==="
    
    read -p "Enter service account name (e.g., 'bigquery-reader'): " SA_NAME
    if [ -z "$SA_NAME" ]; then
        print_error "Service account name cannot be empty"
        exit 1
    fi
    
    read -p "Enter service account display name (optional): " SA_DISPLAY_NAME
    if [ -z "$SA_DISPLAY_NAME" ]; then
        SA_DISPLAY_NAME="$SA_NAME"
    fi
    
    read -p "Enter service account description (optional): " SA_DESCRIPTION
    if [ -z "$SA_DESCRIPTION" ]; then
        SA_DESCRIPTION="Service account for BigQuery access"
    fi
    
    SA_EMAIL="${SA_NAME}@${CURRENT_PROJECT}.iam.gserviceaccount.com"
    print_info "Service account email will be: $SA_EMAIL"
}

prompt_bigquery_details() {
    echo
    print_info "=== BigQuery Access Configuration ==="
    
    read -p "Enter BigQuery dataset ID: " DATASET_ID
    if [ -z "$DATASET_ID" ]; then
        print_error "Dataset ID cannot be empty"
        exit 1
    fi
    
    echo "Will grant read-only access to $DATASET_ID"

    BIGQUERY_ROLE="roles/bigquery.dataViewer"
    JOB_ROLE="roles/bigquery.jobUser"
    METADATA_ROLE="roles/bigquery.metadataViewer"
    
    echo
    print_info "Choose access level:"
    echo "1. Dataset-level access (all tables in dataset)"
    echo "2. Individual table access"
    
    read -p "Enter choice (1 or 2): " ACCESS_CHOICE
    
    case $ACCESS_CHOICE in
        1)
            GRANT_DATASET=true
            GRANT_TABLES=false
            ;;
        2)
            GRANT_DATASET=false
            GRANT_TABLES=true
            ;;
        *)
            print_error "Invalid choice. Exiting out of an abundance of caution."
            exit 1
            ;;
    esac
    
    # Prompt for individual tables if needed
    if [ "$GRANT_TABLES" = true ]; then
        echo
        print_info "=== Individual Table Configuration ==="
        echo "Enter table names one by one (press Enter when done):"
        
        TABLES=()
        while true; do
            read -p "Enter table name (or press Enter to finish): " TABLE_NAME
            if [ -z "$TABLE_NAME" ]; then
                break
            fi
            TABLES+=("$TABLE_NAME")
        done
        
        if [ ${#TABLES[@]} -eq 0 ]; then
            print_error "No tables specified. Only dataset-level permissions will be granted."
            exit 1
        else
            print_info "Tables to grant access to: ${TABLES[*]}"
        fi
    fi
}

prompt_key_creation() {
    echo
    read -p "Create and download service account key? (y/n): " CREATE_KEY
    if [[ "$CREATE_KEY" =~ ^[Yy]$ ]]; then
        read -p "Enter path for key file (default: ./${SA_NAME}-key.json): " KEY_PATH
        if [ -z "$KEY_PATH" ]; then
            KEY_PATH="./${SA_NAME}-key.json"
        fi
    fi
}

# Main functions
create_service_account() {
    echo
    print_info "Creating service account..."
    
    if gcloud iam service-accounts describe "$SA_EMAIL" &>/dev/null; then
        print_warning "Service account $SA_EMAIL already exists. Skipping creation."
    else
        gcloud iam service-accounts create "$SA_NAME" \
            --display-name="$SA_DISPLAY_NAME" \
            --description="$SA_DESCRIPTION"
        
        print_success "Service account created: $SA_EMAIL"
    fi
}

grant_bigquery_permissions() {
    echo
    print_info "Granting BigQuery permissions..."
    
    # Grant project-level job user permission (required to run queries)
    print_info "Granting project-level job user permissions..."
    gcloud projects add-iam-policy-binding "$CURRENT_PROJECT" \
        --member="serviceAccount:$SA_EMAIL" \
        --role="$JOB_ROLE" \
        --condition='None'
    
    # Grant metadata viewer permission (required for information schema access)
    print_info "Granting metadata viewer permissions for $DATASET_ID"
    
    if gcloud projects add-iam-policy-binding "$CURRENT_PROJECT" \
        --member="serviceAccount:$SA_EMAIL" \
        --role="$METADATA_ROLE" \
        --condition='expression=resource.name.startsWith("projects/'$CURRENT_PROJECT'/datasets/'$DATASET_ID'"),title=BigQuery Metadata Access,description=Metadata access limited to specific dataset' 2>/dev/null; then
        print_success "Metadata viewer permissions granted with dataset-level restriction"
    else
        print_error "Failed to grant restricted metadata permissions"
        exit 1
    fi
    
    
    # Grant dataset-level permissions if requested
    if [ "$GRANT_DATASET" = true ]; then
        print_info "Granting dataset-level permissions..."
        
        # Try different approaches for dataset access
        print_info "Attempting to grant dataset access permissions..."

        print_info "Trying project-level permissions with condition..."
        if gcloud projects add-iam-policy-binding "$CURRENT_PROJECT" \
            --member="serviceAccount:$SA_EMAIL" \
            --role="$BIGQUERY_ROLE" \
            --condition='expression=resource.name.startsWith("projects/'$CURRENT_PROJECT'/datasets/'$DATASET_ID'"),title=BigQuery Dataset Access,description=Access to specific BigQuery dataset' 2>/dev/null; then
            print_success "Dataset-level permissions granted via IAM condition"
        else
            print_error "Conditional IAM binding failed"
            print_info "You may need to grant dataset permissions manually via BigQuery Console"
            exit 1
        fi
    fi
    
    # Grant individual table permissions if requested
    if [ "$GRANT_TABLES" = true ] && [ ${#TABLES[@]} -gt 0 ]; then
        print_info "Granting individual table permissions..."
        
        for table in "${TABLES[@]}"; do
            print_info "Granting access to table: $table"
            
            # Try to grant table-level permissions using bq command
            if command -v bq &> /dev/null; then
                if bq add-iam-policy-binding \
                    --member="serviceAccount:$SA_EMAIL" \
                    --role="$BIGQUERY_ROLE" \
                    "$CURRENT_PROJECT:$DATASET_ID.$table" 2>/dev/null; then
                    print_success "Table-level permissions granted for: $table"
                else
                    print_error "Failed to grant table-level permissions for: $table"
                    print_info "You may need to grant table permissions manually via BigQuery Console"
                    exit 1
                fi
            else
                print_error "bq command not found. Table permissions must be granted manually."
                print_info "Use BigQuery Console to grant access to table: $table"
                exit 1
            fi
        done
    fi
}

create_key_file() {
    if [[ "$CREATE_KEY" =~ ^[Yy]$ ]]; then
        echo
        print_info "Creating service account key..."
        
        gcloud iam service-accounts keys create "$KEY_PATH" \
            --iam-account="$SA_EMAIL"
        
        print_success "Service account key created: $KEY_PATH"
        print_warning "Keep this key file secure and do not commit it to version control!"
    fi
}

show_summary() {
    echo
    print_info "=== Setup Summary ==="
    echo "Service Account: $SA_EMAIL"
    echo "Dataset: $DATASET_ID"
    echo "Permissions: $BIGQUERY_ROLE, $JOB_ROLE, $METADATA_ROLE"
    if [ "$GRANT_TABLES" = true ] && [ ${#TABLES[@]} -gt 0 ]; then
        echo "Metadata Access: Limited to dataset $DATASET_ID"
    else
        echo "Metadata Access: Project-wide"
    fi
    
    if [ "$GRANT_DATASET" = true ]; then
        echo "Dataset Access: Granted"
    fi
    
    if [ "$GRANT_TABLES" = true ] && [ ${#TABLES[@]} -gt 0 ]; then
        echo "Individual Tables: ${TABLES[*]}"
    fi
    
    if [[ "$CREATE_KEY" =~ ^[Yy]$ ]]; then
        echo "Key file: $KEY_PATH"
    fi
    echo
    print_info "=== Usage Examples ==="
    echo "# Authenticate using service account key:"
    echo "export GOOGLE_APPLICATION_CREDENTIALS=\"$KEY_PATH\""
    echo
    echo "# Or use gcloud:"
    echo "gcloud auth activate-service-account --key-file=\"$KEY_PATH\""
    echo
    echo "# Test BigQuery access:"
    if [ "$GRANT_TABLES" = true ] && [ ${#TABLES[@]} -gt 0 ]; then
        echo "bq query --use_legacy_sql=false 'SELECT * FROM \`$CURRENT_PROJECT.$DATASET_ID.${TABLES[0]}\` LIMIT 10'"
        echo
        echo "# Test information schema access (columns metadata):"
        echo "bq query --use_legacy_sql=false 'SELECT column_name, data_type, is_nullable FROM \`$CURRENT_PROJECT.$DATASET_ID.INFORMATION_SCHEMA.COLUMNS\` WHERE table_name = \"${TABLES[0]}\"'"
    else
        echo "bq query --use_legacy_sql=false 'SELECT * FROM \`$CURRENT_PROJECT.$DATASET_ID.your_table\` LIMIT 10'"
        echo
        echo "# Test information schema access (columns metadata):"
        echo "bq query --use_legacy_sql=false 'SELECT column_name, data_type, is_nullable FROM \`$CURRENT_PROJECT.$DATASET_ID.INFORMATION_SCHEMA.COLUMNS\` WHERE table_name = \"your_table\"'"
    fi
    echo
    print_info "=== Manual Permission Setup (if needed) ==="
    
    if [ "$GRANT_DATASET" = true ]; then
        echo "If dataset-level permissions weren't granted automatically:"
        echo
        echo "1. Use the BigQuery Console:"
        echo "   - Go to https://console.cloud.google.com/bigquery"
        echo "   - Select your dataset ($DATASET_ID)"
        echo "   - Click 'Share Dataset'"
        echo "   - Add the service account: $SA_EMAIL"
        echo "   - Grant appropriate role (BigQuery Data Viewer/Editor)"
        echo
        echo "2. Use bq command manually:"
        echo "   bq add-iam-policy-binding \\"
        echo "     --member='serviceAccount:$SA_EMAIL' \\"
        echo "     --role='$BIGQUERY_ROLE' \\"
        echo "     '$CURRENT_PROJECT:$DATASET_ID'"
        echo
        echo "3. Grant metadata access manually:"
        echo "   # For project-wide access:"
        echo "   gcloud projects add-iam-policy-binding $CURRENT_PROJECT \\"
        echo "     --member='serviceAccount:$SA_EMAIL' \\"
        echo "     --role='$METADATA_ROLE'"
        echo
    fi
    
    if [ "$GRANT_TABLES" = true ] && [ ${#TABLES[@]} -gt 0 ]; then
        echo "For individual table permissions:"
        echo
        echo "1. Use BigQuery Console:"
        echo "   - Go to https://console.cloud.google.com/bigquery"
        echo "   - Navigate to each table: $DATASET_ID.[table_name]"
        echo "   - Click 'Share' on each table"
        echo "   - Add the service account: $SA_EMAIL"
        echo "   - Grant appropriate role (BigQuery Data Viewer/Editor)"
        echo
        echo "2. Use bq command for each table:"
        for table in "${TABLES[@]}"; do
            echo "   bq add-iam-policy-binding \\"
            echo "     --member='serviceAccount:$SA_EMAIL' \\"
            echo "     --role='$BIGQUERY_ROLE' \\"
            echo "     '$CURRENT_PROJECT:$DATASET_ID.$table'"
        done
        echo
        echo "3. Grant metadata access manually:"
        echo "   # For restricted access (dataset-level):"
        echo "   gcloud projects add-iam-policy-binding $CURRENT_PROJECT \\"
        echo "     --member='serviceAccount:$SA_EMAIL' \\"
        echo "     --role='$METADATA_ROLE' \\"
        echo "     --condition='expression=resource.name.startsWith(\"projects/$CURRENT_PROJECT/datasets/$DATASET_ID\"),title=BigQuery Metadata Access,description=Metadata access limited to specific dataset'"
        echo
    fi
    
    echo "3. Contact your organization admin to enable dataset-level IAM if needed"
}

# Main execution
main() {
    print_info "BigQuery Service Account Setup Script"
    print_info "======================================"
    
    check_gcloud
    get_project
    prompt_service_account_details
    prompt_bigquery_details
    prompt_key_creation
    
    echo
    print_info "=== Configuration Summary ==="
    echo "Project: $CURRENT_PROJECT"
    echo "Service Account: $SA_EMAIL"
    echo "Dataset: $DATASET_ID"
    echo "Access Level: $BIGQUERY_ROLE, $METADATA_ROLE"
    
    if [ "$GRANT_DATASET" = true ]; then
        echo "Dataset Access: Yes"
    fi
    
    if [ "$GRANT_TABLES" = true ] && [ ${#TABLES[@]} -gt 0 ]; then
        echo "Individual Tables: ${TABLES[*]}"
    fi
    
    if [[ "$CREATE_KEY" =~ ^[Yy]$ ]]; then
        echo "Key File: $KEY_PATH"
    fi
    echo
    
    read -p "Proceed with setup? (y/n): " CONFIRM
    if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
        print_info "Setup cancelled."
        exit 0
    fi
    
    create_service_account
    grant_bigquery_permissions
    create_key_file
    show_summary
    
    print_success "Setup completed successfully!"
}

# Run main function
main "$@"