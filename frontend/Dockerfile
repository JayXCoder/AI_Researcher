# Build from repo root: docker build -t frontend -f frontend/Dockerfile .
# Build Flutter web then serve with nginx.
# Pass API URL at build: docker build --build-arg API_URL=https://your-backend.run.app -t frontend -f frontend/Dockerfile .

FROM ghcr.io/cirruslabs/flutter:stable AS builder
WORKDIR /app

# Install Flutter and enable web
RUN flutter config --enable-web

ARG API_URL=http://localhost:8080
ENV API_URL=$API_URL

COPY frontend/ ./
RUN flutter pub get && flutter build web --dart-define=API_URL=$API_URL

FROM nginx:alpine
COPY --from=builder /app/build/web /usr/share/nginx/html
COPY --from=builder /app/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
