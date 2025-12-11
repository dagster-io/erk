#!/bin/bash
set -euo pipefail

# Build script for React frontend
# This script is called during Docker build (staging/production)

echo "📦 Building Admin Panel React frontend..."

cd packages/admin-ui
npm install -g corepack

# Install dependencies with frozen lockfile (use existing yarn.lock)
echo "Installing dependencies..."
yarn install --immutable

# Build production bundle
echo "Building production bundle..."
yarn build

echo "✅ Admin Panel build complete!"
