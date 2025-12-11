#!/bin/bash
set -e

echo "Starting Tailscale daemon..."
# Ensure persistent directory exists and has correct permissions
mkdir -p /var/tailscale
chmod 755 /var/tailscale

# Start tailscaled in background with persistent state directory
tailscaled --tun=userspace-networking --socks5-server=localhost:1055 --statedir=/var/tailscale &
TAILSCALED_PID=$!

echo "Connecting to Tailscale network..."
# Bring up tailscale
until tailscale up --authkey="${TAILSCALE_AUTHKEY}" --hostname="${TAILSCALE_HOSTNAME}" --advertise-tags=tag:compass --force-reauth; do
  echo "Retrying Tailscale connection..."
  sleep 1
done

# Get Tailscale IP
tailscale_ip=$(tailscale ip)
echo "Tailscale is up at IP: ${tailscale_ip}"

# Start nginx
echo "Starting nginx proxy..."
nginx -g "daemon off;" &
NGINX_PID=$!

# Start socat for PostgreSQL TCP proxy
echo "Starting PostgreSQL TCP proxy..."

# Database proxy on port 5432
DB_HOST="${COMPASS_BOT_DB_HOSTNAME:-compass-bot-db}"
echo "Starting DB proxy on port 5432 -> $DB_HOST"
nslookup $DB_HOST || echo "DNS lookup failed for $DB_HOST"
socat -d -d TCP-LISTEN:5432,fork,reuseaddr TCP:$DB_HOST:5432 &
SOCAT_PID=$!

echo "Setup complete:"
echo "  - Tailscale IP: $tailscale_ip"
echo "  - DB proxy on port 5432 -> $DB_HOST"
echo "  - Health check on port 80"

# Cleanup function
cleanup() {
    echo "Shutting down services..."
    kill $SOCAT_PID 2>/dev/null || true
    kill $NGINX_PID 2>/dev/null || true
    kill $TAILSCALED_PID 2>/dev/null || true
    exit 0
}

# Set up signal handlers
trap cleanup EXIT INT TERM

# Handle SIGTERM gracefully for container shutdown
handle_sigterm() {
    echo "Received SIGTERM, initiating graceful shutdown..."
    cleanup
}
trap handle_sigterm TERM

# Wait for processes
wait
