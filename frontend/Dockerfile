# Frontend RCA — build estático con Vite, servido con nginx
# Build: docker build -t rca-frontend ./frontend
# Run:   docker run -p 5175:80 rca-frontend
# La URL del backend se inyecta en build-time con VITE_API_URL

# ── Stage 1: build ──
FROM node:20-alpine AS build
WORKDIR /app

# Layer de deps con cache
COPY frontend/package*.json /app/
RUN npm ci

# Código
COPY frontend/ /app/

# Variable build-time
ARG VITE_API_URL=http://localhost:8010
ENV VITE_API_URL=${VITE_API_URL}

RUN npm run build

# ── Stage 2: nginx que sirve el bundle ──
FROM nginx:1.25-alpine

# Config básica de nginx para SPA (fallback a index.html para client-side routing)
RUN printf 'server {\n\
    listen 80;\n\
    location / {\n\
        root /usr/share/nginx/html;\n\
        index index.html;\n\
        try_files $uri /index.html;\n\
    }\n\
    location = /healthz {\n\
        return 200 "ok";\n\
        add_header Content-Type text/plain;\n\
    }\n\
}\n' > /etc/nginx/conf.d/default.conf

COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://127.0.0.1/healthz || exit 1
