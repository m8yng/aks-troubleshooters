FROM debian:latest
WORKDIR /app
RUN apt update && apt install -y --no-install-recommends \
    python3 python3-pip curl jq && \
    apt clean && \
    rm -rf /var/lib/apt/lists/*
COPY checker.py /app/
RUN pip3 install azure-identity azure-mgmt-resource --break-system-packages
CMD ["python3", "checker.py"]
