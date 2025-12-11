# contains
#   python
#   uv
#   node: for pyright
#   temporal: used in integration tests
#   aws: used in caching plugin

FROM public.ecr.aws/docker/library/python:3.13-slim

LABEL maintainer="Dagster Labs"

WORKDIR /app

# Never prompts the user for choices on installation/configuration of packages (NOTE:
# DEBIAN_FRONTEND does not affect the apt-get command)
ENV DEBIAN_FRONTEND=noninteractive \
    TERM=linux

# Set correct locale first and install deps for installing debian packages
RUN apt-get update -yqq \
    && apt-get upgrade -yqq \
    && apt-get install -yqq --no-install-recommends \
    apt-transport-https \
    curl \
    wget \
    ca-certificates \
    gnupg2 \
    locales \
    lsb-release \
    make \
    git \
    unzip \
    # Set locale
    && sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen \
    && dpkg-reconfigure --frontend=noninteractive locales \
    && update-locale LANG=en_US.UTF-8

# Envionment variables that will be referenced during installation of various packages
ENV LANG=en_US.UTF-8 \
    LANGUAGE=en_US.UTF-8 \
    LC_ALL=en_US.UTF-8 \
    DOCKER_COMPOSE_VERSION=1.29.1 \
    KIND_VERSION=v0.14.0 \
    KUBECTL_VERSION=v1.20.1 \
    FOSSA_VERSION=1.1.10 \
    HELM_VERSION=v3.18.2

RUN pip install uv

# Install Node.js for pyright and yarn for UI builds
RUN curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g npm@latest \
    && npm install -g yarn

# Install Temporal CLI
RUN wget -O temporal.tar.gz "https://temporal.download/cli/archive/latest?platform=linux&arch=amd64" \
    && tar -xzf temporal.tar.gz \
    && ln -s /app/temporal /usr/local/bin/temporal \
    && rm temporal.tar.gz

# Install AWS CLI
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" \
    && unzip awscliv2.zip \
    && ./aws/install \
    && rm -rf awscliv2.zip aws
