# Phase 12: multi-stage build - a Node stage compiles the Vite production
# bundle, then only the static output ships in a lightweight nginx image.
# The Node toolchain (and node_modules) never reaches the final image, and
# no dev Vite server is exposed in production.

# ---- build stage ----
FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Baked into the built JS at build time (Vite inlines import.meta.env.* at
# build, not at container runtime) - must be a URL the *browser* can reach,
# not the Docker-internal "backend" service hostname. Defaults to the
# published host port from docker-compose.yml.
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

# ---- production stage ----
# nginxinc/nginx-unprivileged, not plain nginx: the official nginx image's
# master process runs as root (needed to bind port 80); this is the same
# nginx build pre-configured to run entirely as an unprivileged user on
# port 8080 instead, so the container has no root process at all - the
# backend already runs as "appuser" and this closes the one remaining
# root-process gap in the stack.
FROM nginxinc/nginx-unprivileged:1.27-alpine AS production

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080

# 127.0.0.1, not localhost: this Alpine image's wget resolves "localhost"
# to ::1 first, and nginx's "listen 8080;" only binds the IPv4 wildcard, so
# "localhost" here caused a false-negative "connection refused".
HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=5 \
    CMD wget --quiet --spider http://127.0.0.1:8080/ || exit 1
