# ============================================================
# DocuSense — Frontend Dockerfile
# Serves static files via nginx with a reverse proxy to the
# backend API so the browser never hits a different origin.
# ============================================================

FROM nginx:1.27-alpine

# Copy static frontend files
COPY index.html  /usr/share/nginx/html/index.html
COPY styles.css  /usr/share/nginx/html/styles.css
COPY app.js      /usr/share/nginx/html/app.js

# Replace default nginx config with our custom one
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Healthcheck — curl is available in the alpine image
HEALTHCHECK --interval=30s --timeout=5s --start-period=3s --retries=3 \
  CMD wget -qO- http://localhost/ || exit 1

EXPOSE 80