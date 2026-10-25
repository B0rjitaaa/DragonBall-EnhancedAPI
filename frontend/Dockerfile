# --- Desarrollo: servidor de Vite con recarga en caliente (docker-compose.yml) ---
FROM node:22-alpine AS dev

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev"]

# --- Producción: build estático + Nginx (docker-compose.prod.yml) ---
FROM dev AS build
ARG VITE_HTTPS_PORT=""
ENV VITE_HTTPS_PORT=$VITE_HTTPS_PORT
RUN npm run build

FROM nginx:1.27-alpine AS prod
COPY nginx/app.conf /etc/nginx/snippets/app.conf
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
# HTTPS (necesario para la cámara del móvil): solo si hay certificados en ./certs.
COPY nginx/https.conf /etc/nginx/https.conf.available
COPY --chmod=755 nginx/40-https.sh /docker-entrypoint.d/40-https.sh
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80 443
