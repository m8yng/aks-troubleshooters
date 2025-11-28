FROM golang:1.24-trixie AS gobuild
WORKDIR /src
ARG TARGETARCH
COPY checker.go .
RUN test -f go.mod || go mod init checker && go mod tidy && CGO_ENABLED=0 GOOS=linux GOARCH=${TARGETARCH:-amd64} go build -o checker-go checker.go

FROM debian:trixie-slim
WORKDIR /app
ENV DEBIAN_FRONTEND=noninteractive PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-pip curl jq ca-certificates && update-ca-certificates && python3 -m pip install --no-cache-dir azure-identity azure-mgmt-resource --break-system-packages && apt-get purge -y python3-pip && apt-get autoremove -y && rm -rf /var/lib/apt/lists/* /root/.cache /usr/share/doc /usr/share/man /usr/share/info
COPY checker-py /app/
COPY --from=gobuild /src/checker-go /app/
RUN chmod +x /app/checker-go /app/checker-py
CMD ["/bin/sh","-lc","set -euo pipefail; if [ \"${LANG_EXT:-py}\" = \"go\" ]; then /app/checker-go; else python3 /app/checker-py; fi"]
