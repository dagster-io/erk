# contains
#   node
#   prettier
#   aws: used in caching plugin

FROM node:20-slim

# Install make and Prettier globally
RUN apt-get update && apt-get install -y apt-transport-https unzip ca-certificates curl make git && rm -rf /var/lib/apt/lists/*
RUN npm install -g prettier@3.6.2

# Verify installations
RUN node --version && npm --version && prettier --version

# Set working directory
WORKDIR /workspace

# Install AWS CLI
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" \
    && unzip awscliv2.zip \
    && ./aws/install \
    && rm -rf awscliv2.zip aws
