#!/usr/bin/env bash
set -euo pipefail
export ARBM_HOST_ID="${ARBM_HOST_ID:-gcp-free-persistent}"
export ARBM_CLOUD_VENDOR=gcp
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/../common/bootstrap-persistent-host.sh"
