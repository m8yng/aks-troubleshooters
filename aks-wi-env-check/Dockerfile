FROM debian:bookworm-slim
WORKDIR /app
RUN apt update && apt install -y --no-install-recommends curl jq python3 python3-pip golang
COPY checker.* /app/
RUN pip3 install --no-cache-dir azure-identity azure-mgmt-resource --break-system-packages
RUN chmod +x /app/checker.*
CMD ["/bin/bash", "-c", "./checker.${LANG_EXT:-py}"]