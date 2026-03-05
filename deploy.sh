#!/bin/bash
# Deploy resume-builder to production.
# Usage: ./deploy.sh
set -e

SERVER="root@5.78.109.38"
REMOTE="/opt/resume-builder"

echo "→ Pushing to GitHub..."
git push

echo "→ Pulling on server and restarting..."
ssh $SERVER "cd $REMOTE && git pull && systemctl restart resume-builder"

echo "✓ Deployed to https://resume.norangio.dev"
