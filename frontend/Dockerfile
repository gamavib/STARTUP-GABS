# Build stage for React app
FROM node:20-alpine as build
WORKDIR /app
COPY package*.json ./
RUN apk add --no-cache pnpm && pnpm install
COPY . .
RUN GENERATE_SOURCEMAP=false pnpm run build

# Production stage with Nginx
FROM nginx:stable-alpine
COPY --from=build /app/build /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
