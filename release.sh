#!/bin/bash
#
# Build, test and publish objbase.
#
# Publishes to TestPyPI if TESTPYPI_PUBLISH_TOKEN is set, then to PyPI if
# PYPI_PUBLISH_TOKEN is set. Set ALLOW_DIRTY=1 to release from a working tree
# with uncommitted changes.

set -euo pipefail

cd "$(dirname "$0")"

# Refuse to publish code that is not committed
if [[ -z "${ALLOW_DIRTY:-}" && -n "$(git status --porcelain)" ]]; then
  echo "[ERROR] Working tree has uncommitted changes. Commit them or set ALLOW_DIRTY=1." >&2
  exit 1
fi

VERSION=$(uv version --short)
echo "[INFO] Releasing objbase ${VERSION}"

# Test
echo "[INFO] Running tests ..."
uv run pytest -q

# Build into a clean dist/ so stale artifacts from earlier builds are never published
rm -rf dist
uv build --no-sources

# Publish to TestPyPI
if [[ -n "${TESTPYPI_PUBLISH_TOKEN:-}" ]]; then
  echo "[INFO] Publishing to TestPyPI ..."
  uv publish --index testpypi --token "${TESTPYPI_PUBLISH_TOKEN}"
else
  echo "[WARN] TESTPYPI_PUBLISH_TOKEN is not set. Skipping TestPyPI publish step."
fi

# Publish to PyPI
if [[ -n "${PYPI_PUBLISH_TOKEN:-}" ]]; then
  echo "[INFO] Publishing to PyPI ..."
  uv publish --token "${PYPI_PUBLISH_TOKEN}"
else
  echo "[WARN] PYPI_PUBLISH_TOKEN is not set. Skipping PyPI publish step."
fi
