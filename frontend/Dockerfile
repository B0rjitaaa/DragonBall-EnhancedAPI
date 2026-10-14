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
RUN npm run build

FROM nginx:1.27-alpine AS prod
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
