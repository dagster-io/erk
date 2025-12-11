# contains
#   buildah: builds container images without a docker sidecar
#   aws:     for authing into ECR registry, for some reason buildah can't use creds for host

FROM quay.io/buildah/stable:latest

# Install AWS CLI and docker-credential-ecr-login for ECR authentication
RUN ARCH=$(uname -m) && \
    yum install -y unzip && \
    if [ "$ARCH" = "x86_64" ]; then \
        curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"; \
    elif [ "$ARCH" = "aarch64" ]; then \
        curl "https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip" -o "awscliv2.zip"; \
    fi && \
    unzip awscliv2.zip && \
    ./aws/install && \
    rm -rf awscliv2.zip aws && \
    yum clean all
