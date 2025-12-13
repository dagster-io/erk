# contains
#   dhall: for generating pipeline.yaml, this is the first step in the buildkite pipeline

FROM alpine:3.22.2

WORKDIR /app

# Install glibc compatibility and required libraries for dhall binary
RUN apk add --no-cache wget tar gzip libc6-compat ncurses-libs gmp git && \
    ln -s /usr/lib/libncursesw.so.6 /usr/lib/libtinfo.so.6 && \
    wget https://github.com/dhall-lang/dhall-haskell/releases/download/1.42.2/dhall-json-1.7.12-x86_64-linux.tar.bz2 && \
    tar -xjf dhall-json-1.7.12-x86_64-linux.tar.bz2 && \
    mv bin/* /usr/local/bin/ && \
    rm dhall-json-1.7.12-x86_64-linux.tar.bz2
