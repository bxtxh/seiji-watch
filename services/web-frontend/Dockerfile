# Multi-stage build for Next.js frontend
# Optimized for layer caching, security, and minimal image size

# ============ Stage 1: Dependencies ============
FROM node:18-alpine AS deps

# Install build dependencies
RUN apk add --no-cache libc6-compat

WORKDIR /app

# Copy package files for better caching
COPY package.json package-lock.json* ./

# Install dependencies with cache mount for faster rebuilds
RUN --mount=type=cache,target=/root/.npm \
    npm ci --only=production && \
    cp -R node_modules prod_node_modules && \
    npm ci

# ============ Stage 2: Builder ============
FROM node:18-alpine AS builder

WORKDIR /app

# Copy dependencies from deps stage
COPY --from=deps /app/node_modules ./node_modules

# Copy source code
COPY . .

# Build arguments for environment variables
ARG NEXT_PUBLIC_API_BASE_URL
ARG NODE_ENV=production

# Set build-time environment variables
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL \
    NODE_ENV=$NODE_ENV \
    NEXT_TELEMETRY_DISABLED=1

# Build the application
RUN npm run build

# ============ Stage 3: Development ============
FROM node:18-alpine AS development

# Install development tools
RUN apk add --no-cache libc6-compat git

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install all dependencies (including dev)
RUN npm install

# Copy source code
COPY . .

# Development environment variables
ENV NODE_ENV=development \
    NEXT_TELEMETRY_DISABLED=1 \
    WATCHPACK_POLLING=true

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD node -e "require('http').get('http://localhost:3000/api/health', (r) => {process.exit(r.statusCode === 200 ? 0 : 1)})"

# Development server with hot reload
CMD ["npm", "run", "dev"]

# ============ Stage 4: Testing ============
FROM node:18-alpine AS test

WORKDIR /app

# Copy dependencies and source
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Install test dependencies
RUN npm install --save-dev \
    @testing-library/react \
    @testing-library/jest-dom \
    jest \
    jest-environment-jsdom \
    @playwright/test

# Run tests
CMD ["npm", "run", "test:ci"]

# ============ Stage 5: Production ============
FROM node:18-alpine AS production

# Build arguments
ARG GIT_COMMIT=unknown
ARG BUILD_DATE=unknown
ARG VERSION=latest

# Labels for metadata
LABEL org.opencontainers.image.title="Web Frontend" \
      org.opencontainers.image.description="Diet Issue Tracker Web Frontend" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${GIT_COMMIT}" \
      org.opencontainers.image.source="https://github.com/your-repo/seiji-watch"

# Install dumb-init for proper signal handling
RUN apk add --no-cache dumb-init

# Create non-root user with specific UID/GID
RUN addgroup -g 1000 -S nodejs && \
    adduser -S nextjs -u 1000 -G nodejs

WORKDIR /app

# Set production environment
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME="0.0.0.0"

# Copy production dependencies
COPY --from=deps --chown=nextjs:nodejs /app/prod_node_modules ./node_modules

# Copy built application from builder
COPY --from=builder --chown=nextjs:nodejs /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Create necessary directories with proper permissions
RUN mkdir -p .next/cache && \
    chown -R nextjs:nodejs .next

# Switch to non-root user
USER nextjs

# Expose port
EXPOSE 3000

# Health check for production
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD node -e "require('http').get('http://localhost:3000/api/health', (r) => {if(r.statusCode !== 200) process.exit(1)})" || exit 1

# Use dumb-init to handle signals properly
ENTRYPOINT ["dumb-init", "--"]

# Production server
CMD ["node", "server.js"]