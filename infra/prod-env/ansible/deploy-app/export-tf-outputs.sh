#!/usr/bin/env bash
# Export useful Terraform outputs to env vars used by playbook
set -euo pipefail
cd "$(dirname "$0")/../tf"
# read outputs as JSON
OUT=$(terraform output -json)
# Redis (Valkey)
VALKEY_FQDN=$(echo "$OUT" | jq -r '.redis_endpoints.value[0]')
VALKEY_PASSWORD=$(echo "$OUT" | jq -r '.redis_password.value')
# NLB IP
NLB_IP=$(echo "$OUT" | jq -r '.nlb_public_ip.value')
# Export
cat <<EOF
export VALKEY_FQDN=${VALKEY_FQDN}
export VALKEY_PASSWORD=${VALKEY_PASSWORD}
export NLB_IP=${NLB_IP}
EOF
