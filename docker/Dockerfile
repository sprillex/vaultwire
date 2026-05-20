# Dockerfile to build ARM wheels for VaultWire Pi dependencies
FROM python:3.11-bullseye

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    libssl-dev \
    cargo \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy requirements from the Pi directory
COPY pi/requirements.txt .

# We use an entrypoint script to build the wheels and output them
COPY docker/build_wheels.sh /build_wheels.sh
RUN chmod +x /build_wheels.sh

ENTRYPOINT ["/build_wheels.sh"]
