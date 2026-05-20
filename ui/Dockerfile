# === BUILD STAGE ===
FROM node:20-alpine AS builder

WORKDIR /build

# Step 1: Install dependencies (cached independently)
COPY package.json package-lock.json ./
RUN npm ci --prefer-offline --no-audit

# Step 2: Copy source and build (only invalidates on source change)
COPY src ./src
COPY tsconfig.json tsconfig.node.json vite.config.ts tailwind.config.ts postcss.config.js index.html ./
RUN npm run build

# === PRODUCTION STAGE ===
FROM nginx:1.26-alpine

# Copy built assets from builder
COPY --from=builder /build/dist /usr/share/nginx/html

# Copy optimized nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Create cache and temp directories with proper permissions
RUN mkdir -p /var/cache/nginx/client_temp /var/cache/nginx/proxy_temp && \
    chmod -R 755 /var/cache/nginx && \
    chown -R nginx:nginx /var/cache/nginx /usr/share/nginx/html

# Create healthcheck script
RUN printf '#!/bin/sh\ntest -f /usr/share/nginx/html/index.html && curl -f http://localhost/ > /dev/null 2>&1 || exit 1\n' > /healthcheck.sh && chmod +x /healthcheck.sh

# Health check
HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=5 \
  CMD /healthcheck.sh

EXPOSE 80

# Start nginx in foreground (runs as nginx by default in official image)
CMD ["nginx", "-g", "daemon off;"]
