FROM ubuntu:22.04

# Install required packages
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    nginx \
    dnsutils \
    socat \
    && rm -rf /var/lib/apt/lists/*

# Download and install Tailscale
RUN curl -fsSL https://tailscale.com/install.sh | sh

ADD start.sh /usr/local/bin/start.sh
ADD nginx.conf /etc/nginx/nginx.conf

# Make the script executable
RUN chmod +x /usr/local/bin/start.sh

# Create mount point for persistent disk (Tailscale state)
RUN mkdir -p /var/tailscale

# Expose ports for nginx and PostgreSQL proxy
EXPOSE 80 5432

# Set environment variables that can be overridden
ENV RENDER_SERVICE_NAME=tailscale-proxy

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:80 || exit 1

# Start the services
CMD ["/usr/local/bin/start.sh"]
