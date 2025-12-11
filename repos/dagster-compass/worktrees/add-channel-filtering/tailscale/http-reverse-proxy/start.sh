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

# Set target service hostname and port for nginx config
TARGET_HOST="${TARGET_SERVICE_HOSTNAME}"
TARGET_PORT="${TARGET_SERVICE_PORT:-8080}"
echo "Target service: $TARGET_HOST:$TARGET_PORT"
nslookup $TARGET_HOST || echo "DNS lookup failed for $TARGET_HOST"

# Replace placeholders in nginx config
sed -i "s/\${TARGET_SERVICE_HOSTNAME}/$TARGET_HOST/g" /etc/nginx/nginx.conf
sed -i "s/\${TARGET_SERVICE_PORT}/$TARGET_PORT/g" /etc/nginx/nginx.conf

# Start nginx proxy
echo "Starting nginx proxy..."
nginx -g "daemon off;" &
NGINX_PID=$!

echo "Setup complete:"
echo "  - Tailscale IP: $tailscale_ip"
echo "  - HTTP reverse proxy on port 80 -> $TARGET_HOST:$TARGET_PORT"

# Cleanup function
cleanup() {
    echo "Shutting down services..."
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
