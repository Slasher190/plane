#!/usr/bin/env bash
# Build custom Oneplace CE images from this fork (run from anywhere).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
TAG="${ONEPLACE_IMAGE_TAG:-oneplace-1}"
export DOCKERHUB_USER="${DOCKERHUB_USER:-oneplace}"
export APP_RELEASE="$TAG"

cd "$ROOT"
docker compose -f "$HERE/build.yml" build "$@"

echo "Built images:"
echo "  ${DOCKERHUB_USER}/plane-{frontend,space,admin,backend,proxy,live}:${TAG}"
echo "On UAT: DOCKERHUB_USER=${DOCKERHUB_USER} APP_RELEASE=${TAG} PULL_POLICY=never"
