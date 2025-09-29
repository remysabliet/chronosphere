# =============================================================================
# Ultra-Optimized: Copy node_modules from build stage
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Base - Dependencies and workspace setup
# -----------------------------------------------------------------------------
  FROM node:20-alpine AS base

  # Install pnpm globally
  RUN npm install -g pnpm@8.12.0
  
  # Set working directory
  WORKDIR /app
  
  # Copy workspace configuration files
  COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
  COPY tsconfig.json ./
  
  # Copy shared package (dependency)
  COPY packages/shared ./packages/shared
  COPY packages/user-management-service ./packages/user-management-service
  
  # Install ALL dependencies (dev + prod) for building
  RUN pnpm install --frozen-lockfile
  
  # -----------------------------------------------------------------------------
  # Stage 2: Build - Compilation and building
  # -----------------------------------------------------------------------------
  FROM base AS build
  
  # Build shared package first (dependency)
  RUN pnpm --filter @memosphere/shared build
  
  # Build user-management service
  RUN pnpm --filter @memosphere/user-management-service build
  
  # Create production node_modules (remove dev dependencies)
  RUN pnpm install --prod --frozen-lockfile
  
  # -----------------------------------------------------------------------------
  # Stage 3: Production - Copy everything from build
  # -----------------------------------------------------------------------------
  FROM node:20-alpine AS production
  
  # Create non-root user for security
  RUN addgroup -g 1001 -S nodejs && \
      adduser -S usermgmt -u 1001 -G nodejs
  
  # Set working directory
  WORKDIR /app
  
  # Copy everything from build stage (including optimized node_modules)
  COPY --from=build --chown=usermgmt:nodejs /app/package.json ./package.json
  COPY --from=build --chown=usermgmt:nodejs /app/pnpm-lock.yaml ./pnpm-lock.yaml
  COPY --from=build --chown=usermgmt:nodejs /app/pnpm-workspace.yaml ./pnpm-workspace.yaml
  COPY --from=build --chown=usermgmt:nodejs /app/packages/shared ./packages/shared
  COPY --from=build --chown=usermgmt:nodejs /app/packages/user-management-service ./packages/user-management-service
  COPY --from=build --chown=usermgmt:nodejs /app/node_modules ./node_modules
  
  # Switch to non-root user
  USER usermgmt
  
  # Expose port for user-management service
  EXPOSE 3001
  
  # Start the user-management service
  CMD ["pnpm", "--filter", "@memosphere/user-management-service", "start"]