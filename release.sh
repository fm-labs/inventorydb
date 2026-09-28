#!/bin/bash

set -e

#PYPI_PUBLISH_TOKEN=${PYPI_PUBLISH_TOKEN:?Not set. Please set the PYPI_PUBLISH_TOKEN environment variable to a valid PyPI token.}
#TESTPYPI_PUBLISH_TOKEN=${TESTPYPI_PUBLISH_TOKEN:?Not set. Please set the TESTPYPI_PUBLISH_TOKEN environment variable to a valid TestPyPI token.}

# Build
uv build --no-sources

# Publish to TestPyPI
if [[ -n "${TESTPYPI_PUBLISH_TOKEN}" ]]; then
  echo "[INFO] Publishing to TestPyPI ..."
  #export UV_PUBLISH_TOKEN=${TESTPYPI_PUBLISH_TOKEN}
  uv publish --index testpypi --token ${TESTPYPI_PUBLISH_TOKEN}
else
  echo "[WARN] TESTPYPI_PUBLISH_TOKEN is not set. Skipping TestPyPI publish step."
fi

# Publish to PyPI
if [[ -n "${PYPI_PUBLISH_TOKEN}" ]]; then
  echo "[INFO] Publishing to PyPI ..."
  #export UV_PUBLISH_TOKEN=${PYPI_PUBLISH_TOKEN}
  uv publish --index pypi --token ${PYPI_PUBLISH_TOKEN}
else
  echo "[WARN] PYPI_PUBLISH_TOKEN is not set. Skipping PyPI publish step."
fi
