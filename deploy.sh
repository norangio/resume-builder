#!/usr/bin/env bash
# Deploy resume-builder to production using GitHub as the source of truth.
# Usage: ./deploy.sh [branch]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

SERVER="${SERVER:-root@5.78.109.38}"
REMOTE="${REMOTE:-/opt/resume-builder}"
BRANCH="${1:-$(git rev-parse --abbrev-ref HEAD)}"
REPO_URL="${REPO_URL:-$(git config --get remote.origin.url)}"

if [[ ! "$BRANCH" =~ ^[A-Za-z0-9._/-]+$ ]]; then
  echo "Invalid branch name: $BRANCH" >&2
  exit 1
fi

if [[ "${SKIP_PUSH:-0}" != "1" ]]; then
  echo "→ Pushing $BRANCH to GitHub..."
  git push origin "$BRANCH"
fi

echo "→ Pulling latest code on VPS and deploying..."
ssh "$SERVER" "
set -euo pipefail
if [ ! -d \"$REMOTE/.git\" ]; then
  echo \"→ Bootstrapping git repo at $REMOTE\"
  mkdir -p \"$REMOTE\"
  git -C \"$REMOTE\" init
fi
if git -C \"$REMOTE\" remote get-url origin >/dev/null 2>&1; then
  git -C \"$REMOTE\" remote set-url origin \"$REPO_URL\"
else
  git -C \"$REMOTE\" remote add origin \"$REPO_URL\"
fi
git config --global --add safe.directory \"$REMOTE\"
git -C \"$REMOTE\" fetch origin \"$BRANCH\"
if git -C \"$REMOTE\" show-ref --verify --quiet \"refs/heads/$BRANCH\"; then
  git -C \"$REMOTE\" checkout \"$BRANCH\"
else
  git -C \"$REMOTE\" checkout -b \"$BRANCH\" \"origin/$BRANCH\"
fi
git -C \"$REMOTE\" reset --hard \"origin/$BRANCH\"
bash \"$REMOTE/deploy/server-deploy.sh\" \"$BRANCH\"
"

echo "✓ Deployed to https://resume.norangio.dev"
