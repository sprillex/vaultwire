#!/usr/bin/env bash
# Script to run inside docker to build wheels, or to trigger the docker build

if [ "$1" == "--inside-docker" ]; then
    # We are inside the container
    echo "Building wheels for ARM..."
    mkdir -p /out
    pip wheel -r requirements.txt -w /out
    echo "Wheels built successfully in /out"
else
    # We are on the host, setting up docker build
    echo "Building ARM wheels using Docker buildx..."

    # Ensure multiarch is supported
    docker run --rm --privileged multiarch/qemu-user-static --reset -p yes

    # Ensure dist directory exists
    mkdir -p dist

    # Build the image for arm64 and extract the wheels (loading single platform to local daemon)
    docker buildx build --platform linux/arm64 -t vaultwire-builder:latest -f Dockerfile .. --load

    # Run the container to generate wheels and copy them out
    docker run --rm -v $(pwd)/dist:/out vaultwire-builder:latest --inside-docker

    echo "Wheels have been exported to docker/dist/"
fi