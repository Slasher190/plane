#!/usr/bin/env bash
# Build custom Oneplace CE images for linux/amd64 (UAT).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
TAG="${ONEPLACE_IMAGE_TAG:-oneplace-1}"
export DOCKERHUB_USER="${DOCKERHUB_USER:-oneplace}"
export APP_RELEASE="$TAG"
export DOCKER_DEFAULT_PLATFORM="${DOCKER_DEFAULT_PLATFORM:-linux/amd64}"

cd "$ROOT"
docker buildx inspect oneplace-builder >/dev/null 2>&1 \
  || docker buildx create --name oneplace-builder --driver docker-container --use
docker buildx use oneplace-builder >/dev/null 2>&1 || true

echo "Building ${DOCKERHUB_USER}/plane-*:${TAG} for linux/amd64 ..."
docker compose -f "$HERE/build.yml" build --platform linux/amd64 "$@"

echo "Built images (expect amd64):"
for img in frontend space admin backend proxy live; do
  docker image inspect "${DOCKERHUB_USER}/plane-${img}:${TAG}" \
    --format "${img}: arch={{.Architecture}} os={{.Os}}" 2>/dev/null || echo "${img}: missing"
done
echo "On UAT: DOCKERHUB_USER=${DOCKERHUB_USER} APP_RELEASE=${TAG} PULL_POLICY=never"
