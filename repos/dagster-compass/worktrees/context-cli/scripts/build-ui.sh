#!/bin/bash
set -euo pipefail

# Build script for React frontend
# This script is called during Docker build (staging/production)

echo "📦 Building React frontend..."

cd packages/ui
npm install -g corepack

# Install dependencies with frozen lockfile (use existing yarn.lock)
echo "Installing frontend dependencies..."
yarn install --immutable

# Build production bundle
echo "Building production bundle..."
yarn build

echo "✅ Frontend build complete!"
