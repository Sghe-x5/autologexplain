#!/usr/bin/env bash
# Wrapper to use the YC dynamic inventory script
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/yc_inventory.sh"
