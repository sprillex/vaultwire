#!/usr/bin/env bash
# Script to run inside docker to build wheels and download debs, or to trigger the docker build

if [ "$1" == "--inside-docker" ]; then
    # We are inside the container
    echo "Building wheels for ARM..."
    mkdir -p /out/wheels
    mkdir -p /out/debs

    # Build wheels
    pip wheel -r requirements.txt -w /out/wheels
    echo "Wheels built successfully in /out/wheels"

    echo "Downloading deb packages for offline installation..."
    # Update apt so we can download
    apt-get update

    # List of packages needed on the Pi
    # DietPi is debian based, python 3.11 is target (bookworm or bullseye depending on dietpi version)
    # DietPi usually comes with a base, but we ensure python3-venv and dependencies are grabbed.
    # Note: dietpi for zero 2 is typically arm64 bullseye or bookworm. We assume bullseye to match container base.
    PACKAGES="python3-venv python3-dev build-essential libffi-dev libssl-dev"

    cd /out/debs

    # Download the packages and their dependencies
    for pkg in $PACKAGES; do
        apt-get download $(apt-rdepends --state-follow=Installed,NotInstalled $pkg | grep -v "^ " | grep -v "^$") 2>/dev/null || true
    done

    # Download packages directly to ensure we get at least the top level ones
    apt-get download $PACKAGES 2>/dev/null || true

    echo "Deb packages downloaded to /out/debs"
else
    # We are on the host, setting up docker build
    echo "Building ARM wheels and downloading debs using Docker buildx..."

    # Ensure multiarch is supported
    docker run --rm --privileged multiarch/qemu-user-static --reset -p yes || true

    # Ensure dist directory exists
    mkdir -p dist/wheels dist/debs

    # Build the image for arm64 and extract the wheels (loading single platform to local daemon)
    docker buildx build --platform linux/arm64 -t vaultwire-builder:latest -f Dockerfile .. --load

    # Run the container to generate wheels/debs and copy them out
    docker run --rm -v $(pwd)/dist:/out vaultwire-builder:latest --inside-docker

    echo "Outputs have been exported to docker/dist/"
fi
