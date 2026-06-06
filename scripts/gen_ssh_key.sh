#!/usr/bin/env bash
set -euo pipefail

KEY_NAME="${1:-id_ed25519}"
COMMENT="${2:-generated-key}"

ssh-keygen -t ed25519 -C "$COMMENT" -f "$KEY_NAME" -N ""

echo ""
echo "Private key : $KEY_NAME"
echo "Public key  : $KEY_NAME.pub"
echo "Fingerprint : $(ssh-keygen -lf "$KEY_NAME.pub")"
