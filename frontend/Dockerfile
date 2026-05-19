# Frontend RCA — build estático con Vite, servido con nginx
# Build: docker build -f frontend/Dockerfile -t rca-frontend .
# Run:   docker run -p 8080:80 -e BACKEND_HOST=host.docker.internal:8010 rca-frontend
#
# Variables:
#   VITE_API_URL (build-time)  → URL del backend. VACÍO = same-origin
#                                (nginx proxea /api → backend en este mismo
#                                container). Recomendado para producción.
#   BACKEND_HOST (runtime)     → host:puerto del backend (default "backend:8010").
#                                Se usa en el proxy_pass de nginx via envsubst.

# ── Stage 1: build de Vite ──
FROM node:20-alpine AS build
WORKDIR /app

COPY frontend/package*.json /app/
# Usamos `npm install` en vez de `npm ci` porque el lock puede quedar
# desincronizado cuando se agregan deps nuevas sin regenerarlo.
# --no-audit/--no-fund: builds mas rapidos en CI/Docker.
RUN npm install --no-audit --no-fund

COPY frontend/ /app/

ARG VITE_API_URL=""
ENV VITE_API_URL=${VITE_API_URL}

RUN npm run build

# ── Stage 2: nginx que sirve el bundle + proxy ──
FROM nginx:1.25-alpine

# Default sobreescribible en runtime
ENV BACKEND_HOST=backend:8010

# Plantilla con ${BACKEND_HOST} — nginx la procesa con envsubst al arrancar
# (la imagen oficial de nginx ya lo hace para todo lo que esté en /etc/nginx/templates)
RUN rm -f /etc/nginx/conf.d/default.conf
COPY frontend/nginx.conf.template /etc/nginx/templates/default.conf.template

COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://127.0.0.1/healthz || exit 1
