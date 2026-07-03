# =============================================================================
# Stage 1: Base - Dependencies and workspace setup
# =============================================================================
FROM node:20-alpine AS base

RUN npm install -g pnpm@10.17.1

WORKDIR /app

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY tsconfig.json ./
COPY tools/configs ./tools/configs

COPY packages/shared ./packages/shared
COPY apps/web-app ./apps/web-app

RUN pnpm install --frozen-lockfile --ignore-scripts

# =============================================================================
# Stage 2: Build
# =============================================================================
FROM base AS build

RUN pnpm --filter @memosphere/shared build
RUN pnpm --filter @memosphere/web-app build

# =============================================================================
# Stage 3: Production
# =============================================================================
FROM node:20-alpine AS production

RUN corepack enable && corepack prepare pnpm@10.17.1 --activate

RUN addgroup -g 1001 -S nodejs && \
    adduser -S webapp -u 1001 -G nodejs

WORKDIR /app

COPY --from=build --chown=webapp:nodejs /app/package.json ./package.json
COPY --from=build --chown=webapp:nodejs /app/pnpm-lock.yaml ./pnpm-lock.yaml
COPY --from=build --chown=webapp:nodejs /app/pnpm-workspace.yaml ./pnpm-workspace.yaml
COPY --from=build --chown=webapp:nodejs /app/packages/shared ./packages/shared
COPY --from=build --chown=webapp:nodejs /app/apps/web-app ./apps/web-app
COPY --from=build --chown=webapp:nodejs /app/node_modules ./node_modules

USER webapp

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000 || exit 1

CMD ["pnpm", "--filter", "@memosphere/web-app", "start"]
