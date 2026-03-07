#!/usr/bin/env bash
# Run on the VPS to deploy the latest resume-builder code from GitHub.
# Usage: bash /opt/resume-builder/deploy/server-deploy.sh [branch]
set -euo pipefail

APP_DIR="/opt/resume-builder"
SERVICE="resume-builder"
BRANCH="${1:-main}"

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "This script must run as root." >&2
  exit 1
fi

if [[ ! "$BRANCH" =~ ^[A-Za-z0-9._/-]+$ ]]; then
  echo "Invalid branch name: $BRANCH" >&2
  exit 1
fi

echo "→ Deploying resume-builder branch: $BRANCH"
cd "$APP_DIR"

echo "→ Fetching latest code from GitHub..."
git fetch origin "$BRANCH"
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

echo "→ Installing Python dependencies..."
python3 -m venv .venv
.venv/bin/pip install -q -e "."

echo "→ Restarting service..."
systemctl restart "$SERVICE"

echo "✓ VPS deploy complete"
