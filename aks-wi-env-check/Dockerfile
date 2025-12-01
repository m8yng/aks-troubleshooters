FROM golang:1.24-trixie AS gobuild
WORKDIR /src
ARG TARGETARCH
COPY checker.go .
RUN test -f go.mod || go mod init checker && go mod tidy && CGO_ENABLED=0 GOOS=linux GOARCH=${TARGETARCH:-amd64} go build -o checker-go checker.go

FROM rust:slim-trixie AS rustbuild
WORKDIR /src
ARG TARGETARCH
COPY Cargo.toml checker.rs ./
RUN apt update && apt install -y --no-install-recommends pkg-config libssl-dev ca-certificates && update-ca-certificates \
    && case "$TARGETARCH" in \
        amd64) export RUST_TARGET=x86_64-unknown-linux-gnu ;; \
        arm64) export RUST_TARGET=aarch64-unknown-linux-gnu ;; \
        *) echo "unsupported TARGETARCH=$TARGETARCH" && exit 1 ;; \
    esac \
    && rustup target add $RUST_TARGET \
    && CARGO_TARGET_DIR=/tmp/target cargo build --release --bin checker-rs --target $RUST_TARGET \
    && mkdir -p /out && cp /tmp/target/$RUST_TARGET/release/checker-rs /out/checker-rs

FROM debian:trixie-slim
WORKDIR /app
ENV DEBIAN_FRONTEND=noninteractive PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt update && apt install -y --no-install-recommends python3 python3-pip curl jq ca-certificates && update-ca-certificates && python3 -m pip install --no-cache-dir azure-identity azure-mgmt-resource --break-system-packages && apt purge -y python3-pip && apt autoremove -y && rm -rf /var/lib/apt/lists/* /root/.cache /usr/share/doc /usr/share/man /usr/share/info
COPY checker-py /app/
COPY --from=gobuild /src/checker-go /app/
COPY --from=rustbuild /out/checker-rs /app/
RUN chmod +x /app/checker-go /app/checker-py /app/checker-rs
CMD ["/bin/sh","-lc","set -euo pipefail; if [ \"${LANG_EXT:-py}\" = \"go\" ]; then /app/checker-go; elif [ \"${LANG_EXT:-py}\" = \"rs\" ]; then /app/checker-rs; else python3 /app/checker-py; fi"]
