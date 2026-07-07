#!/usr/bin/env bash
# Frees disk space on Docker Desktop's VM by clearing build cache and unused
# images. Never touches volumes, so the Postgres/Redis dev data is untouched.
set -e

echo "Before:"
docker system df

echo
echo "🧹 Clearing build cache..."
docker builder prune -af

echo
echo "🧹 Clearing unused images..."
docker image prune -af

echo
echo "After:"
docker system df
