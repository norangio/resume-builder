#!/usr/bin/env bash
# Deploy resume-builder to production using GitHub as the source of truth.
# Usage: ./deploy.sh [branch]
set -euo pipefail

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
  if git -C \"$REMOTE\" remote get-url origin >/dev/null 2>&1; then
    git -C \"$REMOTE\" remote set-url origin \"$REPO_URL\"
  else
    git -C \"$REMOTE\" remote add origin \"$REPO_URL\"
  fi
fi
git -C \"$REMOTE\" fetch origin \"$BRANCH\"
git -C \"$REMOTE\" checkout -f \"$BRANCH\"
bash \"$REMOTE/deploy/server-deploy.sh\" \"$BRANCH\"
"

echo "✓ Deployed to https://resume.norangio.dev"
