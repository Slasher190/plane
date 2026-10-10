#!/usr/bin/env bash
# Build custom Oneplace CE images for linux/amd64 (UAT).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
TAG="${ONEPLACE_IMAGE_TAG:-oneplace-1}"
export DOCKERHUB_USER="${DOCKERHUB_USER:-oneplace}"
export APP_RELEASE="$TAG"
# Force amd64 even on Apple Silicon so images run on UAT.
export DOCKER_DEFAULT_PLATFORM="${DOCKER_DEFAULT_PLATFORM:-linux/amd64}"

cd "$ROOT"
echo "Building ${DOCKERHUB_USER}/plane-*:${TAG} for ${DOCKER_DEFAULT_PLATFORM} ..."
docker compose -f "$HERE/build.yml" build "$@"

echo "Built images (expect amd64):"
for img in frontend space admin backend proxy live; do
  docker image inspect "${DOCKERHUB_USER}/plane-${img}:${TAG}" \
    --format "${img}: arch={{.Architecture}} os={{.Os}}" 2>/dev/null || echo "${img}: missing"
done
echo "On UAT: DOCKERHUB_USER=${DOCKERHUB_USER} APP_RELEASE=${TAG} PULL_POLICY=never"
