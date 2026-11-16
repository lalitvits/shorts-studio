#!/bin/sh
# Starts Shorts Studio as the codespace user, with the codespace's secrets (such as GEMINI_API_KEY) loaded.
cd "$1" || exit 1
SECRETS=/workspaces/.codespaces/shared/.env-secrets
if [ -f "$SECRETS" ]; then
  while IFS='=' read -r k v; do
    [ -n "$k" ] && export "$k=$(printf %s "$v" | base64 -d 2>/dev/null)"
  done < "$SECRETS"
fi
exec python -u run.py --no-browser
