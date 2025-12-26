#!/bin/bash
set -e

# Configuration
RDS_HOST="${RDS_HOST}"
RDS_PORT="${RDS_PORT:-5432}"
RDS_REGION="${RDS_REGION}"
DB_USER="${DB_USER}"
USERLIST_FILE="/etc/pgbouncer/userlist.txt"
REFRESH_INTERVAL="${REFRESH_INTERVAL:-600}"  # 10 minutes (tokens last 15 min)

echo "Starting IAM token refresh service..."
echo "RDS Host: $RDS_HOST"
echo "RDS User: $DB_USER"
echo "Region: $RDS_REGION"
echo "Refresh interval: $REFRESH_INTERVAL seconds"

while true; do
    echo "[$(date)] Generating new IAM auth token..."
    
    # Generate IAM auth token
    TOKEN=$(aws rds generate-db-auth-token \
        --hostname "$RDS_HOST" \
        --port "$RDS_PORT" \
        --username "$DB_USER" \
        --region "$RDS_REGION" 2>&1)
    
    if [ $? -eq 0 ]; then
        # Update userlist.txt with new token
        # Format: "username" "password"
        echo "\"$DB_USER\" \"$TOKEN\"" > "$USERLIST_FILE"
        
        # Reload PgBouncer to pick up new password
        # PgBouncer running in same pod should be accessible
        if [ -S /tmp/.s.PGSQL.6432 ]; then
            psql -h /tmp -p 6432 -U pgbouncer pgbouncer -c "RELOAD;" 2>/dev/null || true
        fi
        
        echo "[$(date)] Token updated successfully"
    else
        echo "[$(date)] ERROR: Failed to generate token: $TOKEN"
    fi
    
    sleep "$REFRESH_INTERVAL"
done
