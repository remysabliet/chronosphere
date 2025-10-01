# Database migration service Dockerfile - Local Development Optimized
FROM node:20-alpine

# Enable pnpm using built-in Corepack (faster than npm install -g)
RUN corepack enable && corepack prepare pnpm@latest --activate

# Set working directory to workspace root
WORKDIR /app

# Copy workspace configuration for better layer caching
COPY pnpm-workspace.yaml ./
COPY pnpm-lock.yaml ./
COPY package.json ./

# Copy migration-service package.json
COPY packages/migration-service/package.json ./packages/migration-service/

# Install dependencies (no frozen-lockfile for dev flexibility)
# Use --filter to only install migration-service dependencies
RUN pnpm install --filter @memosphere/migration-service

# Copy migration service files
COPY packages/migration-service/ ./packages/migration-service/

# Set working directory to migration service
WORKDIR /app/packages/migration-service

# Default command - run migrations
CMD ["pnpm", "run", "migrate:latest"]