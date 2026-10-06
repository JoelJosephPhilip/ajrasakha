FROM node:22-alpine AS builder

RUN corepack enable && corepack prepare pnpm@10.4.1 --activate

WORKDIR /app

COPY frontend/package.json frontend/pnpm-lock.yaml ./
COPY frontend/scripts ./scripts

# Copy testers-dashboard/frontend source so the @testers-dashboard alias
# (../testers-dashboard/frontend/src, see vite.config.ts) resolves at build time.
COPY testers-dashboard/frontend /testers-dashboard/frontend

RUN pnpm install --frozen-lockfile

COPY frontend/ .

ARG VITE_ENABLE_MOCKS=false
ARG VITE_API_BASE_URL=/api
ARG VITE_FIREBASE_API_KEY
ARG VITE_FIREBASE_AUTH_DOMAIN
ARG VITE_FIREBASE_PROJECT_ID
ARG VITE_FIREBASE_STORAGE_BUCKET
ARG VITE_FIREBASE_MESSAGING_SENDER_ID
ARG VITE_FIREBASE_APP_ID
ARG VITE_FIREBASE_MEASUREMENT_ID
ARG VITE_SARVAM_API_KEY
ARG VITE_VAPID_PUBLIC_KEY

ENV VITE_ENABLE_MOCKS=$VITE_ENABLE_MOCKS
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_FIREBASE_API_KEY=$VITE_FIREBASE_API_KEY
ENV VITE_FIREBASE_AUTH_DOMAIN=$VITE_FIREBASE_AUTH_DOMAIN
ENV VITE_FIREBASE_PROJECT_ID=$VITE_FIREBASE_PROJECT_ID
ENV VITE_FIREBASE_STORAGE_BUCKET=$VITE_FIREBASE_STORAGE_BUCKET
ENV VITE_FIREBASE_MESSAGING_SENDER_ID=$VITE_FIREBASE_MESSAGING_SENDER_ID
ENV VITE_FIREBASE_APP_ID=$VITE_FIREBASE_APP_ID
ENV VITE_FIREBASE_MEASUREMENT_ID=$VITE_FIREBASE_MEASUREMENT_ID
ENV VITE_SARVAM_API_KEY=$VITE_SARVAM_API_KEY
ENV VITE_VAPID_PUBLIC_KEY=$VITE_VAPID_PUBLIC_KEY

# vite build only (pnpm build also runs tsc, which can fail CI/Docker)
RUN pnpm exec vite build

FROM nginx:1.27-alpine

# APP_PORT env at runtime is substituted into the proxy URL (default 4000)
ENV APP_PORT=4000
COPY frontend/nginx.conf.template /etc/nginx/templates/default.conf.template
COPY frontend/docker/runtime-config.js.template /etc/reviewer/runtime-config.js.template
COPY frontend/docker/10-generate-runtime-config.sh /docker-entrypoint.d/10-generate-runtime-config.sh
RUN chmod +x /docker-entrypoint.d/10-generate-runtime-config.sh
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80
