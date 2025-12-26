FROM ubuntu:22.04

# Install required packages
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    nginx \
    dnsutils \
    && rm -rf /var/lib/apt/lists/*

# Download and install Tailscale
RUN curl -fsSL https://tailscale.com/install.sh | sh

ADD start.sh /usr/local/bin/start.sh
ADD nginx.conf /etc/nginx/nginx.conf

# Remove default nginx configuration
RUN rm -f /etc/nginx/sites-enabled/default

# Make the script executable
RUN chmod +x /usr/local/bin/start.sh

# Create mount point for persistent disk (Tailscale state)
RUN mkdir -p /var/tailscale

# Expose port 80 for HTTP proxy
EXPOSE 80

# Set environment variables that can be overridden
ENV RENDER_SERVICE_NAME=tailscale-http-proxy


# Start the services
CMD ["/usr/local/bin/start.sh"]
