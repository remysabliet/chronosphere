# =============================================================================
# Ultra-Optimized Multi-Stage Dockerfile for quiz-session Service
# Optimized for production with security and performance best practices
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Base - Dependencies and workspace setup
# -----------------------------------------------------------------------------
  FROM node:20-alpine AS base

  # Install pnpm globally with specific version for reproducibility
  RUN npm install -g pnpm@10.17.1
  
  # Set working directory
  WORKDIR /app
  
  # Copy workspace configuration files (for dependency resolution)
  COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
  COPY tsconfig.json ./
  COPY tools/configs ./tools/configs 
  
  # Copy shared package (dependency)
  COPY packages/shared-typescript ./packages/shared-typescript
  
  # Copy quiz session service
  COPY packages/quiz-session-service ./packages/quiz-session-service
  
  # Install ALL dependencies (dev + prod) for building
  RUN pnpm install --frozen-lockfile --ignore-scripts
  
  # -----------------------------------------------------------------------------
  # Stage 2: Build - Compilation and building
  # -----------------------------------------------------------------------------
  FROM base AS build
  
  # Build shared package first (dependency)
  RUN pnpm --filter @memosphere/shared-typescript build
  
  # Build quiz session service
  RUN pnpm --filter @memosphere/quiz-session-service build
  
  # Create production node_modules (remove dev dependencies)
  RUN CI=true pnpm install --prod --frozen-lockfile --ignore-scripts
  
  # -----------------------------------------------------------------------------
  # Stage 3: Production - Copy everything from build
  # -----------------------------------------------------------------------------
  FROM node:20-alpine AS production
  
  # Install pnpm
  RUN corepack enable && corepack prepare pnpm@10.17.1 --activate
  
  # Create non-root user for security
  RUN addgroup -g 1001 -S nodejs && \
      adduser -S quiz-session -u 1001 -G nodejs
  
  # Set working directory
  WORKDIR /app
  
  # Copy everything from build stage (including optimized node_modules)
  COPY --from=build --chown=quiz-session:nodejs /app/package.json ./package.json
  COPY --from=build --chown=quiz-session:nodejs /app/pnpm-lock.yaml ./pnpm-lock.yaml
  COPY --from=build --chown=quiz-session:nodejs /app/pnpm-workspace.yaml ./pnpm-workspace.yaml
  COPY --from=build --chown=quiz-session:nodejs /app/packages/shared-typescript ./packages/shared-typescript
  COPY --from=build --chown=quiz-session:nodejs /app/packages/quiz-session-service ./packages/quiz-session-service
  COPY --from=build --chown=quiz-session:nodejs /app/node_modules ./node_modules
  
  # Switch to non-root user
  USER quiz-session
  
  # Expose port for quiz-session service
  EXPOSE 3003
  
  # Health check
  HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3003/health || exit 1
  
  # Start the quiz-session service
  CMD ["pnpm", "--filter", "@memosphere/quiz-session-service", "start"]